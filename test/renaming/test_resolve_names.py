import ast
import sys

import pytest

from python_minifier.rename.add_parent import add_parent
from python_minifier.rename.bind_names import bind_names
from python_minifier.rename.binding import NameBinding, BuiltinBinding
from python_minifier.rename.create_namespaces import create_all_namespaces
from python_minifier.rename.namespace import ModuleNamespace, ClassNamespace, FunctionNamespace, AnnotationNamespace
from python_minifier.rename.resolve_names import resolve_names


def assert_namespace_tree(module_namespace, expected_tree):
    assert print_namespace(module_namespace) == print_namespace(expected_tree)

def print_namespace(namespace, indent=''):
    s = ''

    if not indent:
        s += '\n'

    s += indent + '+ ' + repr(namespace) + '\n'

    for name in sorted(namespace.global_names):
        s += indent + '  - global ' + name + '\n'

    for name in sorted(namespace.nonlocal_names):
        s += indent + '  - nonlocal ' + name + '\n'

    for binding in namespace.bindings:
        s += indent + '  - ' + repr(binding) + ' (%r references)\n' % len(binding.references)

    for child in namespace.children:
        s += print_namespace(child, indent=indent + '  ')

    return s

def expected(namespace_type, node_type, name='', global_names=None, nonlocal_names=None, bindings=None, children=None):
    """A helper to define expected namespaces in a literate way"""
    if namespace_type is ModuleNamespace:
        ns = ModuleNamespace(node_type())
    else:
        ns = namespace_type(node_type(), name)

    if bindings is not None:
        for b in bindings:
            ns.bindings.append(b)

    if global_names is not None:
        ns.global_names = global_names

    if nonlocal_names is not None:
        ns.nonlocal_names = nonlocal_names

    if children:
        for child in children:
            ns.add_child(child)

    return ns

def binding(name, references):
    b = NameBinding(name)
    [b.add_reference(ast.Name(name)) for _ in range(references)]
    return b

def builtin(name, references):
    b = BuiltinBinding(name, ast.Module())
    [b.add_reference(ast.Name(name)) for _ in range(references)]
    return b

def test_resolve():

    source = '''
A = 'hello'
A = 'helloagain'
print(A + A)
'''

    tree = ast.parse(source)

    add_parent(tree)
    module_namespace = create_all_namespaces(tree)
    bind_names(tree)
    resolve_names(tree)

    print(print_namespace(module_namespace))

    A = binding('A', references=4)
    print_ = builtin('print', references=1)
    expected_namespaces = expected(ModuleNamespace, ast.Module, bindings=[A, print_])

    print(print_namespace(expected_namespaces))

    assert print_namespace(module_namespace) == print_namespace(expected_namespaces)

def test_nonlocal():

    source = '''
A = 'hello'
C = 'world'
def B():
    C = 'world'
    A = 'goodbye'
    nonlocal A
'''

    tree = ast.parse(source)

    add_parent(tree)
    module_namespace = create_all_namespaces(tree)
    bind_names(tree)
    resolve_names(tree)

    print(print_namespace(module_namespace))

    A = binding('A', references=3)
    global_c = binding('C', references=1)
    B = binding('B', references=1)
    inner_c = binding('C', references=1)

    expected_namespaces = expected(ModuleNamespace, ast.Module, bindings=[A, global_c, B], children=[
        expected(FunctionNamespace, ast.FunctionDef, name='B', nonlocal_names=['A'], bindings=[inner_c])
    ])

    print(print_namespace(expected_namespaces))

    assert print_namespace(module_namespace) == print_namespace(expected_namespaces)

