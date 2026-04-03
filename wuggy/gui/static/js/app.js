document.addEventListener("DOMContentLoaded", () => {
    // Elements
    const inputBody        = document.getElementById("input-body");
    const languageSelect   = document.getElementById("language-select");
    const languageStatus   = document.getElementById("language-status");
    const syllabifyBtn     = document.getElementById("syllabify-btn");
    const generateBtn      = document.getElementById("generate-btn");
    const exportBtn        = document.getElementById("export-btn");
    const addRowBtn        = document.getElementById("add-row-btn");
    const clearRowsBtn     = document.getElementById("clear-rows-btn");
    const undoClearBtn     = document.getElementById("undo-clear-btn");
    const resetDefaultsBtn = document.getElementById("reset-defaults-btn");
    const fileInput        = document.getElementById("file-input");
    const progressWrap     = document.getElementById("progress-wrap");
    const progressFill     = document.getElementById("progress-fill");
    const progressText     = document.getElementById("progress-text");
    const tabInputBtn      = document.getElementById("tab-input-btn");
    const tabOutputBtn     = document.getElementById("tab-output-btn");
    const tabLogBtn        = document.getElementById("tab-log-btn");
    const panelInput       = document.getElementById("panel-input");
    const panelOutput      = document.getElementById("panel-output");
    const panelLog         = document.getElementById("panel-log");
    const outputBadge      = document.getElementById("output-badge");
    const logBadge         = document.getElementById("log-badge");
    const logContent       = document.getElementById("log-content");
    const logEmpty         = document.getElementById("log-empty");
    const resultsHeader    = document.getElementById("results-header");
    const resultsBody      = document.getElementById("results-body");
    const resultsCount     = document.getElementById("results-count");
    const resultsEmpty     = document.getElementById("results-empty");

    let currentResults = [];
    let logEntries = [];
    let languageLoaded = false;
    let sortCol = null;
    let sortAsc = true;
    let clearedRows = null;

    const DEFAULTS = {
        ncandidates: 10, max_time: 10, output_type: "pseudowords",
        match_segment_length: true, match_letter_length: true,
        concentric_search: true, match_overlap: true,
        overlap_num: 2, overlap_den: 3,
        show_syllables: true, show_lexicality: true, show_old20: true,
        show_ned1: true, show_overlap: true, show_deviation: true,
    };

    // --- Tabs ---

    function showTab(which) {
        tabInputBtn.classList.toggle("active", which === "input");
        tabOutputBtn.classList.toggle("active", which === "output");
        tabLogBtn.classList.toggle("active", which === "log");
        panelInput.hidden  = which !== "input";
        panelOutput.hidden = which !== "output";
        panelLog.hidden    = which !== "log";
    }

    tabInputBtn.addEventListener("click", () => showTab("input"));
    tabOutputBtn.addEventListener("click", () => showTab("output"));
    tabLogBtn.addEventListener("click", () => showTab("log"));

    // --- Input table ---

    function addInputRow(word = "", syllables = "", regex = "") {
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td class="col-num">${inputBody.children.length + 1}</td>
            <td><input type="text" class="word-input" value="${esc(word)}" placeholder="Enter word…"></td>
            <td><input type="text" class="syl-input" value="${esc(syllables)}" placeholder="e.g. sen-tence" title="Syllabified form. Auto-filled by Syllabify; edit manually for words not in the lexicon."></td>
            <td><input type="text" class="regex-input" value="${esc(regex)}" placeholder="e.g. .+ing$" title="Optional regex: only pseudowords matching this pattern will be included."></td>
            <td><button class="del-row-btn" title="Delete this row">&times;</button></td>
        `;
        tr.querySelector(".del-row-btn").addEventListener("click", () => {
            tr.remove();
            renumberRows();
        });
        tr.querySelector(".word-input").addEventListener("keydown", e => {
            if (e.key !== "Enter") return;
            e.preventDefault();
            const rows = Array.from(inputBody.children);
            const idx = rows.indexOf(tr);
            if (idx === rows.length - 1) addInputRow();
            inputBody.children[idx + 1]?.querySelector(".word-input").focus();
        });
        // Any edit to the word clears the auto-filled syllabification
        tr.querySelector(".word-input").addEventListener("input", () => {
            tr.querySelector(".syl-input").value = "";
        });
        inputBody.appendChild(tr);
        return tr;
    }

    function renumberRows() {
        Array.from(inputBody.children).forEach((tr, i) => {
            tr.querySelector(".col-num").textContent = i + 1;
        });
    }

    function captureRows() {
        return Array.from(inputBody.children).map(tr => ({
            word: tr.querySelector(".word-input").value,
            syllables: tr.querySelector(".syl-input").value,
            regex: tr.querySelector(".regex-input").value,
        }));
    }

    function getInputRows() {
        return Array.from(inputBody.children).map(tr => ({
            word: tr.querySelector(".word-input").value.trim(),
            syllables: tr.querySelector(".syl-input").value.trim(),
            regex: tr.querySelector(".regex-input").value.trim(),
        })).filter(r => r.word.length > 0);
    }

    function esc(s) {
        return String(s).replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;");
    }

    for (let i = 0; i < 10; i++) addInputRow();

    addRowBtn.addEventListener("click", () => {
        addInputRow();
        inputBody.lastElementChild.querySelector(".word-input").focus();
    });

    clearRowsBtn.addEventListener("click", () => {
        clearedRows = captureRows();
        undoClearBtn.hidden = false;
        inputBody.innerHTML = "";
        for (let i = 0; i < 10; i++) addInputRow();
    });

    undoClearBtn.addEventListener("click", () => {
        if (!clearedRows) return;
        inputBody.innerHTML = "";
        clearedRows.forEach(r => addInputRow(r.word, r.syllables, r.regex));
        clearedRows = null;
        undoClearBtn.hidden = true;
    });

    // Hide undo once user starts editing
    inputBody.addEventListener("input", () => {
        if (!undoClearBtn.hidden) {
            clearedRows = null;
            undoClearBtn.hidden = true;
        }
    });

    resetDefaultsBtn.addEventListener("click", () => {
        document.getElementById("max-candidates").value = DEFAULTS.ncandidates;
        document.getElementById("max-time").value = DEFAULTS.max_time;
        document.getElementById("output-type").value = DEFAULTS.output_type;
        document.getElementById("match-segment-length").checked = DEFAULTS.match_segment_length;
        document.getElementById("match-letter-length").checked = DEFAULTS.match_letter_length;
        document.getElementById("concentric-search").checked = DEFAULTS.concentric_search;
        document.getElementById("match-overlap").checked = DEFAULTS.match_overlap;
        document.getElementById("overlap-num").value = DEFAULTS.overlap_num;
        document.getElementById("overlap-den").value = DEFAULTS.overlap_den;
        document.getElementById("show-syllables").checked = DEFAULTS.show_syllables;
        document.getElementById("show-lexicality").checked = DEFAULTS.show_lexicality;
        document.getElementById("show-old20").checked = DEFAULTS.show_old20;
        document.getElementById("show-ned1").checked = DEFAULTS.show_ned1;
        document.getElementById("show-overlap").checked = DEFAULTS.show_overlap;
        document.getElementById("show-deviation").checked = DEFAULTS.show_deviation;
        if (currentResults.length > 0) renderResults();
    });

    // --- File upload ---

    fileInput.addEventListener("change", async () => {
        const file = fileInput.files[0];
        if (!file) return;
        const form = new FormData();
        form.append("file", file);
        try {
            const res = await fetch("/api/upload", { method: "POST", body: form });
            const data = await res.json();
            if (data.error) { alert("Upload error: " + data.error); return; }
            if (data.warnings?.length) alert("Upload warnings:\n" + data.warnings.join("\n") + "\n\nFile was still loaded.");
            if (data.rows) {
                inputBody.innerHTML = "";
                data.rows.forEach(r => addInputRow(r.word || "", r.syllables || "", r.matching_expression || ""));
                if (data.rows.length < 10) for (let i = data.rows.length; i < 10; i++) addInputRow();
            }
        } catch (e) { alert("Error reading file: " + e.message); }
        fileInput.value = "";
    });

    // --- Language loading ---

    let languageAvailability = {};

    async function loadLanguages() {
        try {
            const res = await fetch("/api/languages");
            const data = await res.json();
            languageAvailability = data.availability || {};
            languageSelect.innerHTML = '<option value="">-- Select language --</option>';
            data.available.forEach(lang => {
                const opt = document.createElement("option");
                opt.value = lang;
                const avail = languageAvailability[lang] || "remote";
                const suffix = data.loaded.includes(lang) ? " \u2713"
                             : avail === "remote"         ? " \u2193"
                             : "";
                opt.textContent = lang.replace(/_/g, " ") + suffix;
                if (avail === "remote") opt.style.color = "#aaa";
                languageSelect.appendChild(opt);
            });
            if (data.current) {
                languageSelect.value = data.current;
                languageLoaded = true;
                updateButtons();
                languageStatus.textContent = "Loaded: " + data.current;
                languageStatus.className = "status-msg success";
                loadLexiconInfo();
            }
            languageSelect.disabled = false;
        } catch (e) {
            languageStatus.textContent = "Error loading language list";
            languageStatus.className = "status-msg error";
        }
    }

    async function loadLexiconInfo() {
        try {
            const res = await fetch("/api/language-info");
            if (!res.ok) return;
            const info = await res.json();
            document.getElementById("lex-bigram").textContent   = info.bigram_data    || "—";
            document.getElementById("lex-word").textContent     = info.word_lexicon   || "—";
            document.getElementById("lex-neighbor").textContent = info.neighbor_lexicon || "—";
            document.getElementById("lex-lookup").textContent   = info.lookup_lexicon || "—";
            document.getElementById("lexicon-info").hidden = false;
        } catch (_) {}
    }

    languageSelect.addEventListener("change", async () => {
        const lang = languageSelect.value;
        if (!lang) return;
        languageLoaded = false;
        updateButtons();
        languageSelect.disabled = true;
        const avail = languageAvailability[lang] || "remote";
        languageStatus.textContent = avail === "remote"
            ? "Downloading " + lang + "… (this may take a moment)"
            : "Loading " + lang + "…";
        languageStatus.className = "status-msg loading";
        document.getElementById("lexicon-info").hidden = true;
        try {
            const res = await fetch("/api/load-language", {
                method: "POST", headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ language: lang }),
            });
            const data = await res.json();
            if (data.job_id) {
                await pollJob("/api/load-language/" + data.job_id, job => {
                    if (job.status === "done") {
                        languageLoaded = true;
                        languageStatus.textContent = "Loaded: " + lang;
                        languageStatus.className = "status-msg success";
                        loadLexiconInfo();
                        loadLanguages(); // refresh availability badges
                    } else if (job.status === "error") {
                        languageStatus.textContent = "Error: " + (job.error || "Unknown");
                        languageStatus.className = "status-msg error";
                    }
                });
            }
        } catch (e) {
            languageStatus.textContent = "Error: " + e.message;
            languageStatus.className = "status-msg error";
        }
        languageSelect.disabled = false;
        updateButtons();
    });

    // --- Syllabify ---

    syllabifyBtn.addEventListener("click", async () => {
        const words = Array.from(inputBody.querySelectorAll(".word-input"))
            .map(el => el.value.trim()).filter(w => w);
        if (!words.length) return;
        syllabifyBtn.disabled = true;
        syllabifyBtn.textContent = "Syllabifying…";
        try {
            const res = await fetch("/api/syllabify", {
                method: "POST", headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ words }),
            });
            const data = await res.json();
            const wordInputs = Array.from(inputBody.querySelectorAll(".word-input"));
            const sylInputs  = Array.from(inputBody.querySelectorAll(".syl-input"));
            data.results.forEach(r => {
                for (let i = 0; i < wordInputs.length; i++) {
                    if (wordInputs[i].value.trim() === r.word) {
                        sylInputs[i].value = r.syllables || "(not found)";
                        break;
                    }
                }
            });
        } catch (e) { alert("Syllabify error: " + e.message); }
        syllabifyBtn.disabled = false;
        syllabifyBtn.textContent = "Syllabify";
    });

    // --- Generate ---

    generateBtn.addEventListener("click", async () => {
        const rows = getInputRows();
        if (!rows.length) return;

        // Compile regex filters (client-side post-processing)
        const regexFilters = {};
        for (const r of rows) {
            if (r.regex) {
                try { regexFilters[r.word] = new RegExp(r.regex); }
                catch (e) { alert(`Invalid regex for "${r.word}": ${e.message}`); return; }
            }
        }

        generateBtn.disabled = true;
        syllabifyBtn.disabled = true;
        exportBtn.disabled = true;
        currentResults = [];
        logEntries = [];
        outputBadge.hidden = true;
        logBadge.hidden = true;
        logContent.innerHTML = "";
        logEmpty.hidden = false;

        progressWrap.hidden = false;
        progressFill.style.width = "0%";
        progressFill.classList.remove("done");
        progressText.textContent = "Starting…";

        const settings = {
            ncandidates:                    parseInt(document.getElementById("max-candidates").value) || 10,
            max_search_time:                parseInt(document.getElementById("max-time").value) || 10,
            match_subsyllabic_segment_length: document.getElementById("match-segment-length").checked,
            match_letter_length:            document.getElementById("match-letter-length").checked,
            concentric_search:              document.getElementById("concentric-search").checked,
            output_mode:                    document.getElementById("show-syllables").checked ? "syllabic" : "plain",
            output_type:                    document.getElementById("output-type").value,
        };

        if (document.getElementById("match-overlap").checked) {
            settings.overlap_numerator   = parseInt(document.getElementById("overlap-num").value) || 2;
            settings.overlap_denominator = parseInt(document.getElementById("overlap-den").value) || 3;
        } else {
            settings.overlap_numerator = null;
            settings.overlap_denominator = null;
        }

        // Collect manual syllabifications
        const syllabifications = {};
        rows.forEach(r => { if (r.syllables) syllabifications[r.word] = r.syllables; });

        // Show output tab with empty state while generating
        renderResults(true);
        showTab("output");

        try {
            const res = await fetch("/api/generate", {
                method: "POST", headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ words: rows.map(r => r.word), settings, syllabifications }),
            });
            const data = await res.json();
            if (data.job_id) {
                let lastSeen = 0;
                await pollJob("/api/generate/" + data.job_id, job => {
                    const pct = job.total > 0 ? Math.round((job.completed / job.total) * 100) : 0;
                    progressFill.style.width = pct + "%";
                    if (job.current_word) {
                        progressText.textContent = `Processing "${job.current_word}" (${job.completed + 1}/${job.total})`;
                    }

                    // Stream in new results, route errors to log
                    const newBatch = job.results.slice(lastSeen);
                    if (newBatch.length > 0) {
                        let hasNewResults = false;
                        newBatch.forEach(r => {
                            if (r.error) {
                                appendLogEntry(r.word, r.error, "error");
                            } else {
                                if (r.pseudoword && regexFilters[r.word] && !regexFilters[r.word].test(r.pseudoword)) return;
                                currentResults.push(r);
                                hasNewResults = true;
                            }
                        });
                        lastSeen = job.results.length;
                        if (hasNewResults) renderResults(job.status !== "done");
                    }

                    if (job.status === "done") {
                        progressFill.classList.add("done");
                        const errCount = logEntries.length;
                        const summary = `Done — ${currentResults.length} candidate${currentResults.length !== 1 ? "s" : ""} for ${job.total} word${job.total !== 1 ? "s" : ""}` +
                            (errCount > 0 ? ` (${errCount} error${errCount !== 1 ? "s" : ""}, see Log tab)` : "");
                        progressText.textContent = summary;
                        outputBadge.textContent = currentResults.length;
                        outputBadge.hidden = false;
                        if (errCount > 0) {
                            logBadge.textContent = errCount;
                            logBadge.hidden = false;
                        }
                    } else if (job.status === "error") {
                        progressText.textContent = "Error: " + (job.error || "Unknown");
                    }
                });
            }
        } catch (e) {
            progressText.textContent = "Error: " + e.message;
        }

        updateButtons();
    });

    // --- Export CSV ---

    exportBtn.addEventListener("click", async () => {
        if (!currentResults.length) return;
        const defaultName = `wuggy_${(languageSelect.value || "results").replace(/\s+/g, "_")}_${new Date().toISOString().slice(0, 10)}.csv`;
        const filename = prompt("Save CSV as:", defaultName);
        if (filename === null) return;
        const columns = getVisibleColumns().map(c => c.key);
        try {
            const res = await fetch("/api/export-csv", {
                method: "POST", headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ results: flattenResults(currentResults), columns }),
            });
            const blob = await res.blob();
            const a = Object.assign(document.createElement("a"), { href: URL.createObjectURL(blob), download: filename || defaultName });
            a.click();
            URL.revokeObjectURL(a.href);
        } catch (e) { alert("Export error: " + e.message); }
    });

    // --- Results rendering ---

    const COLUMN_TOOLTIPS = {
        word:                   "The original input word.",
        pseudoword:             "The generated pseudoword candidate.",
        lexicality:             "W = real word in the lexicon; N = nonword.",
        old20:                  "Orthographic Levenshtein Distance to the 20 nearest words. Lower = denser neighborhood.",
        old20_diff:             "Difference in OLD20 between the pseudoword and the input word.",
        ned1:                   "Number of words at edit distance 1 (one substitution, insertion, or deletion).",
        ned1_diff:              "Difference in NED1 between the pseudoword and the input word.",
        overlap_ratio:          "Fraction of subsyllabic segments shared between the pseudoword and the input word.",
        max_deviation:          "Largest deviation in transition frequency between any single bigram in the pseudoword vs the input word.",
        summed_deviation:       "Sum of all absolute transition frequency deviations.",
        max_deviation_position: "Position (bigram index) of the maximally deviating transition.",
    };

    const ALL_COLUMNS = [
        { key: "word",                   label: "Word",              group: null,        getter: r => r.word },
        { key: "pseudoword",             label: "Match",             group: null,        getter: r => r.pseudoword },
        { key: "lexicality",             label: "Lexicality",        group: "lexicality", getter: r => stat(r, "lexicality") },
        { key: "old20",                  label: "OLD20",             group: "old20",     getter: r => stat(r, "old20") },
        { key: "old20_diff",             label: "OLD20 Diff",        group: "old20",     getter: r => diff(r, "old20") },
        { key: "ned1",                   label: "NED1",              group: "ned1",      getter: r => stat(r, "ned1") },
        { key: "ned1_diff",              label: "NED1 Diff",         group: "ned1",      getter: r => diff(r, "ned1") },
        { key: "overlap_ratio",          label: "Overlap Ratio",     group: "overlap",   getter: r => stat(r, "overlap_ratio") },
        { key: "max_deviation",          label: "Max Deviation",     group: "deviation", getter: r => r.max_deviation },
        { key: "summed_deviation",       label: "Summed Dev.",       group: "deviation", getter: r => r.summed_deviation },
        { key: "max_deviation_position", label: "Max Dev. Position", group: "deviation", getter: r => r.max_deviation_position },
    ];

    function stat(r, name) { return r.statistics?.[name] ?? ""; }
    function diff(r, name) { return r.difference_statistics?.[name] ?? ""; }

    function getVisibleColumns() {
        const show = {
            lexicality: document.getElementById("show-lexicality").checked,
            old20:      document.getElementById("show-old20").checked,
            ned1:       document.getElementById("show-ned1").checked,
            overlap:    document.getElementById("show-overlap").checked,
            deviation:  document.getElementById("show-deviation").checked,
        };
        return ALL_COLUMNS.filter(c => c.group === null || show[c.group]);
    }

    function renderResults(partial = false) {
        const cols = getVisibleColumns();

        // Header
        resultsHeader.innerHTML = "";
        cols.forEach(col => {
            const th = document.createElement("th");
            th.title = COLUMN_TOOLTIPS[col.key] || "";
            const label = document.createTextNode(col.label);
            const arrow = document.createElement("span");
            arrow.className = "sort-arrow";
            th.appendChild(label);
            th.appendChild(arrow);
            if (sortCol === col.key) {
                arrow.textContent = sortAsc ? "\u25B2" : "\u25BC";
                th.classList.add(sortAsc ? "sorted-asc" : "sorted-desc");
            } else {
                arrow.textContent = "\u25B2";
            }
            th.addEventListener("click", () => {
                sortCol === col.key ? (sortAsc = !sortAsc) : (sortCol = col.key, sortAsc = true);
                renderResults(partial);
            });
            resultsHeader.appendChild(th);
        });

        // Sort rows
        let rows = [...currentResults];
        if (sortCol) {
            const cd = cols.find(c => c.key === sortCol);
            if (cd) rows.sort((a, b) => {
                let va = cd.getter(a) ?? "", vb = cd.getter(b) ?? "";
                if (typeof va === "number" && typeof vb === "number") return sortAsc ? va - vb : vb - va;
                return sortAsc ? String(va).localeCompare(String(vb)) : String(vb).localeCompare(String(va));
            });
        }

        // Body
        resultsBody.innerHTML = "";
        let lastWord = null;
        rows.forEach(r => {
            const tr = document.createElement("tr");
            if (r.error) {
                tr.className = "error-row";
                tr.innerHTML = `<td colspan="${cols.length}">${esc(r.word)}: ${esc(r.error)}</td>`;
            } else {
                if (r.word !== lastWord && lastWord !== null) tr.classList.add("word-group-start");
                lastWord = r.word;
                cols.forEach(col => {
                    const td = document.createElement("td");
                    const val = col.getter(r);
                    td.textContent = val != null ? val : "";
                    tr.appendChild(td);
                });
            }
            resultsBody.appendChild(tr);
        });

        const countLabel = partial
            ? `${currentResults.length} candidates so far…`
            : `${currentResults.length} candidate${currentResults.length !== 1 ? "s" : ""}`;
        resultsCount.textContent = countLabel;
        resultsEmpty.hidden = currentResults.length > 0;
        exportBtn.disabled = currentResults.length === 0;
    }

    function appendLogEntry(word, message, level = "error") {
        const now = new Date();
        const time = now.toTimeString().slice(0, 8);
        logEntries.push({ time, word, message, level });
        logEmpty.hidden = true;
        const div = document.createElement("div");
        div.className = "log-entry";
        div.innerHTML = `<span class="log-time">${esc(time)}</span><span class="log-word">${esc(word)}</span><span class="log-msg ${esc(level)}">${esc(message)}</span>`;
        logContent.appendChild(div);
    }

    function flattenResults(results) {
        return results.map(r => {
            const flat = { word: r.word, pseudoword: r.pseudoword };
            if (r.statistics) Object.entries(r.statistics).forEach(([k, v]) => { if (typeof v !== "object") flat[k] = v; });
            if (r.difference_statistics) Object.entries(r.difference_statistics).forEach(([k, v]) => { if (typeof v !== "object") flat[k + "_diff"] = v; });
            flat.max_deviation = r.max_deviation;
            flat.summed_deviation = r.summed_deviation;
            flat.max_deviation_position = r.max_deviation_position;
            return flat;
        });
    }

    // Re-render when output options change
    document.querySelectorAll(".settings-group input[data-col]").forEach(cb => {
        cb.addEventListener("change", () => { if (currentResults.length > 0) renderResults(); });
    });

    // --- Utilities ---

    function updateButtons() {
        syllabifyBtn.disabled = !languageLoaded;
        generateBtn.disabled  = !languageLoaded;
        exportBtn.disabled    = currentResults.length === 0;
    }

    async function pollJob(url, onUpdate) {
        while (true) {
            await sleep(600);
            try {
                const res = await fetch(url);
                const job = await res.json();
                onUpdate(job);
                if (job.status === "done" || job.status === "error") return;
            } catch (_) { return; }
        }
    }

    function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

    // --- Init ---
    loadLanguages();
    renderResults(); // show empty state in output tab

    // About modal (wired up inside DOMContentLoaded so the element exists)
    const aboutModal    = document.getElementById("about-modal");
    const aboutCloseBtn = document.getElementById("about-close-btn");
    aboutCloseBtn.addEventListener("click", () => { aboutModal.hidden = true; });
    aboutModal.addEventListener("click", e => { if (e.target === aboutModal) aboutModal.hidden = true; });
});

// Global: called by pywebview's evaluate_js from the native menu
function showAbout() {
    const modal = document.getElementById("about-modal");
    if (modal) modal.hidden = false;
}

// Open external links via the backend so pywebview doesn't navigate away
document.addEventListener("click", e => {
    const link = e.target.closest(".doi-link");
    if (!link) return;
    e.preventDefault();
    const url = link.dataset.url;
    if (url) fetch("/api/open-url", { method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify({url}) });
});
