// Star Seeker — canvas rendering.
// Receives pre-loaded catalogs, camera parameters, and a 2D context.

import { raDecToVec, buildBasis, project, jNowToJ2000, altAzToJ2000Vec } from "./projection.js";

// Solar-system body styling. Colors picked for chromatic survival under
// the night-mode CSS filter (Mars in particular: orange-red rather than
// pure red so it doesn't collapse into background red after hue-rotate).
const PLANET_STYLE = {
    "Sun":     { color: "#ffd84d", size: 7 },
    "Moon":    { color: "#c8c8c8", size: 7 },
    "Mercury": { color: "#8b8682", size: 3 },
    "Venus":   { color: "#f5e9d3", size: 5 },
    "Mars":    { color: "#e85a2a", size: 4 },
    "Jupiter": { color: "#d9b274", size: 5 },
    "Saturn":  { color: "#e8d68a", size: 4 },
    "Uranus":  { color: "#b6e5e3", size: 3 },
    "Neptune": { color: "#4467d1", size: 3 },
    "Pluto":   { color: "#c89c80", size: 2 },
};

const DSO_COLOR = {
    // Galaxies — dusty red
    "G-S": "#b58080", "G-E": "#b58080", "G-Ir": "#b58080",
    "G-QSO": "#b58080",
    // Nebulae
    "PN": "#66ccaa",     // planetary: teal
    "EN": "#ffb066",     // emission: orange
    "RN": "#8090ff",     // reflection: blue
    "DN": "#555555",     // dark: grey
    "SNR": "#ff6666",    // supernova: red
    "EN+OC": "#ffb066",
    // Clusters
    "OC": "#ffee66",     // open: yellow
    "GC": "#ffaa55",     // globular: amber
    // Other
    "AST": "#888888",
    "EXO": "#999999",
    "MWP": "#888888",
    "?":   "#666666",
};

// Carry-correct HMS for RA hours. Rounds to 0.1s, carries up so 23:59:59.96
// becomes 00:00:00.0 (matches FormatRa in CoordinateService.cs).
function formatRaHms(raHours) {
    raHours = ((raHours % 24) + 24) % 24;
    let tenths = Math.round(raHours * 36000);
    if (tenths >= 24 * 36000) tenths -= 24 * 36000;
    const h = Math.floor(tenths / 36000);
    const rem = tenths % 36000;
    const m = Math.floor(rem / 600);
    const s = (rem % 600) / 10;
    return `${String(h).padStart(2, "0")}h ${String(m).padStart(2, "0")}m ${s.toFixed(1).padStart(4, "0")}s`;
}

// Carry-correct DMS for Dec degrees. Rounds to 0.1", carries up so
// 89:59:59.96 becomes 90:00:00.0 (matches FormatDec in CoordinateService.cs).
function formatDecDms(decDeg) {
    const sign = decDeg >= 0 ? "+" : "-";
    decDeg = Math.abs(decDeg);
    const tenths = Math.round(decDeg * 36000);
    const d = Math.floor(tenths / 36000);
    const rem = tenths % 36000;
    const m = Math.floor(rem / 600);
    const s = (rem % 600) / 10;
    return `${sign}${String(d).padStart(2, "0")}°${String(m).padStart(2, "0")}'${s.toFixed(1).padStart(4, "0")}"`;
}

