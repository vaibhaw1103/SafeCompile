// static/script.js
document.addEventListener('DOMContentLoaded', () => {
    const codeInput = document.getElementById('code-input');
    const lineNumbersDiv = document.getElementById('line-numbers');
    const compileButton = document.getElementById('compile-button');
    const analyzeButton = document.getElementById('analyze-button');
    const clearButton = document.getElementById('clear-button');

    const securityVulnerabilitiesDiv = document.getElementById('security-vulnerabilities');
    const analysisPlaceholder = document.getElementById('analysis-placeholder');

    // Elements for dynamic Compiled Output / Input
    const compilerOutputContainer = document.getElementById('compiler-output-container'); // The parent div
    let compilerOutputContent = document.getElementById('compiler-output'); // The actual output div, will be replaced/reverted
    const runWithInputButton = document.getElementById('run-with-input-button'); // New button

    const programOutputDiv = document.getElementById('program-output');

    // Loading indicators
    const compilerLoading = document.getElementById('compiler-loading');
    const programLoading = document.getElementById('program-loading');
    const parseTreeLoading = document.getElementById('parseTreeLoading'); 

    // Parse tree elements
    const parseTreeImage = document.getElementById('parseTreeImage');
    const parseTreeStatus = document.getElementById('parseTreeStatus');

    // Modal elements
    const parseTreeModal = document.getElementById('parseTreeModal');
    const modalParseTreeImage = document.getElementById('modalParseTreeImage');
    const closeButton = document.getElementsByClassName('close-button')[0];


    const errorMessageSection = document.getElementById('error-message-section');
    const errorMessageDiv = document.getElementById('error-message');

    // Store session_id for interactive input flow
    let currentSessionId = null;

    // Default code snippet for convenience
    const defaultCode = `
#include <stdio.h>
#include <string.h> // For vulnerable strcpy

int main() {
    char buffer[10];
    char input[] = "This is a very long string that will overflow the buffer.";

    printf("Hello from SafeCompile!\\n");

    // Vulnerable code: buffer overflow using strcpy
    // This should be flagged by analysis
    strcpy(buffer, input);

    printf("Buffer content: %s\\n", buffer);

    // Example with user input:
    // int num;
    // printf("Enter a number: ");
    // scanf("%d", &num); // This will trigger needs_input
    // printf("You entered: %d\\n", num);

    return 0;
}
    `;
    codeInput.value = defaultCode.trim();

    // --- Line Numbering Logic ---
    const updateLineNumbers = () => {
        const lines = codeInput.value.split('\n').length;
        lineNumbersDiv.innerHTML = '';
        for (let i = 1; i <= lines; i++) {
            const span = document.createElement('span');
            span.textContent = i;
            lineNumbersDiv.appendChild(span);
        }
    };

    codeInput.addEventListener('scroll', () => {
        lineNumbersDiv.scrollTop = codeInput.scrollTop;
    });
    codeInput.addEventListener('input', updateLineNumbers);
    codeInput.addEventListener('propertychange', updateLineNumbers);
    codeInput.addEventListener('change', updateLineNumbers);
    updateLineNumbers();


    // --- Helper for showing/hiding loading indicators ---
    const showLoading = (element, loader) => {
        // Clear element's existing content or ensure it's not visually blocking
        // For image element, we just ensure it's hidden before loading
        if (element.tagName === 'IMG') {
            element.style.display = 'none'; // Hide image while loading starts
            element.src = ''; // Clear source
        } else {
            element.textContent = '';
        }
        loader.classList.remove('hidden');
    };

    const hideLoading = (loader) => {
        loader.classList.add('hidden');
    };

    // --- Output Reset Function ---
    const resetOutput = () => {
        securityVulnerabilitiesDiv.innerHTML = '<p id="analysis-placeholder" class="text-gray-500 text-center py-4">Run analysis to see vulnerabilities...</p>';
        analysisPlaceholder.classList.remove('hidden');

        // Revert compiler output to div and clear content
        if (compilerOutputContent.tagName === 'TEXTAREA') {
            const tempContent = compilerOutputContent.value; // Save any typed input
            compilerOutputContainer.innerHTML = `<div id="compiler-output" class="whitespace-pre-wrap flex-grow"></div>`;
            compilerOutputContent = document.getElementById('compiler-output'); // Re-get reference
            compilerOutputContent.textContent = tempContent; // Restore saved content if desired, or clear
        }
        compilerOutputContent.textContent = ''; // Clear content
        runWithInputButton.classList.add('hidden'); // Hide the button

        programOutputDiv.textContent = '';
        errorMessageDiv.textContent = '';
        errorMessageSection.classList.add('hidden');
        hideLoading(compilerLoading);
        hideLoading(programLoading);
<<<<<<< HEAD
        currentSessionId = null; // Clear session ID
=======

        // Reset parse tree display
        parseTreeImage.src = '';
        parseTreeImage.style.display = 'none'; // Ensure image is hidden
        parseTreeStatus.textContent = 'Run analysis to generate parse tree...';
        hideLoading(parseTreeLoading);
        parseTreeImage.removeEventListener('click', openParseTreeModal); // Remove listener on reset
>>>>>>> 9355ef53ff6fb0c76cc6cdc4856c5930f564d6a2
    };

    // --- Handle Clear Button ---
    clearButton.addEventListener('click', () => {
        codeInput.value = '';
        resetOutput();
        updateLineNumbers();
    });

<<<<<<< HEAD
    // --- Core Compile/Analyze Logic ---
=======
    // --- Modal Functions ---
    const openParseTreeModal = () => {
        if (parseTreeImage.src) { // Only open if an image is loaded
            modalParseTreeImage.src = parseTreeImage.src;
            parseTreeModal.style.display = 'flex'; // Use flex for centering
            document.body.style.overflow = 'hidden'; // Prevent scrolling background
        }
    };

    const closeParseTreeModal = () => {
        parseTreeModal.style.display = 'none';
        modalParseTreeImage.src = ''; // Clear modal image
        document.body.style.overflow = 'auto'; // Restore scrolling
    };

    // Attach click listener to close button
    closeButton.addEventListener('click', closeParseTreeModal);
    // Close modal if user clicks outside of the image (on the modal background)
    window.addEventListener('click', (event) => {
        if (event.target == parseTreeModal) {
            closeParseTreeModal();
        }
    });


    // --- Universal Analyze & Compile Function ---
>>>>>>> 9355ef53ff6fb0c76cc6cdc4856c5930f564d6a2
    const analyzeAndCompile = async (analyzeOnly = false) => {
        const code = codeInput.value;
        if (!code.trim()) {
            errorMessageDiv.textContent = 'Please enter some C code.';
            errorMessageSection.classList.remove('hidden');
            return;
        }

<<<<<<< HEAD
        resetOutput(); // Reset all outputs and hide input elements
        showLoading(compilerOutputContent, compilerLoading);
=======
        resetOutput(); // Reset everything including image
        showLoading(compilerOutputDiv, compilerLoading); // Show loading for compiler
        showLoading(parseTreeImage, parseTreeLoading); // Show loading for parse tree
        parseTreeStatus.textContent = "Generating parse tree..."; 
        
>>>>>>> 9355ef53ff6fb0c76cc6cdc4856c5930f564d6a2
        if (!analyzeOnly) {
            showLoading(programOutputDiv, programLoading);
        }

        compileButton.disabled = true;
        analyzeButton.disabled = true;
        clearButton.disabled = true;

        try {
            const endpoint = '/analyze_and_compile';
            const response = await fetch(endpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ code: code }),
            });

            const data = await response.json();

            if (response.ok) {
                // Display Analysis Report (common for both modes)
                if (data.analysis && data.analysis.report_messages) {
                    analysisPlaceholder.classList.add('hidden');
<<<<<<< HEAD
                    securityVulnerabilitiesDiv.innerHTML = '';
=======
                    securityVulnerabilitiesDiv.innerHTML = ''; 

>>>>>>> 9355ef53ff6fb0c76cc6cdc4856c5930f564d6a2
                    const staticIssues = data.analysis.static_issues || [];
                    const mlVulnerable = data.analysis.ml_vulnerable;
                    const mlProbability = data.analysis.ml_probability;
                    const overallSafe = data.analysis.overall_safe;
                    const reportMessages = data.analysis.report_messages || [];

                    const verdictCard = document.createElement('div');
                    verdictCard.className = `p-4 rounded-md shadow-md mb-4 ${overallSafe ? 'bg-green-700' : 'bg-red-700'}`;
                    verdictCard.innerHTML = `<p class="font-bold text-lg">${overallSafe ? '✅ Code appears SAFE' : '❌ VULNERABILITY DETECTED!'}</p>`;
                    securityVulnerabilitiesDiv.appendChild(verdictCard);

                    const mlCard = document.createElement('div');
                    mlCard.className = `p-4 rounded-md shadow-md mb-4 ${mlVulnerable ? 'bg-red-700' : 'bg-green-700'}`;
                    mlCard.innerHTML = `
                        <p class="font-bold text-lg">ML Prediction (CodeBERT + XGBoost)</p>
                        <p>Probability: ${mlProbability !== undefined ? mlProbability.toFixed(4) : 'N/A'}</p>
                        <p>Verdict: ${mlVulnerable ? 'VULNERABLE' : 'SAFE'}</p>
                    `;
                    securityVulnerabilitiesDiv.appendChild(mlCard);

                    if (staticIssues.length > 0) {
                        const staticHeader = document.createElement('h3');
                        staticHeader.className = 'text-xl font-semibold mt-4 mb-2';
                        staticHeader.textContent = 'Static Analysis Findings:';
                        securityVulnerabilitiesDiv.appendChild(staticHeader);
                        staticIssues.forEach(issue => {
                            const issueCard = document.createElement('div');
                            let bgColor = 'bg-yellow-700';
                            if (issue.includes('Error:') || issue.includes('CRITICAL')) {
                                bgColor = 'bg-red-700';
                            } else if (issue.includes('Warning:')) {
                                bgColor = 'bg-yellow-700';
                            } else if (issue.includes('Suggestion:')) {
                                bgColor = 'bg-blue-700';
                            }
                            issueCard.className = `p-4 rounded-md shadow-md mb-2 ${bgColor}`;
                            issueCard.innerHTML = `<p class="text-sm code-font">${issue}</p>`;
                            securityVulnerabilitiesDiv.appendChild(issueCard);
                        });
                    }
                    if (staticIssues.length === 0 && mlVulnerable === false && !overallSafe) {
                        securityVulnerabilitiesDiv.innerHTML += '<p class="text-gray-400 mt-2">No direct static rule violations detected.</p>';
                    }
                    securityVulnerabilitiesDiv.innerHTML += `<h3 class="text-xl font-semibold mt-4 mb-2">Detailed Report:</h3>`;
                    reportMessages.forEach(msg => {
                        securityVulnerabilitiesDiv.innerHTML += `<p class="text-sm text-gray-400 mb-1">${msg}</p>`;
                    });

                } else {
                    securityVulnerabilitiesDiv.innerHTML = '<p class="text-gray-500 text-center py-4">No security analysis report available.</p>';
                }

                // Display Parse Tree Image
                hideLoading(parseTreeLoading);
                if (data.parse_tree && data.parse_tree.generated && data.parse_tree.image_path) {
                    const imageUrl = `/static/${data.parse_tree.image_path}`; 
                    parseTreeImage.src = imageUrl;
                    // Force the image to display (override any previous display:none)
                    parseTreeImage.style.display = 'block'; 
                    parseTreeStatus.textContent = "Parse tree generated successfully. Click on image to view full size."; 
                    // Add click listener for modal after the image source is set
                    parseTreeImage.addEventListener('click', openParseTreeModal);
                } else {
                    parseTreeImage.style.display = 'none'; 
                    const graphvizError = data.analysis.report_messages.some(msg => msg.includes("Graphviz is not installed"));
                    if (graphvizError) {
                        parseTreeStatus.textContent = "Parse tree visualization failed: Graphviz is not installed or not in server's PATH.";
                    } else {
                        parseTreeStatus.textContent = "Parse tree could not be generated (possible parsing errors or empty code).";
                    }
                }


                // Handle Compilation/Execution Output (only if not analyzeOnly)
                if (!analyzeOnly) {
                    currentSessionId = data.session_id; // Store session ID

<<<<<<< HEAD
                    if (data.needs_input && data.session_id) { // Check if input is needed and session ID is provided
                        // Transform compiler-output div into a textarea for input
                        const originalCompilerOutputText = data.compilation_execution.compiler_output || 'Compilation successful.';
                        compilerOutputContainer.innerHTML = `
                            <div class="whitespace-pre-wrap flex-grow text-gray-400 mb-2 text-sm">${originalCompilerOutputText}</div>
                            <textarea id="compiler-output-input" class="compiler-input-textarea flex-grow" placeholder="Program requires input. Type here and click 'Run Program' below..."></textarea>
                        `;
                        // Re-get reference to the new input textarea
                        compilerOutputContent = document.getElementById('compiler-output-input');
                        runWithInputButton.classList.remove('hidden'); // Show run button
                        programOutputDiv.textContent = 'Program awaiting input...'; // Indicate program status
=======
                    // Display Program Output (only if not analyzeOnly)
                    if (data.compilation_execution && data.compilation_execution.program_output) {
                        programOutputDiv.textContent = data.compilation_execution.program_output;
                    } else if (data.compilation_execution && data.compilation_execution.error_message) {
                        programOutputDiv.textContent = `Program did not produce output due to: ${data.compilation_execution.error_message}`;
>>>>>>> 9355ef53ff6fb0c76cc6cdc4856c5930f564d6a2
                    } else {
                        // Display compiler output normally in the div
                        compilerOutputContainer.innerHTML = `<div id="compiler-output" class="whitespace-pre-wrap flex-grow"></div>`;
                        compilerOutputContent = document.getElementById('compiler-output'); // Re-get reference

                        if (data.compilation_execution && data.compilation_execution.compiler_output) {
                            compilerOutputContent.textContent = data.compilation_execution.compiler_output;
                        } else {
                            compilerOutputContent.textContent = 'No compiler output.';
                        }

                        if (data.compilation_execution && data.compilation_execution.program_output) {
                            programOutputDiv.textContent = data.compilation_execution.program_output;
                        } else if (data.compilation_execution && data.compilation_execution.error_message) {
                            programOutputDiv.textContent = `Program did not produce output due to: ${data.compilation_execution.error_message}`;
                        } else {
                            programOutputDiv.textContent = 'No program output.';
                        }
                    }
                } else {
<<<<<<< HEAD
                    compilerOutputContent.textContent = 'Compilation not performed in Analyze mode.';
=======
                    compilerOutputDiv.textContent = 'Compilation not performed in Analyze mode.';
>>>>>>> 9355ef53ff6fb0c76cc6cdc4856c5930f564d6a2
                    programOutputDiv.textContent = 'Program not executed in Analyze mode.';
                }

                if (data.error) {
                    errorMessageDiv.textContent = data.error;
                    errorMessageSection.classList.remove('hidden');
                }

            } else {
                errorMessageDiv.textContent = data.error || `Server responded with status: ${response.status} - ${response.statusText}`;
                errorMessageSection.classList.remove('hidden');
            }
        } catch (error) {
            console.error('Fetch error:', error);
            errorMessageDiv.textContent = `A network error occurred or the server is unreachable: ${error.message}. Please check your Flask server.`;
            errorMessageSection.classList.remove('hidden');
        } finally {
            hideLoading(compilerLoading);
            hideLoading(programLoading);
<<<<<<< HEAD
            if (!currentSessionId) { // Only re-enable if not waiting for input
                compileButton.disabled = false;
                analyzeButton.disabled = false;
                clearButton.disabled = false;
            }
=======
            hideLoading(parseTreeLoading);
            compileButton.disabled = false;
            analyzeButton.disabled = false;
            clearButton.disabled = false;
>>>>>>> 9355ef53ff6fb0c76cc6cdc4856c5930f564d6a2
        }
    };

    // --- Handle Run With Input Button Click ---
    runWithInputButton.addEventListener('click', async () => {
        if (!currentSessionId || compilerOutputContent.tagName !== 'TEXTAREA') { // Check if session ID exists and element is textarea
            errorMessageDiv.textContent = 'Error: No program awaiting input or invalid state.';
            errorMessageSection.classList.remove('hidden');
            return;
        }

        const input_data = compilerOutputContent.value; // Get input from the textarea
        programOutputDiv.textContent = ''; // Clear previous program output
        showLoading(programOutputDiv, programLoading);

        compileButton.disabled = true; // Keep buttons disabled
        analyzeButton.disabled = true;
        clearButton.disabled = true;
        runWithInputButton.disabled = true; // Disable itself

        try {
            const response = await fetch('/execute_with_input', { // Call new endpoint for execution with input
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ session_id: currentSessionId, input: input_data }), // Send session ID and input
            });

            const data = await response.json();

            if (response.ok) {
                programOutputDiv.textContent = data.program_output || 'Program ran, no output.';
                if (data.error_message) {
                    errorMessageDiv.textContent = `Program execution error: ${data.error_message}`;
                    errorMessageSection.classList.remove('hidden');
                }
            } else {
                errorMessageDiv.textContent = data.error || `Server responded with status: ${response.status} - ${response.statusText}`;
                errorMessageSection.classList.remove('hidden');
            }
        } catch (error) {
            console.error('Execute with input fetch error:', error);
            errorMessageDiv.textContent = `Network error during program execution: ${error.message}.`;
            errorMessageSection.classList.remove('hidden');
        } finally {
            hideLoading(programLoading);
            // Revert compiler output area back to original div structure
            compilerOutputContainer.innerHTML = `<div id="compiler-output" class="whitespace-pre-wrap flex-grow"></div>`;
            compilerOutputContent = document.getElementById('compiler-output'); // Re-get reference
            // You can optionally put the initial compiler output back here if desired
            // compilerOutputContent.textContent = "Initial compilation output..."; // Or fetch it again if needed

            compileButton.disabled = false;
            analyzeButton.disabled = false;
            clearButton.disabled = false;
            runWithInputButton.disabled = false; // Re-enable itself, though it will be hidden by next line
            runWithInputButton.classList.add('hidden'); // Hide button after execution
            currentSessionId = null; // Clear session ID
        }
    });

    // --- Add event listeners for Compile and Analyze buttons ---
    compileButton.addEventListener('click', () => analyzeAndCompile(false));
    analyzeButton.addEventListener('click', () => analyzeAndCompile(true));

    // --- Initial setup ---
    resetOutput(); // Call reset to ensure initial state is clean
});
