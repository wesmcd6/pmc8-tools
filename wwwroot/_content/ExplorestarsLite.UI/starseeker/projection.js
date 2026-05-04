// Star Seeker — stereographic projection math.
// Pure functions, no DOM. Screen units are CSS pixels.

export function raDecToVec(ra, dec) {
    const cd = Math.cos(dec);
    return [cd * Math.cos(ra), cd * Math.sin(ra), Math.sin(dec)];
}

// Equatorial precession via Lieske / Meeus rotation matrices (vector form).
// Inputs/outputs in radians. The earlier in-plane trig form had tan(dec)
// singularities at the pole — the chart uses these helpers for the local
// meridian, zenith marker, RA/Dec grid samples, and the bottom-left
// readout, all of which can land arbitrarily close to or exactly at a
// pole (mount at polar home in particular). The rotation form is
// singularity-free at any latitude and costs only a few extra trig calls
// per call. Accuracy is precession-only (no nutation/aberration); for
// chart display that's plenty — the host's full Lieske handles the mount
// pip's J2000 conversion.
const _J2000_MS = Date.UTC(2000, 0, 1, 12, 0, 0);

function _lieskeAnglesRad(utcDate) {
    // Centuries since J2000.0.
    const T = (utcDate.getTime() - _J2000_MS) / (365.25 * 86400000) / 100;
    const D2R = Math.PI / 180;
    return {
        zeta:  (0.6406161 + (0.0000839 + 0.0000050 * T) * T) * T * D2R,
        z:     (0.6406161 + (0.0003041 + 0.0000051 * T) * T) * T * D2R,
        theta: (0.5567530 - (0.0001185 + 0.0000116 * T) * T) * T * D2R,
    };
}

// Standard rotation primitives. R_z about the celestial pole; R_y about
// the equinox y-axis. Both are orthonormal and stable everywhere.
function _rotZ(v, ang) {
    const c = Math.cos(ang), s = Math.sin(ang);
    return [c * v[0] - s * v[1], s * v[0] + c * v[1], v[2]];
}
function _rotY(v, ang) {
    const c = Math.cos(ang), s = Math.sin(ang);
    return [c * v[0] + s * v[2], v[1], -s * v[0] + c * v[2]];
}

// Convert ra/dec → vector → apply rotation → vector → ra/dec. atan2
// resolves at the pole to whatever the rotation moved it toward;
// asin clamped for float safety.
function _vecRaDec(raRad, decRad) {
    const cd = Math.cos(decRad);
    return [cd * Math.cos(raRad), cd * Math.sin(raRad), Math.sin(decRad)];
}
function _vecToRaDec(v) {
    let ra = Math.atan2(v[1], v[0]);
    if (ra < 0) ra += 2 * Math.PI;
    const dec = Math.asin(Math.max(-1, Math.min(1, v[2])));
    return { ra, dec };
}

// Forward: J2000 → mean of date. Active vector rotation form:
// P = R_z(z) · R_y(-θ) · R_z(ζ). Verified against Meeus AA §21
// (α_new = z + atan2(cosδ·sin(α+ζ), cosθ·cosδ·cos(α+ζ) − sinθ·sinδ)):
// at T = 0.26 century, J2000 (0,0) → mean (+0.333°, +0.145°). The
// passive-axes form P = R_z(-z)·R_y(θ)·R_z(-ζ) (typical textbook
// statement) is the inverse of this — applying it to a vector here
// would precess in the wrong direction.
export function j2000ToJNow(raJ2000, decJ2000, utcDate) {
    const a = _lieskeAnglesRad(utcDate);
    let v = _vecRaDec(raJ2000, decJ2000);
    v = _rotZ(v, a.zeta);
    v = _rotY(v, -a.theta);
    v = _rotZ(v, a.z);
    return _vecToRaDec(v);
}