export function renderFrame(ctx, stars, dsos, camera, size, options) {
    const { lookRa, lookDec, fov } = camera;
    const { width, height } = size;
    const magBright = options?.magBright ?? -3.0;
    const magFaint = options?.magFaint ?? 9.0;
    const drawReticle = options?.reticle ?? false;
    const telemetry = options?.telemetry ?? null;
    const constellations = options?.constellations ?? null;
    const starsByHip = options?.starsByHip ?? null;
    // Prefer an externally supplied basis (Live mode uses phone-anchored
    // basis to avoid the celestial-pole singularity). Fall back to
    // celestial-north-up when not provided (Free mode).
    let basis = options?.basis ?? buildBasis(lookRa, lookDec);
    // Mirror mode: negate the right-vector. Every project() call below
    // returns a horizontally flipped x; text glyphs render normally at
    // those flipped positions — exactly the behavior wanted for a
    // star-diagonal eyepiece view (geometry mirrors, labels readable).
    if (options?.mirror) {
        basis = {
            forward: basis.forward,
            right: [-basis.right[0], -basis.right[1], -basis.right[2]],
            up: basis.up,
        };
    }

    // Layer registry from caller. Each draw call below gates on a key
    // here. Default-on (`!== false`) so a missing/undefined layers
    // object yields the legacy "draw everything" behavior — used by
    // any caller that hasn't migrated to the registry yet.
    const layers = options?.layers ?? {};
    const showLayer = (name) => layers[name] !== false;

    ctx.fillStyle = "#000";
    ctx.fillRect(0, 0, width, height);

    // RA/Dec grid — drawn underneath the four reference circles so the
    // yellow great-circle lines remain visually dominant. FOV-adaptive
    // step; edge labels at the rightmost (Dec) / bottommost (RA) on-canvas
    // sample of each line. Subtle blue-white at low alpha. lookDec drives
    // pole-aware RA-line thinning — at high latitudes the meridians
    // converge geometrically, so we skip every Nth one.
    drawRaDecGrid(ctx, basis, fov, width, height,
        showLayer("showRaDecGrid"), showLayer("showRaDecLabels"), lookDec);

    // Alt/Az grid — same FOV-adaptive step, but in horizon coordinates
    // (alt parallels + az meridians). Each sample is computed in JNow
    // alt/az and converted to a J2000 vector via altAzToJ2000Vec so it
    // projects through the same basis the catalog stars use. Cardinal
    // directions (N/E/S/W) get letter labels in place of numerics.
    if (options?.lstRad != null && options?.observerLatRad != null) {
        drawAltAzGrid(ctx, basis, fov, width, height,
            showLayer("showAltAzGrid"), showLayer("showAltAzLabels"),
            options.observerLatRad, options.lstRad, options?.lookAlt ?? 0);
    }

    // Reference circles — drawn FIRST so everything else paints on top.
    // Each helper accepts (drawLine, drawLabel) so the line can stay
    // visible while the tangent label is suppressed (settings-page UX).
    drawEcliptic(ctx, basis, fov, width, height,
        showLayer("showEcliptic"), showLayer("showEclipticLabel"));
    drawCelestialEquator(ctx, basis, fov, width, height,
        showLayer("showCelestialEquator"), showLayer("showCelestialEquatorLabel"));
    drawGalacticEquator(ctx, basis, fov, width, height,
        showLayer("showGalacticEquator"), showLayer("showGalacticEquatorLabel"));
    if (options?.lstRad != null) {
        drawLocalMeridian(ctx, basis, fov, width, height, options.lstRad,
            showLayer("showMeridian"), showLayer("showMeridianLabel"));
        if (options?.observerLatRad != null && showLayer("showZenith")) {
            drawZenithMarker(ctx, basis, fov, width, height,
                             options.lstRad, options.observerLatRad);
        }
    }

    // Constellation lines (draw below DSOs and stars so they read as
    // background skeleton). Each edge endpoint is a canonical catalog
    // ID ("HIP27989", "HR2061", etc.); positions are looked up in the
    // artifact's stars manifest.
    if (showLayer("showConstellationLines") && constellations && options?.constellationStars) {
        const manifest = options.constellationStars;
        ctx.strokeStyle = "rgba(140, 180, 240, 0.75)";
        ctx.lineWidth = 1.5;
        for (const con of constellations) {
            if (!con.edges) continue;
            for (const edge of con.edges) {
                const a = manifest[edge[0]];
                const b = manifest[edge[1]];
                if (!a || !b) continue;
                const aRa = a.raHours * Math.PI / 12;
                const aDec = a.decDeg * Math.PI / 180;
                const bRa = b.raHours * Math.PI / 12;
                const bDec = b.decDeg * Math.PI / 180;
                const pa = project(raDecToVec(aRa, aDec), basis, fov, width, height);
                const pb = project(raDecToVec(bRa, bDec), basis, fov, width, height);
                if (!pa || !pb) continue;
                const OFF = 200;
                if ((pa.x < -OFF || pa.x > width + OFF || pa.y < -OFF || pa.y > height + OFF) &&
                    (pb.x < -OFF || pb.x > width + OFF || pb.y < -OFF || pb.y > height + OFF)) continue;
                ctx.beginPath();
                ctx.moveTo(pa.x, pa.y);
                ctx.lineTo(pb.x, pb.y);
                ctx.stroke();
            }
        }
    }

    // Constellation name labels at each star-vertex centroid. Independent
    // of showConstellationLines so a settings page can keep the skeleton
    // visible while turning off the names (or vice versa). FOV >= 20°
    // threshold prevents clutter when zoomed inside one constellation.
    if (showLayer("showConstellationLabels")
        && constellations && options?.constellationCentroids) {
        const centroids = options.constellationCentroids;
        if (fov * 180 / Math.PI >= 20) {
            ctx.save();
            ctx.font = "italic 11px ui-monospace, Menlo, monospace";
            ctx.fillStyle = "rgba(180, 200, 230, 0.55)";
            ctx.textAlign = "center";
            ctx.textBaseline = "middle";
            for (const c of centroids) {
                const p = project(c.vec, basis, fov, width, height);
                if (!p) continue;
                if (p.x < 0 || p.x > width || p.y < 0 || p.y > height) continue;
                ctx.fillText(c.name, p.x, p.y);
            }
            ctx.restore();
        }
    }

    // DSOs first (behind stars). Plus a fallback "current target icon"
    // pass for picks that aren't in dsos.json (asterisms, custom coords,
    // catalog stars filtered out of the chart's DSO build).
    const currentDsoMatch = options?.currentDsoMatch ?? null;
    const currentTargetIcon = options?.currentTargetIcon ?? null;
    if (showLayer("showDsos")) for (const d of dsos) {
        // Magnitude band filter. Catalog entries with null vmag (often
        // named objects without a recorded integrated brightness) are
        // assumed to be ~8.5 — moderately faint but on-par with typical
        // Messier-class targets. That keeps the slider's default range
        // showing them while letting the user filter them out alongside
        // stars when they drag the faint cap below 8.5.
        //
        // The user's current target bypasses the filter: their picked
        // object always shows on the chart, even when the slider would
        // otherwise hide it. Object-identity check is O(1) — no string
        // comparison every frame.
        const isCurrentTarget = d === currentDsoMatch;
        if (!isCurrentTarget) {
            const eff = d.vmag ?? 8.5;
            if (eff < magBright || eff > magFaint) continue;
        }

        const p = project(raDecToVec(d.ra, d.dec), basis, fov, width, height);
        if (!p) continue;
        if (p.x < -20 || p.x > width + 20 || p.y < -20 || p.y > height + 20) continue;

        drawDso(ctx, p, d.type);
    }

    // Current-target fallback icon — drawn at the user's selected
    // target coords when no DSO catalog match was found (asterism,
    // exoplanet host, custom RA/Dec, etc.). Always shown regardless
    // of mag slider so the user has a marker at the target position.
    if (currentTargetIcon && !currentDsoMatch) {
        const p = project(raDecToVec(currentTargetIcon.ra, currentTargetIcon.dec),
                          basis, fov, width, height);
        if (p && p.x >= -20 && p.x <= width + 20 && p.y >= -20 && p.y <= height + 20) {
            drawTargetCategoryIcon(ctx, p, currentTargetIcon);
        }
    }

    // Stars on top.
    ctx.fillStyle = "#fff";
    if (showLayer("showStars")) for (const s of stars) {
        // Same band filter as DSOs. Stars always have a vmag, so no
        // null-passes branch needed.
        if (s.vmag < magBright || s.vmag > magFaint) continue;
        const p = project(raDecToVec(s.ra, s.dec), basis, fov, width, height);
        if (!p) continue;
        if (p.x < -5 || p.x > width + 5 || p.y < -5 || p.y > height + 5) continue;

        // Size by magnitude. Sirius ≈ -1.5 → ~4.8 px. mag 3 → ~2.4 px. mag 6 → ~0.8 px.
        const r = Math.max(0.5, 4.0 - 0.55 * s.vmag);
        ctx.beginPath();
        ctx.arc(p.x, p.y, r, 0, Math.PI * 2);
        ctx.fill();
    }

    // Solar-system bodies — Sun, Moon, planets, Pluto. Drawn after stars so
    // they read as foreground; below the mount Telrad and screen reticle.
    // Bypass any mag filter (we don't have one anyway). Names labeled below.
    // Wrapped in save/restore so the textAlign change for centered labels
    // doesn't leak into the bottom-left telemetry block (which expects
    // the default "start" alignment and doesn't set it explicitly).
    const planets = options?.planets ?? null;
    if (planets && showLayer("showPlanets")) {
        ctx.save();
        ctx.font = "11px ui-monospace, Menlo, monospace";
        ctx.textAlign = "center";
        ctx.textBaseline = "top";
        const drawPlanetLabels = showLayer("showPlanetLabels");
        for (const p of planets) {
            const style = PLANET_STYLE[p.name];
            if (!style) continue;
            const proj = project(raDecToVec(p.ra, p.dec), basis, fov, width, height);
            if (!proj) continue;
            if (proj.x < -50 || proj.x > width + 50 || proj.y < -50 || proj.y > height + 50) continue;

            ctx.fillStyle = style.color;
            ctx.beginPath();
            ctx.arc(proj.x, proj.y, style.size, 0, Math.PI * 2);
            ctx.fill();
            if (drawPlanetLabels)
                ctx.fillText(p.name, proj.x, proj.y + style.size + 3);
        }
        ctx.restore();
    }

    // Orange "Mount" marker — projected at the mount's current sky
    // position when connected. Single open ring (no center crosshair) so
    // the object the mount is pointing at stays unobscured. Four short
    // stub lines outside the ring give a visual cross reference without
    // crossing the marker's interior.
    const mountReticle = options?.mountReticle ?? null;
    if (mountReticle != null && showLayer("showMountMarker")) {
        const mp = project(raDecToVec(mountReticle.ra, mountReticle.dec), basis, fov, width, height);
        if (mp && mp.x >= -50 && mp.x <= width + 50 && mp.y >= -50 && mp.y <= height + 50) {
            ctx.save();
            ctx.strokeStyle = "#ff922b";
            ctx.fillStyle = "#ff922b";
            ctx.lineWidth = 2;
            const r = 12, gap = 4, stub = 8;
            ctx.beginPath();
            ctx.arc(mp.x, mp.y, r, 0, Math.PI * 2);
            ctx.stroke();
            ctx.beginPath();
            ctx.moveTo(mp.x - r - gap, mp.y); ctx.lineTo(mp.x - r - gap - stub, mp.y);
            ctx.moveTo(mp.x + r + gap, mp.y); ctx.lineTo(mp.x + r + gap + stub, mp.y);
            ctx.moveTo(mp.x, mp.y - r - gap); ctx.lineTo(mp.x, mp.y - r - gap - stub);
            ctx.moveTo(mp.x, mp.y + r + gap); ctx.lineTo(mp.x, mp.y + r + gap + stub);
            ctx.stroke();
            ctx.font = "12px sans-serif";
            ctx.textBaseline = "bottom";
            ctx.textAlign = "center";
            ctx.fillText("Mount", mp.x, mp.y - r - gap - stub - 4);
            ctx.restore();
        }
    }

    // Pending chart target — yellow open ring + label at the user's
    // Target-page selection (or any pending chart target). Distinct
    // from the active push-to glyph (green filled cross) so the user
    // can see "this is what you picked, tap it to push-to it."
    //
    // If the pending target also carries a category (DSO type or
    // "planet"), draw the appropriate catalog icon inside the ring so
    // the user has a visual marker even when the magnitude slider has
    // hidden the underlying catalog draw call. drawTargetCategoryIcon
    // dispatches to drawDso for DSOs; planets get a small filled disk;
    // stars + unknowns get a small filled dot.
    const pending = options?.pendingTarget ?? null;
    if (pending != null) {
        const pp = project(raDecToVec(pending.ra, pending.dec), basis, fov, width, height);
        if (pp && pp.x >= -50 && pp.x <= width + 50 && pp.y >= -50 && pp.y <= height + 50) {
            drawTargetCategoryIcon(ctx, pp, pending);
            ctx.save();
            ctx.strokeStyle = "#ffd84d";
            ctx.fillStyle = "#ffd84d";
            ctx.lineWidth = 1.5;
            const r = 9;
            ctx.beginPath();
            ctx.arc(pp.x, pp.y, r, 0, Math.PI * 2);
            ctx.stroke();
            ctx.font = "11px sans-serif";
            ctx.textBaseline = "bottom";
            ctx.textAlign = "center";
            if (pending.name) ctx.fillText(pending.name, pp.x, pp.y - r - 3);
            ctx.restore();
        }
    }

    // Push-to navigation vector — arrow from the mount pip toward the
    // selected target with a distance label. Drawn after the mount
    // marker so the arrow base sits on top of the orange ring; before
    // the Telrad reticle so the chart center stays uncluttered. Only
    // built (in starseeker.js's buildPushVector) when push-to is on
    // and a target is selected.
    if (options?.pushVector) {
        drawPushVector(ctx, basis, fov, width, height, options.pushVector);
    }

    // Center-label "vibe" pass — when zoomed in enough that individual
    // objects are well-resolved, label whatever is closest to screen
    // center. Single label, recomputed each frame as the camera or
    // sky moves. Threshold: FOV <= 60°.
    const fovDegForLabel = fov * 180 / Math.PI;
    if (fovDegForLabel <= 60 && showLayer("showCenterLabel")) {
        const cxL = width / 2, cyL = height / 2;
        const starNames = options?.starNames ?? {};
        const bayer = options?.bayerDesignations ?? {};
        const nodeLabels = options?.nodeLabels ?? {};
        // Label cutoff: only objects within the inner-Telrad ring (0.5°)
        // of chart center get a label. Mirrors the same min-22-px outer
        // clamp the Telrad reticle uses so the cutoff visually matches
        // the drawn ring at any FOV.
        const halfMinL = Math.min(width, height) / 2;
        const pxPerDegL = halfMinL / (2 * Math.tan(fov / 4)) * (Math.PI / 180);
        const trueOuterL = 4.0 * pxPerDegL;
        const telradScaleL = trueOuterL < 22 ? 22 / trueOuterL : 1;
        const labelMaxPx2 = (0.5 * pxPerDegL * telradScaleL) ** 2;
        let bestDist2 = Infinity;
        let bestName = null;
        let bestPos = null;
        for (const s of stars) {
            if (s.vmag < magBright || s.vmag > magFaint) continue;
            const p = project(raDecToVec(s.ra, s.dec), basis, fov, width, height);
            if (!p) continue;
            if (p.x < 0 || p.x > width || p.y < 0 || p.y > height) continue;
            const dx = p.x - cxL, dy = p.y - cyL;
            const d2 = dx * dx + dy * dy;
            if (d2 > labelMaxPx2) continue;
            if (d2 < bestDist2) {
                bestDist2 = d2;
                const key = String(s.hip);
                // Lookup priority:
                //   nodeLabels  (constellation-line node — covers Bayer/Flamsteed/HIP+abbr)
                //   bayer       (any star with a Bayer designation)
                //   starNames   (proper name)
                //   "HIP nnnn"  (fallback)
                bestName = nodeLabels[key] ?? bayer[key] ?? starNames[key] ?? `HIP ${s.hip}`;
                bestPos = p;
            }
        }
        for (const d of dsos) {
            const eff = d.vmag ?? 8.5;
            if (eff < magBright || eff > magFaint) continue;
            const p = project(raDecToVec(d.ra, d.dec), basis, fov, width, height);
            if (!p) continue;
            if (p.x < 0 || p.x > width || p.y < 0 || p.y > height) continue;
            const dx = p.x - cxL, dy = p.y - cyL;
            const d2 = dx * dx + dy * dy;
            if (d2 > labelMaxPx2) continue;
            if (d2 < bestDist2) {
                bestDist2 = d2;
                bestName = d.name;
                bestPos = p;
            }
        }
        if (planets) {
            for (const pl of planets) {
                const p = project(raDecToVec(pl.ra, pl.dec), basis, fov, width, height);
                if (!p) continue;
                if (p.x < 0 || p.x > width || p.y < 0 || p.y > height) continue;
                const dx = p.x - cxL, dy = p.y - cyL;
                const d2 = dx * dx + dy * dy;
                if (d2 > labelMaxPx2) continue;
                if (d2 < bestDist2) {
                    bestDist2 = d2;
                    bestName = pl.name;
                    bestPos = p;
                }
            }
        }
        if (bestPos && bestName) {
            ctx.save();
            ctx.font = "12px ui-monospace, Menlo, monospace";
            ctx.textAlign = "left";
            ctx.textBaseline = "top";
            // Label sits right + below the object. If that would clip the
            // right edge, flip to the left side so the text stays on canvas.
            const tw = ctx.measureText(bestName).width;
            const lh = 14;
            let lx = bestPos.x + 8;
            const ly = bestPos.y + 6;
            if (lx + tw + 4 > width) lx = bestPos.x - 8 - tw;
            ctx.fillStyle = "rgba(0,0,0,0.6)";
            ctx.fillRect(lx - 2, ly - 1, tw + 4, lh);
            ctx.fillStyle = "#fff";
            ctx.fillText(bestName, lx, ly);
            ctx.restore();
        }
    }

    // Selection marker — drawn after planets/mount, before the Telrad
    // reticle, so the user sees what they tapped. PN-like glyph (filled
    // green disk + 4 ticks) but rotated 45° so it's distinct from the
    // catalog's actual PN symbol.
    //
    // For active push-to selections (carried through from
    // state.activePushTarget) the selection object also carries
    // category/type — paint the catalog icon underneath so the user
    // sees the object's nature even when the magnitude slider has
    // filtered it out of the regular catalog draw.
    const selection = options?.selection ?? null;
    if (selection != null) {
        const sp = project(raDecToVec(selection.ra, selection.dec), basis, fov, width, height);
        if (sp && sp.x >= -50 && sp.x <= width + 50 && sp.y >= -50 && sp.y <= height + 50) {
            if (selection.category) {
                drawTargetCategoryIcon(ctx, sp, selection);
            }
            ctx.save();
            ctx.strokeStyle = "#00ff41";
            ctx.fillStyle = "#00ff41";
            ctx.lineWidth = 1.5;
            ctx.beginPath();
            ctx.arc(sp.x, sp.y, 3, 0, Math.PI * 2);
            ctx.fill();
            const r1 = 5, r2 = 10;
            const c45 = Math.SQRT1_2;
            ctx.beginPath();
            ctx.moveTo(sp.x + r1*c45, sp.y + r1*c45); ctx.lineTo(sp.x + r2*c45, sp.y + r2*c45);
            ctx.moveTo(sp.x - r1*c45, sp.y + r1*c45); ctx.lineTo(sp.x - r2*c45, sp.y + r2*c45);
            ctx.moveTo(sp.x + r1*c45, sp.y - r1*c45); ctx.lineTo(sp.x + r2*c45, sp.y - r2*c45);
            ctx.moveTo(sp.x - r1*c45, sp.y - r1*c45); ctx.lineTo(sp.x - r2*c45, sp.y - r2*c45);
            ctx.stroke();
            ctx.restore();
        }
    }

    // Telrad reticle (screen center). Three concentric rings at the
    // real-Telrad spacings 0.5° / 2° / 4°, scaled to current chart FOV
    // so they accurately represent eyepiece field at any zoom. Outer
    // ring has a minimum pixel size (so extreme zoom-out keeps the
    // reticle visible); inner rings scale up proportionally to maintain
    // the 1:4:8 ratio. No center mark — the object stays unobscured.
    if (drawReticle && showLayer("showTelrad")) {
        const cx = width / 2, cy = height / 2;
        // Match the stereographic project()'s scale factor at chart center.
        // x_offset(θ) = tan(θ/2) · halfMin / tan(fov/4); near θ=0 this
        // linearizes to (halfMin / (2·tan(fov/4))) · θ, i.e. pxPerRad.
        // Convert to deg with π/180.
        const halfMin = Math.min(width, height) / 2;
        const pxPerDeg = halfMin / (2 * Math.tan(fov / 4)) * (Math.PI / 180);
        const TELRAD_DEG = [0.5, 2.0, 4.0];
        const MIN_OUTER_PX = 22;
        const trueOuter = TELRAD_DEG[2] * pxPerDeg;
        const scale = trueOuter < MIN_OUTER_PX ? MIN_OUTER_PX / trueOuter : 1;
        ctx.save();
        ctx.strokeStyle = "#ff3b3b";
        ctx.lineWidth = 1;
        ctx.globalAlpha = 0.75;
        for (const radiusDeg of TELRAD_DEG) {
            const r = radiusDeg * pxPerDeg * scale;
            ctx.beginPath();
            ctx.arc(cx, cy, r, 0, Math.PI * 2);
            ctx.stroke();
        }
        // Diameter labels at the top of each ring, only at narrow FOVs
        // where the rings are large enough to read labels against.
        if (fov * 180 / Math.PI <= 15 && showLayer("showTelradLabels")) {
            ctx.font = "10px ui-monospace, Menlo, monospace";
            ctx.fillStyle = "#ff3b3b";
            ctx.textAlign = "center";
            ctx.textBaseline = "bottom";
            ctx.setLineDash([]);
            for (const radiusDeg of TELRAD_DEG) {
                const r = radiusDeg * pxPerDeg * scale;
                const dia = (radiusDeg * 2).toFixed(radiusDeg < 1 ? 1 : 0);
                ctx.fillText(`${dia}°`, cx, cy - r - 1);
            }
        }
        ctx.restore();
    }

    // Bottom-left readout — FOV + mag band always; sensor alt/az/RA/Dec when in Live.
    if (!showLayer("showTelemetry")) return;
    const fovDeg = fov * 180 / Math.PI;
    const fovStr = `fov ${fovDeg.toFixed(fovDeg < 10 ? 1 : 0)}°`;
    // Compact mag display: "mag ≤9.0" when bright cap pinned at default,
    // else "mag -3.0..9.0" so the user can see the band without staring
    // at the slider thumbs.
    const magStr = magBright <= -3.0
        ? `mag ≤${magFaint.toFixed(1)}`
        : `mag ${magBright.toFixed(1)}..${magFaint.toFixed(1)}`;
    const lines = [`${fovStr}   ${magStr}`];

    if (telemetry) {
        // telemetry is supplied already in JNow frame (starseeker.js
        // converts J2000→JNow before passing it). That keeps every value
        // here — alt/az AND ra/dec — in lockstep with the mount telemetry
        // strip at the top of the page.
        const altDeg = telemetry.alt * 180 / Math.PI;
        const azDeg = telemetry.az * 180 / Math.PI;
        const raH = ((telemetry.ra * 12 / Math.PI) % 24 + 24) % 24;
        const decDeg = telemetry.dec * 180 / Math.PI;
        lines.push(
            `alt ${altDeg >= 0 ? " " : ""}${altDeg.toFixed(1)}°   az ${azDeg.toFixed(1)}°`,
            `ra  ${formatRaHms(raH)}`,
            `dec ${formatDecDms(decDeg)}`,
        );
    }

    // Push-to readout — appended after the (optional) telemetry block.
    //   browse:   "pip: sensor"
    //   navigate: "→ <target>"  +  "Δ <sep>"  (or "on target" when <0.2°)
    const ptReadout = options?.pushToReadout ?? null;
    if (ptReadout && ptReadout.mode !== "off") {
        if (ptReadout.mode === "browse") {
            lines.push("pip: sensor");
        } else if (ptReadout.mode === "navigate") {
            const sep = ptReadout.separationDeg;
            const sepStr = sep == null
                ? ""
                : sep < 0.2 ? "on target"
                : sep < 1.0 ? `Δ ${(sep * 60).toFixed(0)}'`
                : `Δ ${sep.toFixed(1)}°`;
            lines.push(`→ ${ptReadout.targetName}`);
            if (sepStr) lines.push(sepStr);
        }
    }

    ctx.font = "12px ui-monospace, Menlo, monospace";
    ctx.textBaseline = "bottom";
    ctx.fillStyle = "rgba(0,0,0,0.55)";
    const pad = 4, lh = 15;
    const maxW = Math.max(...lines.map(l => ctx.measureText(l).width));
    const boxY = height - 8 - lh * lines.length - pad;
    ctx.fillRect(8 - pad, boxY, maxW + pad * 2, lh * lines.length + pad * 2);
    ctx.fillStyle = "#8cf";
    for (let i = 0; i < lines.length; i++) {
        ctx.fillText(lines[i], 8, height - 8 - lh * (lines.length - 1 - i));
    }
}

