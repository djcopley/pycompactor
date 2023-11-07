"""
Create namespaces for a tree

Namespaces are used to track where names are defined.
There is always a global namespace, and other namespaces may be nested inside.
Some nodes create new namespaces, such as functions, classes, and comprehensions.

This creates a namespace tree for a module. Each node in the AST has a namespace attribute that points to the namespace it is in.

The namespace tree is populated with the nonlocal and global names for each namespace.
Name bindings are not added here, but in :func:`python_minifier.rename.bind_names.bind_names`

Names in class scope that are not in used in Store context are also considered to be nonlocal.

"""

import ast
import sys

from python_minifier.rename.namespace import Namespace, AnnotationNamespace, ClassNamespace, FunctionNamespace, ModuleNamespace
from python_minifier.util import is_ast_node

def assign_arguments_to_namespace(arguments, parent_namespace, function_namespace):

    assert isinstance(arguments, ast.arguments)
    assert isinstance(function_namespace, Namespace)

    arguments.namespace = function_namespace

    for arg in getattr(arguments, 'posonlyargs', []) + arguments.args:
        create_child_namespaces(arg, function_namespace)
        if hasattr(arg, 'annotation') and arg.annotation is not None:
            create_child_namespaces(arg.annotation, parent_namespace)

    if hasattr(arguments, 'kwonlyargs'):
        for arg in arguments.kwonlyargs:
            create_child_namespaces(arg, function_namespace)
            if arg.annotation is not None:
                create_child_namespaces(arg.annotation, parent_namespace)

        for node in arguments.kw_defaults:
            if node is not None:
                create_child_namespaces(node, parent_namespace)

    for node in arguments.defaults:
        create_child_namespaces(node, parent_namespace)

    if arguments.vararg:
        if hasattr(arguments, 'varargannotation') and arguments.varargannotation is not None:
            create_child_namespaces(arguments.varargannotation, parent_namespace)
        elif isinstance(arguments.vararg, str):
            pass
        else:
            create_child_namespaces(arguments.vararg, function_namespace)

    if arguments.kwarg:
        if hasattr(arguments, 'kwargannotation') and arguments.kwargannotation is not None:
            create_child_namespaces(arguments.kwargannotation, parent_namespace)
        elif isinstance(arguments.kwarg, str):
            pass
        else:
            create_child_namespaces(arguments.kwarg, function_namespace)

def create_comprehension_namespace(node, parent_namespace):
    assert is_ast_node(node, (ast.GeneratorExp, 'SetComp', 'DictComp', 'ListComp'))

    comprehension_namespace = FunctionNamespace(node, name=node.__class__.__name__)
    parent_namespace.add_child(comprehension_namespace)

    if hasattr(node, 'elt'):
        create_child_namespaces(node.elt, parent_namespace=comprehension_namespace)
    elif hasattr(node, 'key'):
        create_child_namespaces(node.key, parent_namespace=comprehension_namespace)
        create_child_namespaces(node.value, parent_namespace=comprehension_namespace)

    iter_namespace = parent_namespace
    for generator in node.generators:
        generator.namespace = comprehension_namespace

        create_child_namespaces(generator.target, parent_namespace=comprehension_namespace)
        create_child_namespaces(generator.iter, parent_namespace=iter_namespace)

        iter_namespace = comprehension_namespace

        for if_ in generator.ifs:
            create_child_namespaces(if_, parent_namespace=comprehension_namespace)

    return comprehension_namespace

def create_functiondef_namespace(functiondef, parent_namespace):
    """
    Functions have up to three namespaces that may be relevant to arguments:

    * The parent namespace, which is where default value expressions are evaluated.
      - Type parameter names from annotation scope are NOT available, nor are function parameter names.
    * The annotation scope namespace, which is where type parameter names are bound.
      - Names from the parent scope are available, but not function parameter names.
    * The function namespace, which is where names in the body of the function are defined.
      Parameter names are bound in this namespace.
      - Names from parent scopes are available.

    If there are no type parameters, then no namespace is created for the annotation scope.

    Type parameter bounds and constraints are evaluated in nested annotation scopes but don't define names,
    so are not relevant to us.
    """
    assert is_ast_node(functiondef, (ast.FunctionDef, 'AsyncFunctionDef'))

    if hasattr(functiondef, 'type_params') and functiondef.type_params:
        annotation_namespace = AnnotationNamespace(functiondef, name=functiondef.name)
        parent_namespace.add_child(annotation_namespace)

        function_namespace = FunctionNamespace(functiondef, name=functiondef.name)
        annotation_namespace.add_child(function_namespace)

        for type_param in functiondef.type_params:
            create_child_namespaces(type_param, parent_namespace=annotation_namespace)

    else:
        function_namespace = FunctionNamespace(functiondef, name=functiondef.name)
        parent_namespace.add_child(function_namespace)

    if functiondef.args is not None:
        assign_arguments_to_namespace(functiondef.args, parent_namespace=parent_namespace, function_namespace=function_namespace)

    for node in functiondef.body:
        create_child_namespaces(node, parent_namespace=function_namespace)

    for node in functiondef.decorator_list:
        create_child_namespaces(node, parent_namespace=parent_namespace)

    if hasattr(functiondef, 'returns') and functiondef.returns is not None:
        create_child_namespaces(functiondef.returns, parent_namespace=parent_namespace)

    return function_namespace

