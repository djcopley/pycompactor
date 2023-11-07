import python_minifier.ast_compat as ast
import sys

from python_minifier.rename.namespace import ModuleNamespace, ClassNamespace, AnnotationNamespace
from python_minifier.util import is_ast_node


def create_is_namespace():

    namespace_nodes = (ast.FunctionDef, ast.Lambda, ast.ClassDef, ast.Module, ast.GeneratorExp)

    if sys.version_info >= (2, 7):
        namespace_nodes += (ast.SetComp, ast.DictComp)

    if sys.version_info >= (3, 0):
        namespace_nodes += (ast.ListComp,)

    if sys.version_info >= (3, 5):
        namespace_nodes += (ast.AsyncFunctionDef,)

    return lambda node: isinstance(node, namespace_nodes)


is_namespace = create_is_namespace()


def get_global_namespace(namespace):
    """
    Return the global namespace for given namespace

    :rtype: :class:`Namespace`

    """

    if isinstance(namespace, ModuleNamespace):
        return namespace

    return get_global_namespace(namespace.parent_namespace)


def get_nonlocal_namespace(namespace):
    """
    Return the nonlocal namespace for a node

    The nonlocal namespace is the closest parent function namespace
    """

    if isinstance(namespace.parent_namespace, ClassNamespace):
        return get_nonlocal_namespace(namespace.parent_namespace)

    return namespace.parent_namespace


def arg_rename_in_place(node):
    """
    Can this argument node by safely renamed

    'self', 'cls', 'args', and 'kwargs' are not commonly referenced by the caller, so
    can be safely renamed. Comprehension arguments are not accessible from outside, so
    can be renamed.

    If the argument is positional-only, it can be safely renamed

    Other arguments may be referenced by the caller as keyword arguments, so should not be
    renamed in place. The name assigner may still decide to bind the argument to a new name
    inside the function namespace.

    :param node: The argument node
    :rtype node: :class:`ast.arg`
    :rtype: bool

    """

    func_node = node.namespace.node

    if isinstance(func_node, ast.comprehension):
        return True

    if isinstance(func_node.namespace, ClassNamespace) and not isinstance(func_node, ast.Lambda):
        # This is a function in class scope

        if len(func_node.args.args) > 0 and node is func_node.args.args[0]:
            if len(func_node.decorator_list) == 0:
                # rename 'self'
                return True
            elif (
                len(func_node.decorator_list) == 1
                and isinstance(func_node.decorator_list[0], ast.Name)
                and func_node.decorator_list[0].id == 'classmethod'
            ):
                # rename 'cls'
                return True

    if func_node.args.vararg is node or func_node.args.kwarg is node:
        # starargs
        return True

    if hasattr(func_node.args, 'posonlyargs') and node in func_node.args.posonlyargs:
        return True

    return False


def insert(suite, new_node):
    """
    Insert a node into a suite

    Inserts new_node as early as possible in the suite, but after docstrings and `import __future__` statements.

    :param suite: The existing suite to insert the node into
    :param new_node: The node to insert
    :return: :class:`collections.Iterable[Node]`

    """

    inserted = False
    for node in suite:

        if not inserted:
            if (isinstance(node, ast.ImportFrom) and node.module == '__future__') or (
                isinstance(node, ast.Expr) and is_ast_node(node.value, ast.Str)
            ):
                pass
            else:
                yield new_node
                inserted = True

        yield node

    if not inserted:
        yield new_node

def find__all__(module):

    names = []

    def is_assign_all_node(node):
        if isinstance(node, ast.Assign):
            for name in node.targets:
                if isinstance(name, ast.Name) and name.id == '__all__':
                    return True

        elif is_ast_node(node, (ast.AugAssign, 'AnnAssign')):
            if isinstance(node.target, ast.Name) and node.target.id == '__all__':
                return True

        return False

    for node in ast.iter_child_nodes(module):
        if not is_assign_all_node(node):
            continue

        if not isinstance(node.value, ast.List):
            continue

        for el in node.value.elts:
            if is_ast_node(el, ast.Str):
                names.append(el.s)

    return names

def apply_global_rename_options(module_namespace, rename_globals, preserve_globals):
    """
    Apply renaming options for the global namespace of a module

    :param module_namespace: The module namespace to apply options to
    :type module_namespace: :class:`ModuleNamespace`
    :param rename_globals: Should global names be renamed
    :type rename_globals: bool
    :param preserve_globals: A list of global names to preserve
    :type preserve_globals: list[str]
    """

    if preserve_globals is None:
        preserve_globals = []

    preserve_globals.extend(find__all__(module_namespace.node))

    for binding in module_namespace.bindings:
        if rename_globals is False or binding.name in preserve_globals:
            binding.disallow_rename()

def apply_local_rename_options(namespace, rename_locals, preserve_locals):
    """
    Apply renaming options to non-global namespaces in a module

    :param namespace: The namespace to apply options to
    :type namespace: :class:`Namespace`
    :param rename_locals: Should local names be renamed
    :type rename_locals: bool
    :param preserve_locals: A list of local names to preserve
    :type preserve_locals: list[str]
    """

    if preserve_locals is None:
        preserve_locals = []

    if not isinstance(namespace, ModuleNamespace):
        for binding in namespace.bindings:
            if rename_locals is False or binding.name in preserve_locals:
                binding.disallow_rename()

    for child_namespace in namespace.children:
        apply_local_rename_options(child_namespace, rename_locals, preserve_locals)


try:
    import builtins
except ImportError:
    # noinspection PyCompatibility
    import __builtin__ as builtins  # type: ignore
