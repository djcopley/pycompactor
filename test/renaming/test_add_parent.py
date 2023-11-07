import ast

from python_minifier.rename.add_parent import add_parent


def test_add_parent():

    source = '''
class A:
    def b(self):
        pass
'''

    tree = ast.parse(source)

    add_parent(tree)

    assert isinstance(tree, ast.Module)

    assert isinstance(tree.body[0], ast.ClassDef)
    assert tree.body[0].parent is tree

    assert isinstance(tree.body[0].body[0], ast.FunctionDef)
    assert tree.body[0].body[0].parent is tree.body[0]

    assert isinstance(tree.body[0].body[0].body[0], ast.Pass)
    assert tree.body[0].body[0].body[0].parent is tree.body[0].body[0]
