// Star Seeker — device orientation + compass fusion.
//
// Outputs a target (ra, dec) reflecting where the phone is pointing,
// computed from:
//   1. Gravity (low-pass filtered accelerometer) -> tilt matrix.
//   2. Webkit compass heading fused with gyro (Mahony-style 1-D
//      complementary filter) -> smooth, drift-corrected yaw.
//   3. Observer latitude + JS-computed LST -> alt/az -> ra/dec.
//
// Permissions handled per iOS 13+ rules (requestPermission on gesture).

// Reference FOV for adaptive filtering (see debug block below).
const REF_FOV_DEG = 40;

const state = {
    // Observer. Updated by Blazor on init/change.
    latRad: 0,
    lonDeg: 0,

    // Raw sensor inputs.
    rawCompassDeg: null,     // iOS webkitCompassHeading (deg CW from true N)
    rawAlpha: null,          // deviceorientation alpha (deg)
    rawBeta: null,           // deg
    rawGamma: null,          // deg
    gyroZ: 0,                // rotationRate.alpha, deg/s, earth-vertical component
    gyroMag: 0,              // total rotation rate magnitude, deg/s, for motion detection
    gravX: 0, gravY: 0, gravZ: 9.8,  // accelerationIncludingGravity, m/s²

    // Filter state.
    filteredGrav: null,      // smoothed gravity vector [x, y, z]
    fusedHeadingRad: null,   // Mahony-fused heading, radians CW from N
    alignOffsetRad: 0,       // user-calibration offset added to fused heading

    // Last event timestamp for gyro integration.
    lastMotionMs: null,

    // Output.
    lookRa: null,
    lookDec: null,
    lookAlt: null,
    lookAz: null,
    // Full phone-anchored basis in world frame. Avoids pole-singularity
    // spin that the celestial-north-anchored basis has near Dec ~90°.
    lookForward: null,
    lookRight: null,
    lookUp: null,

    // Flags.
    sensorActive: false,
    debugLog: false,

    // Current camera FOV in radians, pushed by starseeker.js.
    fovRad: REF_FOV_DEG * Math.PI / 180,
};

// Debug knobs — mutate from Safari/Chrome console to retune live.
// Filter strengths are adaptive to FOV: zoomed in, sensor jitter maps
// to more pixel jitter, so we filter harder. The *Ref values are the
// reference values at REF_FOV_DEG (declared near file top); they scale
// as FOV changes.
const debug = {
    adaptive: true,
    gravityAlphaRef: 0.25,
    headingAlphaBaseRef: 0.92,
    headingAlphaNearZenithRef: 0.985,
    // Motion-gated alpha: when gyro magnitude is low, use still-alpha
    // (heavy filter). When high, use moving-alpha (responsive).
    // Jitter on a held-still phone is typically < ~3 deg/s; intentional
    // panning is tens of deg/s.
    motionStillDegSec: 3,        // below this = still (heavy filter)
    motionMovingDegSec: 25,      // above this = full responsive
    gravityAlphaMoving: 0.40,    // responsive gravity when moving
    headingAlphaMoving: 0.88,    // responsive heading when moving
    yawSign: 1,
    yawOffsetDeg: 0,
    betaSign: -1,   // Field-verified: "glass-up convention" requires negative beta.
    gammaSign: 1,
};

window._starSeekerDebug = { state, debug };

// Public API ---------------------------------------------------------------

export async function requestPermission() {
    try {
        if (typeof DeviceOrientationEvent !== "undefined" &&
            typeof DeviceOrientationEvent.requestPermission === "function") {
            const r1 = await DeviceOrientationEvent.requestPermission();
            if (r1 !== "granted") return false;
        }
        if (typeof DeviceMotionEvent !== "undefined" &&
            typeof DeviceMotionEvent.requestPermission === "function") {
            const r2 = await DeviceMotionEvent.requestPermission();
            if (r2 !== "granted") return false;
        }
        return true;
    } catch {
        return false;
    }
}

export function startSensors() {
    if (state.sensorActive) return;
    window.addEventListener("deviceorientation", onOrientation, true);
    window.addEventListener("deviceorientationabsolute", onOrientation, true);
    window.addEventListener("devicemotion", onMotion, true);
    state.sensorActive = true;
}

export function stopSensors() {
    window.removeEventListener("deviceorientation", onOrientation, true);
    window.removeEventListener("deviceorientationabsolute", onOrientation, true);
    window.removeEventListener("devicemotion", onMotion, true);
    state.sensorActive = false;
    // Reset filter state so next start begins fresh.
    state.filteredGrav = null;
    state.fusedHeadingRad = null;
    state.lastMotionMs = null;
}

export function setObserverLocation(latDeg, lonDeg) {
    state.latRad = latDeg * Math.PI / 180;
    state.lonDeg = lonDeg;
}

