# ast_nodes.py

class ASTNode:
    def __init__(self, node_type, children=None, value=None, line=None):
        self.node_type = node_type
        self.children = children if children else []
        self.value = value
        self.line = line

    def __repr__(self, level=0):
        indent = "  " * level
        repr_str = f"{indent}{self.node_type}: {self.value if self.value else ''} (Line: {self.line})\n"
        for child in self.children:
            if isinstance(child, ASTNode):
                repr_str += child.__repr__(level + 1)
            else:
                repr_str += "  " * (level + 1) + str(child) + "\n"
        return repr_str

# Specific node types for clarity (optional, for future ML hooks or rule engine)
class ProgramNode(ASTNode):
    def __init__(self, children):
        super().__init__('Program', children)

class FunctionDeclNode(ASTNode):
    def __init__(self, name, params, body, line):
        super().__init__('FunctionDecl', [*params, body], value=name, line=line)

class VariableDeclNode(ASTNode):
    def __init__(self, name, var_type, value, line):
        super().__init__('VariableDecl', [value], value=(name, var_type), line=line)

class IfStmtNode(ASTNode):
    def __init__(self, condition, then_branch, else_branch=None, line=None):
        children = [condition, then_branch]
        if else_branch:
            children.append(else_branch)
        super().__init__('IfStatement', children, line=line)

class WhileStmtNode(ASTNode):
    def __init__(self, condition, body, line=None):
        super().__init__('WhileLoop', [condition, body], line=line)

class BinaryOpNode(ASTNode):
    def __init__(self, left, op, right, line=None):
        super().__init__('BinaryOp', [left, right], value=op, line=line)

class IdentifierNode(ASTNode):
    def __init__(self, name, line=None):
        super().__init__('Identifier', value=name, line=line)

class LiteralNode(ASTNode):
    def __init__(self, value, line=None):
        super().__init__('Literal', value=value, line=line)
