// Thumb pad touch controller for manual slewing
// Calls .NET when direction changes: onDirection(axis, direction)
// axis: 0=RA, 1=DEC, -1=neutral
// direction: 0=West/South, 1=East/North

window.thumbPadInit = function (element, dotnetRef) {
    const DEADBAND = 30;
    const HYSTERESIS = 10;
    let centerX = 0, centerY = 0;
    let activeAxis = -1; // -1=none, 0=RA, 1=DEC
    let activeDir = -1;
    let touching = false;

    // Clean up any previous global listeners from a prior init
    if (element._thumbPadCleanup) element._thumbPadCleanup();


    function updateDirection(tx, ty) {
        const dx = tx - centerX;
        const dy = centerY - ty; // invert Y: up = positive

        const adx = Math.abs(dx);
        const ady = Math.abs(dy);

        // Inside deadband?
        if (adx < DEADBAND && ady < DEADBAND) {
            if (activeAxis >= 0) {
                activeAxis = -1;
                activeDir = -1;
                dotnetRef.invokeMethodAsync('OnPadDirection', -1, -1);
            }
            return;
        }

        // Dominant axis with hysteresis
        let newAxis;
        if (activeAxis === 0) {
            // Currently RA — switch to DEC only if DEC wins by margin
            newAxis = (ady > adx + HYSTERESIS) ? 1 : 0;
        } else if (activeAxis === 1) {
            // Currently DEC — switch to RA only if RA wins by margin
            newAxis = (adx > ady + HYSTERESIS) ? 0 : 1;
        } else {
            // No active axis — pick dominant
            newAxis = (adx >= ady) ? 0 : 1;
        }

        const newDir = (newAxis === 0) ? (dx > 0 ? 1 : 0) : (dy > 0 ? 1 : 0);

        if (newAxis !== activeAxis || newDir !== activeDir) {
            activeAxis = newAxis;
            activeDir = newDir;
            dotnetRef.invokeMethodAsync('OnPadDirection', activeAxis, activeDir);
        }
    }

    function getTouch(e) {
        const t = e.touches[0] || e.changedTouches[0];
        return { x: t.clientX, y: t.clientY };
    }

    element.addEventListener('touchstart', function (e) {
        e.preventDefault();
        const rect = element.getBoundingClientRect();
        centerX = rect.left + rect.width / 2;
        centerY = rect.top + rect.height / 2;
        touching = true;
        const t = getTouch(e);
        updateDirection(t.x, t.y);
    }, { passive: false });

    element.addEventListener('touchmove', function (e) {
        if (!touching) return;
        e.preventDefault();
        const t = getTouch(e);
        updateDirection(t.x, t.y);
    }, { passive: false });

    function endTouch() {
        if (!touching) return;
        touching = false;
        activeAxis = -1;
        activeDir = -1;
        dotnetRef.invokeMethodAsync('OnPadDirection', -1, -1);
    }

    element.addEventListener('touchend', function (e) { e.preventDefault(); endTouch(); }, { passive: false });
    element.addEventListener('touchcancel', function () { endTouch(); }, { passive: false });

    // Mouse support for desktop testing
    let mouseDown = false;
    element.addEventListener('mousedown', function (e) {
        e.preventDefault();
        mouseDown = true;
        touching = true;
        const rect = element.getBoundingClientRect();
        centerX = rect.left + rect.width / 2;
        centerY = rect.top + rect.height / 2;
        updateDirection(e.clientX, e.clientY);
    });
    function onMouseMove(e) {
        if (!mouseDown) return;
        updateDirection(e.clientX, e.clientY);
    }
    function onMouseUp() {
        if (!mouseDown) return;
        mouseDown = false;
        endTouch();
    }
    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', onMouseUp);

    // Store cleanup so re-init can remove old global listeners
    element._thumbPadCleanup = function () {
        window.removeEventListener('mousemove', onMouseMove);
        window.removeEventListener('mouseup', onMouseUp);
    };
};
