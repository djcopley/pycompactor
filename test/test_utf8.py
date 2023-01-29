import ast
from python_minifier import unparse
from python_minifier.ast_compare import compare_ast

def test_emoji():

    source = '''
Hello="🔥"
'''

    expected_ast = ast.parse(source)
    actual_ast = unparse(expected_ast)
    compare_ast(expected_ast, ast.parse(actual_ast))
