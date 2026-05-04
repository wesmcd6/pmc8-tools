// Best-effort internet connectivity probe. Used to gate the
// "Wikipedia ↗" affordance on Target + Star Seeker so it stays
// unclickable when there's no WAN. Wikipedia REST endpoint via
// no-cors HEAD: opaque response is fine — we only care that the
// fetch resolves without a network failure. 2.5 s abort timeout.

window.connectivity = (() => {
    let dotnetRef = null;
    let visListenerAttached = false;

    async function probe() {
        try {
            const ctrl = new AbortController();
            const t = setTimeout(() => ctrl.abort(), 2500);
            await fetch('https://en.wikipedia.org/api/rest_v1/page/summary/Main_Page', {
                method: 'HEAD',
                mode: 'no-cors',
                cache: 'no-store',
                signal: ctrl.signal
            });
            clearTimeout(t);
            return true;
        } catch {
            return false;
        }
    }

    async function probeAndPush() {
        const online = navigator.onLine === false ? false : await probe();
        if (dotnetRef) {
            try { await dotnetRef.invokeMethodAsync('SetOnline', online); }
            catch { /* page navigated away — ignore */ }
        }
        return online;
    }

    function init(ref) {
        dotnetRef = ref;
        if (!visListenerAttached) {
            window.addEventListener('online', probeAndPush);
            window.addEventListener('offline', () => {
                if (dotnetRef) {
                    try { dotnetRef.invokeMethodAsync('SetOnline', false); } catch {}
                }
            });
            document.addEventListener('visibilitychange', () => {
                if (document.visibilityState === 'visible') probeAndPush();
            });
            visListenerAttached = true;
        }
        return probeAndPush();
    }

    return { init, probe: probeAndPush };
})();