def test_nested_nonlocal():

    source = '''
A = 'hello'
C = 'world'
def B():
    C = 'world'
    A = 'goodbye'
    nonlocal A
    
    def nested():
        nonlocal A
        A = 'nested'
'''

    tree = ast.parse(source)

    add_parent(tree)
    module_namespace = create_all_namespaces(tree)
    bind_names(tree)
    resolve_names(tree)

    print(print_namespace(module_namespace))

    A = binding('A', references=5)
    global_c = binding('C', references=1)
    B = binding('B', references=1)
    inner_c = binding('C', references=1)
    nested = binding('nested', references=1)

    expected_namespaces = expected(ModuleNamespace, ast.Module, bindings=[A, global_c, B], children=[
        expected(FunctionNamespace, ast.FunctionDef, name='B', nonlocal_names=['A'], bindings=[inner_c, nested], children=[
            expected(FunctionNamespace, ast.FunctionDef, name='nested', nonlocal_names=['A'])
        ])
    ])

    print(print_namespace(expected_namespaces))

    assert print_namespace(module_namespace) == print_namespace(expected_namespaces)


def test_nonlocal_skips_class():

    source = '''
def A():
    att = 3
    class B:
        att = 4
        def C(self):
            nonlocal att
            att += 1
'''

    tree = ast.parse(source)

    add_parent(tree)
    module_namespace = create_all_namespaces(tree)
    bind_names(tree)
    resolve_names(tree)

    print(print_namespace(module_namespace))

    A = binding('A', references=1)
    A_att = binding('att', references=3)
    B = binding('B', references=1)
    C = binding('C', references=1)
    B_att = binding('att', references=1)
    C_self = binding('self', references=1)

    expected_namespaces = expected(ModuleNamespace, ast.Module, bindings=[A], children=[
        expected(FunctionNamespace, ast.FunctionDef, name='A', bindings=[A_att, B], children=[
            expected(ClassNamespace, ast.ClassDef, name='B', bindings=[B_att, C], children=[
                expected(FunctionNamespace, ast.FunctionDef, name='C', nonlocal_names=['att'], bindings=[C_self])
            ])
        ])
    ])

    print(print_namespace(expected_namespaces))

    assert print_namespace(module_namespace) == print_namespace(expected_namespaces)

def test_class_scope():

    source = '''
A = 1
class Class:
    A = 2
'''

    tree = ast.parse(source)

    add_parent(tree)
    module_namespace = create_all_namespaces(tree)
    bind_names(tree)
    resolve_names(tree)

    print(print_namespace(module_namespace))

    A = binding('A', references=1)
    Class = binding('Class', references=1)
    Class_A = binding('A', references=1)

    expected_namespaces = expected(ModuleNamespace, ast.Module, bindings=[A, Class], children=[
        expected(ClassNamespace, ast.ClassDef, name='Class', bindings=[Class_A])
    ])

    print(print_namespace(expected_namespaces))

    assert print_namespace(module_namespace) == print_namespace(expected_namespaces)

def test_class_scope_rebinding_from_parent():
    """
    Test that names in class scope that are used for both looking up existing values and binding new ones are considered
    to be references to a Binding in a parent function scope.
    """

    source = '''
A = 1
class Class:
    A = A + 1
'''

    tree = ast.parse(source)

    add_parent(tree)
    module_namespace = create_all_namespaces(tree)
    bind_names(tree)
    resolve_names(tree)

    print(print_namespace(module_namespace))

    A = binding('A', references=3)
    Class = binding('Class', references=1)

    expected_namespaces = expected(ModuleNamespace, ast.Module, bindings=[A, Class], children=[
        expected(ClassNamespace, ast.ClassDef, name='Class', nonlocal_names=['A'])
    ])

    print(print_namespace(expected_namespaces))

    assert print_namespace(module_namespace) == print_namespace(expected_namespaces)

def test_class_scope_rebinding_from_parent_augassign():

    source = '''
A = 1
class Class:
    A += 2
'''

    tree = ast.parse(source)

    add_parent(tree)
    module_namespace = create_all_namespaces(tree)
    bind_names(tree)
    resolve_names(tree)

    print(print_namespace(module_namespace))

    A = binding('A', references=2)
    Class = binding('Class', references=1)

    expected_namespaces = expected(ModuleNamespace, ast.Module, bindings=[A, Class], children=[
        expected(ClassNamespace, ast.ClassDef, name='Class', nonlocal_names=['A'])
    ])

    print(print_namespace(expected_namespaces))

    assert print_namespace(module_namespace) == print_namespace(expected_namespaces)