// Connect a sequence of sky sample points into a poly-line in screen
// space. Each sample is either a {ra, dec} object (radians) or a raw
// J2000 unit-vector array — the latter is used by the alt/az grid,
// which generates J2000 vectors directly via altAzToJ2000Vec.
// Breaks the line on projection failure (point behind camera) and on
// large pixel jumps (great-circle wraparound). Caller configures
// stroke style + dash before calling.
function drawSkyPolyline(ctx, samples, basis, fov, width, height) {
    let prev = null;
    const breakDist = Math.max(width, height);
    for (const s of samples) {
        const vec = Array.isArray(s) ? s : raDecToVec(s.ra, s.dec);
        const proj = project(vec, basis, fov, width, height);
        if (!proj) { prev = null; continue; }
        if (prev) {
            const dx = proj.x - prev.x, dy = proj.y - prev.y;
            if (dx * dx + dy * dy < breakDist * breakDist) {
                ctx.beginPath();
                ctx.moveTo(prev.x, prev.y);
                ctx.lineTo(proj.x, proj.y);
                ctx.stroke();
            }
        }
        prev = proj;
    }
}

// Project the given samples and return the on-canvas screen position
// closest to chart center, with the line's local tangent angle so the
// label can be drawn along the line. Returns null if no samples fall
// inside the viewport.
function findBestLabelPos(samples, basis, fov, width, height) {
    const cx = width / 2, cy = height / 2;
    const projected = samples.map(s =>
        project(raDecToVec(s.ra, s.dec), basis, fov, width, height));
    let bestIdx = -1;
    let bestDist = Infinity;
    for (let i = 0; i < projected.length; i++) {
        const p = projected[i];
        if (!p) continue;
        if (p.x < 0 || p.x >= width || p.y < 0 || p.y >= height) continue;
        const dx = p.x - cx, dy = p.y - cy;
        const d = dx * dx + dy * dy;
        if (d < bestDist) { bestDist = d; bestIdx = i; }
    }
    if (bestIdx < 0) return null;
    const here = projected[bestIdx];
    // Pick a neighboring projected sample for the tangent direction.
    let neighbor = null;
    for (const off of [1, -1, 2, -2, 3, -3]) {
        const idx = bestIdx + off;
        if (idx < 0 || idx >= projected.length) continue;
        if (projected[idx]) { neighbor = projected[idx]; break; }
    }
    let angle = 0;
    if (neighbor) {
        angle = Math.atan2(neighbor.y - here.y, neighbor.x - here.x);
        // Keep text right-side-up: flip angles past ±90° so the label
        // never reads upside down.
        if (angle > Math.PI / 2) angle -= Math.PI;
        else if (angle < -Math.PI / 2) angle += Math.PI;
    }
    return { x: here.x, y: here.y, angle };
}