// Starseeker pushes current camera FOV so the adaptive filter scales.
export function setFov(fovRad) {
    state.fovRad = fovRad;
}

// User alignment offset (radians). Additive to the fused heading.
// Replace (not accumulate) — caller may load from persistence or
// compute fresh from align-on-star.
export function setAlignOffset(offsetRad) {
    state.alignOffsetRad = offsetRad;
}

export function getAlignOffset() {
    return state.alignOffsetRad;
}

// Current sensor-derived alt/az BEFORE the offset is applied — needed
// by the align flow to compute a new offset relative to where the user
// points right now.
export function getCurrentLookAz() {
    return state.lookAz;
}

// Convert RA/Dec (radians) to local alt/az using the stored observer
// latitude and the current LST. Used by Free mode to synthesize a
// telemetry readout for the panned camera center.
export function computeAltAzFromRaDec(raRad, decRad) {
    const lstRad = localSiderealTime(new Date(), state.lonDeg);
    return raDecToAltAz(raRad, decRad, state.latRad, lstRad);
}

// Current local sidereal time in radians (0 .. 2π). Used by the chart
// renderer to position the local-meridian overlay (RA = LST is the
// great circle currently transiting overhead).
export function getCurrentLstRad() {
    return localSiderealTime(new Date(), state.lonDeg);
}

// Observer latitude in radians. Used by the chart renderer to plot the
// zenith marker at (RA=LST, Dec=lat).
export function getCurrentLatRad() {
    return state.latRad;
}

// True iff at least one valid orientation event has been received since
// startSensors. Used by the host to decide whether to keep LIVE mode
// engaged (and whether to show the ALIGN button) — desktop browsers and
// devices with no motion sensors don't fire deviceorientation, and
// without a probe the chart would silently sit in LIVE mode with no
// data and no UX feedback.
export function hasReceivedSensorData() {
    return state.rawAlpha !== null || state.rawBeta !== null || state.rawGamma !== null;
}

// Returns { ra, dec, alt, az } in radians, or null if sensors haven't produced
// a usable fused pose yet.
export function getCurrentLook() {
    if (state.lookRa === null) return null;
    return {
        ra: state.lookRa, dec: state.lookDec,
        alt: state.lookAlt, az: state.lookAz,
        basis: {
            forward: state.lookForward,
            right: state.lookRight,
            up: state.lookUp,
        },
    };
}

// Internal -----------------------------------------------------------------

function onOrientation(e) {
    if (e.alpha == null || e.beta == null || e.gamma == null) return;
    state.rawAlpha = e.alpha;
    state.rawBeta = e.beta;
    state.rawGamma = e.gamma;
    if ("webkitCompassHeading" in e && e.webkitCompassHeading != null) {
        // iOS Safari: webkitCompassHeading is deg CW from true North.
        state.rawCompassDeg = e.webkitCompassHeading;
    } else if (e.absolute === true || e.type === "deviceorientationabsolute") {
        // Android (Chrome / MAUI WebView): W3C alpha is deg CCW from
        // north when looking down at the screen — invert to match the
        // CW-from-north convention the rest of the file expects. Without
        // this, recompute() early-returns on rawCompassDeg=null and the
        // chart never tracks phone yaw.
        state.rawCompassDeg = (360 - e.alpha) % 360;
    }
    recompute();
}

function onMotion(e) {
    const g = e.accelerationIncludingGravity;
    if (g && g.x != null && g.y != null && g.z != null) {
        state.gravX = g.x; state.gravY = g.y; state.gravZ = g.z;
    }
    const r = e.rotationRate;
    if (r && r.alpha != null) {
        state.gyroZ = r.alpha;  // deg/s around device z (screen-normal)
        const rb = r.beta ?? 0, rg = r.gamma ?? 0;
        state.gyroMag = Math.hypot(r.alpha, rb, rg);  // total deg/s
    }
    // Integrate gyro into fused heading between compass samples.
    const now = performance.now();
    if (state.lastMotionMs !== null && state.fusedHeadingRad !== null) {
        const dt = (now - state.lastMotionMs) / 1000;
        if (dt > 0 && dt < 0.5) {
            const gyroZRad = state.gyroZ * Math.PI / 180 * debug.yawSign;
            state.fusedHeadingRad += gyroZRad * dt;
        }
    }
    state.lastMotionMs = now;
}

