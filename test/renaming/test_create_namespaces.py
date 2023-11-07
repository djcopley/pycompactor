import ast
import sys

import pytest

from python_minifier.rename.add_parent import add_parent
from python_minifier.rename.create_namespaces import create_all_namespaces
from python_minifier.rename.namespace import ModuleNamespace, ClassNamespace, FunctionNamespace, AnnotationNamespace

# TODO: Test ast nodes have the correct namespace attribute

def assert_namespace_tree(module_namespace, expected_tree):
    assert type(module_namespace) is type(expected_tree)

    assert module_namespace.name == expected_tree.name
    assert len(module_namespace.children) == len(expected_tree.children)

    assert type(module_namespace.node) is type(expected_tree.node)

    assert module_namespace.global_names == expected_tree.global_names
    assert module_namespace.nonlocal_names == expected_tree.nonlocal_names

    for child, expected_child in zip(module_namespace.children, expected_tree.children):
        assert_namespace_tree(child, expected_child)

def print_namespace(namespace, indent=''):
    print(indent + repr(namespace))

    for child in namespace.children:
        print_namespace(child, indent=indent + '  ')

def expected(namespace_type, node_type, name='', globals=None, nonlocals=None, children=None):
    if namespace_type is ModuleNamespace:
        ns = ModuleNamespace(node_type())
    else:
        ns = namespace_type(node_type(), name)

    if children:
        for child in children:
            ns.add_child(child)

    if globals:
        ns.global_names = globals
    if nonlocals:
        ns.nonlocal_names = nonlocals
    return ns

def test_create_namespaces():

    source = '''
class A:
    def b(self):
        pass
'''

    tree = ast.parse(source)

    add_parent(tree)
    module_namespace = create_all_namespaces(tree)

    print_namespace(module_namespace)

    expected_namespaces = expected(ModuleNamespace, ast.Module, children=[
        expected(ClassNamespace, ast.ClassDef, 'A', children=[
            expected(FunctionNamespace, ast.FunctionDef, 'b')
        ])
    ])

    assert_namespace_tree(module_namespace, expected_namespaces)

def test_listcomp_python3():
    if sys.version_info < (3, 0):
        pytest.skip()

    source = '''
a = [x for x in range(y) for y in range(z) for z in range(10) if z > 5 if y > 5 if x > 5] 
'''

    tree = ast.parse(source)

    add_parent(tree)
    module_namespace = create_all_namespaces(tree)

    print_namespace(module_namespace)

    expected_namespaces = expected(ModuleNamespace, ast.Module, children=[
        expected(FunctionNamespace, ast.ListComp, 'ListComp')
    ])

    assert_namespace_tree(module_namespace, expected_namespaces)

def test_listcomp_python2():
    if sys.version_info >= (3, 0):
        pytest.skip()

    source = '''
a = [x for x in range(y) for y in range(z) for z in range(10)] 
'''

    tree = ast.parse(source)

    add_parent(tree)
    module_namespace = create_all_namespaces(tree)

    print_namespace(module_namespace)

    expected_namespaces = expected(ModuleNamespace, ast.Module)

    assert_namespace_tree(module_namespace, expected_namespaces)

def test_generatorexp():

    source = '''
a = (x for x in range(y) for y in range(z) for z in range(10)) 
'''

    tree = ast.parse(source)

    add_parent(tree)
    module_namespace = create_all_namespaces(tree)

    print_namespace(module_namespace)

    expected_namespaces = expected(ModuleNamespace, ast.Module, children=[
        expected(FunctionNamespace, ast.GeneratorExp, 'GeneratorExp')
    ])

    assert_namespace_tree(module_namespace, expected_namespaces)

def test_setcomp():

    source = '''
a = {x for x in range(y) for y in range(z) for z in range(10)}
'''

    tree = ast.parse(source)

    add_parent(tree)
    module_namespace = create_all_namespaces(tree)

    print_namespace(module_namespace)

    expected_namespaces = expected(ModuleNamespace, ast.Module, children=[
        expected(FunctionNamespace, ast.SetComp, 'SetComp')
    ])

    assert_namespace_tree(module_namespace, expected_namespaces)