// Italic label box in `color`, rotated to align with the line tangent
// at the anchor point. Saved state isolates the dim background and
// label-only globalAlpha from the line-stroke caller.
function drawLineLabel(ctx, pos, text, color) {
    if (!pos) return;
    ctx.save();
    ctx.font = "italic 10px ui-monospace, Menlo, monospace";
    ctx.textAlign = "left";
    ctx.textBaseline = "bottom";
    ctx.setLineDash([]);
    ctx.globalAlpha = 0.9;
    ctx.translate(pos.x, pos.y);
    ctx.rotate(pos.angle ?? 0);
    const tw = ctx.measureText(text).width;
    ctx.fillStyle = "rgba(0,0,0,0.55)";
    ctx.fillRect(5, -13, tw + 4, 13);
    ctx.fillStyle = color;
    ctx.fillText(text, 7, -2);
    ctx.restore();
}

// Ecliptic plane — Sun's apparent path. β = 0 in the ecliptic frame,
// rotated to equatorial by obliquity. Static great circle in J2000.
const ECLIPTIC_OBLIQUITY = 23.4393 * Math.PI / 180;
function drawEcliptic(ctx, basis, fov, width, height, drawLine, drawLabel) {
    if (!drawLine && !drawLabel) return;
    const samples = [];
    const N = 180;
    const cosE = Math.cos(ECLIPTIC_OBLIQUITY);
    const sinE = Math.sin(ECLIPTIC_OBLIQUITY);
    for (let i = 0; i <= N; i++) {
        const lam = (i / N) * 2 * Math.PI;
        const cosL = Math.cos(lam), sinL = Math.sin(lam);
        let ra = Math.atan2(cosE * sinL, cosL);
        if (ra < 0) ra += 2 * Math.PI;
        const dec = Math.asin(sinE * sinL);
        samples.push({ ra, dec });
    }
    if (drawLine) {
        ctx.save();
        ctx.strokeStyle = "#ffd84d";  // bright yellow — high luminance survives
                                       // night-mode brightness reduction
        ctx.globalAlpha = 0.65;
        ctx.lineWidth = 1.7;
        ctx.setLineDash([4, 5]);
        drawSkyPolyline(ctx, samples, basis, fov, width, height);
        ctx.restore();
    }
    if (drawLabel) {
        drawLineLabel(ctx, findBestLabelPos(samples, basis, fov, width, height),
                      "Ecliptic", "#ffd84d");
    }
}

// Local meridian — full great circle through zenith, nadir, and both
// celestial poles. In equatorial coords this is TWO RA half-circles
// 12 h apart: RA = LST (the part transiting overhead) and RA = LST + 12 h
// (the part below the horizon). Drawing both halves makes the line
// continuous around the celestial sphere at any look direction.
function drawLocalMeridian(ctx, basis, fov, width, height, lstRad, drawLine, drawLabel) {
    if (!drawLine && !drawLabel) return;
    // The meridian is intrinsically a JNow great circle (RA = current LST).
    // The chart projects in J2000, so convert each sample JNow→J2000 before
    // pushing — without this, the line lands ~0.3–0.7° off the mount pip
    // at meridian transit, and the user sees the pip cross "early."
    const now = new Date();
    function half(raJNow) {
        const samples = [];
        const N = 90;
        for (let i = 0; i <= N; i++) {
            const decJNow = (-89 + 178 * i / N) * Math.PI / 180;
            const j2k = jNowToJ2000(raJNow, decJNow, now);
            samples.push({ ra: j2k.ra, dec: j2k.dec });
        }
        return samples;
    }
    const TWO_PI = 2 * Math.PI;
    const opp = (lstRad + Math.PI) % TWO_PI;
    const halfA = half(lstRad);
    const halfB = half(opp);
    if (drawLine) {
        ctx.save();
        ctx.strokeStyle = "#ffd84d";
        ctx.globalAlpha = 0.65;
        ctx.lineWidth = 1.7;
        drawSkyPolyline(ctx, halfA, basis, fov, width, height);
        drawSkyPolyline(ctx, halfB, basis, fov, width, height);
        ctx.restore();
    }
    if (drawLabel) {
        // Label at whichever half currently has visible samples nearest
        // chart center.
        const posA = findBestLabelPos(halfA, basis, fov, width, height);
        const posB = findBestLabelPos(halfB, basis, fov, width, height);
        drawLineLabel(ctx, posA ?? posB, "Meridian", "#ffd84d");
    }
}

