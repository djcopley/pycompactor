import ast

from python_minifier.transforms.remove_literal_statements import RemoveLiteralStatements
from python_minifier.ast_compare import compare_ast
from python_minifier.rename.add_parent import add_parent
from python_minifier.rename.create_namespaces import create_all_namespaces
from python_minifier.rename.bind_names import bind_names
from python_minifier.rename.resolve_names import resolve_names



def remove_literals(source):
    module = ast.parse(source, 'test_remove_literal_statements')

    add_parent(module)
    create_all_namespaces(module)
    #bind_names(module)
    #resolve_names(module)

    return RemoveLiteralStatements()(module)

def test_remove_literal_num():
    source = '213'
    expected = ''

    expected_ast = ast.parse(expected)
    actual_ast = remove_literals(source)
    compare_ast(expected_ast, actual_ast)

def test_remove_literal_str():
    source = '"hello"'
    expected = ''

    expected_ast = ast.parse(expected)
    actual_ast = remove_literals(source)
    compare_ast(expected_ast, actual_ast)

def test_complex():
    source = '''
"module docstring"
a = 'hello'

def t():
    "function docstring"
    a = 2
    0
    2
    'sadfsaf'
    def g():
        "just a docstring"

'''
    expected = '''
a = 'hello'
def t():
    a=2
    def g():
        0
'''

    expected_ast = ast.parse(expected)
    actual_ast = remove_literals(source)
    compare_ast(expected_ast, actual_ast)
