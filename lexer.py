import re

# Define token patterns based on your code blocks
token_patterns = [
    ('KEYWORD', r'\b(if|else|for|while|return|import|from|class|def|try|except|with|as|break|continue|pass|in|is|not|and|or|None|True|False)\b'),
    ('IDENTIFIER', r'\b[a-zA-Z_][a-zA-Z0-9_]*\b'),
    ('NUMBER', r'\b\d+(\.\d+)?\b'),
    ('STRING', r'(\".*?\"|\'.*?\')'),
    ('OPERATOR', r'[\+\-\*/%=<>!&|~^]+'),
    ('SEPARATOR', r'[()\[\]{}:,\.]'),
    ('NEWLINE', r'\n'),
    ('WHITESPACE', r'\s+'),
    ('COMMENT', r'#.*'),
]

# Compile all patterns into a single regex
token_regex = '|'.join(f'(?P<{name}>{pattern})' for name, pattern in token_patterns)
compiled_token_regex = re.compile(token_regex)

def tokenize_code(code):
    tokens = []
    for match in compiled_token_regex.finditer(code):
        kind = match.lastgroup
        value = match.group()
        if kind not in ('WHITESPACE', 'COMMENT', 'NEWLINE'):
            tokens.append((kind, value))
    return tokens