// Celestial equator — full great circle at Dec = 0, sampled all the way
// around RA. Yellow long-dash-dot pattern, distinguishable from the
// meridian (solid) and ecliptic (short-dash) without requiring a third
// hue (which the night-mode filter would collapse anyway).
function drawCelestialEquator(ctx, basis, fov, width, height, drawLine, drawLabel) {
    if (!drawLine && !drawLabel) return;
    const samples = [];
    const N = 180;
    for (let i = 0; i <= N; i++) {
        samples.push({ ra: (i / N) * 2 * Math.PI, dec: 0 });
    }
    if (drawLine) {
        ctx.save();
        ctx.strokeStyle = "#ffd84d";
        ctx.globalAlpha = 0.55;
        ctx.lineWidth = 1.5;
        ctx.setLineDash([10, 4, 2, 4]);
        drawSkyPolyline(ctx, samples, basis, fov, width, height);
        ctx.restore();
    }
    if (drawLabel) {
        drawLineLabel(ctx, findBestLabelPos(samples, basis, fov, width, height),
                      "Cel Equator", "#ffd84d");
    }
}

// Galactic equator — great circle at galactic latitude b = 0, sampled
// around galactic longitude and rotated into J2000 equatorial coords
// via the standard galactic-to-FK5/ICRS rotation matrix. Yellow dotted
// pattern; distinct from the meridian (solid), ecliptic (short-dash),
// and celestial equator (long-dash-dot).
const GAL_TO_EQ = [
    [-0.054876,  0.494109, -0.867666],
    [-0.873437, -0.444830, -0.198076],
    [-0.483835,  0.746982,  0.455984],
];
function drawGalacticEquator(ctx, basis, fov, width, height, drawLine, drawLabel) {
    if (!drawLine && !drawLabel) return;
    const samples = [];
    const N = 180;
    for (let i = 0; i <= N; i++) {
        const l = (i / N) * 2 * Math.PI;
        const xg = Math.cos(l), yg = Math.sin(l), zg = 0;
        const xe = GAL_TO_EQ[0][0]*xg + GAL_TO_EQ[0][1]*yg + GAL_TO_EQ[0][2]*zg;
        const ye = GAL_TO_EQ[1][0]*xg + GAL_TO_EQ[1][1]*yg + GAL_TO_EQ[1][2]*zg;
        const ze = GAL_TO_EQ[2][0]*xg + GAL_TO_EQ[2][1]*yg + GAL_TO_EQ[2][2]*zg;
        let ra = Math.atan2(ye, xe);
        if (ra < 0) ra += 2 * Math.PI;
        const dec = Math.asin(Math.max(-1, Math.min(1, ze)));
        samples.push({ ra, dec });
    }
    if (drawLine) {
        ctx.save();
        ctx.strokeStyle = "#ffd84d";
        ctx.globalAlpha = 0.5;
        ctx.lineWidth = 1.4;
        ctx.setLineDash([2, 5]);
        drawSkyPolyline(ctx, samples, basis, fov, width, height);
        ctx.restore();
    }
    if (drawLabel) {
        drawLineLabel(ctx, findBestLabelPos(samples, basis, fov, width, height),
                      "Gal Equator", "#ffd84d");
    }
}

// RA/Dec grid — parallels of declination + half-meridians of right
// ascension at FOV-adaptive spacings. Drawn in J2000 (matches the catalog
// frame), so in altaz mode the lines correctly appear curved relative to
// the zenith-up basis. Edge labels at the rightmost on-canvas sample of
// each Dec line and bottommost of each RA line — keeps the chart-center
// region uncluttered.
// Adapted from docs/sky-grid-overlay-implementation-prompt.md. A single
// majorStepDeg drives both Dec-degree spacing and RA-hour spacing
// (raStep = majorStepDeg / 15), so the lines have matched angular
// density. labelEvery thins out labels at fine FOVs where every-line
// labeling would clutter — the lines themselves stay drawn.
function chooseGridStep(fovDeg) {
    let majorStepDeg;
    if      (fovDeg > 120)  majorStepDeg = 30;        // 2 h / 30°
    else if (fovDeg >=  60) majorStepDeg = 15;        // 1 h / 15°
    else if (fovDeg >=  30) majorStepDeg = 10;        // 40 m / 10°
    else if (fovDeg >=  15) majorStepDeg = 5;         // 20 m / 5°
    else if (fovDeg >=   8) majorStepDeg = 2;         // 8 m / 2°
    else if (fovDeg >=   3) majorStepDeg = 1;         // 4 m / 1°
    else if (fovDeg >=   1) majorStepDeg = 0.5;       // 2 m / 30′
    else if (fovDeg >= 0.5) majorStepDeg = 0.25;      // 1 m / 15′
    else                    majorStepDeg = 1 / 12;    // 20 s / 5′

    // Doc spec: every line at wide FOV, every other at medium/fine.
    // Coarse-FOV labels are sparse enough by themselves; fine-FOV grids
    // produce dense lines, so labelling every other keeps breathing room.
    const labelEvery = fovDeg > 30 ? 1 : 2;
    return { majorStepDeg, labelEvery };
}

// Format RA in hours/minutes/seconds with precision matched to step size.
function formatRaShort(raRad, stepDeg) {
    const raH = ((raRad * 12 / Math.PI) % 24 + 24) % 24;
    const h = Math.floor(raH);
    if (stepDeg >= 15) return `${h}h`;          // 1 h or coarser
    const m = Math.round((raH - h) * 60);
    if (stepDeg >= 0.25) {                       // sub-hour
        if (m === 60) return `${(h + 1) % 24}h`;
        return m === 0 ? `${h}h` : `${h}h${String(m).padStart(2, "0")}m`;
    }
    // sub-arcminute
    const sFloor = (raH - h) * 60 - m;
    const s = Math.round(sFloor * 60);
    return `${h}h${String(m).padStart(2, "0")}m${String(s).padStart(2, "0")}s`;
}

// Format Dec in degrees / arcmin with precision matched to step size.
function formatDecShort(decRad, stepDeg) {
    const decDeg = decRad * 180 / Math.PI;
    const sign = decDeg >= 0 ? "+" : "-";
    const abs = Math.abs(decDeg);
    const d = Math.floor(abs);
    if (stepDeg >= 1) return `${sign}${Math.round(abs)}°`;
    const m = Math.round((abs - d) * 60);
    return `${sign}${d}°${String(m).padStart(2, "0")}'`;
}

// Find the on-canvas projected sample farthest toward the chosen edge.
// edge: "right" / "bottom" / "left" / "top". Returns null if no sample
// of the line lies inside the viewport.
function findEdgePos(samples, basis, fov, width, height, edge) {
    let best = null;
    let bestVal = -Infinity;
    for (const s of samples) {
        const vec = Array.isArray(s) ? s : raDecToVec(s.ra, s.dec);
        const p = project(vec, basis, fov, width, height);
        if (!p) continue;
        if (p.x < 0 || p.x > width || p.y < 0 || p.y > height) continue;
        let val;
        switch (edge) {
            case "right":  val =  p.x; break;
            case "left":   val = -p.x; break;
            case "bottom": val =  p.y; break;
            case "top":    val = -p.y; break;
            default: val = 0;
        }
        if (val > bestVal) { bestVal = val; best = p; }
    }
    return best;
}