function recompute() {
    // Adaptive filter strengths: scale the reference values by the ratio
    // of current FOV to reference FOV. Zoomed in (small FOV) -> smaller
    // gravityAlpha (slower tilt response) and larger headingAlpha (more
    // gyro-dominant heading, less compass jitter). Clamped to avoid
    // blowing up at extreme zooms.
    let gravAlpha = debug.gravityAlphaRef;
    let headAlphaBase = debug.headingAlphaBaseRef;
    let headAlphaNearZenith = debug.headingAlphaNearZenithRef;
    if (debug.adaptive) {
        const fovDeg = state.fovRad * 180 / Math.PI;
        // Super-linear in FOV so narrow zooms filter much harder than
        // proportional scaling would give.
        const scale = Math.pow(fovDeg / REF_FOV_DEG, 1.5);
        gravAlpha = Math.max(0.005, Math.min(0.6, debug.gravityAlphaRef * scale));
        headAlphaBase       = Math.max(0.80, Math.min(0.998, 1 - (1 - debug.headingAlphaBaseRef) * scale));
        headAlphaNearZenith = Math.max(0.90, Math.min(0.9995, 1 - (1 - debug.headingAlphaNearZenithRef) * scale));

        // Motion gating: blend toward responsive values when gyro says
        // the phone is actually being moved. Kills jitter at rest
        // without slowing intentional pans.
        const still = debug.motionStillDegSec;
        const moving = debug.motionMovingDegSec;
        const motion = Math.max(0, Math.min(1,
            (state.gyroMag - still) / Math.max(0.001, moving - still)));
        gravAlpha      = gravAlpha      * (1 - motion) + debug.gravityAlphaMoving * motion;
        headAlphaBase  = headAlphaBase  * (1 - motion) + debug.headingAlphaMoving * motion;
        headAlphaNearZenith = headAlphaNearZenith * (1 - motion) + debug.headingAlphaMoving * motion;
    }

    // --- Step 1: gravity LPF in device frame.
    const raw = [state.gravX, state.gravY, state.gravZ];
    if (!state.filteredGrav) {
        state.filteredGrav = raw.slice();
    } else {
        for (let i = 0; i < 3; i++) {
            state.filteredGrav[i] = gravAlpha * raw[i] + (1 - gravAlpha) * state.filteredGrav[i];
        }
    }
    const gm = Math.hypot(...state.filteredGrav) || 1;
    const gn = state.filteredGrav.map(v => v / gm);

    // --- Step 2: Mahony-style 1-D fusion of compass heading with gyro.
    if (state.rawCompassDeg == null) return;
    const compassRad = state.rawCompassDeg * Math.PI / 180 + debug.yawOffsetDeg * Math.PI / 180;

    if (state.fusedHeadingRad === null) {
        state.fusedHeadingRad = compassRad;
    } else {
        // Alpha leans further toward gyro near zenith where Safari's
        // internal tilt-comp for webkitCompassHeading gets flaky.
        const pitch = Math.asin(-gn[1]);  // rough pitch from +Y gravity projection
        const nearZenith = Math.abs(pitch) > Math.PI / 3;
        const alpha = nearZenith ? headAlphaNearZenith : headAlphaBase;

        // Shortest-path angular difference between gyro-integrated and compass.
        let diff = compassRad - state.fusedHeadingRad;
        const TWO_PI = 2 * Math.PI;
        while (diff > Math.PI) diff -= TWO_PI;
        while (diff < -Math.PI) diff += TWO_PI;
        // Weighted pull toward compass. alpha = weight on gyro-integrated path.
        state.fusedHeadingRad += (1 - alpha) * diff;
    }

    // --- Step 3: orient the look vector in world frame.
    // Convention per user: "look" is the top edge of the phone.
    //   Phone flat on table, screen up  -> top edge is horizontal -> alt = 0°
    //   Phone vertical, screen facing user, top at zenith -> alt = +90°
    // Matrix composition is polar.js-style: R = transpose(Ry · Rx · Rz).
    // User-calibration offset is applied here to the heading angle.
    const a = state.fusedHeadingRad + state.alignOffsetRad;
    const b = state.rawBeta * Math.PI / 180 * debug.betaSign;
    const g = state.rawGamma * Math.PI / 180 * debug.gammaSign;
    const ca = Math.cos(a), sa = Math.sin(a);
    const cb = Math.cos(b), sb = Math.sin(b);
    const cg = Math.cos(g), sg = Math.sin(g);
    const rz = [[ca, -sa, 0], [sa, ca, 0], [0, 0, 1]];
    const rx = [[1, 0, 0], [0, cb, -sb], [0, sb, cb]];
    const ry = [[cg, 0, sg], [0, 1, 0], [-sg, 0, cg]];
    const rt = transpose(matMul(ry, matMul(rx, rz)));
    const w = matVec(rt, [0, 1, 0]);           // top edge (forward)
    const wRight = matVec(rt, [1, 0, 0]);      // phone's right edge in world
    const wUp = matVec(rt, [0, 0, 1]);         // phone's screen-normal in world

    // World frame (polar.js convention): +x = east, +y = north, +z = up.
    const alt = Math.asin(Math.max(-1, Math.min(1, w[2])));
    let az = Math.atan2(w[0], w[1]);  // clockwise from north (x=east, y=north)
    if (az < 0) az += 2 * Math.PI;

    // --- Step 4: alt/az -> ra/dec at observer.
    const lstRad = localSiderealTime(new Date(), state.lonDeg);
    const { ra, dec } = altAzToRaDec(alt, az, state.latRad, lstRad);
    state.lookRa = ra;
    state.lookDec = dec;
    state.lookAlt = alt;
    state.lookAz = az;
    // Transform phone-derived basis vectors from local ENU frame into
    // the celestial equatorial frame the catalog uses. Without this, the
    // chart centers on the ENU look direction, not the sky point it
    // actually corresponds to.
    state.lookForward = enuToCelestial(w,       state.latRad, lstRad);
    state.lookRight   = enuToCelestial(wRight,  state.latRad, lstRad);
    state.lookUp      = enuToCelestial(wUp,     state.latRad, lstRad);

    if (state.debugLog) {
        console.log(`[seeker] alt=${(alt*180/Math.PI).toFixed(1)} az=${(az*180/Math.PI).toFixed(1)} -> ra=${(ra*12/Math.PI).toFixed(2)}h dec=${(dec*180/Math.PI).toFixed(1)}`);
    }
}