def test_shadowed_across_class_namespace():

    source = '''
def A():
    att = 3
    att = 2
    class B:
        att = 4
        def C(self):
            att = 1
'''

    tree = ast.parse(source)

    add_parent(tree)
    module_namespace = create_all_namespaces(tree)
    bind_names(tree)
    resolve_names(tree)

    print(print_namespace(module_namespace))

    A = binding('A', references=1)
    A_att = binding('att', references=2)
    B = binding('B', references=1)
    C = binding('C', references=1)
    B_att = binding('att', references=1)
    C_self = binding('self', references=1)
    C_att = binding('att', references=1)

    expected_namespaces = expected(ModuleNamespace, ast.Module, bindings=[A], children=[
        expected(FunctionNamespace, ast.FunctionDef, name='A', bindings=[A_att, B], children=[
            expected(ClassNamespace, ast.ClassDef, name='B', bindings=[B_att, C], children=[
                expected(FunctionNamespace, ast.FunctionDef, name='C', bindings=[C_self, C_att])
            ])
        ])
    ])

    print(print_namespace(expected_namespaces))

    assert print_namespace(module_namespace) == print_namespace(expected_namespaces)

def test_shadowed():

    source = '''
def A():
    att = 3
    att = att + 2
    def B():
        att = 4
        att += 3
'''

    tree = ast.parse(source)

    add_parent(tree)
    module_namespace = create_all_namespaces(tree)
    bind_names(tree)
    resolve_names(tree)

    print(print_namespace(module_namespace))

    A = binding('A', references=1)
    A_att = binding('att', references=3)
    B = binding('B', references=1)
    B_att = binding('att', references=2)

    expected_namespaces = expected(ModuleNamespace, ast.Module, bindings=[A], children=[
        expected(FunctionNamespace, ast.FunctionDef, name='A', bindings=[A_att, B], children=[
            expected(FunctionNamespace, ast.FunctionDef, name='B', bindings=[B_att])
        ])
    ])

    print(print_namespace(expected_namespaces))

    assert print_namespace(module_namespace) == print_namespace(expected_namespaces)

def test_global_creates_binding():

    source = '''
def A():
    global B
    B = 1
'''

    tree = ast.parse(source)

    add_parent(tree)
    module_namespace = create_all_namespaces(tree)
    bind_names(tree)
    resolve_names(tree)

    print(print_namespace(module_namespace))

    A = binding('A', references=1)
    B = binding('B', references=2)

    expected_namespaces = expected(ModuleNamespace, ast.Module, bindings=[A, B], children=[
        expected(FunctionNamespace, ast.FunctionDef, name='A', global_names=['B'])
    ])

    print(print_namespace(expected_namespaces))

    assert print_namespace(module_namespace) == print_namespace(expected_namespaces)

def test_global_existing_binding():

    source = '''
B = 2
def A():
    global B
    B = 1
'''

    tree = ast.parse(source)

    add_parent(tree)
    module_namespace = create_all_namespaces(tree)
    bind_names(tree)
    resolve_names(tree)

    print(print_namespace(module_namespace))

    A = binding('A', references=1)
    B = binding('B', references=3)

    expected_namespaces = expected(ModuleNamespace, ast.Module, bindings=[B, A], children=[
        expected(FunctionNamespace, ast.FunctionDef, name='A', global_names=['B'])
    ])

    print(print_namespace(expected_namespaces))

    assert print_namespace(module_namespace) == print_namespace(expected_namespaces)

