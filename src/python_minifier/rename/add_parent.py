"""
Set the parent attribute of all nodes in the tree

This is for easier traversal of the tree
"""

import python_minifier.ast_compat as ast

def add_parent(node, parent=None):
    """
    Add a parent attribute to child nodes

    :param node: The tree to add parent attribute to
    :type node: :class:`ast.AST`
    :param parent: The parent node of this node
    :type parent: :class:`ast.AST`
    """

    if parent is not None:
        node.parent = parent

    for child in ast.iter_child_nodes(node):
        add_parent(child, parent=node)