function drawRaDecGrid(ctx, basis, fov, width, height, drawLines, drawLabels, lookDec) {
    if (!drawLines && !drawLabels) return;
    const fovDeg = fov * 180 / Math.PI;
    const { majorStepDeg, labelEvery } = chooseGridStep(fovDeg);
    const raStepDeg = majorStepDeg;     // single step drives both axes
    const decStepDeg = majorStepDeg;

    // Pole-aware RA thinning. At high |Dec| the meridians converge
    // geometrically — the visible spacing between adjacent RA lines at
    // the chart's center latitude is cos(Dec)·raStep. When that puts
    // many lines across the FOV, drop to every Nth so the chart stays
    // legible. thinFactor must divide the original line count cleanly,
    // so we use 1/2/3/6 only.
    const absDecRad = Math.abs(lookDec ?? 0);
    const cosDec = Math.cos(absDecRad);
    const linesPerFov = fovDeg / Math.max(0.001, cosDec * raStepDeg);
    let raThin = 1;
    if      (linesPerFov > 18) raThin = 6;
    else if (linesPerFov > 10) raThin = 3;
    else if (linesPerFov > 7)  raThin = 2;

    ctx.save();
    if (drawLines) {
        // Slightly heavier and brighter than the original draft. Stays
        // visually below the yellow reference circles but reads cleanly
        // against bright stars.
        ctx.strokeStyle = "rgba(170, 200, 235, 0.36)";
        ctx.lineWidth = 1;
        ctx.setLineDash([]);
    }

    // The grid is drawn in the JNow frame so it aligns with the local
    // meridian (which is RA = current LST) and with the bottom-left
    // telemetry readout (which displays JNow RA/Dec). Each sample is
    // generated in JNow and converted JNow→J2000 before projecting,
    // matching the same conversion used for the meridian/zenith.
    // Without this, a "RA = 18h" grid line and the meridian line at
    // LST = 18h are separated by ~26 years of precession.
    const now = new Date();

    // Dec lines — parallels at constant Dec (in JNow), sampled along RA.
    // Skip the poles (collapse to a point) and skip Dec=0 (celestial-
    // equator layer draws that line in yellow already). Labels: both
    // canvas edges, with the right-side label suppressed inside the
    // mag-slider zone.
    let decIdx = 0;
    for (let decDeg = -90 + decStepDeg; decDeg <= 90 - decStepDeg + 1e-6; decDeg += decStepDeg, decIdx++) {
        if (Math.abs(decDeg) < 1e-6) continue;
        const decJNow = decDeg * Math.PI / 180;
        const samples = [];
        const N = 180;
        for (let i = 0; i <= N; i++) {
            const raJNow = (i / N) * 2 * Math.PI;
            const j2k = jNowToJ2000(raJNow, decJNow, now);
            samples.push({ ra: j2k.ra, dec: j2k.dec });
        }
        if (drawLines) drawSkyPolyline(ctx, samples, basis, fov, width, height);
        if (drawLabels && decIdx % labelEvery === 0) {
            const text = formatDecShort(decJNow, decStepDeg);
            const left = findEdgePos(samples, basis, fov, width, height, "left");
            if (left) drawGridLabel(ctx, left.x, left.y, text, "left", width, height);
            const right = findEdgePos(samples, basis, fov, width, height, "right");
            if (right && !inMagSliderZone(right.x, right.y, width, height))
                drawGridLabel(ctx, right.x, right.y, text, "right", width, height);
        }
    }

    // RA lines — half-meridians (in JNow) from -85° Dec to +85° Dec.
    // Iterate to just under 360° so a 0 h line draws but we don't
    // double-stroke 360 h on top of 0 h. RA step is the same angular
    // value as Dec; labels use the time-equivalent (e.g. 10° → "0h40m",
    // 0.0833° → "Hh MMm SSs"). Skip every Nth line per the pole-aware
    // thin factor.
    const totalRa = Math.round(360 / raStepDeg);
    // Suppress labels whose bottommost on-canvas point lands near the
    // top of the chart — that happens near the celestial pole, where
    // many meridians converge and would label-collide otherwise. Below
    // that band, normal edge-bottom labelling.
    const poleLabelMaxY = height * 0.33;
    for (let raIdx = 0; raIdx < totalRa; raIdx++) {
        if (raIdx % raThin !== 0) continue;
        const raDeg = raIdx * raStepDeg;
        const raJNow = raDeg * Math.PI / 180;
        const samples = [];
        const N = 90;
        for (let i = 0; i <= N; i++) {
            const decJNow = (-85 + 170 * i / N) * Math.PI / 180;
            const j2k = jNowToJ2000(raJNow, decJNow, now);
            samples.push({ ra: j2k.ra, dec: j2k.dec });
        }
        if (drawLines) drawSkyPolyline(ctx, samples, basis, fov, width, height);
        const lineIdx = raIdx / raThin;
        if (drawLabels && lineIdx % labelEvery === 0) {
            const pos = findEdgePos(samples, basis, fov, width, height, "bottom");
            if (pos && pos.y > poleLabelMaxY)
                drawGridLabel(ctx, pos.x, pos.y,
                    formatRaShort(raJNow, raStepDeg), "bottom", width, height);
        }
    }

    // Pole crosshairs — small + at NCP and SCP (JNow Dec=±90°, RA
    // arbitrary). Drawn in grid color/weight so they read as part of
    // the grid rather than as features. Useful visual landmark since
    // RA meridians converge to a single point with no other indicator
    // there. Skipped if drawLines is off (the user has the grid
    // hidden — the crosshair belongs to the grid).
    if (drawLines) {
        const now = new Date();
        for (const decSign of [+1, -1]) {
            const j2k = jNowToJ2000(0, decSign * Math.PI / 2 * 0.99999, now);
            // Nudged off the exact pole (×0.99999) to dodge the projection
            // singularity where the basis "right" vector degenerates.
            const pp = project(raDecToVec(j2k.ra, j2k.dec), basis, fov, width, height);
            if (!pp) continue;
            if (pp.x < -10 || pp.x > width + 10 || pp.y < -10 || pp.y > height + 10) continue;
            const r = 6;
            ctx.beginPath();
            ctx.moveTo(pp.x - r, pp.y); ctx.lineTo(pp.x + r, pp.y);
            ctx.moveTo(pp.x, pp.y - r); ctx.lineTo(pp.x, pp.y + r);
            ctx.stroke();
        }
    }

    ctx.restore();
}

// Mag-slider geometry (mirror of starseeker.js's initMagSlider). Used
// to suppress grid labels that would land underneath the slider track,
// where they'd be invisible to the user.
const MAG_SLIDER_RIGHT_PX = 52;   // 8 px right offset + 32 px slider + ~12 px pad for thumb labels
const MAG_SLIDER_TOP_PCT  = 0.16;
const MAG_SLIDER_BOT_PCT  = 0.84;
function inMagSliderZone(x, y, width, height) {
    return x >= width - MAG_SLIDER_RIGHT_PX
        && y >= height * MAG_SLIDER_TOP_PCT
        && y <= height * MAG_SLIDER_BOT_PCT;
}

// Format alt in deg or deg/arcmin, with sign so the user can see
// negative (below-horizon) values cleanly.
function formatAltShort(altRad, stepDeg) {
    const altDeg = altRad * 180 / Math.PI;
    const sign = altDeg >= 0 ? "+" : "-";
    const abs = Math.abs(altDeg);
    if (stepDeg >= 1) return `${sign}${Math.round(abs)}°`;
    const d = Math.floor(abs);
    const m = Math.round((abs - d) * 60);
    return `${sign}${d}°${String(m).padStart(2, "0")}'`;
}

// Format az with cardinal-direction shorthand (N/E/S/W) when on a
// cardinal multiple of 90°. Otherwise plain degrees.
function formatAzShort(azRad, stepDeg) {
    const azDeg = ((azRad * 180 / Math.PI) % 360 + 360) % 360;
    const rounded = Math.round(azDeg);
    if (Math.abs(azDeg - rounded) < 0.01) {
        if (rounded === 0)   return "N";
        if (rounded === 90)  return "E";
        if (rounded === 180) return "S";
        if (rounded === 270) return "W";
    }
    if (stepDeg >= 1) return `${Math.round(azDeg)}°`;
    const d = Math.floor(azDeg);
    const m = Math.round((azDeg - d) * 60);
    return `${d}°${String(m).padStart(2, "0")}'`;
}

