import python_minifier.ast_compat as ast

from python_minifier.rename.add_parent import add_parent
from python_minifier.rename.create_namespaces import create_child_namespaces
from python_minifier.rename.namespace import FunctionNamespace, ModuleNamespace
from python_minifier.util import is_ast_node


class NodeVisitor(object):
    """
    A visitor for AST nodes.

    visits all nodes in the tree and calls a visitor method for each node.
    """

    def visit(self, node):
        """Visit a node."""
        method = 'visit_' + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node):
        """Called if no explicit visitor function exists for a node."""
        for field, value in ast.iter_fields(node):
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, ast.AST):
                        self.visit(item)
            elif isinstance(value, ast.AST):
                self.visit(value)

    def visit_Constant(self, node):
        """
        Dispatch to a visit method based on the type of the Constant

        Before Constant was introduced, these values were
        represented by NameConstant, Num, Str, Bytes, Ellipsis nodes.

        :param node: The node to visit
        :type node: :class:`ast.Constant`
        """

        if node.value in [None, True, False]:
            method = 'visit_NameConstant'
        elif isinstance(node.value, (int, float, complex)):
            method = 'visit_Num'
        elif isinstance(node.value, str):
            method = 'visit_Str'
        elif isinstance(node.value, bytes):
            method = 'visit_Bytes'
        elif node.value == Ellipsis:
            method = 'visit_Ellipsis'
        else:
            raise RuntimeError('Unknown Constant value %r' % type(node.value))

        visitor = getattr(self, method, self.generic_visit)
        return visitor(node)


class SuiteTransformer(NodeVisitor):
    """
    Transform suites of instructions
    """

    def __call__(self, node):
        return self.visit(node)

    def visit_ClassDef(self, node):
        node.bases = [self.visit(b) for b in node.bases]

        if hasattr(node, 'type_params') and node.type_params is not None:
            node.type_params = [self.visit(t) for t in node.type_params]

        node.body = self.suite(node.body, parent=node)
        node.decorator_list = [self.visit(d) for d in node.decorator_list]

        if hasattr(node, 'starargs') and node.starargs is not None:
            node.starargs = self.visit(node.starargs)

        if hasattr(node, 'kwargs') and node.kwargs is not None:
            node.kwargs = self.visit(node.kwargs)

        if hasattr(node, 'keywords'):
            node.keywords = [self.visit(kw) for kw in node.keywords]

        return node

    def visit_FunctionDef(self, node):
        node.args = self.visit(node.args)
        node.body = self.suite(node.body, parent=node)
        node.decorator_list = [self.visit(d) for d in node.decorator_list]

        if hasattr(node, 'returns') and node.returns is not None:
            node.returns = self.visit(node.returns)

        return node

    def visit_AsyncFunctionDef(self, node):
        return self.visit_FunctionDef(node)

    def visit_For(self, node):
        node.target = self.visit(node.target)
        node.iter = self.visit(node.iter)

        node.body = self.suite(node.body, parent=node)

        if node.orelse:
            node.orelse = self.suite(node.orelse, parent=node)

        return node

    def visit_AsyncFor(self, node):
        return self.visit_For(node)

    def visit_If(self, node):
        node.test = self.visit(node.test)

        node.body = self.suite(node.body, parent=node)

        if node.orelse:
            node.orelse = self.suite(node.orelse, parent=node)

        return node

    def visit_Try(self, node):
        node.body = self.suite(node.body, parent=node)

        node.handlers = [self.visit(h) for h in node.handlers]

        if node.orelse:
            node.orelse = self.suite(node.orelse, parent=node)

        if node.finalbody:
            node.finalbody = self.suite(node.finalbody, parent=node)

        return node

    def visit_While(self, node):
        node.test = self.visit(node.test)

        node.body = self.suite(node.body, parent=node)

        if node.orelse:
            node.orelse = self.suite(node.orelse, parent=node)

        return node

    def visit_With(self, node):

        if hasattr(node, 'items'):
            node.items = [self.visit(i) for i in node.items]
        else:
            if node.context_expr:
                node.context_expr = self.visit(node.context_expr)
            if node.optional_vars:
                node.optional_vars = self.visit(node.optional_vars)

        node.body = self.suite(node.body, parent=node)
        return node

    def visit_AsyncWith(self, node):
        return self.visit_With(node)

    def visit_Module(self, node):
        node.body = self.suite(node.body, parent=node)
        return node

    def suite(self, node_list, parent):
        return [self.visit(node) for node in node_list]

    def generic_visit(self, node):
        for field, old_value in ast.iter_fields(node):
            if isinstance(old_value, list):
                new_values = []
                for value in old_value:
                    if isinstance(value, ast.AST):
                        value = self.visit(value)
                        if value is None:
                            continue
                        elif not isinstance(value, ast.AST):
                            new_values.extend(value)
                            continue
                    new_values.append(value)
                old_value[:] = new_values
            elif isinstance(old_value, ast.AST):
                new_node = self.visit(old_value)
                if new_node is None:
                    delattr(node, field)
                else:
                    setattr(node, field, new_node)
        return node

    def add_child(self, child, parent):
        """
        Add the child tree to the parent tree

        This sets the parent attributes of each node of the child tree.
        The parent of the root node of the child tree is set to the parent node.

        The namespace tree is also updated to reflect the new child tree.

        :param child: The child tree to add
        :type child: :class:`ast.AST`
        :param parent: The parent tree to add to
        :type parent: :class:`ast.AST`
        """

        add_parent(child, parent=parent)
        create_child_namespaces(child, parent_namespace=parent.namespace)
        return child
