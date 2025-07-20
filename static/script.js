// Declare all DOM elements globally for accessibility
let codeEditorContainer, analyzeButton, runButton, clearButton, parseTreeButton;
let reportContentDiv, analysisPlaceholder, reportTitle;
let terminalDiv, terminalLoading;
let parseTreeModal, modalParseTreeImage, closeModalButton;
// Elements for resizable layout
let editorPanel, terminalPanel, verticalResizer, leftColumn;

// Monaco Editor, xterm.js, and Socket.IO instances
let monacoEditor;
let term;
let fitAddon;
let socket;

// State variables
let currentLineDecoration = [];
let currentDisplayMode = 'security'; // 'security' or 'parsetree'

// Reusable loading indicator HTML
const loadingIndicatorHTML = `
<div class="flex flex-col items-center justify-center h-full text-gray-500">
    <svg class="animate-spin h-8 w-8 text-cyan-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
    <p class="mt-3 text-sm">Loading...</p>
</div>`;

// Default secure and compilable C code
const defaultCode = `
#include <stdio.h>

int main() {
  // Your code goes here
  printf("Hello, World!");
  return 0;
}
`;

document.addEventListener('DOMContentLoaded', () => {
    try {
        assignDOMElements();
        initializeMonacoEditor();
    } catch (mainError) {
        console.error('A critical error occurred during script initialization:', mainError);
    }
});

function assignDOMElements() {
    codeEditorContainer = document.getElementById('code-editor-container');
    analyzeButton = document.getElementById('analyze-button');
    runButton = document.getElementById('run-button');
    clearButton = document.getElementById('clear-button');
    parseTreeButton = document.getElementById('parsetree-button');
    reportContentDiv = document.getElementById('report-content');
    analysisPlaceholder = document.getElementById('analysis-placeholder');
    reportTitle = document.getElementById('report-title');
    terminalDiv = document.getElementById('terminal');
    terminalLoading = document.getElementById('terminal-loading');
    parseTreeModal = document.getElementById('parseTreeModal');
    modalParseTreeImage = document.getElementById('modalParseTreeImage');
    closeModalButton = document.getElementById('closeModalButton');
    editorPanel = document.getElementById('editor-panel');
    terminalPanel = document.getElementById('terminal-panel');
    verticalResizer = document.getElementById('vertical-resizer');
    leftColumn = document.getElementById('left-column');
}

function initializeMonacoEditor() {
    if (typeof require === 'undefined') {
        console.error("Monaco Editor loader not found.");
        return;
    }
    require.config({ paths: { 'vs': 'https://cdn.jsdelivr.net/npm/monaco-editor@0.40.0/min/vs' } });
    require(['vs/editor/editor.main'], () => {

        monaco.editor.defineTheme('safeCompileBlack', {
            base: 'vs-dark',
            inherit: true,
            rules: [],
            colors: {
                'editor.background': '#000000',
                'editorGutter.background': '#000000'
            }
        });

        monacoEditor = monaco.editor.create(codeEditorContainer, {
            value: defaultCode.trim(),
            language: 'c',
            theme: 'safeCompileBlack',
            automaticLayout: true,
            minimap: { enabled: false },
            scrollBeyondLastLine: false,
            fontSize: 14,
            fontFamily: '"Fira Code", monospace',
            tabSize: 4,
            insertSpaces: true,
        });
        
        initializeTerminal();
        attachEventListeners();
        initializeResizablePanels();
    });
}

function initializeTerminal() {
    if (!terminalDiv) return;
    term = new Terminal({
        theme: { background: '#080909', foreground: '#c9d1d9', cursor: '#22d3ee', selection: 'rgba(34, 211, 238, 0.3)' },
        scrollback: 2000,
        cursorBlink: true,
        cursorStyle: 'block',
        fontFamily: 'Fira Code, monospace',
        fontSize: 14,
        convertEol: true,
    });

    fitAddon = new FitAddon.FitAddon();
    term.loadAddon(fitAddon);
    term.open(terminalDiv);
    fitAddon.fit();

    initializeSocket();
}

function initializeSocket() {
    socket = io();
    socket.on('connect', () => term.write('\x1b[36m[INFO]: Connected to backend. Ready.\x1b[0m\r\n'));
    socket.on('disconnect', () => term.write('\x1b[31m\r\n[ERROR]: Disconnected from backend.\x1b[0m\r\n'));
    socket.on('terminal_output', (data) => data.output && term.write(data.output));
    socket.on('program_started', (data) => {
        term.write(`\x1b[36m\r\n[INFO]: ${data.message}\x1b[0m\r\n`);
        hideLoading(terminalLoading);
        term.focus();
    });
    socket.on('execution_complete', (data) => {
        const exitMessage = data.success 
            ? `\x1b[32m\r\n[INFO]: Program exited with code ${data.exit_code || 0}.\x1b[0m\r\n`
            : `\x1b[31m\r\n[ERROR]: Program execution failed: ${data.error || 'Unknown error'}.\x1b[0m\r\n`;
        term.write(exitMessage);
        setButtonsDisabled(false);
        hideLoading(terminalLoading);
    });

    term.onData(e => {
        const code = e.charCodeAt(0);
        if (e === '\r') {
            term.write('\r\n');
        } else if (code === 127 || code === 8) {
            if (term.buffer.active.cursorX > 0) term.write('\b \b');
        } else {
            term.write(e);
        }
        socket.emit('terminal_input', { input: e });
    });
}

