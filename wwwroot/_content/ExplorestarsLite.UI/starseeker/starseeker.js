// Star Seeker — entry point. Loads catalogs once, renders a static
// frame at a hard-coded look vector. Phase 2 has no sensors or pan.

import { renderFrame } from "./render.js";
import {
    raDecToVec, buildBasis, buildBasisAltaz,
    unproject, j2000ToJNow, jNowToJ2000, j2000ToJNowApparent,
    altAzToJ2000Vec, j2000VecToAltAz, jNowVecToJ2000Vec,
} from "./projection.js";
import * as orientation from "./orientation.js";

const state = {
    stars: null,
    dsos: null,
    starsByHip: null,
    starNames: {},               // HIP (string) -> common name, for tap-selection label
    bayerDesignations: {},       // HIP (string) -> "α CMa" Bayer + abbr label
    nodeLabels: {},              // HIP (string) -> best label for constellation-line node stars (α Cam / 38 Lyn / "HIP n ABBR")
    constellations: null,        // edge list array from artifact
    constellationStars: {},      // canonical-id -> {raHours, decDeg, vmag, name}
    constellationCentroids: [],  // [{name, abbr, vec}] for label placement
    // Per-layer visibility registry. Each draw call in render.js is
    // gated on a key here. The full set is exposed so a future settings
    // page can build its UI from this single source. Defaults preserve
    // existing behavior (everything that used to render still renders).
    // Persisted as one JSON object (chartLayers) by StarSeeker.razor so
    // adding a new layer doesn't ripple into every save site.
    //
    // Reference-circle layers are split line/label so a user can keep
    // a familiar circle drawn while turning off its tangent label once
    // they no longer need the reminder. Constellation gets the same
    // split. Other entries are single toggles (no label-only mode).
    layers: {
        showStars: true,
        showDsos: true,
        showConstellationLines: true,
        showConstellationLabels: true,
        showEcliptic: true,
        showEclipticLabel: true,
        showCelestialEquator: true,
        showCelestialEquatorLabel: true,
        showGalacticEquator: true,
        showGalacticEquatorLabel: true,
        showMeridian: true,
        showMeridianLabel: true,
        showRaDecGrid: true,
        showRaDecLabels: true,
        showAltAzGrid: true,
        showAltAzLabels: true,
        // When true, the active grid follows the chart's projection
        // mode: EQ projection shows only the RA/Dec grid; ALTAZ shows
        // only the Alt/Az grid. The individual show* toggles above
        // still work as filters within the chosen grid (e.g. you can
        // turn off RA/Dec labels while keeping the lines). Default OFF
        // so existing behavior — both grids visible regardless of mode
        // — is preserved unless the user opts in.
        gridFollowsProjection: false,
        showZenith: true,
        showMountMarker: true,
        showTelrad: true,
        showTelradLabels: true,
        showCenterLabel: true,
        showPlanets: true,
        showPlanetLabels: true,
        showTelemetry: true,
    },
    // Push-to mode: not a layer (it changes interaction semantics, not
    // just visibility). When true and sensors are active, the chart's
    // mount pip is driven by the orientation pipeline rather than motor
    // counts; tap behavior, ALIGN, and camera-follow all branch on this.
    // Persisted by Razor as chartPushToMode.
    pushToMode: false,
    // Interval handle for the push-to tick. When non-null, a 20 Hz tick
    // is reading sensor pose and updating mountRa/mountDec.
    pushToTickId: null,
    canvas: null,
    ctx: null,
    logicalWidth: 0,
    logicalHeight: 0,
    camera: null,
    // Magnitude filter band, applied to BOTH stars and DSOs (planets exempt
    // because they live in their own list and can render arbitrarily bright).
    // Defaults: bright cap −3 (effectively no upper limit; brighter than any
    // catalog entry) and faint cap 9 (was the prior single-slider default).
    // Range exposed by the slider widget: −3 to 14.
    magBright: -3.0,
    magFaint: 9.0,
    // 'free' — finger pan drives camera. 'live' — sensors drive camera.
    mode: "free",
    liveTickId: null,
    // Latest sensor pose (for on-screen readout in Live mode).
    pose: null,
    // Phone-anchored basis in Live mode; null in Free (render builds one).
    liveBasis: null,
    // Mount position in radians (J2000), pushed from Blazor when connected.
    // null = no mount / disconnected; renderer skips the orange Telrad.
    mountRa: null,
    mountDec: null,
    // Solar-system body positions — list of { name, ra, dec } in radians,
    // pushed from Blazor on every State.OnChange tick.
    planets: [],
    // Selection marker — set by handleTap when a hit is found, cleared by
    // Razor when the bottom panel is dismissed (× or after GoTo). null = none.
    // Used by the existing (non-push-to) selection panel and by render.js
    // to draw the orange tap-result reticle. Phase 3 splits push-to off
    // this field entirely.
    selectedRa: null,
    selectedDec: null,
    // Active push-to target — { ra, dec, name } in radians, or null.
    // Set by chart tap in push-to mode (Phase 3); the push vector arrow
    // anchors to this position and persists through pan/zoom until the
    // user taps a new target or clears it. Distinct from selectedRa/Dec
    // because push-to taps don't open a selection popup.
    activePushTarget: null,
    // Pending chart target — { ra, dec, name } in radians, or null. Set
    // when the user navigates from the Target page; chart centers on it
    // and the target marker draws there, but no vector and no sensor
    // follow until the user taps the object on the chart (which promotes
    // it to activePushTarget).
    pendingChartTarget: null,
    // Auto-recenter camera on mount each time mount position arrives.
    // Cleared by any pan gesture so the user can break out and explore;
    // re-arming is a button press in the host UI.
    lockedToMount: false,
    // Push-to camera follow — set when a push-to tap promotes a target
    // (snaps the chart back to the sensor pip and follows it). Cleared
    // by pan; re-engaged by the next push-to tap. Independent of
    // lockedToMount because that's the manual LOCK button (OFF mode);
    // this is automatic and unique to push-to mode.
    followingMountAim: false,
    // Mirror left/right — for star-diagonal eyepiece use. The chart
    // geometry flips horizontally; text labels stay readable. Pan and
    // tap math compensate so the chart still feels natural to the user.
    mirror: false,
    // Current user-selected target — its catalog icon is force-drawn at
    // the target's coords regardless of the magnitude filter band, so
    // the user always sees a marker at the target position even after a
    // GoTo when all transient markers (yellow ring, green glyph,
    // selection panel) have cleared.
    //
    //   currentTargetName  — the Name from AppState.SelectedTarget
    //   currentDsoMatch    — DSO entry from state.dsos that matches
    //                        (by name or coords). If found, the regular
    //                        DSO loop force-draws this entry.
    //   currentTargetIcon  — fallback: when no DSO match, render.js
    //                        draws this icon at currentTargetCoords.
    //                        Carries { ra, dec, type, category }.
    currentTargetName: null,
    currentDsoMatch: null,
    currentTargetIcon: null,
    // DotNetObjectReference supplied by Blazor, for tap-select callback.
    dotnet: null,
};