// ENU vector (east, north, up) -> celestial equatorial unit vector,
// given observer latitude and local sidereal time (both radians).
// Columns are the celestial coordinates of the ENU unit axes.
function enuToCelestial(v, latRad, lstRad) {
    const cphi = Math.cos(latRad), sphi = Math.sin(latRad);
    const clst = Math.cos(lstRad), slst = Math.sin(lstRad);
    return [
        v[0] * (-slst)     + v[1] * (-sphi * clst) + v[2] * (cphi * clst),
        v[0] * ( clst)     + v[1] * (-sphi * slst) + v[2] * (cphi * slst),
        v[0] * 0           + v[1] * ( cphi)        + v[2] * ( sphi),
    ];
}

// ra/dec -> alt/az. Inverse of altAzToRaDec.
function raDecToAltAz(raRad, decRad, latRad, lstRad) {
    const H = lstRad - raRad;  // hour angle
    const sd = Math.sin(decRad), cd = Math.cos(decRad);
    const sp = Math.sin(latRad), cp = Math.cos(latRad);
    const sinAlt = sd * sp + cd * cp * Math.cos(H);
    const alt = Math.asin(Math.max(-1, Math.min(1, sinAlt)));
    const y = -cd * Math.sin(H);
    const x = sd * cp - cd * sp * Math.cos(H);
    let az = Math.atan2(y, x);
    if (az < 0) az += 2 * Math.PI;
    return { alt, az };
}

// alt/az -> ra/dec. lat/lst in radians. az = CW from north.
function altAzToRaDec(alt, az, latRad, lstRad) {
    const sa = Math.sin(alt), ca = Math.cos(alt);
    const sp = Math.sin(latRad), cp = Math.cos(latRad);
    const sinDec = sa * sp + ca * cp * Math.cos(az);
    const dec = Math.asin(Math.max(-1, Math.min(1, sinDec)));
    const y = -ca * Math.sin(az);
    const x = sa * cp - ca * sp * Math.cos(az);
    const H = Math.atan2(y, x);
    let ra = lstRad - H;
    const TWO_PI = 2 * Math.PI;
    ra = ((ra % TWO_PI) + TWO_PI) % TWO_PI;
    return { ra, dec };
}

function localSiderealTime(date, lonDeg) {
    // Greenwich mean sidereal time approximation, good to a few arcsec.
    const JD = date.getTime() / 86400000 + 2440587.5;
    const D = JD - 2451545.0;
    let GMSThours = 18.697374558 + 24.06570982441908 * D;
    GMSThours = ((GMSThours % 24) + 24) % 24;
    let LSThours = GMSThours + lonDeg / 15;
    LSThours = ((LSThours % 24) + 24) % 24;
    return LSThours * Math.PI / 12;
}

function matMul(a, b) {
    const r = [[0, 0, 0], [0, 0, 0], [0, 0, 0]];
    for (let i = 0; i < 3; i++)
        for (let j = 0; j < 3; j++)
            for (let k = 0; k < 3; k++)
                r[i][j] += a[i][k] * b[k][j];
    return r;
}
function transpose(m) {
    return [[m[0][0], m[1][0], m[2][0]], [m[0][1], m[1][1], m[2][1]], [m[0][2], m[1][2], m[2][2]]];
}
function matVec(m, v) {
    return [
        m[0][0] * v[0] + m[0][1] * v[1] + m[0][2] * v[2],
        m[1][0] * v[0] + m[1][1] * v[1] + m[1][2] * v[2],
        m[2][0] * v[0] + m[2][1] * v[1] + m[2][2] * v[2],
    ];
}
