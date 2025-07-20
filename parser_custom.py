# parser_custom.py
import logging # Import logging
from lexer import tokenize_code 
from parse_tree_node import ParseTreeNode 

# Set up logging for parser_custom.py
parser_logger = logging.getLogger(__name__ + '.Parser')
parser_logger.setLevel(logging.INFO) # Set to INFO for production, DEBUG for more verbose output

class Parser:
    # Define insecure functions and their info as class-level attributes
    insecure_functions = [
        "gets", "strcpy", "strcat", "scanf", "sprintf", "system",
        "eval", "popen", "vsprintf", "printf", "malloc", "realloc", "calloc"
    ]
    insecure_function_info = {
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

    def __init__(self, tokens):
        self.tokens = tokens
        self.current_token_index = 0
        self.current_token = None
        self.warnings = [] # Collect general parser warnings/errors here
        self.insecure_function_issues = [] # Collect structured insecure function findings
        self.advance() # Initialize current_token

        self.parse_tree_root = None 
        
        parser_logger.info(f"Parser initialized. Insecure function issues list length: {len(self.insecure_function_issues)}")


    def advance(self):
        """Advances to the next token and also returns the token's ParseTreeNode."""
        if self.current_token_index < len(self.tokens):
            token_data = self.tokens[self.current_token_index]
            self.current_token = token_data
            self.current_token_index += 1
            # Return a ParseTreeNode for the consumed token
            return ParseTreeNode(token_data[0], value=token_data[1], is_terminal=True)
        else:
            self.current_token = None # End of tokens
            return None # No token to advance to


    def warn(self, message, line_num):
        self.warnings.append(f"{line_num}: {message}")

    def match(self, expected_type, expected_value=None):
        """
        Attempts to match the current token. If successful, advances and returns
        the ParseTreeNode for the consumed token. Otherwise, returns None.
        """
        if self.current_token and \
           self.current_token[0] == expected_type and \
           (expected_value is None or self.current_token[1] == expected_value):
            # Capture the token's ParseTreeNode before advancing
            token_pt_node = ParseTreeNode(self.current_token[0], value=self.current_token[1], is_terminal=True)
            self.advance() # Move to next token
            return token_pt_node # Return the parse tree node of the matched token
        return None # No match


    def expect(self, expected_type, expected_value=None, error_msg="Syntax Error"):
        """
        Attempts to match the current token. If successful, advances and returns
        the ParseTreeNode for the consumed token. If not, adds a warning and returns None.
        """
        matched_pt_node = self.match(expected_type, expected_value)
        if matched_pt_node:
            return matched_pt_node
        self.warn(f"❌ Error: {error_msg}. Expected {expected_type}{' (' + str(expected_value) + ')' if expected_value else ''}, got {self.current_token[0] if self.current_token else 'EOF'} ('{self.current_token[1]}' if self.current_token and len(self.current_token) > 1 else '')", self.current_token[2] if self.current_token else "EOF")
        return None

    def skip_whitespace_and_comments(self):
        # NEW: We won't return parse tree nodes for skipped tokens,
        # as they are typically not part of the concrete syntax tree.
        while self.current_token:
            token_type = self.current_token[0]
            if token_type == "WHITESPACE":
                self.advance()
            elif token_type == "PREPROCESSOR":
                self.warn(f"📌 Skipping preprocessor: {self.current_token[1]}", self.current_token[2])
                self.advance()
            elif token_type == "COMMENT":
                self.advance()
            else:
                break

    def parse(self):
        self.skip_whitespace_and_comments() # Initial skip for global tokens

        # NEW: Create a root node for the entire program's parse tree
        program_pt_node = ParseTreeNode('Program')

        while self.current_token:
            if self.current_token[0] == "KEYWORD" and self.current_token[1] in ["int", "void", "char", "float", "double", "long", "short", "unsigned", "signed"]:
                func_def_pt = self.parse_function_definition()
                if func_def_pt:
                    program_pt_node.add_child(func_def_pt)
            else:
                self.warn(f"❌ Error: Invalid top-level construct", self.current_token[2] if self.current_token else "EOF")
                self.warn(f"⚠️ Skipping unrecognized token: {self.current_token[1]} (type: {self.current_token[0]})", self.current_token[2] if self.current_token else "EOF")
                self.advance()
            self.skip_whitespace_and_comments()

        self.parse_tree_root = program_pt_node # Store the root
        # DEBUG LOG: Show the insecure_function_issues list right before returning
        parser_logger.info(f"DEBUG_PARSER: insecure_function_issues before return from parse(): {self.insecure_function_issues}")
        # Return both general warnings and structured insecure function issues
        return self.warnings, self.insecure_function_issues, self.parse_tree_root 

    def parse_function_definition(self):
        func_def_pt = ParseTreeNode('FunctionDefinition')

        # type (e.g., int, void)
        type_token_pt = self.expect("KEYWORD")
        if not type_token_pt: return None
        func_def_pt.add_child(type_token_pt)

        # function name
        id_token_pt = self.expect("IDENTIFIER")
        if not id_token_pt: return None
        func_def_pt.add_child(id_token_pt)

        # '('
        lparen_pt = self.expect("SEPARATOR", "(")
        if not lparen_pt: return None
        func_def_pt.add_child(lparen_pt)

        # parameters (simplified: just consume until ')')
        params_pt = ParseTreeNode('Parameters')
        func_def_pt.add_child(params_pt) # Add parameters non-terminal
        while self.current_token and not (self.current_token[0] == "SEPARATOR" and self.current_token[1] == ")"):
            # We need to capture each parameter token as a child of Parameters
            param_token_pt = self.advance() # advance already returns the PT node
            if param_token_pt:
                params_pt.add_child(param_token_pt)
            else: # EOF reached
                self.warn("❌ Error: Unclosed function parameters", self.tokens[-1][2] if self.tokens else "EOF")
                return None
        
        rparen_pt = self.expect("SEPARATOR", ")")
        if not rparen_pt: return None
        func_def_pt.add_child(rparen_pt)

        # '{' (function body start)
        lbrace_pt = self.expect("SEPARATOR", "{")
        if not lbrace_pt: return None
        func_def_pt.add_child(lbrace_pt)

        parser_logger.info("✅ Function Declaration Found")
        # Parse function body and add its parse tree to func_def_pt
        func_body_pt = self.parse_function_body()
        if func_body_pt:
            func_def_pt.add_child(func_body_pt)
        else:
            return None # Error in body parsing

        return func_def_pt # Return the ParseTreeNode for this function definition


    def parse_function_body(self):
        func_body_pt = ParseTreeNode('FunctionBody')
        # Parse statements until '}'
        while self.current_token and not (self.current_token[0] == "SEPARATOR" and self.current_token[1] == "}"):
            self.skip_whitespace_and_comments()
            statement_pt = self.parse_statement()
            if statement_pt:
                func_body_pt.add_child(statement_pt)
            else:
                # If parse_statement returned None, it means an error occurred or
                # an unhandled token was encountered. We should try to recover.
                if self.current_token and not (self.current_token[0] == "SEPARATOR" and self.current_token[1] == "}"):
                    self.warn(f"⚠️ Skipping unparsable token in function body: {self.current_token[1]} (type: {self.current_token[0]})", self.current_token[2] if self.current_token else "EOF")
                    self.advance() # Advance to prevent infinite loop
        
        rbrace_pt = self.expect("SEPARATOR", "}")
        if not rbrace_pt:
            self.warn("❌ Error: Unclosed function body", self.tokens[-1][2] if self.tokens else "EOF")
            return None
        func_body_pt.add_child(rbrace_pt)

        parser_logger.info("✅ Function Block Closed")
        return func_body_pt

    def parse_statement(self):
        statement_pt = ParseTreeNode('Statement')
        
        token_type, token_value, token_line = self.current_token if self.current_token else (None, None, None)

        # Variable Declaration (simplified: Type Identifier;)
        if token_type == "KEYWORD" and token_value in ["int", "char", "float", "double", "long", "short", "unsigned", "signed"]:
            type_token_pt = self.advance() # Consume type keyword
            statement_pt.add_child(type_token_pt)

            id_token_pt = self.match("IDENTIFIER") # Variable name
            if id_token_pt:
                statement_pt.add_child(id_token_pt)
                # Handle array declarations (e.g., `char arr[10];`)
                if self.current_token and self.current_token[0] == "OPERATOR" and self.current_token[1] == "[":
                    lsquare_pt = self.advance()
                    statement_pt.add_child(lsquare_pt)
                    # Consume array size tokens (simplified, just advance over them)
                    array_size_pt = ParseTreeNode('ArraySize') # New non-terminal for array size
                    statement_pt.add_child(array_size_pt)
                    while self.current_token and not (self.current_token[0] == "OPERATOR" and self.current_token[1] == "]"):
                        size_token_pt = self.advance()
                        if size_token_pt: array_size_pt.add_child(size_token_pt)
                        else: break # EOF
                    rsquare_pt = self.expect("OPERATOR", "]")
                    if rsquare_pt: statement_pt.add_child(rsquare_pt)
                    parser_logger.info("✅ Array Declaration")
            else:
                self.warn(f"❌ Error: Expected identifier after type keyword", token_line)
                return None # Failed to parse

            semicolon_pt = self.expect("SEPARATOR", ";", "Missing ';' in declaration")
            if semicolon_pt:
                statement_pt.add_child(semicolon_pt)
                parser_logger.info("✅ Variable Declaration")
                return statement_pt
            return None # Failed to parse

        # Return statement
        elif token_type == "KEYWORD" and token_value == "return":
            return_token_pt = self.advance() # Consume 'return'
            statement_pt.add_child(return_token_pt)

            expr_pt = self.parse_expression() # Consume the expression after return
            if expr_pt:
                statement_pt.add_child(expr_pt)
            else:
                # This could be a "return;" statement without an expression
                # Or an error. Let's assume 'return;' is valid here.
                pass 
            
            semicolon_pt = self.expect("SEPARATOR", ";", "Missing ';' after return statement")
            if semicolon_pt:
                statement_pt.add_child(semicolon_pt)
                parser_logger.info("✅ Return Statement")
                return statement_pt
            return None # Failed to parse

        # If/While/For (simplified: just consume the structure without detailed parsing)
        elif token_type == "KEYWORD" and token_value in ["if", "while", "for"]:
            keyword_pt = self.advance()
            statement_pt.add_child(keyword_pt)

            self.warn(f"📌 Skipping control flow structure: {token_value}", token_line)
            
            lparen_pt = self.match("SEPARATOR", "(") # Consume condition start
            if lparen_pt:
                statement_pt.add_child(lparen_pt)
                condition_pt = ParseTreeNode('Condition') # New non-terminal
                statement_pt.add_child(condition_pt)
                while self.current_token and not (self.current_token[0] == "SEPARATOR" and self.current_token[1] == ")"):
                    cond_token_pt = self.advance()
                    if cond_token_pt: condition_pt.add_child(cond_token_pt)
                    else: break # EOF
                rparen_pt = self.expect("SEPARATOR", ")")
                if rparen_pt: statement_pt.add_child(rparen_pt)
            
            # Handle the block or single statement body
            if self.current_token and self.current_token[0] == "SEPARATOR" and self.current_token[1] == "{":
                lbrace_pt = self.advance()
                statement_pt.add_child(lbrace_pt)
                block_body_pt = self.parse_function_body() # Treat block like a mini-function body
                if block_body_pt: statement_pt.add_child(block_body_pt)
            else: # Single statement or unparsed block
                single_stmt_pt = self.parse_statement() # Attempt to parse the next statement
                if single_stmt_pt: statement_pt.add_child(single_stmt_pt)
            
            return statement_pt

        # Expression Statement (e.g., function call, assignment)
        elif token_type in ["IDENTIFIER", "NUMBER", "STRING", "OPERATOR"] or \
             (token_type == "SEPARATOR" and token_value == '('): # Allow expressions starting with (
            expr_stmt_pt = self.parse_expression_statement()
            if expr_stmt_pt:
                statement_pt.add_child(expr_stmt_pt)
                return statement_pt
            return None # Failed to parse

        # Unrecognized token as a statement
        self.warn(f"⚠️ Skipping unknown/unhandled token as statement: {self.current_token[1]} (type: {self.current_token[0]})", token_line)
        self.advance() # Advance to avoid infinite loop
        return None # Indicate failure to parse this statement

    def parse_expression(self):
        expr_pt = ParseTreeNode('Expression')
        # This function needs to be more robust to build a proper expression sub-tree.
        # For simplicity, we'll continue to consume tokens for the expression,
        # but now we capture them as children of the Expression node.

        while self.current_token and \
              not (self.current_token[0] == "SEPARATOR" and self.current_token[1] in [";", "{", "}", ")", "]", ","]):
            
            token_type, token_value, _ = self.current_token

            # Handle parentheses for sub-expressions
            if token_type == "SEPARATOR" and token_value == "(":
                lparen_pt = self.advance()
                expr_pt.add_child(lparen_pt)
                sub_expr_pt = self.parse_expression() # Recursive call for nested expression
                if sub_expr_pt: expr_pt.add_child(sub_expr_pt)
                rparen_pt = self.expect("SEPARATOR", ")", "Unclosed parenthesis in expression")
                if rparen_pt: expr_pt.add_child(rparen_pt)
            
            # Handle array access (e.g., `arr[index]`) within expressions
            elif token_type == "OPERATOR" and token_value == "[":
                lsquare_pt = self.advance()
                expr_pt.add_child(lsquare_pt)
                array_index_expr_pt = self.parse_expression() # Index itself can be an expression
                if array_index_expr_pt: expr_pt.add_child(array_index_expr_pt)
                rsquare_pt = self.expect("OPERATOR", "]", "Unclosed bracket in array access")
                if rsquare_pt: expr_pt.add_child(rsquare_pt)

            else: # Consume general expression tokens (ID, NUMBER, STRING, OPERATOR)
                current_token_pt = self.advance()
                if current_token_pt:
                    expr_pt.add_child(current_token_pt)
                else: # EOF or unexpected token
                    break
        
        # If no children were added, it means the expression was empty or just a terminal
        if not expr_pt.children:
            return None # Indicate no valid expression was found
        
        return expr_pt


    def parse_expression_statement(self):
        expr_stmt_pt = ParseTreeNode('ExpressionStatement')
        token_type, token_value, token_line = self.current_token if self.current_token else (None, None, None)
        current_line = token_line # Store current line for warnings

        # This part handles things like function calls or assignments
        # Check for explicitly insecure functions (this needs to be robust)
        if token_type == "IDENTIFIER" and token_value in Parser.insecure_functions: # Access as class attribute
            self.check_insecure_function(token_value, current_line)
            
        # Parse the initial part of the expression (identifier, number, etc.)
        initial_expr_pt = self.parse_expression()
        if initial_expr_pt:
            expr_stmt_pt.add_child(initial_expr_pt)
        else:
            # If the initial expression cannot be parsed, it's an error
            self.warn(f"❌ Error: Cannot parse beginning of expression statement at token '{token_value}'", current_line)
            return None
        
        # Expect a semicolon to end the statement
        semicolon_pt = self.match("SEPARATOR", ";")
        if semicolon_pt:
            expr_stmt_pt.add_child(semicolon_pt)
            # parser_logger.info("✅ Expression Statement") # Removed to avoid excessive logging
            return expr_stmt_pt
        else:
            self.warn("❌ Error: Missing ';' in statement", current_line)
            return None # Indicate parse failure

    def check_insecure_function(self, func_name, line_num):
        # Access insecure_function_info as a class attribute
        info = Parser.insecure_function_info.get(func_name) 
        if info:
            fix_suggestion, cwe = info
            issue_data = {
                "function": func_name,
                "line": line_num,
                "fix": fix_suggestion,
                "cwe": cwe,
                "source": "Custom Parser"
            }
            self.insecure_function_issues.append(issue_data)
            parser_logger.info(f"DEBUG_PARSER: Added insecure function issue: {issue_data}. Current issues: {self.insecure_function_issues}")
        else:
            issue_data = {
                "function": func_name,
                "line": line_num,
                "fix": "Consult documentation for secure alternatives.",
                "cwe": "N/A",
                "source": "Custom Parser"
            }
            self.insecure_function_issues.append(issue_data)
            parser_logger.info(f"DEBUG_PARSER: Added insecure function issue (no detailed info): {issue_data}. Current issues: {self.insecure_function_issues}")


# --- Example Usage (for testing parser_custom.py independently) ---
if __name__ == "__main__":
    from lexer import Lexer # Import the Lexer class for testing

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
            x = x + 1;
        }
        printf("Vulnerable printf here.\\n"); // This should be flagged
        return 0;
    }

    void another_func(int a, char* b) {
        printf("Another printf.\\n"); // This should be flagged
        int* ptr = malloc(10 * sizeof(int)); // Should be flagged
        if (ptr == NULL) { /* handle error */ }
        free(ptr); // Not flagged
    }
    """
    
    lexer = Lexer(test_code)
    tokens = list(lexer.tokenize()) # Ensure tokens is a list

    parser = Parser(tokens)
    # Get both general warnings and specific insecure function issues
    warnings, insecure_func_issues, parse_tree_root = parser.parse() 

    print("\n--- Parser General Warnings/Errors ---")
    if warnings:
        for w in warnings:
            print(w)
    else:
        print("No general parser warnings or errors detected.")

    print("\n--- Insecure Function Findings (Custom Parser) ---")
    if insecure_func_issues:
        for issue in insecure_func_issues:
            print(f"Function: {issue['function']}(), Line: {issue['line']}, Fix: {issue['fix']}, CWE: {issue['cwe']}")
    else:
        print("No insecure functions detected by custom parser.")

    print("\n--- Generated Parse Tree ---")
    if parse_tree_root:
        parse_tree_root.print_tree()
        
        # --- Visualization (Requires visualize_tree.py and Graphviz installation) ---
        try:
            from visualize_tree import create_parse_tree_graph
            create_parse_tree_graph(parse_tree_root, 'output_parse_tree')
            print("\nParse tree image generated: output_parse_tree.png")
        except ImportError:
            print("\n'visualize_tree.py' or 'graphviz' library not found. Skipping visualization.")
        except Exception as e:
            print(f"\nError during parse tree visualization: {e}")
            print("Make sure Graphviz is installed and added to your system's PATH.")
    else:
        print("No parse tree was generated.")
