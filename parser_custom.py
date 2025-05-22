class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0
        self.current_token = self.tokens[self.pos] if self.tokens else None
        self.warnings = []

    def warn(self, message, line=None):
        formatted = f"{line}: {message}" if line else message
        print(formatted)
        self.warnings.append(formatted)

    def advance(self):
        self.pos += 1
        if self.pos < len(self.tokens):
            self.current_token = self.tokens[self.pos]
        else:
            self.current_token = None
        return self.current_token

    def peek(self):
        return self.current_token

    def match(self, expected_type, expected_value=None):
        if self.current_token is None:
            return False
        token_type, token_value, *_ = self.current_token
        if token_type == expected_type and (expected_value is None or token_value == expected_value):
            self.advance()
            return True
        return False

    def parse(self):
        print("\U0001F50D Parsing Program...\n")
        while self.current_token is not None:
            if self.current_token[0] == "PREPROCESSOR":
                print(f"📌 Skipping preprocessor: {self.current_token}")
                self.advance()
                continue

            start_pos = self.pos
            self.parse_function()
            if self.pos == start_pos:
                self.warn(f"⚠️ Skipping unrecognized token: {self.current_token}", self.current_token[2] if self.current_token else None)
                self.advance()
        return self.warnings

    def parse_function(self):
        if self.current_token and self.current_token[0] == "KEYWORD":
            self.advance()  # Return type
            if self.match("IDENTIFIER") and self.match("SEPARATOR", "("):
                while not self.match("SEPARATOR", ")") and self.current_token:
                    self.advance()
                if self.match("SEPARATOR", "{"):
                    print("✅ Function Declaration Found\n")
                    self.parse_statements()
                    if self.match("SEPARATOR", "}"):
                        print("✅ Function Block Closed\n")
                    else:
                        self.warn("❌ Error: Missing '}'", self.current_token[2] if self.current_token else None)
                    return
                else:
                    self.warn("❌ Error: Missing '{'", self.current_token[2] if self.current_token else None)
                    return
        self.warn("❌ Error: Invalid function definition", self.current_token[2] if self.current_token else None)

    def parse_statements(self):
        while self.current_token and self.current_token[1] != "}":
            self.parse_statement()

    def parse_statement(self):
        if not self.current_token:
            return

        token_type, token_value, token_line = self.current_token

        if token_type == "KEYWORD" and token_value == "return":
            self.parse_return()
            return
        if token_type == "KEYWORD":
            self.parse_declaration()
            return
        if token_type == "IDENTIFIER":
            self.parse_expression_statement()
            return
        if token_type == "SEPARATOR" and token_value == "{":
            self.advance()
            self.parse_statements()
            if not self.match("SEPARATOR", "}"):
                self.warn("❌ Error: Missing '}' for block", token_line)
            else:
                print("✅ Block Closed\n")
            return
        if token_type == "SEPARATOR" and token_value == ";":
            self.advance()
            return

        self.warn(f"⚠️ Skipping unknown/unhandled token: {token_value}", token_line)
        self.advance()

    def parse_declaration(self):
        token_line = self.current_token[2]
        self.advance()  # Skip type
        if self.match("IDENTIFIER"):
            # Check for array declaration
            if self.match("SEPARATOR", "["):
                if self.match("NUMBER") and self.match("SEPARATOR", "]"):
                    if self.match("SEPARATOR", ";"):
                        print("✅ Array Declaration\n")
                        return
                    else:
                        self.warn("❌ Error: Missing ';' in array declaration", token_line)
                        return
            if self.match("OPERATOR", "="):
                self.parse_expression()
            if self.match("SEPARATOR", ";"):
                print("✅ Variable Declaration\n")
            else:
                self.warn("❌ Error: Missing ';' in declaration", token_line)

    def parse_expression_statement(self):
        token_type, token_value, token_line = self.current_token
        if token_type == "IDENTIFIER" and token_value in [
            "gets", "strcpy", "strcat", "scanf", "sprintf", "system",
            "eval", "popen", "vsprintf", "printf", "malloc"
        ]:
            self.check_insecure_function(token_value, token_line)

        self.advance()

        if self.match("SEPARATOR", "("):
            while self.current_token and not self.match("SEPARATOR", ")"):
                self.advance()
            if self.match("SEPARATOR", ";"):
                print("✅ Function Call\n")
            else:
                self.warn("❌ Error: Missing ';' after function call", token_line)
            return

        if self.match("OPERATOR", "="):
            self.parse_expression()
            if self.match("SEPARATOR", ";"):
                print("✅ Assignment\n")
            else:
                self.warn("❌ Error: Missing ';' in assignment", token_line)
            return

        if self.match("SEPARATOR", ";"):
            print("✅ Expression Statement\n")
            return

        self.warn("⚠️ Unable to parse expression or call", token_line)

    def parse_return(self):
        token_line = self.current_token[2]
        self.advance()
        self.parse_expression()
        if self.match("SEPARATOR", ";"):
            print("✅ Return Statement\n")
        else:
            self.warn("❌ Error: Missing ';' in return", token_line)

    def parse_expression(self):
        if self.current_token and self.current_token[0] in ["NUMBER", "IDENTIFIER", "STRING"]:
            self.advance()
        else:
            self.warn(f"❌ Error: Invalid expression at {self.current_token}", self.current_token[2] if self.current_token else None)
            self.advance()

    def check_insecure_function(self, func_name, line):
        self.warn(f"❌ Use of insecure function {func_name}() detected.", line)
        tips = {
            "gets": ("fgets()", "CWE-120"),
            "strcpy": ("strncpy()", "CWE-121"),
            "strcat": ("strncat()", "CWE-120"),
            "scanf": ("%10s", "CWE-134"),
            "sprintf": ("snprintf()", "CWE-120"),
            "vsprintf": ("vsnprintf()", "CWE-120"),
            "system": ("sanitize inputs", "CWE-78"),
            "popen": ("avoid or sanitize", "CWE-78"),
            "eval": ("use ast.literal_eval()", "CWE-95"),
            "printf": ("format string literal", "CWE-134"),
        }
        if func_name in tips:
            tip, cwe = tips[func_name]
            self.warn(f"   💡 Suggested fix: {tip}. [{cwe}]", line)
