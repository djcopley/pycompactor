"""
Test for rename of builtins

This assumes the standard NameAssigner and name_generator
"""

import ast

from python_minifier import unparse
from python_minifier.ast_compare import compare_ast, CompareError
from python_minifier.rename.add_parent import add_parent
from python_minifier.rename.bind_names import bind_names
from python_minifier.rename.create_namespaces import create_all_namespaces
from python_minifier.rename.renamer import rename
from python_minifier.rename.resolve_names import resolve_names
from python_minifier.rename.util import apply_local_rename_options, apply_global_rename_options


def do_rename(source):
    # This will raise if the source file can't be parsed
    module = ast.parse(source, 'test_rename_bultins')
    add_parent(module)
    create_all_namespaces(module)
    bind_names(module)
    resolve_names(module)
    apply_local_rename_options(module.namespace, True, [])
    apply_global_rename_options(module.namespace, True, [])
    rename(module)
    return module


def assert_code(expected_ast, actual_ast):
    try:
        compare_ast(expected_ast, actual_ast)
    except CompareError as e:
        print(e)
        print(unparse(actual_ast))
        raise


def test_rename_builtins():
    source = '''
sorted()
sorted()
sorted()
sorted()
sorted()
'''
    expected = '''
A=sorted
A()
A()
A()
A()
A()
'''

    expected_ast = ast.parse(expected)
    actual_ast = do_rename(source)
    assert_code(expected_ast, actual_ast)


def test_no_rename_assigned_builtin():
    source = '''
if random.choice([True, False]):
    sorted=str
sorted()
sorted()
sorted()
sorted()
sorted()
'''
    expected = source

    expected_ast = ast.parse(expected)
    actual_ast = do_rename(source)
    assert_code(expected_ast, actual_ast)

def test_rename_local_builtin():
    source = '''
def t():
    sorted()
    sorted()
    sorted()
    sorted()
    sorted()
'''
    expected = '''
A=sorted
def B():
    A()
    A()
    A()
    A()
    A()
'''

    expected_ast = ast.parse(expected)
    actual_ast = do_rename(source)
    assert_code(expected_ast, actual_ast)

def test_no_rename_local_assigned_builtin():
    source = '''
def a():
    if random.choice([True, False]):
        sorted=str
    sorted()
    sorted()
    sorted()
    sorted()
    sorted()
'''

    expected = '''
def A():
    if random.choice([True, False]):
        sorted=str
    sorted()
    sorted()
    sorted()
    sorted()
    sorted()
'''

    expected_ast = ast.parse(expected)
    actual_ast = do_rename(source)
    assert_code(expected_ast, actual_ast)