// Inverse: JNow mean of date → J2000. P^T applied as active vector
// rotation: R_z(-ζ) · R_y(θ) · R_z(-z) (the inverse of the active
// forward sequence above).
export function jNowToJ2000(raJNow, decJNow, utcDate) {
    const a = _lieskeAnglesRad(utcDate);
    let v = _vecRaDec(raJNow, decJNow);
    v = _rotZ(v, -a.z);
    v = _rotY(v, a.theta);
    v = _rotZ(v, -a.zeta);
    return _vecToRaDec(v);
}

// Vector-form variants — same rotations as above but applied to and
// returning a 3D unit vector. Used for the LIVE-mode basis: the
// orientation pipeline produces ENU→celestial vectors in JNow frame
// (because LST is JNow-relative), but the chart's catalog and mount-
// pip are J2000. Without converting, projecting J2000 vectors through
// the JNow basis offsets everything by ~26 years of precession (~0.4°)
// — visible as the mount pip drifting off the Telrad center even when
// the OTA is centered on the target.
export function j2000VecToJNowVec(v, utcDate) {
    const a = _lieskeAnglesRad(utcDate);
    let r = _rotZ(v, a.zeta);
    r = _rotY(r, -a.theta);
    r = _rotZ(r, a.z);
    return r;
}
export function jNowVecToJ2000Vec(v, utcDate) {
    const a = _lieskeAnglesRad(utcDate);
    let r = _rotZ(v, -a.z);
    r = _rotY(r, a.theta);
    r = _rotZ(r, -a.zeta);
    return r;
}