export async function init(canvasEl, starsUrl, dsosUrl, dotnetRef) {
    state.canvas = canvasEl;
    state.ctx = canvasEl.getContext("2d");
    state.dotnet = dotnetRef ?? null;

    // Derive the star-names + constellation-lines URLs from the star-catalog URL.
    const namesUrl = starsUrl.replace(/stars_mag6\.json.*$/, "star_names.json");
    const linesUrl = starsUrl.replace(/stars_mag6\.json.*$/, "constellation_lines.json");
    const bayerUrl = starsUrl.replace(/stars_mag6\.json.*$/, "bayer_designations.json");
    const nodeLabelsUrl = starsUrl.replace(/stars_mag6\.json.*$/, "node_labels.json");
    const [stars, dsos, names, linesArtifact, bayer, nodeLabels] = await Promise.all([
        fetch(starsUrl).then(r => r.json()),
        fetch(dsosUrl).then(r => r.json()),
        fetch(namesUrl).then(r => r.ok ? r.json() : {}).catch(() => ({})),
        fetch(linesUrl).then(r => r.ok ? r.json() : null).catch(() => null),
        fetch(bayerUrl).then(r => r.ok ? r.json() : {}).catch(() => ({})),
        fetch(nodeLabelsUrl).then(r => r.ok ? r.json() : {}).catch(() => ({})),
    ]);
    state.stars = stars;
    state.dsos = dsos;
    state.starNames = names;
    state.bayerDesignations = bayer;
    state.nodeLabels = nodeLabels;
    // New artifact shape: { schema, constellations: [...], stars: {id: {raHours, decDeg, ...}} }
    if (linesArtifact && Array.isArray(linesArtifact.constellations)) {
        state.constellations = linesArtifact.constellations;
        state.constellationStars = linesArtifact.stars || {};
    } else {
        state.constellations = [];
        state.constellationStars = {};
    }
    // Precompute a unit-vector centroid per constellation from its node
    // star positions. Used by render.js to place the constellation name
    // label. Done once at load — node positions don't move.
    state.constellationCentroids = [];
    for (const con of state.constellations) {
        let sx = 0, sy = 0, sz = 0, n = 0;
        for (const edge of (con.edges || [])) {
            for (const ep of edge) {
                const star = state.constellationStars[ep];
                if (!star) continue;
                const ra = star.raHours * Math.PI / 12;
                const dec = star.decDeg * Math.PI / 180;
                const cd = Math.cos(dec);
                sx += cd * Math.cos(ra);
                sy += cd * Math.sin(ra);
                sz += Math.sin(dec);
                n++;
            }
        }
        if (n === 0) continue;
        const len = Math.sqrt(sx * sx + sy * sy + sz * sz) || 1;
        state.constellationCentroids.push({
            name: con.name,
            abbr: con.abbr,
            vec: [sx / len, sy / len, sz / len],
        });
    }
    // Index stars by HIP for fast tap-select and telemetry lookup.
    state.starsByHip = new Map(stars.map(s => [s.hip, s]));

    // Initial look vector — Orion sword area. Phase 3+ lets the user pan.
    // Camera carries BOTH equatorial and alt-az look pairs; whichever
    // matches projectionMode is canonical. The other is recomputed on
    // mode switch and on each draw frame so external callers (Razor:
    // setLook, setLockToMount, setMountPosition) only ever see
    // equatorial-style J2000 RA/Dec — no callsite needs to know about
    // the mode toggle.
    state.camera = {
        projectionMode: "equatorial",  // "equatorial" | "altaz"
        lookRa: 5.583 * Math.PI / 12,
        lookDec: -5 * Math.PI / 180,
        // Alt-az pair — populated lazily when entering altaz mode.
        lookAlt: 0,
        lookAz: 0,
        fov: 40 * Math.PI / 180,
    };

    resize();
    draw();
    orientation.setFov(state.camera.fov);

    window.addEventListener("resize", () => { resize(); scheduleDraw(); });
    bindInput(canvasEl);

    return { stars: stars.length, dsos: dsos.length };
}

function resize() {
    const dpr = window.devicePixelRatio || 1;
    const rect = state.canvas.getBoundingClientRect();
    state.logicalWidth = rect.width;
    state.logicalHeight = rect.height;
    state.canvas.width = Math.round(rect.width * dpr);
    state.canvas.height = Math.round(rect.height * dpr);
    // setTransform resets any prior scale + applies DPR
    state.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
}

// Apply mode-aware grid override. When gridFollowsProjection is on,
// suppress the off-mode grid pair (lines + labels). The user's actual
// state.layers values are preserved — they come back the moment the
// override is turned off.
function effectiveLayers() {
    if (!state.layers.gridFollowsProjection) return state.layers;
    const e = { ...state.layers };
    if (state.camera.projectionMode === "equatorial") {
        e.showAltAzGrid = false;
        e.showAltAzLabels = false;
    } else if (state.camera.projectionMode === "altaz") {
        e.showRaDecGrid = false;
        e.showRaDecLabels = false;
    }
    return e;
}

function draw() {
    if (!state.stars || !state.dsos) return;

    // In altaz mode the canonical look pair is (lookAlt, lookAz). Derive
    // the J2000 forward vector and a J2000 zenith vector for THIS frame
    // (zenith drifts with sidereal time), then build the chart basis with
    // zenith-up. We also resync state.camera.lookRa/lookDec from the new
    // forward so external callers / persistence still see equatorial RA/Dec.
    const lstRad = orientation.getCurrentLstRad();
    const latRad = orientation.getCurrentLatRad?.() ?? 0;
    const now = new Date();
    let altazBasis = null;
    if (state.camera.projectionMode === "altaz" && state.mode !== "live") {
        // Lock-to-mount in altaz: the mount's J2000 RA/Dec is stable
        // for a tracked target, but its alt/az drifts every second as
        // the sky rotates. Re-derive lookAlt/lookAz from mount J2000
        // each frame so the chart center stays glued to the mount —
        // setMountPosition's dedup means we can't rely on push-driven
        // updates while the mount is just tracking.
        if (state.lockedToMount && state.mountRa != null && state.mountDec != null) {
            const aa = _altazFromJ2000RaDec(state.mountRa, state.mountDec);
            state.camera.lookAlt = aa.alt;
            state.camera.lookAz = aa.az;
        }
        const fwd = altAzToJ2000Vec(state.camera.lookAlt, state.camera.lookAz, latRad, lstRad, now);
        const zen = altAzToJ2000Vec(Math.PI / 2, 0, latRad, lstRad, now);
        altazBasis = buildBasisAltaz(fwd, zen);
        // Resync RA/Dec so getCameraState/persistence/setLook reflect
        // where the camera is actually pointing in J2000.
        state.camera.lookRa = Math.atan2(fwd[1], fwd[0]);
        if (state.camera.lookRa < 0) state.camera.lookRa += 2 * Math.PI;
        state.camera.lookDec = Math.asin(Math.max(-1, Math.min(1, fwd[2])));
    }

    // Telemetry: in Live, from sensor-derived pose. In Free, synthesize
    // from the camera's look vector so the readout matches the reticle
    // at screen center as the user pans.
    //
    // The chart works in J2000 internally, but the bottom-left readout
    // must match the mount-telemetry strip at the top of the page (which
    // is JNow). Convert J2000 → JNow once here and pass the JNow values
    // into renderFrame; computing alt/az from the JNow ra/dec keeps the
    // 4-tuple (ra, dec, alt, az) self-consistent and consistent with the
    // mount, instead of half-J2000-half-JNow.
    let telemetry = null;
    if (state.mode === "live") {
        // state.pose is already JNow: orientation.js derives ra/dec from
        // sensor alt/az + current LST, and alt/az is the real-sky pose.
        telemetry = state.pose;
    } else {
        // Apparent place — precession + nutation + aberration — so the
        // bottom-left readout matches the Target page's JNow display
        // (which goes through C# CoordinateService.J2000ToJNow with the
        // same Meeus Ch. 21–23 formulas). Without nutation+aberration
        // here there's a ~25" residual that's visible against a pinned
        // mount/target reading.
        const jnow = j2000ToJNowApparent(state.camera.lookRa, state.camera.lookDec, now);
        const altAz = orientation.computeAltAzFromRaDec(jnow.ra, jnow.dec);
        telemetry = {
            ra: jnow.ra,
            dec: jnow.dec,
            alt: altAz.alt,
            az: altAz.az,
        };
    }

    renderFrame(state.ctx, state.stars, state.dsos, state.camera,
        { width: state.logicalWidth, height: state.logicalHeight },
        {
            magBright: state.magBright,
            magFaint: state.magFaint,
            // Force-draw the user's current target even if mag-filtered.
            // render.js's DSO loop checks d === currentDsoMatch and skips
            // the band-filter early-out for that one entry. When no DSO
            // match (entry filtered out of dsos.json, or custom coords),
            // currentTargetIcon carries a synthesized marker that the
            // post-DSO-loop pass paints at the target's coords.
            currentDsoMatch: state.currentDsoMatch,
            currentTargetIcon: state.currentTargetIcon,
            reticle: true,   // reticle is always centered; user aims the sky under it
            telemetry,
            // Basis precedence: LIVE sensor-driven > FREE altaz-driven >
            // FREE equatorial (renderFrame falls back to its own
            // buildBasis(lookRa, lookDec) when basis is null).
            basis: state.mode === "live" ? state.liveBasis : altazBasis,
            // Per-layer visibility — render.js gates each draw call on
            // the corresponding state.layers entry. When the user has
            // enabled "change grid with projection," override the
            // grid-pair toggles per the active projection mode without
            // mutating state.layers (so the user's underlying toggles
            // stay intact when they switch the override off).
            layers: effectiveLayers(),
            constellations: state.constellations,
            constellationStars: state.constellationStars,
            constellationCentroids: state.constellationCentroids,
            // Observer latitude (radians) for the zenith marker. Read from
            // orientation.js's stored lat (set by setObserverLocation).
            observerLatRad: orientation.getCurrentLatRad?.() ?? 0,
            planets: state.planets,
            // For the center-label feature, the lookup priority is:
            // nodeLabels (constellation-line nodes) → bayer → starNames →
            // "HIP nnnn" fallback. nodeLabels covers Bayer + Flamsteed +
            // "HIP n ABBR" for every constellation node, so the only
            // thing it doesn't cover is non-node stars.
            starNames: state.starNames,
            bayerDesignations: state.bayerDesignations,
            nodeLabels: state.nodeLabels,
            // In push-to mode, the activePushTarget IS the selection
            // (no separate panel, no separate marker). In OFF mode, the
            // tap-result glyph at selectedRa/Dec serves as the marker.
            // Forward category/type/vmag through for active push-to so
            // render.js can paint the catalog icon underneath the green
            // glyph when the underlying object is mag-filtered out. OFF-
            // mode tap selection always lands on a visible catalog
            // object (filtered ones aren't returned by findNearest in
            // that path), so no category lookup is needed there.
            selection: state.pushToMode
                ? (state.activePushTarget
                    ? {
                        ra: state.activePushTarget.ra,
                        dec: state.activePushTarget.dec,
                        category: state.activePushTarget.category ?? null,
                        type: state.activePushTarget.type ?? null,
                      }
                    : null)
                : (state.selectedRa != null && state.selectedDec != null
                    ? { ra: state.selectedRa, dec: state.selectedDec }
                    : null),
            // LST drives the local-meridian overlay (RA = LST). Passing it
            // here rather than recomputing inside render.js keeps the math
            // confined to orientation.js.
            lstRad: orientation.getCurrentLstRad(),
            mountReticle: (state.mountRa != null && state.mountDec != null)
                ? { ra: state.mountRa, dec: state.mountDec }
                : null,
            // Pending chart target (Target-page handoff). Rendered as a
            // yellow open ring + label so the user can see where their
            // pick is, even if it isn't a star/DSO that the chart's own
            // catalog draws (e.g. a Messier object the chart's DSO list
            // doesn't include, or a custom RA/Dec entry).
            pendingTarget: state.pendingChartTarget,
            // Chart-center altitude in radians — used by the alt/az grid
            // for zenith-aware density thinning (looking near zenith,
            // azimuth meridians converge like RA at the celestial pole).
            lookAlt: telemetry?.alt ?? 0,
            // Push-to navigation arrow data. Built only when push-to is
            // active AND a target is selected AND the pip and target are
            // both real points. render.js's drawPushVector projects both
            // J2000 vectors and draws the arrow + distance label.
            pushVector: buildPushVector(),
            // Push-to readout state for the lower-left telemetry block.
            // - mode: "off" / "browse" / "navigate"
            // - targetName + separationDeg only meaningful in "navigate"
            pushToReadout: buildPushToReadout(),
            // Mirror is applied inside render.js by negating basis.right
            // so all geometry (stars, lines, markers, labels' positions)
            // flips uniformly while text glyphs stay readable.
            mirror: state.mirror,
        });
}