function attachEventListeners() {
    analyzeButton.addEventListener('click', () => startProcess('analyze'));
    parseTreeButton.addEventListener('click', () => startProcess('parsetree'));
    runButton.addEventListener('click', () => startProcess('run'));
    clearButton.addEventListener('click', () => {
        monacoEditor.setValue('');
        resetOutput();
    });
    
    closeModalButton.addEventListener('click', closeParseTreeModal);
    parseTreeModal.addEventListener('click', (event) => {
        if (event.target === parseTreeModal) closeParseTreeModal();
    });
    
    window.addEventListener('resize', () => {
        if (fitAddon) fitAddon.fit();
    });
}

function initializeResizablePanels() {
    if (!verticalResizer) return;
    let isResizing = false;
    verticalResizer.addEventListener('mousedown', (e) => {
        isResizing = true;
        document.body.style.cursor = 'ns-resize';
        document.body.style.userSelect = 'none';
        const onMouseMove = (e) => {
            if (!isResizing) return;
            const containerRect = leftColumn.getBoundingClientRect();
            const editorPanelHeight = e.clientY - containerRect.top;
            const editorPanelPercent = (editorPanelHeight / containerRect.height) * 100;
            if (editorPanelPercent > 20 && editorPanelPercent < 80) {
                editorPanel.style.height = `${editorPanelPercent}%`;
                terminalPanel.style.height = `${100 - editorPanelPercent}%`;
            }
        };
        const onMouseUp = () => {
            isResizing = false;
            document.body.style.cursor = 'default';
            document.body.style.userSelect = 'auto';
            document.removeEventListener('mousemove', onMouseMove);
            document.removeEventListener('mouseup', onMouseUp);
        };
        document.addEventListener('mousemove', onMouseMove);
        document.addEventListener('mouseup', onMouseUp);
    });
}

function startProcess(mode) {
    const code = monacoEditor.getValue();
    if (!code.trim()) {
        alert('Please enter some C code.');
        return;
    }

    resetOutput();
    setButtonsDisabled(true);

    currentDisplayMode = (mode === 'parsetree') ? 'parsetree' : 'security';

    switch (mode) {
        case 'analyze':
            reportTitle.textContent = 'Security Report';
            reportContentDiv.innerHTML = loadingIndicatorHTML;
            break;
            
        case 'parsetree':
            reportTitle.textContent = 'Parse Tree';
            reportContentDiv.innerHTML = loadingIndicatorHTML;
            break;

        case 'run':
            terminalPanel.classList.remove('hidden');
            verticalResizer.classList.remove('hidden');
            showLoading(terminalLoading);
            setTimeout(() => fitAddon.fit(), 50);

            reportTitle.textContent = 'Security Report';
            reportContentDiv.innerHTML = loadingIndicatorHTML;
            break;
    }
    
    const backendMode = (mode === 'run') ? 'compile' : 'analyze';
    socket.emit('compile_and_analyze', { code: code, mode: backendMode });

    socket.once('analysis_results', handleAnalysisResults);
    if (mode === 'run') {
        socket.once('compiler_output', handleCompilerOutput);
    }
}

function handleAnalysisResults(data) {
    if (!data || !data.analysis) {
        reportContentDiv.innerHTML = `<p class="text-red-400">Error receiving analysis results.</p>`;
        return;
    }
    
    reportContentDiv.innerHTML = ''; // Clear placeholder/loader

    if (currentDisplayMode === 'parsetree') {
        reportTitle.textContent = 'Parse Tree';
        if (data.parse_tree && data.parse_tree.generated) {
            const img = document.createElement('img');
            img.src = `/static/${data.parse_tree.image_path}?t=${new Date().getTime()}`;
            img.className = "max-w-full max-h-full object-contain cursor-pointer";
            img.addEventListener('click', openParseTreeModal);
            
            modalParseTreeImage.src = img.src;
            reportContentDiv.appendChild(img);
        } else {
            reportContentDiv.innerHTML = '<p class="text-gray-500 text-center py-4">Parse tree could not be generated.</p>';
        }
    } else { // 'security' mode
        reportTitle.textContent = 'Security Report';
        
        // Add the ML summary card to the top of the report
        reportContentDiv.appendChild(createMLSummaryCard(data.analysis));

        const geminiFindings = data.analysis.gemini_findings || [];
        if (geminiFindings.length > 0) {
            geminiFindings.forEach(finding => {
                reportContentDiv.appendChild(createFindingCard(finding));
            });
        } else {
            // Append a "no findings" message if no other issues were found
            const noFindingsDiv = document.createElement('div');
            noFindingsDiv.innerHTML = '<div class="text-center pt-4"><p class="text-green-400 font-semibold">✅ No other vulnerabilities found.</p></div>';
            reportContentDiv.appendChild(noFindingsDiv);
        }
    }
    
    const wasRunCommand = runButton.disabled && !terminalPanel.classList.contains('hidden');
    if (!wasRunCommand) {
        setButtonsDisabled(false);
    }
}