// Alt/Az grid. Mirror of drawRaDecGrid but in horizon coordinates.
// Each sample (alt, az) is converted to a J2000 unit vector via
// altAzToJ2000Vec, then projected through the same basis as everything
// else. Density-thinned by chart-center altitude so az meridians don't
// pile up when the user is looking near the zenith.
function drawAltAzGrid(ctx, basis, fov, width, height, drawLines, drawLabels,
                      latRad, lstRad, lookAltRad) {
    if (!drawLines && !drawLabels) return;
    const fovDeg = fov * 180 / Math.PI;
    const { majorStepDeg, labelEvery } = chooseGridStep(fovDeg);
    const stepDeg = majorStepDeg;
    const now = new Date();

    // Zenith-aware az meridian thinning — same logic as the RA grid
    // uses near the celestial pole, but keyed on |alt| since alt-az
    // meridians converge at the zenith.
    const absAlt = Math.abs(lookAltRad ?? 0);
    const cosAlt = Math.cos(absAlt);
    const linesPerFov = fovDeg / Math.max(0.001, cosAlt * stepDeg);
    let azThin = 1;
    if      (linesPerFov > 18) azThin = 6;
    else if (linesPerFov > 10) azThin = 3;
    else if (linesPerFov > 7)  azThin = 2;

    ctx.save();
    if (drawLines) {
        // Warm tan — visually distinct from the cool-blue RA/Dec grid
        // and from the bright-yellow reference circles. Same alpha so
        // neither grid dominates when both are enabled.
        ctx.strokeStyle = "rgba(220, 175, 120, 0.32)";
        ctx.lineWidth = 1;
        ctx.setLineDash([]);
    }

    // Alt parallels — sample az 0..2π at constant alt. Range -5° to +85°
    // so just-below-horizon shows (the chart already renders below the
    // horizon). Skip ±90° since those collapse to a point at the zenith.
    let altIdx = 0;
    for (let altDeg = -5; altDeg <= 85 + 1e-6; altDeg += stepDeg, altIdx++) {
        const altRad = altDeg * Math.PI / 180;
        const samples = [];
        const N = 180;
        for (let i = 0; i <= N; i++) {
            const azRad = (i / N) * 2 * Math.PI;
            samples.push(altAzToJ2000Vec(altRad, azRad, latRad, lstRad, now));
        }
        if (drawLines) drawSkyPolyline(ctx, samples, basis, fov, width, height);
        if (drawLabels && altIdx % labelEvery === 0) {
            const text = formatAltShort(altRad, stepDeg);
            const left = findEdgePos(samples, basis, fov, width, height, "left");
            if (left) drawGridLabelAltAz(ctx, left.x, left.y, text, "left", width, height);
            const right = findEdgePos(samples, basis, fov, width, height, "right");
            if (right && !inMagSliderZone(right.x, right.y, width, height))
                drawGridLabelAltAz(ctx, right.x, right.y, text, "right", width, height);
        }
    }

    // Az meridians — sample alt -5° to +85° at constant az. Skip every
    // Nth via azThin near the zenith.
    const totalAz = Math.round(360 / stepDeg);
    const zenithLabelMaxY = height * 0.33;
    for (let azIdx = 0; azIdx < totalAz; azIdx++) {
        if (azIdx % azThin !== 0) continue;
        const azRad = azIdx * stepDeg * Math.PI / 180;
        const samples = [];
        const N = 90;
        for (let i = 0; i <= N; i++) {
            const altRad = (-5 + 90 * i / N) * Math.PI / 180;
            samples.push(altAzToJ2000Vec(altRad, azRad, latRad, lstRad, now));
        }
        if (drawLines) drawSkyPolyline(ctx, samples, basis, fov, width, height);
        const lineIdx = azIdx / azThin;
        if (drawLabels && lineIdx % labelEvery === 0) {
            const pos = findEdgePos(samples, basis, fov, width, height, "bottom");
            if (pos && pos.y > zenithLabelMaxY) {
                const text = formatAzShort(azRad, stepDeg);
                drawGridLabelAltAz(ctx, pos.x, pos.y, text, "bottom", width, height);
            }
        }
    }
    ctx.restore();
}

// Place an alt/az grid label — same shape as the RA/Dec version but in
// the alt/az palette so the user can tell the two grids apart at a
// glance when both are enabled.
function drawGridLabelAltAz(ctx, x, y, text, edge, width, height) {
    ctx.save();
    ctx.font = "italic 10px ui-monospace, Menlo, monospace";
    const tw = ctx.measureText(text).width;
    const lh = 12;
    let bx, by, tx, ty;
    if (edge === "right") {
        tx = Math.min(x - 4, width - 8);
        ty = y;
        bx = tx - tw - 2;
        by = ty - lh / 2;
        ctx.textAlign = "right";
        ctx.textBaseline = "middle";
    } else if (edge === "left") {
        tx = Math.max(x + 4, 6);
        ty = y;
        bx = tx - 2;
        by = ty - lh / 2;
        ctx.textAlign = "left";
        ctx.textBaseline = "middle";
    } else { // bottom
        tx = x;
        ty = Math.min(y - 2, height - 2);
        bx = tx - tw / 2 - 2;
        by = ty - lh + 1;
        ctx.textAlign = "center";
        ctx.textBaseline = "bottom";
    }
    ctx.fillStyle = "rgba(0, 0, 0, 0.55)";
    ctx.fillRect(bx, by, tw + 4, lh);
    ctx.fillStyle = "rgba(245, 220, 170, 0.9)";
    ctx.fillText(text, tx, ty);
    ctx.restore();
}

// Place a grid edge label with a small dark backdrop so it stays
// readable even when the line crosses bright stars or other layers.
function drawGridLabel(ctx, x, y, text, edge, width, height) {
    ctx.save();
    ctx.font = "italic 10px ui-monospace, Menlo, monospace";
    const tw = ctx.measureText(text).width;
    const lh = 12;
    let bx, by, tx, ty;
    if (edge === "right") {
        // sit just inside the right edge, tip of label toward the line.
        // 8 px clearance from the canvas right edge so glyph antialiasing
        // and italic slant don't push the rightmost pixel off-screen.
        tx = Math.min(x - 4, width - 8);
        ty = y;
        bx = tx - tw - 2;
        by = ty - lh / 2;
        ctx.textAlign = "right";
        ctx.textBaseline = "middle";
    } else if (edge === "left") {
        // mirror image of right — sit just inside the left edge.
        tx = Math.max(x + 4, 6);
        ty = y;
        bx = tx - 2;
        by = ty - lh / 2;
        ctx.textAlign = "left";
        ctx.textBaseline = "middle";
    } else { // bottom
        tx = x;
        ty = Math.min(y - 2, height - 2);
        bx = tx - tw / 2 - 2;
        by = ty - lh + 1;
        ctx.textAlign = "center";
        ctx.textBaseline = "bottom";
    }
    ctx.fillStyle = "rgba(0, 0, 0, 0.55)";
    ctx.fillRect(bx, by, tw + 4, lh);
    ctx.fillStyle = "rgba(200, 220, 245, 0.85)";
    ctx.fillText(text, tx, ty);
    ctx.restore();
}

// Push-to navigation vector — arrow from the mount pip toward the
// selected target. When the gap is small (<10'), the arrow is replaced
// by a green on-target ring around the pip. When either endpoint is
// off-canvas, falls back to a corner overlay with the angular
// separation and az/alt deltas so the user still gets useful info.
const PUSH_ON_TARGET_RAD = 10 / 60 * Math.PI / 180; // 10 arcmin
function drawPushVector(ctx, basis, fov, width, height, pv) {
    const pipP = project(pv.pipVec, basis, fov, width, height);
    const tgtP = project(pv.tgtVec, basis, fov, width, height);

    // On target → green ring around pip; suppress arrow.
    if (pv.sepRad < PUSH_ON_TARGET_RAD && pipP) {
        ctx.save();
        ctx.strokeStyle = "rgba(0, 255, 64, 0.9)";
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(pipP.x, pipP.y, 18, 0, Math.PI * 2);
        ctx.stroke();
        ctx.font = "11px ui-monospace, Menlo, monospace";
        ctx.fillStyle = "rgba(0, 255, 64, 0.9)";
        ctx.textAlign = "center";
        ctx.textBaseline = "top";
        ctx.fillText("ON TARGET", pipP.x, pipP.y + 22);
        ctx.restore();
        return;
    }

    const sepText = formatSep(pv.sepRad);
    const aaText  = formatAltAzDelta(pv.altDelta, pv.azDelta);

    const onCanvas = (p) => p
        && p.x >= 0 && p.x <= width
        && p.y >= 0 && p.y <= height;
    const pipOn = onCanvas(pipP);
    const tgtOn = onCanvas(tgtP);

    // Both endpoints off-canvas — show a corner overlay with deltas.
    // User pans the chart to find the pip or target; the text keeps
    // the navigation info visible regardless.
    if (!pipOn && !tgtOn) {
        ctx.save();
        ctx.font = "11px ui-monospace, Menlo, monospace";
        ctx.textAlign = "right";
        ctx.textBaseline = "top";
        const lines = [`→ ${sepText}`, aaText];
        const lineH = 14;
        const w = Math.max(...lines.map(l => ctx.measureText(l).width));
        const x = width - 10, y = 10;
        ctx.fillStyle = "rgba(0,0,0,0.55)";
        ctx.fillRect(x - w - 6, y - 2, w + 8, lineH * lines.length + 4);
        ctx.fillStyle = "rgba(0, 255, 200, 0.9)";
        for (let i = 0; i < lines.length; i++) ctx.fillText(lines[i], x - 2, y + lineH * i);
        ctx.restore();
        return;
    }

    // At least one endpoint is on-canvas. Draw an arrow from pip to
    // target, clipping the off-canvas end to the canvas edge so the
    // visible tip points toward the truly off-canvas endpoint.
    let p1 = pipOn ? pipP : clipToEdge(pipP, tgtP, width, height);
    let p2 = tgtOn ? tgtP : clipToEdge(tgtP, pipP, width, height);
    if (!p1 || !p2) return;

    ctx.save();
    ctx.strokeStyle = "rgba(0, 255, 200, 0.9)";
    ctx.fillStyle   = "rgba(0, 255, 200, 0.9)";
    ctx.lineWidth = 1.8;
    ctx.setLineDash([]);

    // Shaft.
    ctx.beginPath();
    ctx.moveTo(p1.x, p1.y);
    ctx.lineTo(p2.x, p2.y);
    ctx.stroke();

    // Arrowhead at the target end (if on-canvas) or at the clipped
    // edge point (if target was off-canvas — chevron toward it).
    const dx = p2.x - p1.x, dy = p2.y - p1.y;
    const len = Math.hypot(dx, dy);
    if (len > 4) {
        const ux = dx / len, uy = dy / len;
        const headLen = 10, headHalf = 5;
        const baseX = p2.x - ux * headLen;
        const baseY = p2.y - uy * headLen;
        const nxL = -uy, nyL = ux;
        ctx.beginPath();
        ctx.moveTo(p2.x, p2.y);
        ctx.lineTo(baseX + nxL * headHalf, baseY + nyL * headHalf);
        ctx.lineTo(baseX - nxL * headHalf, baseY - nyL * headHalf);
        ctx.closePath();
        ctx.fill();
    }

    // Distance label at the line midpoint, offset perpendicular so
    // the text doesn't sit directly on the shaft.
    if (len > 30) {
        const midX = (p1.x + p2.x) / 2;
        const midY = (p1.y + p2.y) / 2;
        const ux = dx / len, uy = dy / len;
        const nxL = -uy, nyL = ux;
        const lx = midX + nxL * 10, ly = midY + nyL * 10;
        ctx.font = "11px ui-monospace, Menlo, monospace";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        const tw = ctx.measureText(sepText).width;
        ctx.fillStyle = "rgba(0,0,0,0.55)";
        ctx.fillRect(lx - tw / 2 - 3, ly - 7, tw + 6, 14);
        ctx.fillStyle = "rgba(0, 255, 200, 0.95)";
        ctx.fillText(sepText, lx, ly);
    }

    // Az/alt delta near the pip end so the user knows which way to
    // push (lift / rotate). Skips when the pip is off-canvas (no
    // anchor point) — the corner overlay branch above covers that.
    if (pipOn) {
        ctx.font = "10px ui-monospace, Menlo, monospace";
        ctx.textAlign = "left";
        ctx.textBaseline = "top";
        const tw = ctx.measureText(aaText).width;
        const ax = pipP.x + 14, ay = pipP.y + 14;
        ctx.fillStyle = "rgba(0,0,0,0.55)";
        ctx.fillRect(ax - 2, ay - 1, tw + 4, 13);
        ctx.fillStyle = "rgba(0, 255, 200, 0.85)";
        ctx.fillText(aaText, ax, ay);
    }

    ctx.restore();
}