// Full apparent-place transform: J2000 → JNow with precession +
// nutation + annual aberration. Matches C# CoordinateService's
// PrecessJ2000ToDate (Meeus AA Ch. 21–23) so the chart's lower-left
// readout agrees with the rest of the app's JNow displays. Without the
// nutation/aberration terms there's a ~25" residual that's visible
// against the Target page's RA/Dec field.
//
// Used only for human-readable readouts; chart geometry (meridian,
// zenith, grids, mount-pip transform) keeps the lighter precession-
// only path because the geometry is in J2000 internally and the few
// JNow-bound elements there are well below the 25" tolerance for
// pixel-level chart drawing.
export function j2000ToJNowApparent(raJ2000, decJ2000, utcDate) {
    // T in centuries since J2000.0.
    const T = (utcDate.getTime() - _J2000_MS) / (365.25 * 86400000) / 100;
    const D2R = Math.PI / 180;

    // === 1. Precession (Lieske / Meeus eq. 21.2). Mirrors C#. ===
    const zetaA  = (0.6406161 + (0.0000839 + 0.0000050 * T) * T) * T * D2R;
    const zA     = (0.6406161 + (0.0003041 + 0.0000051 * T) * T) * T * D2R;
    const thetaA = (0.5567530 - (0.0001185 + 0.0000116 * T) * T) * T * D2R;

    const cosD0 = Math.cos(decJ2000), sinD0 = Math.sin(decJ2000);
    const cosTheta = Math.cos(thetaA), sinTheta = Math.sin(thetaA);
    const sinRaZeta = Math.sin(raJ2000 + zetaA);
    const cosRaZeta = Math.cos(raJ2000 + zetaA);

    const A = cosD0 * sinRaZeta;
    const B = cosTheta * cosD0 * cosRaZeta - sinTheta * sinD0;
    const C = sinTheta * cosD0 * cosRaZeta + cosTheta * sinD0;

    let raMean  = Math.atan2(A, B) + zA;
    const decMean = Math.asin(Math.max(-1, Math.min(1, C)));

    // Polar guard: nutation/aberration formulas have tan(dec) and
    // 1/cos(dec) that blow up at |dec|=90°. Skip them at the pole;
    // sub-arcminute corrections aren't visible on a chart anyway.
    if (Math.abs(decMean) > 89.5 * D2R) {
        const TWO_PI = 2 * Math.PI;
        raMean = ((raMean % TWO_PI) + TWO_PI) % TWO_PI;
        return { ra: raMean, dec: decMean };
    }

    // === 2. Nutation (Meeus Ch. 22, leading 5 terms). ===
    const D  = (297.85036 + (445267.111480 + (-0.0019142 + T / 189474) * T) * T) * D2R;
    const Ms = (357.52772 + (35999.050340 + (-0.0001603 - T / 300000) * T) * T) * D2R;
    const Mm = (134.96298 + (477198.867398 + (0.0086972 + T / 56250) * T) * T) * D2R;
    const F  = (93.27191 + (483202.017538 + (-0.0036825 + T / 327270) * T) * T) * D2R;
    const Om = (125.04452 + (-1934.136261 + (0.0020708 + T / 450000) * T) * T) * D2R;

    // Nutation in longitude / obliquity (arcseconds).
    const dPsi = -17.20 * Math.sin(Om)
                 - 1.32 * Math.sin(2 * (F - D + Om))
                 - 0.23 * Math.sin(2 * (F + Om))
                 + 0.21 * Math.sin(2 * Om)
                 - 0.10 * Math.sin(Ms);
    const dEps =  9.20 * Math.cos(Om)
                 + 0.57 * Math.cos(2 * (F - D + Om))
                 + 0.10 * Math.cos(2 * (F + Om))
                 - 0.09 * Math.cos(2 * Om);

    const eps0 = 23.439291111 + (-0.013004167 + (-0.00000016389 + 0.000000504 * T) * T) * T;
    const eps  = (eps0 + dEps / 3600.0) * D2R;

    const tanDec = Math.tan(decMean);
    const sinRaM = Math.sin(raMean), cosRaM = Math.cos(raMean);

    // Convert dPsi/dEps from arcsec → radians.
    const dPsiRad = dPsi / 3600.0 * D2R;
    const dEpsRad = dEps / 3600.0 * D2R;

    const dRaNut  = (Math.cos(eps) + Math.sin(eps) * sinRaM * tanDec) * dPsiRad
                   - cosRaM * tanDec * dEpsRad;
    const dDecNut = Math.sin(eps) * cosRaM * dPsiRad + sinRaM * dEpsRad;

    const raNut  = raMean + dRaNut;
    const decNut = decMean + dDecNut;

    // === 3. Annual aberration (Meeus Ch. 23). ===
    const L0 = 280.46646 + (36000.76983 + 0.0003032 * T) * T;
    const Msun = (357.52911 + (35999.05029 - 0.0001537 * T) * T) * D2R;
    const Csun = (1.914602 - (0.004817 + 0.000014 * T) * T) * Math.sin(Msun)
                 + (0.019993 - 0.000101 * T) * Math.sin(2 * Msun)
                 + 0.000289 * Math.sin(3 * Msun);
    const sunLon = ((L0 + Csun) % 360.0) * D2R;
    const e = 0.016708634 + (-0.000042037 - 0.0000001267 * T) * T;
    const piLon = (102.93735 + (1.7195366 + (0.00045688 + 0.000000028 * T) * T) * T) * D2R;

    const KAPPA_RAD = 20.49552 / 3600.0 * D2R;   // const of aberration → radians
    const cosDecN = Math.cos(decNut),  sinDecN = Math.sin(decNut);
    const sinRaN  = Math.sin(raNut),   cosRaN  = Math.cos(raNut);
    const cosEps  = Math.cos(eps),     sinEps  = Math.sin(eps);

    const dRaAb = -KAPPA_RAD *
                  (cosRaN * Math.cos(sunLon) * cosEps + sinRaN * Math.sin(sunLon)) / cosDecN
                + e * KAPPA_RAD *
                  (cosRaN * Math.cos(piLon) * cosEps + sinRaN * Math.sin(piLon)) / cosDecN;
    const tanEps = Math.tan(eps);
    const dDecAb = -KAPPA_RAD *
                   (Math.cos(sunLon) * cosEps * (tanEps * cosDecN - sinRaN * sinDecN)
                    + cosRaN * sinDecN * Math.sin(sunLon))
                 + e * KAPPA_RAD *
                   (Math.cos(piLon) * cosEps * (tanEps * cosDecN - sinRaN * sinDecN)
                    + cosRaN * sinDecN * Math.sin(piLon));

    let raApp = raNut + dRaAb;
    const decApp = decNut + dDecAb;
    const TWO_PI = 2 * Math.PI;
    raApp = ((raApp % TWO_PI) + TWO_PI) % TWO_PI;
    return { ra: raApp, dec: decApp };
}