def test_dictcomp():

    source = '''
a = {x: 'blah' for x in range(y) for y in range(z) for z in range(10)}
'''

    tree = ast.parse(source)

    add_parent(tree)
    module_namespace = create_all_namespaces(tree)

    print_namespace(module_namespace)

    expected_namespaces = expected(ModuleNamespace, ast.Module, children=[
        expected(FunctionNamespace, ast.DictComp, 'DictComp')
    ])

    assert_namespace_tree(module_namespace, expected_namespaces)

def test_typeparam():

    source = '''
@decorator
def f[T: int, U: (int, str), *V, **P](
    x: T = SOME_CONSTANT,
    y: U = 2+2,
    *args: *Ts,
    **kwargs: P.kwargs,
) -> T:
    class C[T](Base):
        def generic_method[Tx](self, x: T, y: Nested) -> T:
          pass
'''

    tree = ast.parse(source)

    add_parent(tree)
    module_namespace = create_all_namespaces(tree)

    print_namespace(module_namespace)

    expected_namespaces = expected(ModuleNamespace, ast.Module, children=[
        expected(AnnotationNamespace, ast.FunctionDef, 'f', children=[
            expected(FunctionNamespace, ast.FunctionDef, 'f', children=[
                expected(AnnotationNamespace, ast.ClassDef, 'C', children=[
                    expected(ClassNamespace, ast.ClassDef, 'C', nonlocals={'Nested', 'T'}, children=[
                        expected(AnnotationNamespace, ast.FunctionDef, 'generic_method', children=[
                            expected(FunctionNamespace, ast.FunctionDef, 'generic_method')
                        ])
                    ])
                ])
            ])
        ])
    ])

    assert_namespace_tree(module_namespace, expected_namespaces)

def test_lambda():

    source = '''
a = lambda x, y, *args, **kwargs: x + y
'''

    tree = ast.parse(source)

    add_parent(tree)
    module_namespace = create_all_namespaces(tree)

    print_namespace(module_namespace)

    expected_namespaces = expected(
        ModuleNamespace, ast.Module, children=[
            expected(FunctionNamespace, ast.Lambda, 'Lambda', [])
        ]
    )

    assert_namespace_tree(module_namespace, expected_namespaces)

def test_async_functiondef():

    source = '''
@decorator
async def f[T: int, U: (int, str), *V, **P](
    x: T = SOME_CONSTANT,
    y: U = 2+2,
    *args: *Ts,
    **kwargs: P.kwargs,
) -> T:
    pass
'''

    tree = ast.parse(source)

    add_parent(tree)
    module_namespace = create_all_namespaces(tree)

    print_namespace(module_namespace)

    expected_namespaces = expected(ModuleNamespace, ast.Module, children=[
        expected(AnnotationNamespace, ast.AsyncFunctionDef, 'f', children=[
            expected(FunctionNamespace, ast.AsyncFunctionDef, 'f')
        ])
    ])

    assert_namespace_tree(module_namespace, expected_namespaces)

def test_classdef():

    source = '''
@decorator
class C[T](Base, keyword='hello'):
    pass
'''

    tree = ast.parse(source)

    add_parent(tree)
    module_namespace = create_all_namespaces(tree)

    print_namespace(module_namespace)

    expected_namespaces = expected(ModuleNamespace, ast.Module, children=[
        expected(AnnotationNamespace, ast.ClassDef, 'C', children=[
            expected(ClassNamespace, ast.ClassDef, 'C')
        ])
    ])

    assert_namespace_tree(module_namespace, expected_namespaces)

def test_global_nonlocal():

    source = '''
def A():
  global A, B
  
  def n():
    nonlocal A
    global B
    
  def c():
    global c
'''

    tree = ast.parse(source)

    add_parent(tree)
    module_namespace = create_all_namespaces(tree)

    print_namespace(module_namespace)

    expected_namespaces = expected(ModuleNamespace, ast.Module, children=[
        expected(FunctionNamespace, ast.FunctionDef, 'A', globals={'A','B'}, children=[
            expected(FunctionNamespace, ast.FunctionDef, 'n', globals=set('B'), nonlocals=set('A')),
            expected(FunctionNamespace, ast.FunctionDef, 'c', globals=set('c'))
        ])
    ])

    assert_namespace_tree(module_namespace, expected_namespaces)
