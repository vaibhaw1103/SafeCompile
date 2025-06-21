# parser_custom.py
from lexer import tokenize_code # Assuming Lexer is in lexer.py

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.current_token_index = 0
        self.current_token = None
        self.warnings = [] # Collect warnings/errors here
        self.advance() # Initialize current_token

        # List of functions considered insecure
        self.insecure_functions = [
            "gets", "strcpy", "strcat", "scanf", "sprintf", "system",
            "eval", "popen", "vsprintf", "printf", "malloc", "realloc", "calloc" # Added realloc, calloc
        ]
        # Map insecure functions to their CWE and suggested fix
        self.insecure_function_info = {
            "gets": ("use fgets()", "CWE-120"),
            "strcpy": ("use strncpy() with size limit", "CWE-120"),
            "strcat": ("use strncat() with size limit", "CWE-120"),
            "scanf": ("specify field width", "CWE-120"),
            "sprintf": ("use snprintf()", "CWE-120"),
            "system": ("avoid executing external commands", "CWE-78"),
            "eval": ("avoid code injection", "CWE-94"),
            "popen": ("avoid executing external commands", "CWE-78"),
            "vsprintf": ("use vsnprintf()", "CWE-120"),
            "printf": ("format string literal", "CWE-134"), # Note: this will flag all printf
            "malloc": ("check return value for NULL", "CWE-399"), # Not directly insecure, but common source of error
            "realloc": ("check return value for NULL", "CWE-399"),
            "calloc": ("check return value for NULL", "CWE-399")
        }


    def advance(self):
        if self.current_token_index < len(self.tokens):
            self.current_token = self.tokens[self.current_token_index]
            self.current_token_index += 1
        else:
            self.current_token = None # End of tokens

    def warn(self, message, line_num):
        self.warnings.append(f"{line_num}: {message}")

    def match(self, expected_type, expected_value=None):
        if self.current_token and \
           self.current_token[0] == expected_type and \
           (expected_value is None or self.current_token[1] == expected_value):
            self.advance()
            return True
        return False

    def expect(self, expected_type, expected_value=None, error_msg="Syntax Error"):
        if self.match(expected_type, expected_value):
            return True
        self.warn(f"❌ Error: {error_msg}", self.current_token[2] if self.current_token else "EOF")
        return False

    def skip_whitespace_and_comments(self):
        # Skip whitespace, preprocessor directives, and comments
        while self.current_token:
            token_type = self.current_token[0]
            if token_type == "WHITESPACE":
                self.advance()
            elif token_type == "PREPROCESSOR":
                # We often just skip preprocessor directives for basic parsing
                self.warn(f"📌 Skipping preprocessor: {self.current_token}", self.current_token[2])
                self.advance()
            elif token_type == "COMMENT":
                self.advance()
            else:
                break # Not a whitespace, preprocessor, or comment, so stop skipping

    def parse(self):
        self.skip_whitespace_and_comments() # Initial skip for global tokens

        while self.current_token:
            if self.current_token[0] == "KEYWORD" and self.current_token[1] in ["int", "void", "char", "float", "double", "long", "short", "unsigned", "signed"]:
                self.parse_function_definition()
            else:
                # If it's not a keyword for a function, it's something unrecognized at top level
                self.warn(f"❌ Error: Invalid function definition", self.current_token[2])
                self.warn(f"⚠️ Skipping unrecognized token: {self.current_token}", self.current_token[2])
                self.advance() # Try to advance to avoid infinite loop on bad tokens
            self.skip_whitespace_and_comments() # Skip between top-level constructs
        return self.warnings

    def parse_function_definition(self):
        # type (e.g., int, void)
        if not self.expect("KEYWORD"):
            return

        # function name
        if not self.expect("IDENTIFIER"):
            return

        # '('
        if not self.expect("SEPARATOR", "("):
            return

        # parameters (simplified: just consume until ')')
        while self.current_token and not self.match("SEPARATOR", ")"):
            self.advance() # consume parameter tokens
        if not self.current_token: # Reached EOF without ')'
            self.warn("❌ Error: Unclosed function parameters", self.tokens[-1][2] if self.tokens else "EOF")
            return

        # '{' (function body start)
        if not self.expect("SEPARATOR", "{"):
            return

        print("✅ Function Declaration Found\n")
        self.parse_function_body()


    def parse_function_body(self):
        # Parse statements until '}'
        while self.current_token and not self.match("SEPARATOR", "}"):
            self.skip_whitespace_and_comments() # Skip inside function body
            self.parse_statement()
        if not self.current_token: # Reached EOF without '}'
            self.warn("❌ Error: Unclosed function body", self.tokens[-1][2] if self.tokens else "EOF")
            return
        print("✅ Function Block Closed\n")

    def parse_statement(self):
        token_type, token_value, token_line = self.current_token

        # Variable Declaration (simplified: Type Identifier;)
        if token_type == "KEYWORD" and token_value in ["int", "char", "float", "double", "long", "short", "unsigned", "signed"]:
            self.advance() # Consume type keyword
            if self.match("IDENTIFIER"): # Variable name
                # Handle array declarations (e.g., `char arr[10];`)
                if self.match("OPERATOR", "["):
                    while self.current_token and not self.match("OPERATOR", "]"):
                        self.advance() # Consume array size tokens
                    print("✅ Array Declaration\n")
            if self.expect("SEPARATOR", ";", "Missing ';' in declaration"):
                print("✅ Variable Declaration\n")
            return

        # Return statement
        if token_type == "KEYWORD" and token_value == "return":
            self.advance() # Consume 'return'
            self.parse_expression() # Consume the expression after return
            if self.expect("SEPARATOR", ";", "Missing ';' after return statement"):
                print("✅ Return Statement\n")
            return

        # If/While/For (simplified: just consume the structure without detailed parsing)
        if token_type == "KEYWORD" and token_value in ["if", "while", "for"]:
            self.warn(f"📌 Skipping control flow structure: {token_value}", token_line)
            self.advance() # Consume keyword
            if self.match("SEPARATOR", "("): # Consume condition
                while self.current_token and not self.match("SEPARATOR", ")"):
                    self.advance()
            if self.current_token and self.current_token[0] == "SEPARATOR" and self.current_token[1] == "{": # Consume block
                self.advance()
                self.parse_function_body() # Treat block like a mini-function body
            else: # Single statement or unparsed block
                self.parse_statement() # Attempt to parse the next statement
            return

        # Expression Statement (e.g., function call, assignment)
        # This is the most common type of statement not covered by other rules.
        if token_type == "IDENTIFIER" or token_type == "NUMBER" or token_type == "STRING" or token_type == "OPERATOR":
            self.parse_expression_statement()
            return

        # Unrecognized token as a statement
        self.warn(f"⚠️ Skipping unknown/unhandled token as statement: {self.current_token}", token_line)
        self.advance() # Advance to avoid infinite loop


    def parse_expression(self):
        # Extremely simplified expression parsing: just consume tokens until a semicolon or end of line/block
        # This will not actually build an expression tree, just skip over it.
        while self.current_token and \
              self.current_token[0] not in ["SEPARATOR", "KEYWORD", "OPERATOR"] and \
              self.current_token[1] not in [";", "{", "}", ")", "]", ","]:
            self.advance()
        # Handle cases where it's a number, string, or identifier followed by an operator
        if self.current_token and self.current_token[0] in ["NUMBER", "STRING", "IDENTIFIER"]:
             self.advance()
        if self.current_token and self.current_token[0] == "OPERATOR" and self.current_token[1] != ";": # Consume operators
            self.advance() # Consume the operator
            self.parse_expression() # And whatever follows it


    def parse_expression_statement(self):
        token_type, token_value, token_line = self.current_token
        current_line = token_line # Store current line for warnings

        # This part handles things like function calls or assignments
        # Check for explicitly insecure functions (this needs to be robust)
        if token_type == "IDENTIFIER" and token_value in self.insecure_functions:
            self.check_insecure_function(token_value, current_line)

        # Advance past the identifier or initial token of the expression
        self.advance()

        # Simplified parsing of whatever follows (function call, assignment, etc.)
        # Consume tokens until a semicolon, brace, or parenthesis closure
        while self.current_token and \
              self.current_token[0] != "SEPARATOR" or \
              self.current_token[1] not in [";", "{", "}"]: # Stop before potential block/end
            # If it's an opening parenthesis, consume until closing one
            if self.current_token[0] == "SEPARATOR" and self.current_token[1] == "(":
                self.advance() # Consume '('
                while self.current_token and not (self.current_token[0] == "SEPARATOR" and self.current_token[1] == ")"):
                    self.advance()
                if self.current_token and self.current_token[0] == "SEPARATOR" and self.current_token[1] == ")":
                    self.advance() # Consume ')'
                    print("✅ Function Call\n") # Assume it was a function call if ()
                else:
                    self.warn(f"❌ Error: Unclosed parenthesis in expression/call", current_line)
                    break # Break to avoid infinite loop
            # Handle array access [ ]
            elif self.current_token[0] == "OPERATOR" and self.current_token[1] == "[":
                self.advance() # Consume '['
                while self.current_token and not (self.current_token[0] == "OPERATOR" and self.current_token[1] == "]"):
                    self.advance()
                if self.current_token and self.current_token[0] == "OPERATOR" and self.current_token[1] == "]":
                    self.advance() # Consume ']'
                else:
                    self.warn(f"❌ Error: Unclosed bracket in array access", current_line)
                    break # Break to avoid infinite loop
            else:
                self.advance() # Consume other tokens in the expression

        # Expect a semicolon to end the statement
        if self.match("SEPARATOR", ";"):
            # If it was a function call, we've already printed that
            # If it was an assignment, we should print that
            # For now, just a generic "Expression Statement"
            # print("✅ Expression Statement\n") # Commented out to avoid double print with Function Call
            pass
        else:
            self.warn("❌ Error: Missing ';' in statement", current_line)


    def check_insecure_function(self, func_name, line_num):
        info = self.insecure_function_info.get(func_name)
        if info:
            fix_suggestion, cwe = info
            self.warn(f"❌ Use of insecure function {func_name}() detected.", line_num)
            self.warn(f"    💡 Suggested fix: {fix_suggestion}. [CWE-{cwe}]", line_num)
        else:
            self.warn(f"❌ Detected use of '{func_name}' (marked as insecure).", line_num)