// Camera basis: +Z = forward (look direction), +Y = up toward celestial north,
// +X = right (east). Near the poles we fall back to an arbitrary east AND
// re-orthogonalize it against forward — without that step, "right" was a
// unit vector but not perpendicular to forward (forward·right ≈ cos(δ)·cos(α)
// at the pole), so a point lying exactly along the look direction projected
// a few pixels off canvas center. Visible as a Telrad/mount-marker offset
// when the chart is centered on Polaris or the SCP.
export function buildBasis(lookRa, lookDec) {
    const forward = raDecToVec(lookRa, lookDec);
    const worldUp = [0, 0, 1];
    let right;
    if (Math.abs(dot(forward, worldUp)) > 0.9999) {
        // Gram–Schmidt: project [1,0,0] onto the plane perpendicular to forward.
        const seed = [1, 0, 0];
        const d = dot(seed, forward);
        right = normalize([
            seed[0] - d * forward[0],
            seed[1] - d * forward[1],
            seed[2] - d * forward[2],
        ]);
    } else {
        right = normalize(cross(worldUp, forward));
    }
    const up = cross(forward, right);
    return { forward, right, up };
}

// Alt-Az basis: +Z = forward (J2000 vector at observer's chosen alt/az),
// +Y = chart-up = zenith (J2000 vector at observer's zenith), +X = right
// (toward az+90° in the local horizon plane). Same Gram-Schmidt fallback
// for the zenith-look singularity. Both `forward` and `zenith` are J2000
// unit vectors — caller does the alt/az → ENU → JNow → J2000 conversion
// once per frame via altAzToJ2000Vec().
export function buildBasisAltaz(forward, zenith) {
    let right;
    if (Math.abs(dot(forward, zenith)) > 0.9999) {
        const seed = [1, 0, 0];
        const d = dot(seed, forward);
        right = normalize([
            seed[0] - d * forward[0],
            seed[1] - d * forward[1],
            seed[2] - d * forward[2],
        ]);
    } else {
        // Note opposite-sign cross compared to equatorial: in altaz the
        // chart's "right" is east of forward (az + 90°), so right =
        // cross(forward, zenith). In equatorial we use cross(NCP, forward)
        // — same hand, different reference axis. Don't fold the two.
        right = normalize(cross(forward, zenith));
    }
    const up = cross(right, forward);
    return { forward, right, up };
}

// Convert local (alt, az) at observer to a J2000 unit vector. Used to
// build the altaz basis's `forward` and `zenith` vectors. az is CW from
// north in the standard convention. The chain is ENU → JNow celestial
// (via observer lat + LST) → J2000 (via low-precision precession), so
// the resulting vector lives in the same frame as the catalog.
export function altAzToJ2000Vec(altRad, azRad, latRad, lstRad, utcDate) {
    const cAlt = Math.cos(altRad), sAlt = Math.sin(altRad);
    const cAz = Math.cos(azRad), sAz = Math.sin(azRad);
    // ENU convention: x=east, y=north, z=up. az measured CW from north.
    const enu = [sAz * cAlt, cAz * cAlt, sAlt];

    // ENU → JNow celestial (rotation by lat + LST).
    const cphi = Math.cos(latRad), sphi = Math.sin(latRad);
    const clst = Math.cos(lstRad), slst = Math.sin(lstRad);
    const jnow = [
        enu[0] * (-slst) + enu[1] * (-sphi * clst) + enu[2] * (cphi * clst),
        enu[0] * ( clst) + enu[1] * (-sphi * slst) + enu[2] * (cphi * slst),
        enu[0] * 0       + enu[1] * ( cphi)        + enu[2] * ( sphi),
    ];

    // Extract JNow ra/dec, precess to J2000, rebuild unit vector.
    const ra = Math.atan2(jnow[1], jnow[0]);
    const dec = Math.asin(Math.max(-1, Math.min(1, jnow[2])));
    const j2k = jNowToJ2000(ra, dec, utcDate);
    return raDecToVec(j2k.ra, j2k.dec);
}