// Construct the lower-left readout's push-to status. Three states:
// "off" (push-to disabled), "browse" (push-to on, no active target), and
// "navigate" (push-to on with active target — show distance).
function buildPushToReadout() {
    if (!state.pushToMode) return { mode: "off" };
    if (!state.activePushTarget) return { mode: "browse" };
    // Compute angular separation pip → target. Reuse the buildPushVector
    // result if available; recompute defensively otherwise.
    const v = buildPushVector();
    const sepDeg = v ? (v.sepRad * 180 / Math.PI) : null;
    return {
        mode: "navigate",
        targetName: state.activePushTarget.name ?? "?",
        separationDeg: sepDeg,
    };
}

// Build the push-to navigation indicator's data bundle, or null if it
// shouldn't render this frame. Used by render.js's drawPushVector.
// Computes angular separation via stable atan2(|cross|, dot) (acos
// loses precision for small angles) and alt/az delta (for the
// "push up X°, rotate Y°" hint).
function buildPushVector() {
    if (!state.pushToMode) return null;
    if (!state.activePushTarget) return null;
    if (state.mountRa == null || state.mountDec == null) return null;

    const tgt = state.activePushTarget;
    const pipVec = raDecToVec(state.mountRa, state.mountDec);
    const tgtVec = raDecToVec(tgt.ra, tgt.dec);
    // Stable angular-separation: atan2(|cross|, dot).
    const cx = pipVec[1] * tgtVec[2] - pipVec[2] * tgtVec[1];
    const cy = pipVec[2] * tgtVec[0] - pipVec[0] * tgtVec[2];
    const cz = pipVec[0] * tgtVec[1] - pipVec[1] * tgtVec[0];
    const crossMag = Math.sqrt(cx * cx + cy * cy + cz * cz);
    const dotPT = pipVec[0] * tgtVec[0] + pipVec[1] * tgtVec[1] + pipVec[2] * tgtVec[2];
    const sepRad = Math.atan2(crossMag, dotPT);

    // Alt/az delta: how much to push up and rotate. Positive altDelta
    // = lift OTA; positive azDelta = rotate clockwise as seen from above.
    const lstRad = orientation.getCurrentLstRad();
    const latRad = orientation.getCurrentLatRad?.() ?? 0;
    const now = new Date();
    const pipAA = j2000VecToAltAz(pipVec, latRad, lstRad, now);
    const tgtAA = j2000VecToAltAz(tgtVec, latRad, lstRad, now);
    const altDelta = tgtAA.alt - pipAA.alt;
    let azDelta = tgtAA.az - pipAA.az;
    while (azDelta >  Math.PI) azDelta -= 2 * Math.PI;
    while (azDelta <= -Math.PI) azDelta += 2 * Math.PI;

    return { pipVec, tgtVec, sepRad, altDelta, azDelta };
}

let _pendingDraw = false;
function scheduleDraw() {
    if (_pendingDraw) return;
    _pendingDraw = true;
    requestAnimationFrame(() => {
        _pendingDraw = false;
        draw();
    });
}

// Finger/mouse drag pans the look vector. Pinch (or wheel) zooms FOV.
// Dragging right moves sky right, so look vector moves west (RA decreases).
// Near the poles, dividing by cos(dec) amplifies horizontal drags — clamped.
function pan(dxPx, dyPx) {
    // Any user pan breaks the lock-to-mount state. Notifying the host
    // (Blazor) so the UI button updates without polling.
    if (state.lockedToMount) {
        state.lockedToMount = false;
        console.log("[starseeker] mount lock cleared by pan");
        if (state.dotnet) {
            state.dotnet.invokeMethodAsync("OnMountLockCleared").catch(() => { });
        }
    }
    // Push-to follow ends on any pan — user wants to browse. Vector
    // and active target stay armed; next push-to tap re-engages follow.
    state.followingMountAim = false;
    const anglePerPx = state.camera.fov / Math.min(state.logicalWidth, state.logicalHeight);
    // In mirror mode the chart is flipped horizontally; flip the pan-x
    // sign so dragging right still moves what the user sees rightward.
    const dx = state.mirror ? -dxPx : dxPx;
    const TWO_PI = Math.PI * 2;

    if (state.camera.projectionMode === "altaz") {
        // Alt-az pan: drag-right shifts az west (sky content slides right);
        // drag-down increases altitude (camera looks higher). cos(alt)
        // factor matches equatorial's cos(dec) so panning near the
        // zenith doesn't fly across in a single drag.
        const cosAlt = Math.max(0.1, Math.cos(state.camera.lookAlt));
        state.camera.lookAz -= dx * anglePerPx / cosAlt;
        state.camera.lookAlt += dyPx * anglePerPx;
        state.camera.lookAz = ((state.camera.lookAz % TWO_PI) + TWO_PI) % TWO_PI;
        const maxAlt = Math.PI / 2 - 0.001;
        state.camera.lookAlt = Math.max(-maxAlt, Math.min(maxAlt, state.camera.lookAlt));
        return;
    }

    // Equatorial pan.
    const cosDec = Math.max(0.1, Math.cos(state.camera.lookDec));
    state.camera.lookRa -= dx * anglePerPx / cosDec;
    state.camera.lookDec += dyPx * anglePerPx;
    state.camera.lookRa = ((state.camera.lookRa % TWO_PI) + TWO_PI) % TWO_PI;
    const maxDec = Math.PI / 2 - 0.001;
    state.camera.lookDec = Math.max(-maxDec, Math.min(maxDec, state.camera.lookDec));
}