def test_global_skips_function():

    source = '''
B = 2
def A():
    B = 4
    def C():
        global B
        B = 1
'''

    tree = ast.parse(source)

    add_parent(tree)
    module_namespace = create_all_namespaces(tree)
    bind_names(tree)
    resolve_names(tree)

    print(print_namespace(module_namespace))

    A = binding('A', references=1)
    B = binding('B', references=3)
    A_B = binding('B', references=1)
    C = binding('C', references=1)

    expected_namespaces = expected(ModuleNamespace, ast.Module, bindings=[B, A], children=[
        expected(FunctionNamespace, ast.FunctionDef, name='A', bindings=[A_B, C], children=[
            expected(FunctionNamespace, ast.FunctionDef, name='C', global_names=['B'])
        ])
    ])

    print(print_namespace(expected_namespaces))

    assert print_namespace(module_namespace) == print_namespace(expected_namespaces)

def test_function_type_params():
    if sys.version_info < (3, 12):
        pytest.skip('Type Parameters not supported in Python < 3.12')

    source = '''
def A[T]():
    return T
'''

    tree = ast.parse(source)

    add_parent(tree)
    module_namespace = create_all_namespaces(tree)
    bind_names(tree)
    resolve_names(tree)

    print(print_namespace(module_namespace))

    A = binding('A', references=1)
    T = binding('T', references=2)

    expected_namespaces = expected(ModuleNamespace, ast.Module, bindings=[A], children=[
        expected(AnnotationNamespace, ast.FunctionDef, name='A', bindings=[T], children=[
            expected(FunctionNamespace, ast.FunctionDef, name='A')
        ])
    ])

    print(print_namespace(expected_namespaces))

    assert print_namespace(module_namespace) == print_namespace(expected_namespaces)

def test_function_class_type_params():
    if sys.version_info < (3, 12):
        pytest.skip('Type Parameters not supported in Python < 3.12')

    source = '''
class Class[T]:
    T()
    def A[M](self=M):
        return M + T
'''

    tree = ast.parse(source)

    add_parent(tree)
    module_namespace = create_all_namespaces(tree)
    bind_names(tree)
    resolve_names(tree)

    print(print_namespace(module_namespace))

    global_M = binding('M', references=1)
    Class = binding('Class', references=1)
    T = binding('T', references=3)
    A = binding('A', references=1)
    M = binding('M', references=2)
    self = binding('self', references=1)

    expected_namespaces = expected(ModuleNamespace, ast.Module, bindings=[Class, global_M], children=[
        expected(AnnotationNamespace, ast.ClassDef, name='Class', bindings=[T], children=[
            expected(ClassNamespace, ast.ClassDef, name='Class', nonlocal_names=['T', 'M'], bindings=[A], children=[
                expected(AnnotationNamespace, ast.FunctionDef, name='A', bindings=[M], children=[
                    expected(FunctionNamespace, ast.FunctionDef, name='A', bindings=[self])
                ])
            ])
        ])
    ])

    print(print_namespace(expected_namespaces))

    assert print_namespace(module_namespace) == print_namespace(expected_namespaces)

def test_method_defaults():

    source = '''
A = 1
class Class:
    A = 100
    def B(self, C=A):
        return C+A
'''

    tree = ast.parse(source)

    add_parent(tree)
    module_namespace = create_all_namespaces(tree)
    bind_names(tree)
    resolve_names(tree)

    print(print_namespace(module_namespace))

    A = binding('A', references=4)
    Class = binding('Class', references=1)
    B = binding('B', references=1)
    C = binding('C', references=2)
    self = binding('self', references=1)

    expected_namespaces = expected(ModuleNamespace, ast.Module, bindings=[A, Class], children=[
        expected(ClassNamespace, ast.ClassDef, name='Class', nonlocal_names=['A'], bindings=[B], children=[
            expected(FunctionNamespace, ast.FunctionDef, name='B', bindings=[self, C])
        ])
    ])

    print(print_namespace(expected_namespaces))

    assert print_namespace(module_namespace) == print_namespace(expected_namespaces)