// Clip a vector from `outside` toward `inside` to the canvas rectangle,
// returning the screen point where the line first enters the canvas.
// Trivial parametric clip; if either input is null returns null.
function clipToEdge(outside, inside, width, height) {
    if (!outside || !inside) return null;
    const dx = inside.x - outside.x, dy = inside.y - outside.y;
    if (dx === 0 && dy === 0) return outside;
    let tMin = 0, tMax = 1;
    function clamp(p, q) {
        if (p === 0) return q >= 0;
        const t = q / p;
        if (p < 0) { if (t > tMax) return false; if (t > tMin) tMin = t; }
        else        { if (t < tMin) return false; if (t < tMax) tMax = t; }
        return true;
    }
    // Liang-Barsky clip against [0, width] x [0, height].
    if (!clamp(-dx, outside.x) || !clamp(dx, width - outside.x)
     || !clamp(-dy, outside.y) || !clamp(dy, height - outside.y)) return null;
    return { x: outside.x + tMin * dx, y: outside.y + tMin * dy };
}

function formatSep(rad) {
    const deg = rad * 180 / Math.PI;
    if (deg >= 1) return `Δ ${deg.toFixed(1)}°`;
    return `Δ ${(deg * 60).toFixed(1)}'`;
}

function formatAltAzDelta(altDelta, azDelta) {
    const altDeg = altDelta * 180 / Math.PI;
    const azDeg  = azDelta  * 180 / Math.PI;
    const altArrow = altDeg >= 0 ? "↑" : "↓";
    const azArrow  = azDeg  >= 0 ? "→" : "←";
    return `${altArrow} ${Math.abs(altDeg).toFixed(1)}° ${azArrow} ${Math.abs(azDeg).toFixed(1)}°`;
}

// Zenith marker — small open ring + "Z" label at (RA = LST, Dec = lat).
// Zenith is overhead by definition; this gives the chart a visible
// orientation anchor without pretending to be a clickable target.
function drawZenithMarker(ctx, basis, fov, width, height, lstRad, latRad) {
    // Zenith is at (RA=LST, Dec=lat) in JNow. Convert to J2000 for the
    // chart's projection so the "Z" marker lands at the same J2000 sky
    // point a mount pip would for a target overhead.
    const j2k = jNowToJ2000(lstRad, latRad, new Date());
    const p = project(raDecToVec(j2k.ra, j2k.dec), basis, fov, width, height);
    if (!p) return;
    if (p.x < -50 || p.x > width + 50 || p.y < -50 || p.y > height + 50) return;
    ctx.save();
    ctx.strokeStyle = "#ffd84d";
    ctx.fillStyle = "#ffd84d";
    ctx.globalAlpha = 0.85;
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.arc(p.x, p.y, 7, 0, Math.PI * 2);
    ctx.stroke();
    ctx.font = "bold 10px ui-monospace, Menlo, monospace";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText("Z", p.x, p.y);
    ctx.restore();
}

// Sky-atlas iconography per object type.
// Draw a catalog-shaped icon at a target position based on its
// category. Used by the pending-target ring and the active push-to
// glyph so the user sees the object's nature even when the magnitude
// slider has filtered it out of the regular catalog draw.
//
// Categories supported:
//   "dso"    — dispatches to drawDso(type) using DSO sub-type colors
//   "planet" — small filled white-yellow disk
//   anything else — small filled white dot (treat as star)
function drawTargetCategoryIcon(ctx, p, target) {
    if (!target) return;
    if (target.category === "dso" && target.type) {
        drawDso(ctx, p, target.type);
        return;
    }
    ctx.save();
    if (target.category === "planet") {
        ctx.fillStyle = "#ffe6a8";
        ctx.beginPath();
        ctx.arc(p.x, p.y, 2.5, 0, Math.PI * 2);
        ctx.fill();
    } else {
        // Star or unknown — small filled white dot.
        ctx.fillStyle = "#ffffff";
        ctx.beginPath();
        ctx.arc(p.x, p.y, 1.8, 0, Math.PI * 2);
        ctx.fill();
    }
    ctx.restore();
}

function drawDso(ctx, p, type) {
    const color = DSO_COLOR[type] ?? "#666";
    ctx.strokeStyle = color;
    ctx.fillStyle = color;
    ctx.lineWidth = 1;

    if (type && type.startsWith("G")) {
        // Galaxy: elongated ellipse with a small center dot.
        ctx.beginPath();
        ctx.ellipse(p.x, p.y, 4.5, 2.5, 0, 0, Math.PI * 2);
        ctx.stroke();
        ctx.beginPath();
        ctx.arc(p.x, p.y, 0.6, 0, Math.PI * 2);
        ctx.fill();
    } else if (type === "OC" || type === "EN+OC") {
        // Open cluster: dashed circle.
        ctx.beginPath();
        ctx.setLineDash([2, 2]);
        ctx.arc(p.x, p.y, 4, 0, Math.PI * 2);
        ctx.stroke();
        ctx.setLineDash([]);
    } else if (type === "GC") {
        // Globular cluster: circle with cross.
        ctx.beginPath();
        ctx.arc(p.x, p.y, 4, 0, Math.PI * 2);
        ctx.stroke();
        ctx.beginPath();
        ctx.moveTo(p.x - 4, p.y); ctx.lineTo(p.x + 4, p.y);
        ctx.moveTo(p.x, p.y - 4); ctx.lineTo(p.x, p.y + 4);
        ctx.stroke();
    } else if (type === "PN") {
        // Planetary nebula: small disk with four external ticks.
        ctx.beginPath();
        ctx.arc(p.x, p.y, 2.2, 0, Math.PI * 2);
        ctx.stroke();
        ctx.beginPath();
        const r1 = 3, r2 = 5.5;
        ctx.moveTo(p.x + r1, p.y); ctx.lineTo(p.x + r2, p.y);
        ctx.moveTo(p.x - r1, p.y); ctx.lineTo(p.x - r2, p.y);
        ctx.moveTo(p.x, p.y + r1); ctx.lineTo(p.x, p.y + r2);
        ctx.moveTo(p.x, p.y - r1); ctx.lineTo(p.x, p.y - r2);
        ctx.stroke();
    } else if (type === "EN" || type === "RN" || type === "DN" || type === "SNR") {
        // Nebula: dashed square.
        ctx.setLineDash([2, 2]);
        ctx.strokeRect(p.x - 4, p.y - 4, 8, 8);
        ctx.setLineDash([]);
    } else {
        // Asterism / exoplanet / unknown: small solid circle.
        ctx.beginPath();
        ctx.arc(p.x, p.y, 3, 0, Math.PI * 2);
        ctx.stroke();
    }
}
