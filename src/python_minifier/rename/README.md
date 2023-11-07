# Renaming

We can save bytes by shortening the names used in a python program.

One simple way to do this is to replace each unique name in a module with a shorter one. 
This will probably exhaust the available single character names, so is not as efficient as it could be.
Also, not all names can be safely changed this way.

By determining the scope of each name, we can assign the same short name to multiple non-overlapping scopes.
This means sibling namespaces may have the same names, and names will be shadowed in inner namespaces where possible.

To do this we manipulate two data structures:
- AST - The Abstract Syntax Tree of the program, as returned by the ast module.
- Namespace Tree - A tree of namespaces, which is parallel to the AST.

This file is a guide for how the python_minifier package shortens names.
There are multiple steps to the renaming process.

## 1. Add parent attributes

To make it easier to traverse the AST, we add a parent attribute to each node.

## 2. Create namespace tree

Nodes in the AST can introduce new namespaces, which are represented by Namespace nodes in the namespace tree.

There are different types of Namespace nodes, reflecting how names are resolved in that namespace.
- ModuleNamespace
- FunctionNamespace
- AnnotationNamespace
- ClassNamespace

The root of the namespace tree is a ModuleNamespace, which represents the global namespace.
- FunctionDef, AsyncFunctionDef, GeneratorExp, SetComp, DictComp, Lambda and (in Python 3+) ListComp nodes create a FunctionNamespace.
- ClassDef nodes create a ClassNamespace.
- FunctionDef nodes with type parameters create a AnnotationNamespace as the parent of their FunctionNamespace.
- ClassDef nodes with type parameters create a AnnotationNamespace as the parent of their ClassNamespace.

Namespace nodes have these attributes:
- global_names - A list of global names in this namespace, populated in this step by Global nodes.
- nonlocal_names - A list of nonlocal names in this namespace, populated in this step by Nonlocal nodes.
- bindings - A list of Bindings local to this namespace, which will be populated in later steps.

### Assigning namespaces to AST nodes

Each node in the AST has a namespace attribute set to the Namespace node that will be used for name binding and resolution.
This is usually the closest parent namespace node. The exceptions are:

- Function argument default values are in the same namespace as their function.
- Function decorators are in the same namespace as their function.
- Function annotations are in the same namespace as their function.
- Class decorator are in the same namespace as their class.
- Class bases, keywords, starargs and kwargs are in the same namespace as their class.
- The first iteration expression of a comprehension is in the same namespace as it's parent ListComp/SetComp/DictComp or GeneratorExp.

### Function (& module) scope

In function scope any statement that binds a name causes that name to refer to a binding in the local namespace, regardless of if that name is *currently* bound or not.
(except for nonlocal/global names, which are bound as indicated by the nonlocal/global keyword)
This can be a cause of UnboundLocalError, like in this example:

```python
a = 5
def A():
    print(a)
    a = 6
```

### Class scope
Class scope is different - names can be bound to the class namespace during execution of the body, but when unbound they are resolved in the parent namespace.

This makes thing like this possible, but awkward to minify:
```python 
message = 'Hello'

class MyClass:
    if something():
        message = message + ' World'
    else:
        message = 'Goodbye World'
```

In class scope a name lookup could refer to:
- A name bound in the class namespace, which is an attribute of the class, which we must not rename
- A name bound in a parent namespace, which may be renamed

Given arbitrary code, it is not generally possible to determine if a name is bound in the class namespace or not at the point of reference.
In the above example this means the message global is not renamed because we don't know if it's safe. 

What we can do is check if there is *any* lookup of a name in the class namespace and if not assume any binding of that name in the class scope is local to the class namespace. (and it shadows any binding in a parent namespace)

If there *is* a lookup of any name in the class scope, we must assume all reference to that name are to a binding in a parent function namespace. This is done by adding the name to the nonlocal_names of the class namespace.

## 3. Bind names

Every node that binds a name creates a NameBinding for that name in its namespace.
The node is added to the NameBinding as a reference.

If the name is nonlocal in its namespace it does not create a binding.

Nodes that create a binding:
- FunctionDef nodes bind their name
- ClassDef nodes bind their name
- arg nodes bind their arg
- Name nodes in Store or Del context bind their id
- MatchAs nodes bind their name
- MatchStar nodes bind their name
- MatchMapping nodes bind their rest
- TypeVar nodes bind their name
- TypeVarTuple nodes bind their name
- ParamSpec nodes bind their name

### Preventing renaming

Some names must not be renamed, and we can detect these in this step.
- Names that refer to builtins (?)
- Names with a Binding in ClassNamespace will be an attribute of the class
- Names that are nonlocal in the ModuleNamespace (not valid python, but we can't rename them)
- Lambda function arguments could be called with keyword arguments, so we can't rename them
- Relative imports (?)

Most function parameters can't be renamed without changing the function signature, so we don't rename them.
The exceptions are conventional use of self, cls, args, kwargs.

But we can potentially rebind (non-lambda) function parameters to a different name in the body of the function. 
We reserve the original name in the function namespace now, in case we want to do this later.

### 4. Resolve names

For the remaining unbound name nodes and nodes that normally create a binding but are for a nonlocal name, we find their binding.

Bindings for name references are found by searching their namespace, then parent namespaces.
If a name is global in a searched namespace, skip straight to the module node.
If a name is nonlocal in a searched namespace, skip to the next parent function namespace.

If a NameBinding is found, add the node as a reference.
If no NameBinding is found, check if the name would resolve to a builtin. 
If so, create a BuiltinBinding in the module namespace and add this node as a reference.

Otherwise we failed to find a binding for this name - Create a NameBinding in the module namespace and add this node 
as a reference.

## Hoist Literals

At this point we do the HoistLiterals transform, which adds new HoistedLiteral bindings to the namespaces where it wants
to introduce new names.

## Name Assignment

Collect all bindings in the module and sort by estimated byte savings

For each binding:
 - Determine it's 'reservation scope', which is the set of namespaces that name is referenced in (and all namespaces between them)
 - Get the next available name that is unassigned and unreserved in all namespaces in the reservation scope.
 - Check if we should proceed with the rename - is it space efficient to do this rename, or has the original name been assigned somewhere else?
 - Rename the binding, rename all referenced nodes to the new name, and record this name as assigned in every namespace of the reservation scope.