const FOV_MIN = 2 * Math.PI / 180;
const FOV_MAX = 160 * Math.PI / 180;
function zoom(scale) {
    // Pinch-zoom also breaks the lock. Otherwise zooming in while
    // locked would feel weird — the mount position pin stays centered
    // but the user has expressed an intent to control the view.
    if (state.lockedToMount) {
        state.lockedToMount = false;
        console.log("[starseeker] mount lock cleared by zoom");
        if (state.dotnet) {
            state.dotnet.invokeMethodAsync("OnMountLockCleared").catch(() => { });
        }
    }
    state.camera.fov = Math.max(FOV_MIN, Math.min(FOV_MAX, state.camera.fov / scale));
    orientation.setFov(state.camera.fov);
}

function bindInput(el) {
    const pointers = new Map();
    let lastX = 0, lastY = 0, lastPinch = 0;
    // Tap tracking: a pointer is a tap if it was down briefly and barely moved.
    let tapCandidate = null;

    el.addEventListener("pointerdown", e => {
        el.setPointerCapture(e.pointerId);
        pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
        if (pointers.size === 1) {
            lastX = e.clientX; lastY = e.clientY;
            tapCandidate = { id: e.pointerId, x: e.clientX, y: e.clientY, t: performance.now() };
        } else {
            tapCandidate = null;  // second finger => not a tap
            if (pointers.size === 2) {
                const [a, b] = [...pointers.values()];
                lastPinch = Math.hypot(a.x - b.x, a.y - b.y);
            }
        }
        e.preventDefault();
    });

    el.addEventListener("pointermove", e => {
        if (!pointers.has(e.pointerId)) return;
        pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });

        if (tapCandidate && e.pointerId === tapCandidate.id) {
            const moved = Math.hypot(e.clientX - tapCandidate.x, e.clientY - tapCandidate.y);
            if (moved > 8) tapCandidate = null;  // movement threshold => it's a drag, not a tap
        }

        if (pointers.size === 1) {
            const dx = e.clientX - lastX;
            const dy = e.clientY - lastY;
            lastX = e.clientX; lastY = e.clientY;
            if (state.mode === "free" && !tapCandidate) {
                pan(dx, dy);
                scheduleDraw();
            }
        } else if (pointers.size === 2) {
            const [a, b] = [...pointers.values()];
            const d = Math.hypot(a.x - b.x, a.y - b.y);
            if (lastPinch > 0 && d > 0) zoom(d / lastPinch);
            lastPinch = d;
            scheduleDraw();
        }
    });

    const endPointer = e => {
        const wasTap = tapCandidate
            && e.pointerId === tapCandidate.id
            && performance.now() - tapCandidate.t < 500;
        pointers.delete(e.pointerId);
        if (pointers.size === 1) {
            const rem = [...pointers.values()][0];
            lastX = rem.x; lastY = rem.y;
        }
        lastPinch = 0;
        if (wasTap) {
            tapCandidate = null;
            handleTap(e.clientX, e.clientY);
        }
    };
    el.addEventListener("pointerup", endPointer);
    el.addEventListener("pointercancel", endPointer);
    el.addEventListener("lostpointercapture", endPointer);

    // Wheel zoom for desktop. Wheel up (deltaY < 0) zooms in.
    el.addEventListener("wheel", e => {
        e.preventDefault();
        const scale = e.deltaY < 0 ? 1.15 : 1 / 1.15;
        zoom(scale);
        scheduleDraw();
    }, { passive: false });
}

// ---- Align on bright star ----

const ALIGN_STORAGE_KEY = "starseeker.align.v1";
const ALIGN_MAX_MAG = 2.5;        // only named stars brighter than this
const ALIGN_SEARCH_RAD = 15 * Math.PI / 180;  // search within 15° of reticle

// Returns the nearest named bright star to the current phone-aim direction,
// or null if none close enough. Uses state.liveBasis.forward as the aim.
export function findAlignCandidate() {
    if (state.mode !== "live" || !state.liveBasis) return null;
    const aim = state.liveBasis.forward;
    const cosCutoff = Math.cos(ALIGN_SEARCH_RAD);
    let best = null;
    let bestCos = cosCutoff;
    for (const s of state.stars) {
        if (s.vmag == null || s.vmag > ALIGN_MAX_MAG) continue;
        const name = state.starNames[String(s.hip)];
        if (!name) continue;  // only named stars
        const v = raDecToVec(s.ra, s.dec);
        const c = v[0] * aim[0] + v[1] * aim[1] + v[2] * aim[2];
        if (c > bestCos) {
            bestCos = c;
            best = { hip: s.hip, name, ra: s.ra, dec: s.dec, vmag: s.vmag };
        }
    }
    if (!best) return null;
    const angRad = Math.acos(Math.max(-1, Math.min(1, bestCos)));
    return {
        name: best.name,
        hip: best.hip,
        raHours: best.ra * 12 / Math.PI,
        decDeg: best.dec * 180 / Math.PI,
        vmag: best.vmag,
        distanceDeg: angRad * 180 / Math.PI,
    };
}

// Confirm the align. Computes heading offset so that the star's current
// true az equals the phone's current reading, then stores and persists it.
export function applyAlign(hip) {
    if (state.mode !== "live") return false;
    const s = state.stars.find(x => x.hip === hip);
    if (!s) return false;

    // Current phone-reported az (post existing offset, pre new correction).
    const currentAz = orientation.getCurrentLookAz();
    if (currentAz === null || currentAz === undefined) return false;

    // Star's TRUE az at this instant, from its RA/Dec + observer + LST.
    const trueAltAz = orientation.computeAltAzFromRaDec(s.ra, s.dec);

    // Shortest-path angular delta in (−π, π].
    let delta = trueAltAz.az - currentAz;
    const TWO_PI = 2 * Math.PI;
    while (delta > Math.PI) delta -= TWO_PI;
    while (delta < -Math.PI) delta += TWO_PI;

    const newOffset = orientation.getAlignOffset() + delta;
    orientation.setAlignOffset(newOffset);

    persistAlign(newOffset, s.hip, state.starNames[String(s.hip)] ?? `HIP ${s.hip}`);
    return true;
}

// Push-to ALIGN — calibrate sensor heading using a user-selected target's
// J2000 coords. Distinct from applyAlign() (which is LIVE-mode auto-
// bright-star) because:
//   - works in FREE chart mode (push-to runs in FREE)
//   - takes coords directly (target may be a DSO with no HIP)
//   - per design doc, does not issue PMC-Eight Sync or touch motors
export function applyAlignByCoords(raHours, decDeg, name) {
    if (raHours == null || decDeg == null) return false;
    const ra = raHours * Math.PI / 12;
    const dec = decDeg * Math.PI / 180;

    const currentAz = orientation.getCurrentLookAz();
    if (currentAz === null || currentAz === undefined) return false;

    const trueAltAz = orientation.computeAltAzFromRaDec(ra, dec);

    let delta = trueAltAz.az - currentAz;
    const TWO_PI = 2 * Math.PI;
    while (delta > Math.PI) delta -= TWO_PI;
    while (delta < -Math.PI) delta += TWO_PI;

    const newOffset = orientation.getAlignOffset() + delta;
    orientation.setAlignOffset(newOffset);

    persistAlign(newOffset, 0, name ?? "?");
    return true;
}

export function clearAlign() {
    orientation.setAlignOffset(0);
    try { localStorage.removeItem(ALIGN_STORAGE_KEY); } catch { }
}

export function getAlignState() {
    try {
        const raw = localStorage.getItem(ALIGN_STORAGE_KEY);
        return raw ? JSON.parse(raw) : null;
    } catch { return null; }
}

function persistAlign(offsetRad, hip, name) {
    try {
        localStorage.setItem(ALIGN_STORAGE_KEY, JSON.stringify({
            offsetRad,
            hip,
            name,
            timestampUtc: new Date().toISOString(),
        }));
    } catch { }
}

// Load and apply persisted alignment (if any). Called after observer
// location is set so the offset is meaningful.
export function loadPersistedAlign() {
    const s = getAlignState();
    if (s && typeof s.offsetRad === "number") {
        orientation.setAlignOffset(s.offsetRad);
    }
    return s;
}

