// Altitude vs Time chart engine — extracted from ExploreStars altvstime.html
// Called from Blazor via JS interop
'use strict';

const DEG2RAD = Math.PI / 180;
const RAD2DEG = 180 / Math.PI;
const HRS2RAD = Math.PI / 12;
const RAD2HRS = 12 / Math.PI;
const DEFAULT_DELTA_T_SECONDS = 69;
const REFRACTION_PRESSURE_HPA = 1010;
const REFRACTION_TEMP_C = 10;
const ALT_Y_MIN = -10;
const ALT_Y_MAX = 90;
const RS_SEARCH_PAD_MIN = 60;

const clamp = (x, a, b) => Math.max(a, Math.min(b, x));

function jdUTC(date) { return date.getTime() / 86400000 + 2440587.5; }
function jdTTFromUTC(jdUTC_, deltaTsec = DEFAULT_DELTA_T_SECONDS) { return jdUTC_ + deltaTsec / 86400; }

function gmst(jd) {
    const T = (jd - 2451545.0) / 36525;
    let gmstSec = 67310.54841 + (876600 * 3600 + 8640184.812866) * T + 0.093104 * T * T - 6.2e-6 * T * T * T;
    gmstSec = ((gmstSec % 86400) + 86400) % 86400;
    return (gmstSec / 240) * DEG2RAD;
}

function lstRadians(jd, lonDeg) {
    const L = gmst(jd) + lonDeg * DEG2RAD;
    return ((L % (2 * Math.PI)) + 2 * Math.PI) % (2 * Math.PI);
}

function precessJ2000ToDate(raJ2000_rad, decJ2000_rad, jdTT) {
    const T = (jdTT - 2451545.0) / 36525;
    const zeta = (2306.2181 + 1.39656 * T - 0.000139 * T * T) * T + (0.30188 - 0.000344 * T) * T * T + 0.017998 * T * T * T;
    const z = (2306.2181 + 1.39656 * T - 0.000139 * T * T) * T + (1.09468 + 0.000066 * T) * T * T + 0.018203 * T * T * T;
    const th = (2004.3109 - 0.85330 * T - 0.000217 * T * T) * T - (0.42665 + 0.000217 * T) * T * T - 0.041833 * T * T * T;
    const zetaRad = (zeta / 3600) * DEG2RAD;
    const zRad = (z / 3600) * DEG2RAD;
    const thRad = (th / 3600) * DEG2RAD;
    const x0 = Math.cos(decJ2000_rad) * Math.cos(raJ2000_rad);
    const y0 = Math.cos(decJ2000_rad) * Math.sin(raJ2000_rad);
    const z0 = Math.sin(decJ2000_rad);
    const x1 = x0 * Math.cos(zetaRad) - y0 * Math.sin(zetaRad);
    const y1 = x0 * Math.sin(zetaRad) + y0 * Math.cos(zetaRad);
    const x2 = x1 * Math.cos(thRad) + z0 * Math.sin(thRad);
    const y2 = y1;
    const z2 = -x1 * Math.sin(thRad) + z0 * Math.cos(thRad);
    const x3 = x2 * Math.cos(zRad) - y2 * Math.sin(zRad);
    const y3 = x2 * Math.sin(zRad) + y2 * Math.cos(zRad);
    const z3 = z2;
    const ra = Math.atan2(y3, x3);
    const dec = Math.atan2(z3, Math.hypot(x3, y3));
    return { ra_rad: (ra + 2 * Math.PI) % (2 * Math.PI), dec_rad: dec };
}

function hourAngle(lst_rad, ra_rad) {
    let H = lst_rad - ra_rad;
    if (H > Math.PI) H -= 2 * Math.PI;
    if (H < -Math.PI) H += 2 * Math.PI;
    return H;
}

function altitudeDegUnrefracted(latDeg, decDeg, HA_rad) {
    const phi = latDeg * DEG2RAD, delta = decDeg * DEG2RAD;
    return RAD2DEG * Math.asin(Math.sin(phi) * Math.sin(delta) + Math.cos(phi) * Math.cos(delta) * Math.cos(HA_rad));
}

function refractionArcminBennett(hDeg) {
    const h = Math.max(-1, Math.min(89.9, hDeg));
    const R = 1.02 / Math.tan((h + 10.3 / (h + 5.11)) * DEG2RAD);
    const scale = (REFRACTION_PRESSURE_HPA / 1010) * (283 / (273 + REFRACTION_TEMP_C));
    return R * scale;
}

