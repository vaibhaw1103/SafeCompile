# parse_tree_node.py

class ParseTreeNode:
    """
    Represents a node in a simplified Abstract Syntax Tree (AST).
    Used for visualization.
    """
    def __init__(self, name: str, value: str = None, is_terminal: bool = False):
        self.name = name          # The type or role of the node (e.g., 'FunctionDecl', 'IntegerLiteral')
        self.value = value        # The actual value if it's a terminal node (e.g., '10', 'main')
        self.is_terminal = is_terminal # True if this node is a leaf in the simplified tree
        self.children = []        # List of child ParseTreeNode objects

    def add_child(self, child_node):
        """Adds a child node to this node."""
        if isinstance(child_node, ParseTreeNode):
            self.children.append(child_node)
        else:
            raise TypeError("Child must be an instance of ParseTreeNode")

    def __repr__(self):
        return f"ParseTreeNode(name='{self.name}', value='{self.value}', terminal={self.is_terminal}, children={len(self.children)})"

    def __str__(self):
        return self.name + (f" ({self.value})" if self.value else "")