// ---- Tap to select ----

function handleTap(clientX, clientY) {
    if (!state.dotnet) return;
    const rect = state.canvas.getBoundingClientRect();
    let px = clientX - rect.left;
    const py = clientY - rect.top;
    // In mirror mode the displayed chart is x-flipped; map the tap back
    // to the un-flipped projection space so unproject lands on what the
    // user actually saw under their finger.
    if (state.mirror) px = state.logicalWidth - px;
    let basis;
    if (state.mode === "live" && state.liveBasis) {
        basis = state.liveBasis;
    } else if (state.camera.projectionMode === "altaz") {
        const lstRad = orientation.getCurrentLstRad();
        const latRad = orientation.getCurrentLatRad?.() ?? 0;
        const now = new Date();
        const fwd = altAzToJ2000Vec(state.camera.lookAlt, state.camera.lookAz, latRad, lstRad, now);
        const zen = altAzToJ2000Vec(Math.PI / 2, 0, latRad, lstRad, now);
        basis = buildBasisAltaz(fwd, zen);
    } else {
        basis = buildBasis(state.camera.lookRa, state.camera.lookDec);
    }
    const sky = unproject(px, py, basis, state.camera.fov,
        state.logicalWidth, state.logicalHeight);

    const hit = findNearest(sky);
    if (hit) {
        // Push-to mode: tap promotes directly to the active push-to
        // target — no selection panel, no GoTo button. Vector arrow
        // anchors to activePushTarget. Razor's OnObjectTapped branches
        // on _pushToMode and skips the panel.
        // OFF mode: stamp the green selection marker so the user gets
        // visual confirmation; Razor opens the bottom panel.
        if (state.pushToMode) {
            state.activePushTarget = {
                ra: hit.raHours * Math.PI / 12,
                dec: hit.decDeg * Math.PI / 180,
                name: hit.name ?? null,
            };
            state.pendingChartTarget = null;  // tapping consumes pending
        } else {
            state.selectedRa = hit.raHours * Math.PI / 12;
            state.selectedDec = hit.decDeg * Math.PI / 180;
            // Tapping on the chart supersedes any Target-page pending
            // selection — clear the yellow pending ring so it doesn't
            // visually compete with the green tap-result marker.
            state.pendingChartTarget = null;
        }
        scheduleDraw();
        state.dotnet.invokeMethodAsync("OnObjectTapped", hit).catch(() => { });
    }
}

// Set or clear the on-chart selection marker. Pass (null, null) to clear.
// Razor calls this when the bottom panel is dismissed.
export function setSelection(raHours, decDeg) {
    if (raHours == null || decDeg == null) {
        state.selectedRa = null;
        state.selectedDec = null;
    } else {
        state.selectedRa = raHours * Math.PI / 12;
        state.selectedDec = decDeg * Math.PI / 180;
    }
    scheduleDraw();
}

// Promote a tapped object to the active push-to target. Distinct from
// setSelection (which is the non-push-to selection-panel path). Phase 3
// will wire this to the push-to-mode tap branch in Razor; Phase 4 will
// re-center the camera on the mount/aim pip when this fires.
export function setActivePushTarget(raHours, decDeg, name) {
    if (raHours == null || decDeg == null) {
        state.activePushTarget = null;
    } else {
        state.activePushTarget = {
            ra: raHours * Math.PI / 12,
            dec: decDeg * Math.PI / 180,
            name: name ?? null,
            ...lookupTargetCategory(name),
        };
    }
    scheduleDraw();
}

export function clearActivePushTarget() {
    state.activePushTarget = null;
    scheduleDraw();
}

// Pending chart target — set by Target-page navigation. Chart centers
// on this once and the target marker draws here, but no vector and no
// sensor follow until the user taps the object on the chart (which
// promotes it to activePushTarget).
export function setPendingChartTarget(raHours, decDeg, name) {
    if (raHours == null || decDeg == null) {
        state.pendingChartTarget = null;
    } else {
        state.pendingChartTarget = {
            ra: raHours * Math.PI / 12,
            dec: decDeg * Math.PI / 180,
            name: name ?? null,
            ...lookupTargetCategory(name),
        };
    }
    scheduleDraw();
}

// Match a target name against the chart's catalogs and return its
// drawing category + DSO sub-type (if applicable). Used by the pending
// and active push-to setters so render.js can draw the proper catalog
// icon underneath the marker ring even when the magnitude slider has
// hidden the original catalog draw call. Falls back to no category
// when no match is found (custom RA/Dec entries, names that don't
// appear in the catalog).
function lookupTargetCategory(name) {
    if (!name) return {};
    // Exact name match against DSO list — covers "M31", "NGC 1" etc.
    // The DSO catalog also has a "full" descriptive form ("M31 (Galaxy …)")
    // so check both to be safe against the user's exact pick on
    // /target.
    if (state.dsos && state.dsos.length) {
        for (const d of state.dsos) {
            if (d.name === name || d.full === name) {
                return { category: "dso", type: d.type ?? null, vmag: d.vmag ?? null };
            }
        }
    }
    // Solar-system bodies — match by name. PlanetService outputs the
    // canonical body name ("Mars", "Sun", …).
    if (state.planets && state.planets.length) {
        for (const p of state.planets) {
            if (p.name === name) return { category: "planet", type: null, vmag: null };
        }
    }
    // Stars — names from /target are typically Bayer/Flamsteed proper
    // names ("Vega", "α CMa") that don't directly key into the chart's
    // HIP-indexed star list. Skipping the exhaustive star scan: bright
    // stars never get filtered out anyway, and faint star picks are
    // uncommon. The fallback path (no category) just shows the marker
    // ring on its own, which is still tappable and labelled.
    return {};
}

export function clearPendingChartTarget() {
    state.pendingChartTarget = null;
    scheduleDraw();
}

