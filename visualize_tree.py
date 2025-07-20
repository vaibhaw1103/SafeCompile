
import time
# visualize_tree.py
from graphviz import Digraph
from parse_tree_node import ParseTreeNode # Adjust import based on your project structure

def create_parse_tree_graph(root_node, filename='parse_tree'):
    """
    Generates and saves a graphical representation of the parse tree.

    Args:
        root_node (ParseTreeNode): The root of the parse tree.
        filename (str): The base name for the output file (e.g., 'parse_tree.png').
    """
    if not root_node:
        print("DEBUG: No root node provided for parse tree visualization.")
        return

    dot = Digraph(comment='Parse Tree', graph_attr={'rankdir': 'TB', 'splines': 'true'}) # TB: Top to Bottom

    node_count = 0
    node_map = {} # To map ParseTreeNode objects to unique graphviz node names

    def add_nodes_edges_recursive(node):
        nonlocal node_count
        graphviz_node_name = f'node{node_count}'
        node_map[node] = graphviz_node_name

        label = node.name
        if node.is_terminal and node.value is not None:
            # For terminal nodes, show type and value
            label += f'\n("{node.value}")'

        dot.node(graphviz_node_name, label, shape='box' if node.is_terminal else 'ellipse', style='filled', fillcolor='lightblue' if node.is_terminal else 'lightgray')
        node_count += 1

        for child in node.children:
            child_graphviz_node_name = add_nodes_edges_recursive(child)
            dot.edge(graphviz_node_name, child_graphviz_node_name)

        return graphviz_node_name

    if root_node:
        add_nodes_edges_recursive(root_node)
        try:
            dot.render(filename, view=False, format='png', cleanup=False) # Renders to 'filename.png'
            time.sleep(0.5) # Wait for 0.5 seconds to ensure file system has caught up
            print(f"DEBUG: Graphviz render successful for {filename}.png (cleanup=False)") 
            # cleanup=True removes the intermediate .dot file
        except Exception as e:
            print(f"Error rendering graph: {e}")
            print("Make sure Graphviz is installed and added to your system's PATH.")
    else:
        print("No parse tree root provided for visualization.")