def create_lambda_namespace(lambda_, parent_namespace):
    """
    Lambdas are very similar to functions

    Since they have no type parameters, return annotations, or decorators the implementation is simpler
    """

    assert isinstance(lambda_, ast.Lambda)

    function_namespace = FunctionNamespace(lambda_, name='Lambda')
    parent_namespace.add_child(function_namespace)

    assign_arguments_to_namespace(lambda_.args, function_namespace=function_namespace, parent_namespace=parent_namespace)
    create_child_namespaces(lambda_.body, parent_namespace=function_namespace)

    return function_namespace

def create_class_namespace(classdef, parent_namespace):
    """

    """
    assert isinstance(classdef, ast.ClassDef)

    if hasattr(classdef, 'type_params') and classdef.type_params:
        annotation_namespace = AnnotationNamespace(classdef, name=classdef.name)
        parent_namespace.add_child(annotation_namespace)
        class_namespace = ClassNamespace(classdef, name=classdef.name)
        annotation_namespace.add_child(class_namespace)

        for type_param in classdef.type_params:
            create_child_namespaces(type_param, parent_namespace=annotation_namespace)

    else:
        class_namespace = ClassNamespace(classdef, name=classdef.name)
        parent_namespace.add_child(class_namespace)

    for node in classdef.bases:
        create_child_namespaces(node, parent_namespace=parent_namespace)

    if hasattr(classdef, 'keywords'):
        for node in classdef.keywords:
            create_child_namespaces(node, parent_namespace=parent_namespace)

    if hasattr(classdef, 'starargs') and classdef.starargs is not None:
        create_child_namespaces(classdef.starargs, parent_namespace=parent_namespace)

    if hasattr(classdef, 'kwargs') and classdef.kwargs is not None:
        create_child_namespaces(classdef.kwargs, parent_namespace=parent_namespace)

    for node in classdef.body:
        create_child_namespaces(node, parent_namespace=class_namespace)

    for node in classdef.decorator_list:
        create_child_namespaces(node, parent_namespace=parent_namespace)

def create_child_namespaces(node, parent_namespace):
    """
    :param node: The tree to build the namespaces for
    :type node: :class:`ast.AST`
    :param parent_namespace: The namespace Node that this node is in
    :type parent_namespace: :class:`Namespace`
    """

    node.namespace = parent_namespace

    if is_ast_node(node, (ast.FunctionDef, 'AsyncFunctionDef')):
        create_functiondef_namespace(node, parent_namespace)

    elif is_ast_node(node, (ast.GeneratorExp, ast.SetComp, ast.DictComp)):
        create_comprehension_namespace(node, parent_namespace)

    elif sys.version_info >= (3, 0) and is_ast_node(node, ast.ListComp):
        create_comprehension_namespace(node, parent_namespace)

    elif isinstance(node, ast.Lambda):
        create_lambda_namespace(node, parent_namespace)

    elif isinstance(node, ast.ClassDef):
        create_class_namespace(node, parent_namespace)

    elif isinstance(node, ast.Global):
        parent_namespace.global_names.update(node.names)

    elif is_ast_node(node, 'Nonlocal'):
        parent_namespace.nonlocal_names.update(node.names)

    elif isinstance(node, ast.Name):
        if isinstance(parent_namespace, ClassNamespace):
            if isinstance(node.ctx, ast.Load):
                parent_namespace.nonlocal_names.add(node.id)
            elif isinstance(node.ctx, ast.Store) and isinstance(node.parent, ast.AugAssign):
                parent_namespace.nonlocal_names.add(node.id)

    else:
        for child in ast.iter_child_nodes(node):
            create_child_namespaces(child, parent_namespace)

def create_all_namespaces(module):
    """
    Build all namespaces for a module

    :param module: The module to build namespaces for
    :type module: :class:`ast.Module`
    :return: The module namespace
    :rtype: :class:`Namespace`
    """
    global_namespace = ModuleNamespace(module)
    create_child_namespaces(module, parent_namespace=global_namespace)

    return global_namespace
