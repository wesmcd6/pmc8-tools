// Daylight Polar Alignment — device orientation handler
// Calls .NET with (alt, az, gamma) on each orientation update

window.polarAlignInit = function (dotnetRef, latDeg, declination) {
    const TIME_CONSTANT = 0.5;
    let filtered_x = 0, filtered_y = 0, last_time = null;
    let alt_ncp = Math.abs(latDeg);
    let az_ncp = latDeg >= 0 ? 0 : 180;
    let magDec = declination || 0;

    function degToRad(d) { return d * Math.PI / 180; }

    function matMul(a, b) {
        const r = [[0,0,0],[0,0,0],[0,0,0]];
        for (let i=0;i<3;i++) for (let j=0;j<3;j++) for (let k=0;k<3;k++) r[i][j]+=a[i][k]*b[k][j];
        return r;
    }

    function transpose(m) {
        return [[m[0][0],m[1][0],m[2][0]],[m[0][1],m[1][1],m[2][1]],[m[0][2],m[1][2],m[2][2]]];
    }

    function matVec(m, v) {
        return [m[0][0]*v[0]+m[0][1]*v[1]+m[0][2]*v[2],
                m[1][0]*v[0]+m[1][1]*v[1]+m[1][2]*v[2],
                m[2][0]*v[0]+m[2][1]*v[1]+m[2][2]*v[2]];
    }

    function handleOrientation(event) {
        let alpha = event.alpha, beta = event.beta, gamma = event.gamma;
        if (alpha == null || beta == null || gamma == null) return;

        let heading = alpha;
        if ('webkitCompassHeading' in event) heading = event.webkitCompassHeading;

        const true_alpha = ((heading + magDec + 180) % 360);
        const a = degToRad(true_alpha), b = degToRad(beta), g = degToRad(gamma);

        const ca=Math.cos(a),sa=Math.sin(a),cb=Math.cos(b),sb=Math.sin(b),cg=Math.cos(g),sg=Math.sin(g);
        const rz=[[ca,-sa,0],[sa,ca,0],[0,0,1]];
        const rx=[[1,0,0],[0,cb,-sb],[0,sb,cb]];
        const ry=[[cg,0,sg],[0,1,0],[-sg,0,cg]];
        const rt = transpose(matMul(ry, matMul(rx, rz)));
        const w = matVec(rt, [0, -1, 0]);

        let alt = Math.asin(w[2]) * 180 / Math.PI;
        let az = Math.atan2(w[0], w[1]) * 180 / Math.PI;
        if (az < 0) az += 360;

        let dAlt = alt - alt_ncp;
        let dAz = az - az_ncp;
        if (dAz > 180) dAz -= 360;
        else if (dAz < -180) dAz += 360;

        const scale = 40; // px per degree
        const xOff = dAz * scale;
        const yOff = -dAlt * scale;

        const now = performance.now() / 1000;
        let af = 1;
        if (last_time !== null) af = 1 - Math.exp(-(now - last_time) / TIME_CONSTANT);
        last_time = now;

        filtered_x = af * xOff + (1 - af) * filtered_x;
        filtered_y = af * yOff + (1 - af) * filtered_y;

        dotnetRef.invokeMethodAsync('OnPolarUpdate', alt, az, filtered_x, filtered_y, gamma);
    }

    window.addEventListener('deviceorientation', handleOrientation, true);
    window.addEventListener('deviceorientationabsolute', handleOrientation, true);

    // Check if events are firing after 2 seconds
    let eventReceived = false;
    const origHandler = handleOrientation;
    handleOrientation = function(e) { eventReceived = true; origHandler(e); };
    setTimeout(function() {
        if (!eventReceived) {
            dotnetRef.invokeMethodAsync('OnPolarError', 'No orientation events received. Sensor may not be available.');
        }
    }, 2000);

    return true;
};

window.polarAlignRequestPermission = async function () {
    if (typeof DeviceOrientationEvent.requestPermission === 'function') {
        const response = await DeviceOrientationEvent.requestPermission();
        return response === 'granted';
    }
    return true; // Android/desktop don't need permission
};

window.polarAlignUpdateDeclination = function (dec) {
    // Update stored declination for next orientation event
    if (window._polarMagDec !== undefined) window._polarMagDec = dec;
};
