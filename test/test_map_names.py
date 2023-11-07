import ast

from python_minifier.rename.create_namespaces import create_all_namespaces
from python_minifier.rename.namespace import Namespace


def test_name_map():
    source = '''
a = 'Hello'
'''

    the_ast = ast.parse(source)

    global_namespace = create_all_namespaces(the_ast)

    assert isinstance(global_namespace, Namespace)
