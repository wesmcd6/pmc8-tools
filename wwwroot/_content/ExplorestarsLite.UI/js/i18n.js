/* i18n.js — glossary-only localizer for ExploreStars Envision.
 *
 * Modeled on the main ExploreStars app's i18n-shared.js but stripped of
 * the LibreTranslate fallback. Anything not in the glossary stays in
 * its English source.
 *
 * Glossary format (locales/glossary.json):
 *   {
 *     "_meta": { "version": "...", "languages": ["en","zh-Hans",...] },
 *     "entries": {
 *       "Connection": { "en": "Connection", "zh-Hans": "连接", ... },
 *       ...
 *     }
 *   }
 *
 * Public API:
 *   window.eslI18n.setLanguage(lang)     — apply translations and persist
 *   window.eslI18n.getLanguage()         — current language code
 *   window.eslI18n.getAvailableLanguages() → array of language codes
 *   window.eslI18n.init()                — auto-applies saved language at boot
 *
 * Persistence: localStorage key 'esl_language'. Default 'en'.
 */
window.eslI18n = (function () {
    const STORAGE_KEY = 'esl_language';
    const GLOSSARY_URL = '_content/ExplorestarsLite.UI/locales/glossary.json';
    const ATTR_LIST = ['title', 'alt', 'placeholder', 'aria-label'];
    const ORIG_ATTR_PREFIX = 'data-i18n-orig-';

    let _glossary = null;
    let _currentLang = 'en';
    let _observer = null;
    let _debounce = null;

    function normalizeKey(s) {
        if (!s) return '';
        return String(s)
            .replace(/\u00A0/g, ' ')   // NBSP → space
            .replace(/\s+/g, ' ')       // collapse internal whitespace
            .trim();
    }

    /**
     * Look up a phrase in the glossary for a given language. Returns the
     * translation string, or null if no translation exists (or English).
     */
    function lookup(text, lang) {
        if (!_glossary || !_glossary.entries) return null;
        if (lang === 'en') return null;
        const key = normalizeKey(text);
        if (!key) return null;
        const entry = _glossary.entries[key];
        if (!entry) return null;
        const t = entry[lang];
        if (typeof t === 'string' && t.trim().length > 0) return t;
        return null;
    }

    async function loadGlossary() {
        if (_glossary) return _glossary;
        try {
            const r = await fetch(GLOSSARY_URL);
            _glossary = await r.json();
        } catch (e) {
            console.warn('[i18n] glossary load failed:', e);
            _glossary = { entries: {} };
        }
        return _glossary;
    }

    /**
     * Forward-translate a single text node. ONLY writes when a glossary
     * translation exists and differs from the current value. Untranslated
     * text (dynamic values like LST, RA/Dec readouts, percent counters)
     * is left alone so Blazor's continuous renders flow through.
     *
     * The "restore to original" path lives in restoreAll() and runs only
     * on language change, never on observer ticks. That's what prevents
     * the feedback loop where telemetry would freeze at the first cached
     * value.
     */
    function translateTextNode(node, lang) {
        if (!node || node.nodeType !== 3) return;
        const parent = node.parentElement;
        if (!parent) return;
        if (parent.closest('script,style,code,noscript,meta,textarea')) return;
        if (parent.hasAttribute && parent.hasAttribute('data-i18n-skip')) return;

        const current = node.nodeValue;
        if (!current) return;
        const trimmed = current.trim();
        if (!trimmed) return;

        const t = lookup(trimmed, lang);
        if (t === null) return;   // not in glossary → leave alone

        const lead = current.match(/^\s*/)[0];
        const trail = current.match(/\s*$/)[0];
        const newValue = lead + t + trail;
        if (node.nodeValue === newValue) return;   // already translated → no-op

        // Cache the original on first translation, so a language switch
        // (or revert to English) can put it back.
        if (node._origText == null) node._origText = current;
        node.nodeValue = newValue;
    }

    /**
     * Walk all previously-translated text nodes and attributes and put
     * them back to their cached originals. Called on language change so
     * the new language starts from a clean English baseline.
     */
    function restoreAll() {
        if (!document.body) return;
        // Text nodes
        const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null);
        let n;
        while ((n = walker.nextNode())) {
            if (n._origText != null && n.nodeValue !== n._origText) {
                n.nodeValue = n._origText;
            }
        }
        // Attributes
        const all = document.body.getElementsByTagName('*');
        for (let i = 0; i < all.length; i++) {
            const el = all[i];
            for (const attr of ATTR_LIST) {
                const cacheKey = ORIG_ATTR_PREFIX + attr;
                if (el.hasAttribute(cacheKey)) {
                    const orig = el.getAttribute(cacheKey);
                    if (el.getAttribute(attr) !== orig) el.setAttribute(attr, orig);
                }
            }
        }
    }

    /**
     * Forward-translate the four common attributes on an element. Same
     * write-only-when-translation-exists discipline as translateTextNode
     * to avoid clobbering dynamically-bound attribute values.
     */
    function translateAttributes(el, lang) {
        if (!el || el.nodeType !== 1) return;
        for (const attr of ATTR_LIST) {
            const cacheKey = ORIG_ATTR_PREFIX + attr;
            const val = el.getAttribute(attr);
            if (!val) continue;
            const trimmed = val.trim();
            if (!trimmed) continue;
            const t = lookup(trimmed, lang);
            if (t === null) continue;   // not in glossary → leave alone
            const lead = val.match(/^\s*/)[0];
            const trail = val.match(/\s*$/)[0];
            const newValue = lead + t + trail;
            if (val === newValue) continue;   // already translated → no-op
            if (!el.hasAttribute(cacheKey)) el.setAttribute(cacheKey, val);
            el.setAttribute(attr, newValue);
        }
    }

    /**
     * Walk a subtree and translate all text nodes + attributes.
     */
    function translateSubtree(root, lang) {
        if (!root) return;
        // Element attributes (root + descendants).
        if (root.nodeType === 1) {
            translateAttributes(root, lang);
            const all = root.getElementsByTagName('*');
            for (let i = 0; i < all.length; i++) translateAttributes(all[i], lang);
        }
        // Text nodes (root + descendants).
        const walker = document.createTreeWalker(
            root.nodeType === 1 ? root : root.parentNode || document.body,
            NodeFilter.SHOW_TEXT,
            null
        );
        // If root is itself a text node, handle it directly.
        if (root.nodeType === 3) {
            translateTextNode(root, lang);
            return;
        }
        let n;
        while ((n = walker.nextNode())) translateTextNode(n, lang);
    }

    function translateAll(lang) {
        if (!document.body) return;
        translateSubtree(document.body, lang);
    }

    function startObserver() {
        if (_observer) return;
        _observer = new MutationObserver(() => {
            // English mode: nothing to translate; observer stays running
            // so we capture nodes for restore on next language switch.
            if (_currentLang === 'en') return;
            // Debounce so we run once after a Blazor render burst settles
            // rather than on every individual mutation. Then re-translate
            // the whole body — overkill for any single mutation but
            // robust against the cases where attribute-only mutations
            // on a parent imply Blazor has re-emitted child text we'd
            // otherwise miss with a per-mutation strategy.
            if (_debounce) clearTimeout(_debounce);
            _debounce = setTimeout(() => {
                _debounce = null;
                translateAll(_currentLang);
            }, 50);
        });
        _observer.observe(document.body, {
            childList: true,
            subtree: true,
            characterData: true,
            attributes: true,
            attributeFilter: ATTR_LIST
        });
    }

    async function setLanguage(lang) {
        const target = (lang || 'en');
        await loadGlossary();
        const prev = _currentLang;
        _currentLang = target;
        try { localStorage.setItem(STORAGE_KEY, target); } catch (e) { /* private mode */ }
        // If switching away from a non-English language, first revert
        // every previously-translated node to its original. Then apply
        // the new language. This keeps the per-tick walker write-only
        // (no untranslated-node reverts), which is what makes dynamic
        // telemetry text flow through cleanly.
        if (prev !== target && prev !== 'en') restoreAll();
        translateAll(target);
        startObserver();
    }

    function getLanguage() { return _currentLang; }

    /**
     * Returns the language list as objects: [{code, label}, ...].
     * Handles both the legacy ["en","zh-Hans"] form and the new
     * [{code,label}] form, so old or partially-edited glossary files
     * still work. Always includes English as a safe fallback if the
     * glossary hasn't loaded yet.
     */
    function getAvailableLanguages() {
        if (!_glossary || !_glossary._meta) return [{ code: 'en', label: 'English' }];
        var langs = _glossary._meta.languages;
        if (!Array.isArray(langs) || langs.length === 0) return [{ code: 'en', label: 'English' }];
        return langs.map(function (l) {
            if (typeof l === 'string') return { code: l, label: l };
            return { code: l.code, label: l.label || l.code };
        });
    }

    /**
     * Boot-time initializer. Called once after the DOM and Blazor are
     * up. Reads the saved language from localStorage (defaulting to
     * 'en') and applies it. Idempotent — safe to call repeatedly.
     */
    async function init() {
        let saved = 'en';
        try { saved = localStorage.getItem(STORAGE_KEY) || 'en'; } catch (e) { }
        await setLanguage(saved);
    }

    /**
     * Diagnostic: walk the live DOM, find every text-node phrase, and
     * report which of a target list are present, how many times, and
     * whether the glossary has a translation in the current language.
     * Type eslI18n.debug() in the console to print the report.
     */
    function debug(targetPhrases) {
        var phrases = targetPhrases || [
            'Connection', 'Mount Model', 'Tools', 'Site Location & Time',
            'Calculators', 'Firmware Config', 'Polar Alignment', 'Star Alignment',
            'Get GPS Location', 'Nearby', 'GoTo', 'SYNC', 'Wikipedia ↗'
        ];
        var w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null);
        var found = {};
        var n;
        while ((n = w.nextNode())) {
            var v = (n.nodeValue || '').replace(/^\s+|\s+$/g, '').replace(/\s+/g, ' ');
            if (v) found[v] = (found[v] || 0) + 1;
        }
        console.log('=== eslI18n.debug — language:', _currentLang, '===');
        console.log('Glossary loaded:', _glossary ? _glossary.entries ? Object.keys(_glossary.entries).length : 0 : 'no');
        for (var i = 0; i < phrases.length; i++) {
            var p = phrases[i];
            var inDom = found[p] || 0;
            var inGlossary = _glossary && _glossary.entries && _glossary.entries[p];
            var translation = inGlossary && inGlossary[_currentLang];
            console.log(
                p,
                '| DOM count:', inDom,
                '| in glossary:', !!inGlossary,
                '| translation:', translation || '(empty)'
            );
        }
    }

    /**
     * Inspect every text-node match for a phrase: shows parent element,
     * whether the walker has visited it (origText cached), and what the
     * text node currently contains. Useful for diagnosing why a known
     * glossary entry isn't translating.
     */
    function inspect(phrase) {
        var w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null);
        var n, i = 0;
        while ((n = w.nextNode())) {
            var trimmed = (n.nodeValue || '').replace(/^\s+|\s+$/g, '').replace(/\s+/g, ' ');
            if (trimmed === phrase) {
                i++;
                console.log(
                    phrase, '#' + i,
                    '| parent <' + n.parentElement.tagName + ' class="' + n.parentElement.className + '">',
                    '| origText cached:', n._origText !== undefined,
                    '| current nodeValue:', JSON.stringify((n.nodeValue || '').substring(0, 60))
                );
            }
        }
        if (i === 0) console.log(phrase, '— no DOM matches');
    }

    /**
     * Force-retranslate now. Useful after a Razor re-render to see if
     * the walker can reach all nodes if invoked again.
     */
    function retranslate() {
        if (_currentLang === 'en') {
            console.log('Language is English — nothing to translate');
            return;
        }
        translateAll(_currentLang);
        console.log('Force-retranslated for language:', _currentLang);
    }

    return { setLanguage, getLanguage, getAvailableLanguages, init, debug, inspect, retranslate };
})();