// Inverse: J2000 vector → (alt, az) at observer. Used by tap-handling
// in altaz mode and for telemetry display when the canonical camera
// pair is alt/az. utcDate is "now" for the precession step.
export function j2000VecToAltAz(vec, latRad, lstRad, utcDate) {
    // Vector → J2000 (ra, dec) → JNow (ra, dec) → JNow celestial vector
    // → ENU (rotation inverse) → alt/az.
    const ra = Math.atan2(vec[1], vec[0]);
    const dec = Math.asin(Math.max(-1, Math.min(1, vec[2])));
    const jn = j2000ToJNow(ra, dec, utcDate);
    const cdJN = Math.cos(jn.dec);
    const jnow = [cdJN * Math.cos(jn.ra), cdJN * Math.sin(jn.ra), Math.sin(jn.dec)];

    // Inverse of the enuToCelestial rotation (it's an orthogonal matrix
    // so the inverse equals its transpose).
    const cphi = Math.cos(latRad), sphi = Math.sin(latRad);
    const clst = Math.cos(lstRad), slst = Math.sin(lstRad);
    const enu = [
        jnow[0] * (-slst)        + jnow[1] * ( clst)        + jnow[2] * 0,
        jnow[0] * (-sphi * clst) + jnow[1] * (-sphi * slst) + jnow[2] * cphi,
        jnow[0] * ( cphi * clst) + jnow[1] * ( cphi * slst) + jnow[2] * sphi,
    ];
    const alt = Math.asin(Math.max(-1, Math.min(1, enu[2])));
    let az = Math.atan2(enu[0], enu[1]);  // CW from north
    if (az < 0) az += 2 * Math.PI;
    return { alt, az };
}

// Stereographic project a unit sky vector to screen coordinates.
// Returns { x, y } in CSS pixels, or null if behind the camera.
// fov is the angular extent matched to min(width, height).
export function project(sky, basis, fov, width, height) {
    const cx = dot(sky, basis.right);
    const cy = dot(sky, basis.up);
    const cz = dot(sky, basis.forward);
    if (cz <= -0.999) return null;
    const k = 2.0 / (1.0 + cz);
    const sx = cx * k;
    const sy = cy * k;
    const halfMin = Math.min(width, height) / 2;
    const scale = halfMin / (2 * Math.tan(fov / 4));
    return {
        x: width / 2 + sx * scale,
        y: height / 2 - sy * scale,
    };
}

// Inverse stereographic: screen pixel -> unit sky vector in world frame.
export function unproject(sx, sy, basis, fov, width, height) {
    const halfMin = Math.min(width, height) / 2;
    const scale = halfMin / (2 * Math.tan(fov / 4));
    const nx = (sx - width / 2) / scale;
    const ny = -(sy - height / 2) / scale;
    const rho2 = nx * nx + ny * ny;
    const cz = (4 - rho2) / (rho2 + 4);
    const k = 2 / (1 + cz);
    const cx = nx / k;
    const cy = ny / k;
    return [
        cx * basis.right[0] + cy * basis.up[0] + cz * basis.forward[0],
        cx * basis.right[1] + cy * basis.up[1] + cz * basis.forward[1],
        cx * basis.right[2] + cy * basis.up[2] + cz * basis.forward[2],
    ];
}

function dot(a, b) { return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]; }
function cross(a, b) {
    return [
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    ];
}
function normalize(v) {
    const n = Math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2]);
    return [v[0] / n, v[1] / n, v[2] / n];
}