# --- Example Usage (for testing parser_custom.py independently) ---
if __name__ == "__main__":
    test_code = """
    // This is a test comment
    #include <stdio.h> // Another comment
    /* Multi-line
       comment */
    int main() {
        char buffer[10];
        // strcpy(buffer, "too long string"); // This should be flagged
        fputs("Hello, world!", stdout); // This should NOT be flagged
        gets(buffer); // This should be flagged
        if (1) {
            int x = 5;
        }
        return 0;
    }

    void another_func() {
        printf("Vulnerable printf here.\\n"); // This should be flagged
        int* ptr = malloc(10 * sizeof(int)); // Should be flagged
        if (ptr == NULL) { /* handle error */ }
        free(ptr); // Not flagged
    }
    """
    lexer = Lexer(test_code)
    tokens = lexer.tokenize()

    parser = Parser(tokens)
    warnings = parser.parse()

    print("\n--- Parser Warnings/Errors ---")
    if warnings:
        for w in warnings:
            print(w)
    else:
        print("No parser-specific warnings or errors detected (apart from expected insecure function warnings).")

    # This part should be handled by analyze.py and main.py
    # print("\n--- Insecure Function Detections ---")
    # if parser.insecure_function_warnings:
    #    for warning in parser.insecure_function_warnings:
    #        print(warning)
    # else:
    #    print("No insecure functions detected.")