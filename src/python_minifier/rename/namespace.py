import ast

class Namespace(object):
    """
    A namespace is where names are defined.

    Each module has a global namespace, other namespaces may be nested inside.
    Namespaces are created for various constructs, such as functions, classes, and comprehensions.

    Each namespace has a list of bindings, which are the names defined in (local to) that namespace.

    Namespaces also have a set of global names and nonlocal names, which are the names that are
    NOT defined in that namespace, but are defined in a parent namespace.

    :param node: The node that introduced this namespace
    :type node: :class:`ast.AST`
    :param name: A descriptive name for this namespace
    :type name: str
    :param parent_namespace: The parent namespace
    :type parent_namespace: :class:`Namespace` or None
    """

    def __init__(self, node, name=''):
        assert isinstance(node, ast.AST)

        self.name = name
        self.node = node
        self.parent_namespace = None

        self.bindings = []
        self.global_names = set()
        self.nonlocal_names = set()
        self.children = []

        self._tainted = False

        # Names that are assigned in this namespace
        self.assigned_names = set()  # type: set[str]

    def __repr__(self):
        return '%s(node=%s, name=%r)' % (self.__class__.__name__, self.node.__class__.__name__, self.name)

    def __str__(self):
        return self.name

    def add_child(self, child):
        child.parent_namespace = self
        self.children.append(child)

    def taint(self):
        """
        There is untraceable usage of names within this namespace
        """
        self._tainted = True

    @property
    def is_tainted(self):
        return self._tainted

class ModuleNamespace(Namespace):
    def __init__(self, node):
        assert isinstance(node, ast.Module)
        super(ModuleNamespace, self).__init__(node, name='')

    def __repr__(self):
        return 'ModuleNamespace(node=Module)'

class AnnotationNamespace(Namespace):
    pass

class FunctionNamespace(Namespace):
    pass

class ClassNamespace(Namespace):
    pass