function altitudeDegRefracted(hDeg) {
    if (!Number.isFinite(hDeg)) return hDeg;
    if (hDeg > 85) return hDeg;
    return hDeg + refractionArcminBennett(hDeg) / 60;
}

function findTransitLocal(ra_rad, lonDeg, nearLocal) {
    let guess = new Date(nearLocal.getTime());
    for (let i = 0; i < 6; i++) {
        const jd = jdUTC(new Date(guess.toISOString()));
        const LST = lstRadians(jd, lonDeg);
        const diffHrs = ((ra_rad - LST + 3 * Math.PI) % (2 * Math.PI) - Math.PI) * RAD2HRS;
        const civilHours = diffHrs / 1.00273790935;
        guess = new Date(guess.getTime() + civilHours * 3600 * 1000);
    }
    return guess;
}

function refractedAltAt(localDate, latDeg, lonDeg, raOfDate_rad, decOfDate_rad) {
    const jd = jdUTC(new Date(localDate.toISOString()));
    const LST = lstRadians(jd, lonDeg);
    const H = hourAngle(LST, raOfDate_rad);
    const h0 = altitudeDegUnrefracted(latDeg, decOfDate_rad * RAD2DEG, H);
    return altitudeDegRefracted(h0);
}

function findZeroCrossing(lat, lon, ra_rad, dec_rad, tA, tB) {
    let a = new Date(tA), b = new Date(tB);
    let fa = refractedAltAt(a, lat, lon, ra_rad, dec_rad);
    for (let i = 0; i < 40; i++) {
        const mid = new Date((a.getTime() + b.getTime()) / 2);
        const fm = refractedAltAt(mid, lat, lon, ra_rad, dec_rad);
        if (Math.sign(fm) === Math.sign(fa)) { a = mid; fa = fm; } else { b = mid; }
    }
    return new Date((a.getTime() + b.getTime()) / 2);
}

function hhmm(d) {
    return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
}

function computeCurve(raHours, decDeg, latD, lonD) {
    const local = new Date();
    const midnight = new Date(local); midnight.setHours(0, 0, 0, 0);
    const nextMidnight = new Date(midnight.getTime() + 24 * 3600 * 1000);

    const jd_utc = jdUTC(local);
    const jd_tt = jdTTFromUTC(jd_utc);

    // Always precess from J2000
    const p = precessJ2000ToDate(raHours * HRS2RAD, decDeg * DEG2RAD, jd_tt);
    const raOfDate_rad = p.ra_rad;
    const decOfDate_rad = p.dec_rad;

    const transitLocal = findTransitLocal(raOfDate_rad, lonD, local);

    // Visibility scan
    let anyAbove = false, anyBelow = false;
    for (let t = new Date(midnight); t <= nextMidnight; t = new Date(t.getTime() + 5 * 60000)) {
        const h = refractedAltAt(t, latD, lonD, raOfDate_rad, decOfDate_rad);
        if (h > 0) anyAbove = true; else anyBelow = true;
        if (anyAbove && anyBelow) break;
    }

    const sampleBetween = (start, end) => {
        const spanMin = Math.max(1, Math.round((end - start) / 60000));
        const stepMin = spanMin > 600 ? 3 : 1;
        const pts = [];
        for (let t = new Date(start); t <= end; t = new Date(t.getTime() + stepMin * 60000)) {
            pts.push({ time: new Date(t), alt: refractedAltAt(t, latD, lonD, raOfDate_rad, decOfDate_rad) });
        }
        if (pts.length === 0 || +pts[pts.length - 1].time !== +end) {
            pts.push({ time: new Date(end), alt: refractedAltAt(end, latD, lonD, raOfDate_rad, decOfDate_rad) });
        }
        return pts;
    };

    let start, end, label, circumpolar = false, neverRises = false;

    if (!anyAbove && anyBelow) {
        start = midnight; end = nextMidnight; label = 'never rises (24h)'; neverRises = true;
    } else if (anyAbove && !anyBelow) {
        start = midnight; end = nextMidnight; label = 'never sets (24h)'; circumpolar = true;
    } else {
        const before = new Date(transitLocal.getTime() - RS_SEARCH_PAD_MIN * 60000 * 12);
        const after = new Date(transitLocal.getTime() + RS_SEARCH_PAD_MIN * 60000 * 12);
        let riseA = null, riseB = null, setA = null, setB = null;
        let lastT = new Date(before);
        let lastH = refractedAltAt(lastT, latD, lonD, raOfDate_rad, decOfDate_rad);
        for (let t = new Date(lastT.getTime() + 5 * 60000); t <= after; t = new Date(t.getTime() + 5 * 60000)) {
            const h = refractedAltAt(t, latD, lonD, raOfDate_rad, decOfDate_rad);
            if (lastH <= 0 && h > 0 && !riseA) { riseA = lastT; riseB = t; }
            if (lastH >= 0 && h < 0 && !setA) { setA = lastT; setB = t; }
            lastT = t; lastH = h;
            if (riseA && setA) break;
        }
        if (!riseA || !setA) {
            start = midnight; end = nextMidnight; label = '24h (fallback)';
        } else {
            start = findZeroCrossing(latD, lonD, raOfDate_rad, decOfDate_rad, riseA, riseB);
            end = findZeroCrossing(latD, lonD, raOfDate_rad, decOfDate_rad, setA, setB);
            label = 'rise \u2192 set';
        }
    }

    const points = sampleBetween(start, end);
    const transitInWindow = transitLocal >= start && transitLocal <= end ? transitLocal : null;

    return {
        points, start, end, label, transit: transitInWindow,
        raOfDate_rad, decOfDate_rad, latD, lonD,
        circumpolar, neverRises
    };
}