// Push the user's current selected target (whatever's in
// AppState.SelectedTarget) so the chart can always show a catalog icon
// at its position, regardless of the magnitude slider.
//
// Two-tier resolution:
//   1. Name match against state.dsos (covers most picks). The resolved
//      entry goes into state.currentDsoMatch — the regular DSO draw
//      loop checks d === currentDsoMatch (O(1)) and bypasses the
//      mag-filter for that one entry, so the user sees the actual
//      catalog draw at the actual catalog position.
//   2. Fallback: when name doesn't match (entry filtered out at DSO-
//      build time, or custom RA/Dec, or star not in Hipparcos), we
//      still want a marker at the target position. raHours/decDeg are
//      passed through from Razor (always known via SelectedTarget).
//      Type is parsed from the catalog name format
//      "X (Description - TYPE - Designation)" — the "TYPE" segment is
//      the DSO sub-type code like "G-S", "OC", "GC". render.js uses
//      this to draw the proper icon at the fallback coords.
//
// Pass null/empty name to clear all three.
export function setCurrentTarget(name, raHours, decDeg) {
    state.currentTargetName = name || null;
    state.currentDsoMatch = null;
    state.currentTargetIcon = null;

    if (!name) { scheduleDraw(); return; }

    // Tier 1: DSO catalog match.
    if (state.dsos && state.dsos.length) {
        for (const d of state.dsos) {
            if (d.name === name || d.full === name) {
                state.currentDsoMatch = d;
                scheduleDraw();
                return;
            }
        }
    }

    // Tier 2: fallback — synthesize an icon at the passed coords.
    if (raHours == null || decDeg == null) { scheduleDraw(); return; }
    const ra = raHours * Math.PI / 12;
    const dec = decDeg * Math.PI / 180;
    let category = null, type = null;

    // Solar-system match by exact name.
    if (state.planets && state.planets.length) {
        for (const p of state.planets) {
            if (p.name === name) { category = "planet"; break; }
        }
    }

    // Catalog name format: "X (... - TYPE - ...)". Pull the TYPE token
    // from inside the parentheses if present.
    if (!category) {
        const m = name.match(/\(\s*[^()]*?\s*-\s*([A-Z][A-Z0-9+\-]*)\s*-/);
        if (m) {
            type = m[1];
            // AST / asterism / star-classified entries use a generic
            // small dot; everything else dispatches to drawDso(type).
            category = "dso";
        } else {
            // Unknown — small white dot fallback.
            category = "star";
        }
    }

    state.currentTargetIcon = { ra, dec, category, type };
    scheduleDraw();
}

function findNearest(skyVec) {
    // Fingertip ≈ 20 px; convert to angular tolerance using current FOV.
    const pxTolerance = 20;
    const angTol = pxTolerance * state.camera.fov /
        Math.min(state.logicalWidth, state.logicalHeight);
    let bestCos = Math.cos(angTol);
    let best = null;

    for (const s of state.stars) {
        // Tap-test honors the same band filter as the renderer so the user
        // can't accidentally select a hidden star.
        if (s.vmag != null && (s.vmag < state.magBright || s.vmag > state.magFaint)) continue;
        const v = raDecToVec(s.ra, s.dec);
        const c = v[0] * skyVec[0] + v[1] * skyVec[1] + v[2] * skyVec[2];
        if (c > bestCos) {
            bestCos = c;
            const common = state.starNames[String(s.hip)] ?? null;
            best = {
                name: common ? `${common} (HIP ${s.hip})` : `HIP ${s.hip}`,
                raHours: s.ra * 12 / Math.PI,
                decDeg: s.dec * 180 / Math.PI,
                vmag: s.vmag,
                type: "star",
                full: `HIP ${s.hip}`,
            };
        }
    }
    for (const d of state.dsos) {
        // Match render.js's null-vmag treatment so users can't tap a
        // DSO that was filtered out of the visible chart.
        const eff = d.vmag ?? 8.5;
        if (eff < state.magBright || eff > state.magFaint) continue;
        const v = raDecToVec(d.ra, d.dec);
        const c = v[0] * skyVec[0] + v[1] * skyVec[1] + v[2] * skyVec[2];
        if (c > bestCos) {
            bestCos = c;
            best = {
                name: d.name,
                raHours: d.ra * 12 / Math.PI,
                decDeg: d.dec * 180 / Math.PI,
                vmag: d.vmag,
                type: d.type,
                full: d.full,
            };
        }
    }
    // Solar-system bodies — exempt from any mag filter, name == display label.
    for (const pl of state.planets) {
        const v = raDecToVec(pl.ra, pl.dec);
        const c = v[0] * skyVec[0] + v[1] * skyVec[1] + v[2] * skyVec[2];
        if (c > bestCos) {
            bestCos = c;
            best = {
                name: pl.name,
                raHours: pl.ra * 12 / Math.PI,
                decDeg: pl.dec * 180 / Math.PI,
                vmag: null,
                type: "planet",
                full: pl.name,
            };
        }
    }
    // Persisted chart targets — pending (yellow ring from Target-page
    // handoff) and active push-to (green glyph). Tappable regardless of
    // the magnitude slider so the user can always interact with what
    // they explicitly selected, even if the underlying catalog entry is
    // hidden by the current mag-filter band.
    const persisted = [];
    if (state.pendingChartTarget) persisted.push(state.pendingChartTarget);
    if (state.activePushTarget) persisted.push(state.activePushTarget);
    for (const tgt of persisted) {
        const v = raDecToVec(tgt.ra, tgt.dec);
        const c = v[0] * skyVec[0] + v[1] * skyVec[1] + v[2] * skyVec[2];
        if (c > bestCos) {
            bestCos = c;
            best = {
                name: tgt.name ?? "target",
                raHours: tgt.ra * 12 / Math.PI,
                decDeg: tgt.dec * 180 / Math.PI,
                vmag: null,
                type: "target",
                full: tgt.name ?? "target",
            };
        }
    }
    return best;
}

// ---- Live mode (sensor-driven camera) ----

export async function requestSensorPermission() {
    return await orientation.requestPermission();
}

// Lets the Razor host probe whether motion-sensor events have arrived
// since LIVE mode started — distinguishes "phone with sensors" from
// "desktop browser / device without motion API." Used to disable ALIGN
// and revert from LIVE to FREE if no sensor data is detected.
export function hasReceivedSensorData() {
    return orientation.hasReceivedSensorData();
}

// Silent sensor-availability probe. Used at chart init so the push-to
// toggle can be disabled / labeled correctly without requiring a user
// gesture. Returns "available", "needs-gesture", or "unavailable".
//
//  - "available"     → events arrived during the probe window; sensors work.
//  - "needs-gesture" → iOS 13+ permission API present; no meaningful
//                      probe possible until the user taps something.
//  - "unavailable"   → no permission API and no events; treat as no sensors.
//
// On iOS, return "needs-gesture" immediately — events never fire before
// the user grants permission, so waiting is a guaranteed false negative
// that locks the user out of even attempting to enable push-to. The
// toggle stays tappable and the actual permission flow happens in
// requestSensorPermission() during TogglePushToMode.
//
// On non-iOS, attach a listener and wait up to timeoutMs. Removes the
// listener if no events arrive so we don't leak it.
export async function probeSensors(timeoutMs = 1500) {
    if (typeof DeviceOrientationEvent !== "undefined" &&
        typeof DeviceOrientationEvent.requestPermission === "function") {
        return "needs-gesture";
    }

    orientation.startSensors();
    await new Promise(r => setTimeout(r, timeoutMs));
    const got = orientation.hasReceivedSensorData();
    if (got) return "available";
    orientation.stopSensors();
    return "unavailable";
}

export function setObserverLocation(latDeg, lonDeg) {
    orientation.setObserverLocation(latDeg, lonDeg);
    // Free-mode telemetry reads location during draw; refresh so the
    // initial frame doesn't stay on the lat=0 readout.
    scheduleDraw();
}

// Mount sky position in J2000. Pass null/null to clear (disconnect).
// Caller (Blazor) is responsible for the JNow -> J2000 conversion before
// calling, since the chart's catalog is J2000.
export function setMountPosition(raHours, decDeg) {
    if (raHours == null || decDeg == null) {
        state.mountRa = null;
        state.mountDec = null;
    } else {
        state.mountRa = raHours * Math.PI / 12;
        state.mountDec = decDeg * Math.PI / 180;
        // Lock-to-mount: keep camera glued to mount as it slews / tracks.
        // Only meaningful in FREE mode; in LIVE the sensor tick overwrites
        // the camera, so the lock is silently inert there.
        if (state.lockedToMount && state.mode === "free") {
            state.camera.lookRa = state.mountRa;
            state.camera.lookDec = state.mountDec;
            // In altaz mode the canonical pair is alt/az; refresh it so
            // the chart actually re-centers (otherwise draw() rebuilds
            // the basis from stale alt/az and the lock looks broken).
            if (state.camera.projectionMode === "altaz") {
                const aa = _altazFromJ2000RaDec(state.mountRa, state.mountDec);
                state.camera.lookAlt = aa.alt;
                state.camera.lookAz = aa.az;
            }
        }
    }
    scheduleDraw();
}

// Generic per-layer toggle. Razor settings page will drive this for
// every entry in state.layers. Unknown names are ignored so renaming
// a layer doesn't crash old persisted state.
export function setLayer(name, on) {
    if (!Object.prototype.hasOwnProperty.call(state.layers, name)) return;
    state.layers[name] = !!on;
    scheduleDraw();
}

// Push-to mode toggle. Mode (not layer) — controls interaction
// semantics across the chart: tap path, ALIGN path, camera follow,
// sensor lifecycle. Razor calls this on init (to push persisted state)
// and from the push-to toggle UI.
export function setPushToMode(on) {
    const wasOn = state.pushToMode;
    state.pushToMode = !!on;
    if (wasOn !== state.pushToMode) {
        syncSensorState();
        syncPushToTick();
        // Per design doc, turning push-to OFF clears the active target.
        // Pending stays — it's just a chart-centering pointer that
        // outlives mode toggles. Camera-follow flag also drops because
        // it's exclusive to push-to mode.
        if (!state.pushToMode) {
            state.activePushTarget = null;
            state.followingMountAim = false;
        }
        scheduleDraw();
    }
}

// Coordinate sensor lifecycle across multiple consumers. LIVE mode and
// push-to mode each need orientation events. Sensors run when EITHER is
// engaged; sensors stop when both are off (battery + permission scope
// minimization). orientation.js's start/stop helpers are idempotent so
// this is safe to call from any state transition.
function syncSensorState() {
    const wantSensors = state.mode === "live" || state.pushToMode;
    if (wantSensors) orientation.startSensors();
    else orientation.stopSensors();
}

// Start or stop the push-to tick to match state.pushToMode. When the
// tick stops, clear the sensor-driven mount pip so a stale position
// doesn't linger; if a motor mount is connected, the host's next
// setMountPosition push repopulates from motor counts.
function syncPushToTick() {
    const want = !!state.pushToMode;
    if (want && state.pushToTickId === null) {
        state.pushToTickId = setInterval(pushToTick, 50);  // 20 Hz
    } else if (!want && state.pushToTickId !== null) {
        clearInterval(state.pushToTickId);
        state.pushToTickId = null;
        state.mountRa = null;
        state.mountDec = null;
        scheduleDraw();
    }
}

// Push-to tick: read the orientation pipeline's current pose (JNow),
// convert to J2000 via the polar-safe vector form, and write into
// state.mountRa/mountDec — the same fields the motor pipeline writes
// to. render.js draws the mount marker at whichever value is current,
// agnostic of the source.
function pushToTick() {
    const look = orientation.getCurrentLook();
    if (look === null) return;  // sensors haven't produced a pose yet
    const j2k = jNowToJ2000(look.ra, look.dec, new Date());
    state.mountRa = j2k.ra;
    state.mountDec = j2k.dec;
    state.pose = look;  // keep state.pose populated for the bottom-left readout in LIVE mode
    // Push-to camera follow — when armed (after a push-to tap), the
    // camera tracks the sensor pip every tick. Pan clears the flag.
    if (state.followingMountAim && state.mode === "free") {
        state.camera.lookRa = state.mountRa;
        state.camera.lookDec = state.mountDec;
        if (state.camera.projectionMode === "altaz") {
            const aa = _altazFromJ2000RaDec(state.mountRa, state.mountDec);
            state.camera.lookAlt = aa.alt;
            state.camera.lookAz = aa.az;
        }
    }
    scheduleDraw();
}

// Snap the camera to the current sensor-driven mount/aim pip and
// engage follow — every subsequent pushToTick re-centers. Pan breaks
// the follow. Used by Razor's push-to tap branch immediately after
// promoting a tap to active push-to target.
export function centerOnMountAim() {
    if (state.mountRa == null || state.mountDec == null) {
        // No pip yet (sensors haven't produced a pose). Arm the follow
        // anyway — the next push-to tick will jump the camera as soon
        // as the first sample lands.
        state.followingMountAim = true;
        return;
    }
    state.camera.lookRa = state.mountRa;
    state.camera.lookDec = state.mountDec;
    if (state.camera.projectionMode === "altaz") {
        const aa = _altazFromJ2000RaDec(state.mountRa, state.mountDec);
        state.camera.lookAlt = aa.alt;
        state.camera.lookAz = aa.az;
    }
    state.followingMountAim = true;
    scheduleDraw();
}

// Convenience: toggle constellation-line drawing. Kept as a single
// entry point because the existing LINES button is a one-press toggle
// for both lines and labels (the settings page will expose them
// separately when it lands).
export function setShowConstellations(on) {
    state.layers.showConstellationLines = !!on;
    state.layers.showConstellationLabels = !!on;
    scheduleDraw();
}

// Toggle mirror-image rendering for star-diagonal eyepieces. Geometry
// flips left-right; labels stay readable. Pan and tap automatically
// compensate so the chart still feels natural.
export function setMirror(on) {
    state.mirror = !!on;
    scheduleDraw();
}

// Convert a J2000 (ra, dec) pair to (alt, az) at the current observer
// site. This is the EXACT inverse of altAzToJ2000Vec, which the basis
// builder uses — so seeding lookAlt/lookAz this way guarantees that the
// next draw's `forward` vector matches the J2000 RA/Dec we just locked
// onto. Using orientation.computeAltAzFromRaDec instead would skip the
// precession step and produce ~0.5° HA error, doubled into az near the
// meridian — which manifested as "lock missed" in altaz at transit.
function _altazFromJ2000RaDec(raJ2000, decJ2000) {
    const lstRad = orientation.getCurrentLstRad();
    const latRad = orientation.getCurrentLatRad?.() ?? 0;
    const fwd = raDecToVec(raJ2000, decJ2000);
    return j2000VecToAltAz(fwd, latRad, lstRad, new Date());
}

// Switch projection mode between equatorial (default — celestial north up)
// and altaz (zenith up). Stars sweep across the chart with sidereal time
// in altaz, so a slow redraw timer is started/stopped here as needed.
// Switching syncs the canonical look pair from whichever direction is
// fresher: equatorial → altaz computes alt/az from current lookRa/lookDec
// + LST; altaz → equatorial relies on draw()'s already-resynced ra/dec.
export function setProjectionMode(mode) {
    if (mode !== "equatorial" && mode !== "altaz") return;
    if (state.camera.projectionMode === mode) return;

    if (mode === "altaz") {
        // Seed alt/az from current J2000 ra/dec so the camera doesn't jump.
        const aa = _altazFromJ2000RaDec(state.camera.lookRa, state.camera.lookDec);
        state.camera.lookAlt = aa.alt;
        state.camera.lookAz = aa.az;
    }
    state.camera.projectionMode = mode;
    syncAltazRedrawTimer();
    scheduleDraw();
}

// Slow tick (1 Hz) that schedules a redraw so the sky drifts visibly
// in altaz FREE mode. Pure display: the canonical (lookAlt, lookAz) is
// fixed during the drift, but the J2000 forward/zenith vectors that
// derive from it depend on LST and so change over time. Gated to the
// only mode where it matters; LIVE has its own 20 Hz tick already.
let _altazDriftId = null;
function syncAltazRedrawTimer() {
    const wantTimer =
        state.camera.projectionMode === "altaz" && state.mode === "free";
    if (wantTimer && _altazDriftId === null) {
        _altazDriftId = setInterval(() => scheduleDraw(), 1000);
    } else if (!wantTimer && _altazDriftId !== null) {
        clearInterval(_altazDriftId);
        _altazDriftId = null;
    }
}

// Build a dual-thumb vertical magnitude-band slider inside `containerEl`.
// Drives state.magBright / state.magFaint and triggers a redraw on change.
// Range is hard-coded -3 (brighter than any catalog entry) to 14 (deeper
// than the DSO catalog reaches). Snapped to 0.5-mag increments. Document-
// level pointermove/up listeners keep the drag alive when the user's
// finger leaves the thumb element — no setPointerCapture interop needed.
const MAG_RANGE_MIN = -3;
const MAG_RANGE_MAX = 14;
const MAG_RANGE_SPAN = MAG_RANGE_MAX - MAG_RANGE_MIN;

function magToY(mag) {
    return ((MAG_RANGE_MAX - mag) / MAG_RANGE_SPAN) * 100;
}
function yToMag(yPct) {
    const m = MAG_RANGE_MAX - (yPct / 100) * MAG_RANGE_SPAN;
    return Math.max(MAG_RANGE_MIN, Math.min(MAG_RANGE_MAX, Math.round(m * 2) / 2));
}

export function initMagSlider(containerEl) {
    if (!containerEl || containerEl.dataset.eslMagInit === "1") return;
    containerEl.dataset.eslMagInit = "1";

    // Inline styles — no external CSS dependency, isolation-safe.
    Object.assign(containerEl.style, {
        position: "absolute", right: "8px", top: "20%", height: "60%",
        width: "32px", zIndex: "12", touchAction: "none", userSelect: "none",
    });

    const track = document.createElement("div");
    Object.assign(track.style, {
        position: "absolute", left: "50%", top: "0", bottom: "0", width: "1px",
        transform: "translateX(-50%)", background: "rgba(255,255,255,0.18)",
    });
    containerEl.appendChild(track);

    const band = document.createElement("div");
    Object.assign(band.style, {
        position: "absolute", left: "50%", width: "5px",
        transform: "translateX(-50%)", background: "rgba(77,171,247,0.32)",
        borderRadius: "3px", pointerEvents: "none",
    });
    containerEl.appendChild(band);

    const label = document.createElement("div");
    Object.assign(label.style, {
        position: "absolute", top: "-16px", left: "50%",
        transform: "translateX(-50%)", color: "#8cf",
        font: "10px ui-monospace, Menlo, monospace", pointerEvents: "none",
    });
    label.textContent = "MAG";
    containerEl.appendChild(label);

    function makeThumb() {
        const t = document.createElement("div");
        Object.assign(t.style, {
            position: "absolute", left: "50%", width: "26px", height: "16px",
            transform: "translate(-50%, -50%)", background: "#1a1a2e",
            border: "1px solid #4dabf7", borderRadius: "3px",
            color: "#8cf", font: "10px ui-monospace, Menlo, monospace",
            lineHeight: "14px", textAlign: "center", cursor: "grab",
            touchAction: "none",
        });
        containerEl.appendChild(t);
        return t;
    }
    const faintThumb = makeThumb();
    const brightThumb = makeThumb();

    function refresh() {
        const yFaint = magToY(state.magFaint);
        const yBright = magToY(state.magBright);
        faintThumb.style.top = yFaint + "%";
        brightThumb.style.top = yBright + "%";
        faintThumb.textContent = state.magFaint.toFixed(1);
        brightThumb.textContent = state.magBright.toFixed(1);
        band.style.top = yFaint + "%";
        band.style.height = (yBright - yFaint) + "%";
        scheduleDraw();
    }
    refresh();

    // Minimum separation (mag) between the two thumbs. Without this, a
    // user who drags the faint thumb all the way down to overlap the
    // bright thumb can't grab the faint thumb back up — both end up at
    // the same y-position and the brightThumb (second in DOM order) sits
    // on top, blocking pointerdown on faintThumb. 0.5 = one slider snap.
    const MAG_MIN_GAP = 0.5;
    function startDrag(thumb) {
        const onMove = (e) => {
            const rect = containerEl.getBoundingClientRect();
            const yPct = ((e.clientY - rect.top) / rect.height) * 100;
            const mag = yToMag(yPct);
            if (thumb === "faint") {
                state.magFaint = Math.max(state.magBright + MAG_MIN_GAP, mag);
            } else {
                state.magBright = Math.min(state.magFaint - MAG_MIN_GAP, mag);
            }
            refresh();
        };
        const onEnd = () => {
            document.removeEventListener("pointermove", onMove);
            document.removeEventListener("pointerup", onEnd);
            document.removeEventListener("pointercancel", onEnd);
        };
        document.addEventListener("pointermove", onMove);
        document.addEventListener("pointerup", onEnd);
        document.addEventListener("pointercancel", onEnd);
    }
    faintThumb.addEventListener("pointerdown", (e) => { e.stopPropagation(); startDrag("faint"); });
    brightThumb.addEventListener("pointerdown", (e) => { e.stopPropagation(); startDrag("bright"); });
}

// Replace the cached solar-system body list. Each entry is
// { name, raHours, decDeg } in J2000. Razor pushes this every
// State.OnChange tick; positions slow enough that 1 Hz is overkill but
// the cost is microseconds and the redraw is already happening.
export function setPlanets(list) {
    if (!Array.isArray(list)) return;
    state.planets = list.map(p => ({
        name: p.name,
        ra: p.raHours * Math.PI / 12,
        dec: p.decDeg * Math.PI / 180,
    }));
    scheduleDraw();
}

// Toggle the chart's lock-to-mount behavior. When `on`, the camera
// snaps to the supplied J2000 RA/Dec immediately and tracks subsequent
// mount updates. Razor passes current mount position along so the snap
// doesn't depend on a prior setMountPosition push having landed (those
// are deduped — could easily be stale at the instant of toggle).
// Any pan gesture clears the lock and notifies the host.
export function setLockToMount(on, raHours, decDeg) {
    state.lockedToMount = !!on;
    if (state.lockedToMount && state.mode === "free") {
        if (raHours != null && decDeg != null) {
            state.mountRa = raHours * Math.PI / 12;
            state.mountDec = decDeg * Math.PI / 180;
            state.camera.lookRa = state.mountRa;
            state.camera.lookDec = state.mountDec;
        } else if (state.mountRa != null && state.mountDec != null) {
            state.camera.lookRa = state.mountRa;
            state.camera.lookDec = state.mountDec;
        }
        // Sync alt/az if the chart is currently rendering in that frame.
        if (state.camera.projectionMode === "altaz") {
            const aa = _altazFromJ2000RaDec(state.camera.lookRa, state.camera.lookDec);
            state.camera.lookAlt = aa.alt;
            state.camera.lookAz = aa.az;
        }
        scheduleDraw();
    }
}

export function setSensorSign(name, sign) {
    const dbg = window._starSeekerDebug?.debug;
    if (!dbg) return;
    if (name === "beta") dbg.betaSign = sign;
    else if (name === "gamma") dbg.gammaSign = sign;
    else if (name === "yaw") dbg.yawSign = sign;
}

export function setMode(mode) {
    if (mode !== "free" && mode !== "live") return;
    if (state.mode === mode) return;

    if (mode === "live") {
        state.mode = "live";
        if (state.liveTickId === null) {
            state.liveTickId = setInterval(liveTick, 50);  // 20 Hz camera update
        }
    } else {
        if (state.liveTickId !== null) {
            clearInterval(state.liveTickId);
            state.liveTickId = null;
        }
        state.mode = "free";
        state.liveBasis = null;
        scheduleDraw();
    }
    // Sensors are shared with push-to; let the coordinator decide
    // whether they should be running based on the combined state.
    syncSensorState();
    syncAltazRedrawTimer();
}

function liveTick() {
    const look = orientation.getCurrentLook();
    if (look === null) return;
    // orientation.js produces basis vectors and ra/dec in JNow frame
    // (LST is JNow-relative). The chart's catalog and mount pip live
    // in J2000. Without this conversion, projecting J2000 vectors
    // through a JNow basis offsets everything by the precession
    // amount (~0.4° at 26 years post-J2000) — visible as the mount
    // pip drifting off the Telrad center even when the OTA is
    // physically centered on the target.
    const now = new Date();
    const j2k = jNowToJ2000(look.ra, look.dec, now);
    state.camera.lookRa = j2k.ra;
    state.camera.lookDec = j2k.dec;
    state.liveBasis = {
        forward: jNowVecToJ2000Vec(look.basis.forward, now),
        right:   jNowVecToJ2000Vec(look.basis.right, now),
        up:      jNowVecToJ2000Vec(look.basis.up, now),
    };
    state.pose = look;
    scheduleDraw();
}

// Set the chart's look vector + FOV. Used by Blazor for boot-centering
// and state-restore on tab re-open. fovDeg defaults to current FOV so
// callers can pass nulls for "leave alone".
export function setLook(raHours, decDeg, fovDeg) {
    if (raHours != null) state.camera.lookRa = raHours * Math.PI / 12;
    if (decDeg != null)  state.camera.lookDec = decDeg * Math.PI / 180;
    if (fovDeg != null) {
        state.camera.fov = fovDeg * Math.PI / 180;
        orientation.setFov(state.camera.fov);
    }
    // In altaz mode the canonical pair is alt/az — sync from the new
    // ra/dec so draw() doesn't snap back to the old altaz target.
    if (state.camera.projectionMode === "altaz") {
        const aa = _altazFromJ2000RaDec(state.camera.lookRa, state.camera.lookDec);
        state.camera.lookAlt = aa.alt;
        state.camera.lookAz = aa.az;
    }
    scheduleDraw();
}

// Snapshot the current camera + mode so Blazor can re-apply on the next
// tab open. Returns degrees / hours for ergonomic Razor interop.
export function getCameraState() {
    return {
        raHours: state.camera.lookRa * 12 / Math.PI,
        decDeg:  state.camera.lookDec * 180 / Math.PI,
        fovDeg:  state.camera.fov * 180 / Math.PI,
        mode:    state.mode,
        mirror:  state.mirror,
        projectionMode: state.camera.projectionMode,
    };
}

// Debug handle — tweak from Safari/Chrome console.
window._starSeeker = {
    state,
    draw,
    setLook(raHours, decDeg, fovDeg = 40) {
        state.camera.lookRa = raHours * Math.PI / 12;
        state.camera.lookDec = decDeg * Math.PI / 180;
        state.camera.fov = fovDeg * Math.PI / 180;
        orientation.setFov(state.camera.fov);
        draw();
    },
    setMagFilter(bright, faint) {
        state.magBright = Math.max(MAG_RANGE_MIN, Math.min(MAG_RANGE_MAX, bright));
        state.magFaint = Math.max(state.magBright, Math.min(MAG_RANGE_MAX, faint));
        draw();
    },
    showLines(on) {
        state.layers.showConstellationLines = !!on;
        state.layers.showConstellationLabels = !!on;
        draw();
    },
    setLayer(name, on) {
        if (!Object.prototype.hasOwnProperty.call(state.layers, name)) return;
        state.layers[name] = !!on;
        draw();
    },
    setMode,
};
