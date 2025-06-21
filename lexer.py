import re

# Token patterns for C/C++
token_patterns = [
    ('COMMENT', r'//[^\n]*|/\*[\s\S]*?\*/'),
    ('PREPROCESSOR', r'#\s*(include|define|ifdef|ifndef|endif|pragma|undef|elif|else)\b.*'),
    ('KEYWORD', r'\b(alignas|alignof|and|and_eq|asm|auto|bitand|bitor|bool|break|case|catch|char|char16_t|char32_t|class|compl|const|constexpr|const_cast|continue|decltype|default|delete|do|double|dynamic_cast|else|enum|explicit|export|extern|false|float|for|friend|goto|if|inline|int|long|mutable|namespace|new|noexcept|nullptr|operator|or|or_eq|private|protected|public|register|reinterpret_cast|return|short|signed|sizeof|static|static_assert|static_cast|struct|switch|template|this|thread_local|throw|true|try|typedef|typeid|typename|union|unsigned|using|virtual|void|volatile|wchar_t|while|xor|xor_eq)\b'),
    ('IDENTIFIER', r'\b[a-zA-Z_][a-zA-Z0-9_]*\b'),
    ('NUMBER', r'0x[0-9a-fA-F]+|\b\d+(\.\d+)?([eE][-+]?\d+)?\b'),
    ('CHAR', r"'(\\.|[^\\'])'"),
    ('STRING', r'"(\\.|[^\\"])*"'),
    ('OPERATOR', r'>>=|<<=|\+\+|--|->\*|->|==|!=|>=|<=|&&|\|\||<<|>>|::|\+=|-=|\*=|/=|%=|&=|\|=|\^=|~|!|=|\+|-|\*|/|%|<|>|\^|&|\||\?|\:'),
    ('SEPARATOR', r'[{}\[\]();,\.]'),
    ('WHITESPACE', r'\s+'),
    ('UNKNOWN', r'.'),
]

token_regex = re.compile(
    '|'.join(f'(?P<{name}>{pattern})' for name, pattern in token_patterns),
    re.MULTILINE
)

def tokenize_code(code):
    tokens = []
    line_num = 1
    for match in token_regex.finditer(code):
        kind = match.lastgroup
        value = match.group()
        lines = value.count('\n')
        if kind not in ('WHITESPACE', 'COMMENT'):
            tokens.append((kind, value, line_num))
        line_num += lines
    return tokens