function setupCanvas(canvas, cssWidth, cssHeight) {
    const dpr = window.devicePixelRatio || 1;
    canvas.style.width = cssWidth + 'px';
    canvas.style.height = cssHeight + 'px';
    canvas.width = Math.round(cssWidth * dpr);
    canvas.height = Math.round(cssHeight * dpr);
    const ctx = canvas.getContext('2d');
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    return ctx;
}

function drawChart(canvas, data, targetName) {
    const parent = canvas.parentElement;
    const cssW = Math.max(240, parent.clientWidth);
    const isPortrait = window.matchMedia('(orientation: portrait)').matches;
    const cssH = clamp(Math.round(cssW * (isPortrait ? 0.9 : 0.55)), 260, 520);
    const ctx = setupCanvas(canvas, cssW, cssH);

    const { points, start, end, label, transit, raOfDate_rad, decOfDate_rad, latD, lonD } = data;
    const narrow = cssW < 380;
    const base = clamp(Math.floor(cssW / 48), 11, 14);
    const small = Math.max(10, base - 1);
    const W = cssW, H = cssH;
    ctx.clearRect(0, 0, W, H);

    const padL = Math.round(clamp(W * 0.11, 46, 68));
    const padR = 16, padT = 20, padB = Math.round(clamp(W * 0.09, 38, 56));
    const plotW = W - padL - padR;
    const plotH = H - padT - padB;

    const t0 = +start, t1 = +end;
    const xOf = (t) => padL + ((t - t0) / (t1 - t0)) * plotW;
    const yOf = (alt) => padT + (1 - (alt - ALT_Y_MIN) / (ALT_Y_MAX - ALT_Y_MIN)) * plotH;

    const font = `system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial`;

    // Y grid
    const yStep = narrow ? 20 : 10;
    ctx.strokeStyle = '#374151'; ctx.lineWidth = 1; ctx.beginPath();
    for (let alt = ALT_Y_MIN; alt <= ALT_Y_MAX; alt += yStep) {
        const y = yOf(alt); ctx.moveTo(padL, y); ctx.lineTo(W - padR, y);
    }
    ctx.stroke();

    // Axes
    ctx.strokeStyle = '#6b7280'; ctx.lineWidth = 1.2; ctx.beginPath();
    ctx.moveTo(padL, H - padB); ctx.lineTo(W - padR, H - padB);
    ctx.moveTo(padL, padT); ctx.lineTo(padL, H - padB);
    ctx.stroke();

    // Y labels
    ctx.fillStyle = '#9ca3af'; ctx.font = `${small}px ${font}`;
    ctx.textAlign = 'right'; ctx.textBaseline = 'middle';
    for (let alt = ALT_Y_MIN; alt <= ALT_Y_MAX; alt += yStep) {
        ctx.fillText(`${alt}\u00b0`, padL - 8, yOf(alt));
    }

    // X ticks
    const minorMin = narrow ? 30 : 15;
    const msMajor = 60 * 60000;
    const firstMinor = new Date(start);
    firstMinor.setMinutes(Math.floor(firstMinor.getMinutes() / minorMin) * minorMin, 0, 0);

    ctx.strokeStyle = '#374151'; ctx.lineWidth = 1;
    for (let t = +firstMinor; t <= +end; t += minorMin * 60000) {
        const x = xOf(t); ctx.beginPath(); ctx.moveTo(x, padT); ctx.lineTo(x, H - padB); ctx.stroke();
    }

    // Major X ticks with labels
    ctx.textAlign = 'center'; ctx.textBaseline = 'top';
    ctx.font = `${base}px ${font}`;
    const spanMin = Math.max(1, Math.round((end - start) / 60000));
    const pxPerHour = (plotW / spanMin) * 60;
    const labelW = ctx.measureText('00:00').width + 10;
    const hoursBetween = Math.max(1, Math.ceil(labelW / pxPerHour));
    const msBetween = hoursBetween * msMajor;

    for (let t = +firstMinor; t <= +end; t += msMajor) {
        const x = xOf(t);
        ctx.strokeStyle = '#4b5563'; ctx.beginPath(); ctx.moveTo(x, padT); ctx.lineTo(x, H - padB); ctx.stroke();
        if ((t - +firstMinor) % msBetween === 0) {
            ctx.fillStyle = '#9ca3af';
            ctx.fillText(hhmm(new Date(t)), x, H - padB + 6);
        }
    }

    // Horizon
    ctx.strokeStyle = '#6b7280'; ctx.setLineDash([4, 4]);
    ctx.beginPath(); ctx.moveTo(padL, yOf(0)); ctx.lineTo(W - padR, yOf(0)); ctx.stroke();
    ctx.setLineDash([]);

    // Curve
    ctx.strokeStyle = '#60a5fa'; ctx.lineWidth = 2; ctx.beginPath();
    for (let i = 0; i < points.length; i++) {
        const x = xOf(+points[i].time), y = yOf(points[i].alt);
        if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    }
    ctx.stroke();

    // Transit marker
    if (transit) {
        const x = xOf(+transit);
        ctx.strokeStyle = '#60a5fa'; ctx.setLineDash([6, 6]);
        ctx.beginPath(); ctx.moveTo(x, padT); ctx.lineTo(x, H - padB); ctx.stroke();
        ctx.setLineDash([]);
        ctx.fillStyle = '#60a5fa'; ctx.textAlign = 'left'; ctx.textBaseline = 'bottom';
        ctx.font = `${small}px ${font}`;
        ctx.fillText(`Transit ${hhmm(transit)}`, x + 6, padT + 14);
    }

    // Now marker
    const now = new Date();
    if (now >= start && now <= end) {
        const altNow = refractedAltAt(now, latD, lonD, raOfDate_rad, decOfDate_rad);
        const x = xOf(+now), y = yOf(altNow);
        ctx.strokeStyle = '#4ade80'; ctx.setLineDash([4, 6]);
        ctx.beginPath(); ctx.moveTo(x, padT); ctx.lineTo(x, H - padB); ctx.stroke();
        ctx.setLineDash([]);
        ctx.fillStyle = '#4ade80';
        ctx.beginPath(); ctx.arc(x, y, 4, 0, 2 * Math.PI); ctx.fill();
        ctx.textAlign = 'left'; ctx.textBaseline = 'top';
        ctx.font = `${small}px ${font}`;
        ctx.fillText(`Now ${hhmm(now)}  ${altNow.toFixed(1)}\u00b0`, x + 6, y + 6);
    }

    // Title
    ctx.fillStyle = '#e5e5e5'; ctx.textAlign = 'left'; ctx.textBaseline = 'alphabetic';
    ctx.font = `600 ${small + 1}px ${font}`;
    const title = targetName ? `${targetName} \u2014 ${label}` : `Altitude vs Time (${label})`;
    ctx.fillText(title, padL, 16);

    // Return stats
    return {
        rise: hhmm(start),
        set: hhmm(end),
        transit: transit ? hhmm(transit) : null,
        label: label,
        transitAlt: transit ? refractedAltAt(transit, latD, lonD, raOfDate_rad, decOfDate_rad).toFixed(1) : null,
        nowAlt: refractedAltAt(now, latD, lonD, raOfDate_rad, decOfDate_rad).toFixed(1)
    };
}

// Global API for Blazor JS interop
window.altVsTime = {
    _lastData: null,
    _lastName: null,

    plot: function (canvasId, raHours, decDeg, latDeg, lonDeg, targetName) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return null;
        const data = computeCurve(raHours, decDeg, latDeg, lonDeg);
        this._lastData = data;
        this._lastName = targetName || null;
        return drawChart(canvas, data, targetName);
    },

    redraw: function (canvasId) {
        if (!this._lastData) return;
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;
        drawChart(canvas, this._lastData, this._lastName);
    }
};
