import ast
import sys

import pytest

from python_minifier.rename.add_parent import add_parent
from python_minifier.rename.bind_names import bind_names
from python_minifier.rename.binding import NameBinding
from python_minifier.rename.create_namespaces import create_all_namespaces
from python_minifier.rename.namespace import ModuleNamespace, ClassNamespace, FunctionNamespace, AnnotationNamespace

def assert_namespace_tree(module_namespace, expected_tree):
    assert print_namespace(module_namespace) == print_namespace(expected_tree)

def print_namespace(namespace, indent=''):
    s = ''

    if not indent:
        s += '\n'

    s += indent + '+ ' + repr(namespace) + '\n'

    for name in namespace.global_names:
        s += indent + '  - global ' + name + '\n'

    for name in namespace.nonlocal_names:
        s += indent + '  - nonlocal ' + name + '\n'

    for binding in namespace.bindings:
        s += indent + '  - ' + repr(binding) + '\n'

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
            ns.bindings.append(NameBinding(b))

    if global_names is not None:
        ns.global_names = global_names

    if nonlocal_names is not None:
        ns.nonlocal_names = nonlocal_names

    if children:
        for child in children:
            ns.add_child(child)

    return ns

def test_functiondef_binding():

    source = '''
@decorator
def A[B](C):
    Hello=World
'''

    tree = ast.parse(source)

    add_parent(tree)
    module_namespace = create_all_namespaces(tree)
    bind_names(tree)

    print_namespace(module_namespace)

    expected_namespaces = expected(ModuleNamespace, ast.Module, bindings=['A'], children=[
        expected(AnnotationNamespace, ast.FunctionDef, 'A', bindings=['B'], children=[
            expected(FunctionNamespace, ast.FunctionDef, 'A', bindings=['C', 'Hello'])
        ])
    ])

    assert_namespace_tree(module_namespace, expected_namespaces)

def test_classdef_binding():

    source = '''
@decorator
class Class[B]:
    def A[B](self, C):
        Hello=World
'''

    tree = ast.parse(source)

    add_parent(tree)
    module_namespace = create_all_namespaces(tree)
    bind_names(tree)

    print(print_namespace(module_namespace))

    expected_namespaces = expected(ModuleNamespace, ast.Module, bindings=['Class'], children=[
        expected(AnnotationNamespace, ast.ClassDef, 'Class', bindings=['B'], children=[
            expected(ClassNamespace, ast.ClassDef, 'Class', bindings=['A'], children=[
                expected(AnnotationNamespace, ast.FunctionDef, 'A', bindings=['B'], children=[
                    expected(FunctionNamespace, ast.FunctionDef, 'A', bindings=['self', 'C', 'Hello'])
                ])
            ])
        ])
    ])

    print(print_namespace(expected_namespaces))

    assert print_namespace(module_namespace) == print_namespace(expected_namespaces)


def test_class_name_rebinding():

    source = '''
OhALongName = 'Hello'
OhALongName = 'Hello'
OhALongName = 'Hello'
OhALongName = 'Hello'

def func():
  class C:
    OhALongName = OhALongName + ' World'

funmc()
'''

    tree = ast.parse(source)

    add_parent(tree)
    module_namespace = create_all_namespaces(tree)
    bind_names(tree)

    print(print_namespace(module_namespace))

    expected_namespaces = expected(ModuleNamespace, ast.Module, bindings=['OhALongName', 'func'], children=[
        expected(FunctionNamespace, ast.FunctionDef, 'func', bindings=['C'], children=[
            expected(ClassNamespace, ast.ClassDef, 'C', nonlocal_names={'OhALongName'}, children=[
            ])
        ])
    ])

    print(print_namespace(expected_namespaces))

    assert print_namespace(module_namespace) == print_namespace(expected_namespaces)