function createMLSummaryCard(analysis) {
    const isVulnerable = analysis.ml_vulnerable;
    const color = isVulnerable ? "yellow" : "green";
    const predictionText = isVulnerable ? "Vulnerable" : "Likely Safe";
    
    const probabilityPercent = (analysis.ml_probability * 100).toFixed(1);

    const card = document.createElement('div');
    card.className = `p-3 rounded-md mb-4 bg-gray-900/50 border border-gray-700`;
    
    card.innerHTML = `
        <div class="flex justify-between items-center">
            <p class="font-semibold text-md text-cyan-400">
                Machine Learning Analysis
            </p>
            <p class="text-md font-semibold text-${color}-400">
                Prediction: ${predictionText}
            </p>
        </div>
        <div class="w-full bg-gray-700 rounded-full h-2.5 mt-2">
            <div class="bg-${color}-500 h-2.5 rounded-full" style="width: ${probabilityPercent}%"></div>
        </div>
        <p class="text-xs text-right text-gray-400 mt-1">Confidence: ${probabilityPercent}%</p>
    `;
    return card;
}

function createFindingCard(finding) {
    const severityColor = { "Critical": "red", "Medium": "yellow", "Low": "green" }[finding.severity] || "gray";
    const card = document.createElement('div');
    card.className = `p-3 rounded-md mb-3 bg-gray-900/50 border border-gray-700 cursor-pointer transition transform hover:border-cyan-500`;
    const sanitizedSuggestion = finding.suggestion.replace(/</g, "&lt;").replace(/>/g, "&gt;");
    card.innerHTML = `
        <div class="flex justify-between items-center mb-2">
            <p class="font-semibold text-md text-${severityColor}-400 flex items-center">
                <span class="w-2 h-2 bg-${severityColor}-500 rounded-full mr-2"></span>
                ${finding.title}
            </p>
            <span class="text-xs font-mono text-gray-500">Line: ${finding.line_number}</span>
        </div>
        <p class="text-sm text-gray-400 mb-2 pl-4 border-l-2 border-gray-700"><strong>Explanation:</strong> ${finding.explanation}</p>
        <p class="text-sm text-gray-300 mb-1 pl-4"><strong>Suggestion:</strong></p>
        <pre class="bg-gray-900 p-2 rounded-md text-xs code-font whitespace-pre-wrap ml-4"><code>${sanitizedSuggestion}</code></pre>
    `;
    if (finding.line_number > 0) {
        card.addEventListener('click', () => jumpToLineAndHighlight(finding.line_number));
    }
    return card;
}

function handleCompilerOutput(data) {
    if (data.output) {
        const fullOutput = data.output;
        const hasError = fullOutput.toLowerCase().includes('error:');
        if (hasError) {
            term.write(`\x1b[31m--- COMPILATION ERRORS ---\r\n${fullOutput}\r\n--------------------------\x1b[0m\r\n`);
        } else {
            term.write(`\x1b[32m[INFO]: Compilation successful.\x1b[0m\r\n`);
        }
    }
}

function setButtonsDisabled(disabled) {
    [analyzeButton, runButton, clearButton, parseTreeButton].forEach(btn => btn.disabled = disabled);
}

function showLoading(loader) {
    if (loader) loader.classList.remove('hidden');
}

function hideLoading(loader) {
    if (loader) loader.classList.add('hidden');
}

function resetOutput() {
    reportContentDiv.innerHTML = '<p id="analysis-placeholder" class="text-gray-500 text-center py-4">Run analysis to see results...</p>';
    reportTitle.textContent = 'Security Report';
    if (term) term.clear();
    hideLoading(terminalLoading);
    if (monacoEditor) monacoEditor.deltaDecorations(currentLineDecoration, []);

    if (terminalPanel && verticalResizer) {
        terminalPanel.classList.add('hidden');
        verticalResizer.classList.add('hidden');
    }
}

function jumpToLineAndHighlight(lineNumber) {
    if (!monacoEditor || isNaN(lineNumber)) return;
    currentLineDecoration = monacoEditor.deltaDecorations(currentLineDecoration, [{
        range: new monaco.Range(lineNumber, 1, lineNumber, 1),
        options: { isWholeLine: true, className: 'myLineHighlight' }
    }]);
    monacoEditor.revealLineInCenter(lineNumber);
    monacoEditor.focus();
}

function openParseTreeModal() {
    if (modalParseTreeImage && modalParseTreeImage.src) {
        parseTreeModal.classList.remove('hidden');
    }
}

function closeParseTreeModal() {
    parseTreeModal.classList.add('hidden');
}