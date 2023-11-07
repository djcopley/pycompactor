import ast
import sys

import pytest

from python_minifier.ast_compare import compare_ast
from python_minifier.transforms.remove_exception_brackets import remove_no_arg_exception_call
from python_minifier.rename.add_parent import add_parent
from python_minifier.rename.create_namespaces import create_all_namespaces
from python_minifier.rename.bind_names import bind_names
from python_minifier.rename.resolve_names import resolve_names


def remove_brackets(source):
    module = ast.parse(source, 'remove_brackets')

    add_parent(module)
    create_all_namespaces(module)
    bind_names(module)
    resolve_names(module)

    return remove_no_arg_exception_call(module)


def test_exception_brackets():
    """This is a buitin so remove the brackets"""
    if sys.version_info < (3, 0):
        pytest.skip('transform does not work in this version of python')

    source = 'def a(): raise Exception()'
    expected = 'def a(): raise Exception'

    expected_ast = ast.parse(expected)
    actual_ast = remove_brackets(source)
    compare_ast(expected_ast, actual_ast)

def test_zero_division_error_brackets():
    """This is a buitin so remove the brackets"""
    if sys.version_info < (3, 0):
        pytest.skip('transform does not work in this version of python')

    source = 'def a(): raise ZeroDivisionError()'
    expected = 'def a(): raise ZeroDivisionError'

    expected_ast = ast.parse(expected)
    actual_ast = remove_brackets(source)
    compare_ast(expected_ast, actual_ast)

def test_builtin_with_arg():
    """This has an arg so dont' remove the brackets"""
    if sys.version_info < (3, 0):
        pytest.skip('transform does not work in this version of python')

    source = 'def a(): raise Exception(1)'
    expected = 'def a(): raise Exception(1)'

    expected_ast = ast.parse(expected)
    actual_ast = remove_brackets(source)
    compare_ast(expected_ast, actual_ast)

def test_one_division_error_brackets():
    """This is not a builtin so don't remove the brackets even though it's not defined in the module"""
    if sys.version_info < (3, 0):
        pytest.skip('transform does not work in this version of python')

    source = 'def a(): raise OneDivisionError()'
    expected = source

    expected_ast = ast.parse(expected)
    actual_ast = remove_brackets(source)
    compare_ast(expected_ast, actual_ast)

def test_redefined():
    """This is usually a builtin, but don't remove brackets if it's been redefined"""
    if sys.version_info < (3, 0):
        pytest.skip('transform does not work in this version of python')

    source = '''
def a():
    raise ZeroDivisionError()
def b():
    ZeroDivisionError = blag
    raise ZeroDivisionError()
'''
    expected = '''
def a():
    raise ZeroDivisionError
def b():
    ZeroDivisionError = blag
    raise ZeroDivisionError()
'''
    expected_ast = ast.parse(expected)
    actual_ast = remove_brackets(source)
    compare_ast(expected_ast, actual_ast)

def test_raise_from():
    """This is a builtin so remove the brackets"""
    if sys.version_info < (3, 0):
        pytest.skip('raise from not supported in this version of python')

    source = 'def a(): raise Exception() from Exception()'
    expected = 'def a(): raise Exception from Exception'

    expected_ast = ast.parse(expected)
    actual_ast = remove_brackets(source)
    compare_ast(expected_ast, actual_ast)

def test_raise_from_only():
    """This is a builtin so remove the brackets"""
    if sys.version_info < (3, 0):
        pytest.skip('raise from not supported in this version of python')

    source = 'def a(): raise Hello() from Exception()'
    expected = 'def a(): raise Hello() from Exception'

    expected_ast = ast.parse(expected)
    actual_ast = remove_brackets(source)
    compare_ast(expected_ast, actual_ast)

def test_raise_from_arg():
    """This is a builtin so remove the brackets"""
    if sys.version_info < (3, 0):
        pytest.skip('raise from not supported in this version of python')

    source = 'def a(): raise Hello() from Exception(1)'
    expected = 'def a(): raise Hello() from Exception(1)'

    expected_ast = ast.parse(expected)
    actual_ast = remove_brackets(source)
    compare_ast(expected_ast, actual_ast)
