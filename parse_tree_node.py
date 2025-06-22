# parse_tree_node.py

class ParseTreeNode:
    def __init__(self, name, children=None, value=None, is_terminal=False):
        """
        Initializes a Parse Tree Node.

        Args:
            name (str): The name of the grammar rule (non-terminal) or the token type (terminal).
            children (list, optional): A list of child ParseTreeNode objects. Defaults to None.
            value (any, optional): The actual value of the token for terminal nodes (e.g., 'main', '123'). Defaults to None.
            is_terminal (bool): True if this node represents a terminal symbol (a token).
        """
        self.name = name
        self.children = children if children is not None else []
        self.value = value
        self.is_terminal = is_terminal

    def add_child(self, child_node):
        """Adds a child node to this node's children list."""
        if not isinstance(child_node, ParseTreeNode):
            raise TypeError("Child must be a ParseTreeNode instance.")
        self.children.append(child_node)

    def __repr__(self):
        """String representation for debugging."""
        if self.is_terminal:
            # For terminals, show type and value
            return f"<{self.name}: '{self.value}'>" if self.value is not None else f"<{self.name}>"
        else:
            # For non-terminals, just show the rule name
            return f"<{self.name}>"

    def print_tree(self, indent=0):
        """Recursively prints the parse tree structure."""
        prefix = "  " * indent
        print(f"{prefix}{self.__repr__()}")
        for child in self.children:
            child.print_tree(indent + 1)