# security_rules.py

class SecurityIssue:
    def __init__(self, line, severity, message, tip=None, cwe=None):
        self.line = line
        self.severity = severity  # e.g. "Warning", "Error", "Info"
        self.message = message
        self.tip = tip
        self.cwe = cwe

    def format_message(self):
        emoji_map = {
            "Error": "❌",
            "Warning": "⚠️",
            "Info": "✅",
        }
        emoji = emoji_map.get(self.severity, "⚠️")
        lines = []
        lines.append(f"{emoji} {self.severity}: {self.message}")
        if self.tip:
            lines.append(f"   💡 {self.tip}")
        if self.cwe:
            lines[-1] += f" [{self.cwe}]"
        lines.append(f"   (at line {self.line})")
        return "\n".join(lines)

    def __repr__(self):
        return self.format_message()


class SecurityRule:
    def __init__(self):
        self.issues = []

    def check(self, ast_node):
        raise NotImplementedError

    def report(self):
        return self.issues


class DangerousFunctionRule(SecurityRule):
    # Map dangerous functions to detailed messages, tips, CWE references
    DANGEROUS_FUNCS_INFO = {
        'gets': (
            "Use of insecure function `gets()` detected.",
            "Use `fgets()` instead of `gets()` to avoid buffer overflows.",
            "CWE-120"
        ),
        'strcpy': (
            "Use of insecure function `strcpy()` detected.",
            "Use `strncpy()` instead with size limit.",
            "CWE-121"
        ),
        'strcat': (
            "Use of insecure function `strcat()` detected.",
            "Use `strncat()` instead with length checking.",
            "CWE-120"
        ),
        'sprintf': (
            "Use of insecure function `sprintf()` detected.",
            "Use `snprintf()` to avoid overflow.",
            "CWE-120"
        ),
        'scanf': (
            "Use of insecure function `scanf()` detected.",
            "Always use length specifiers like `%10s` in `scanf`.",
            "CWE-134"
        ),
    }

    def check(self, ast_node):
        if ast_node.type == 'FunctionCall':
            func_name = ast_node.value
            if func_name in self.DANGEROUS_FUNCS_INFO:
                msg, tip, cwe = self.DANGEROUS_FUNCS_INFO[func_name]
                self.issues.append(SecurityIssue(
                    ast_node.line,
                    "Warning",
                    msg,
                    tip,
                    cwe
                ))
        for child in ast_node.children:
            self.check(child)


class RiskySyscallRule(SecurityRule):
    RISKY_SYSCALLS_INFO = {
        'system': (
            "Use of insecure function `system()` detected.",
            "Avoid `system()` or validate/sanitize inputs.",
            "CWE-78"
        ),
        'exec': (
            "Use of insecure function `exec()` detected.",
            "Ensure input arguments are validated to prevent injection.",
            "CWE-78"
        ),
        'popen': (
            "Use of insecure function `popen()` detected.",
            "Validate commands to avoid injection vulnerabilities.",
            "CWE-78"
        ),
    }

    def check(self, ast_node):
        if ast_node.type == 'FunctionCall':
            func_name = ast_node.value
            if func_name in self.RISKY_SYSCALLS_INFO:
                msg, tip, cwe = self.RISKY_SYSCALLS_INFO[func_name]
                self.issues.append(SecurityIssue(
                    ast_node.line,
                    "Warning",
                    msg,
                    tip,
                    cwe
                ))
        for child in ast_node.children:
            self.check(child)


class MissingSemicolonRule(SecurityRule):
    # Just an example error rule for missing semicolon based on parsing info
    def __init__(self, missing_line):
        super().__init__()
        self.missing_line = missing_line

    def check(self, ast_node=None):
        # This rule is triggered externally when parser detects missing ';'
        self.issues.append(SecurityIssue(
            self.missing_line,
            "Error",
            "Missing ';' in declaration",
            None,
            None
        ))

    def report(self):
        return self.issues


class MallocCheckRule(SecurityRule):
    # Check for malloc usage, remind to check return for NULL (CWE-690)
    def check(self, ast_node):
        if ast_node.type == 'FunctionCall' and ast_node.value == 'malloc':
            self.issues.append(SecurityIssue(
                ast_node.line,
                "Warning",
                "`malloc()` used — ensure return is checked for NULL.",
                None,
                "CWE-690"
            ))
        for child in ast_node.children:
            self.check(child)


# ... You can add other rules following this pattern


class SecurityRuleEngine:
    def __init__(self, ast, extra_errors=None):
        self.ast = ast
        self.rules = [
            DangerousFunctionRule(),
            RiskySyscallRule(),
            MallocCheckRule(),
        ]
        # extra_errors is a list of SecurityIssue for errors detected at parsing stage (e.g., missing semicolon)
        self.extra_errors = extra_errors or []

    def run(self):
        issues = []
        for rule in self.rules:
            rule.issues = []
            rule.check(self.ast)
            issues.extend(rule.report())
        issues.extend(self.extra_errors)
        return issues
