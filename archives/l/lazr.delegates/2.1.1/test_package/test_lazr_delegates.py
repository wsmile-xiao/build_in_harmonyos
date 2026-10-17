#!/usr/bin/env python3
"""Smoke test for the lazr.delegates 2.1.1 conan package (python-require).

Actually uses the library API — the delegate_to class decorator (with a
zope.interface Interface) and the Passthrough descriptor — so a broken or
incomplete package fails this test.  Modeled on the upstream doctest
(src/lazr/delegates/docs/index.rst) and test_passthrough.py.
"""
import os
import sys

# site-packages dirs of lazr.delegates + zope.interface (os.pathsep joined)
site_paths = sys.argv[1].split(os.pathsep)
for p in site_paths:
    if p:
        sys.path.insert(0, p)

import lazr.delegates
from lazr.delegates import Passthrough, delegate_to

# __init__.py calls importlib.metadata.version("lazr.delegates") at import
# time — the packaged egg-info metadata must be present, else this raises
# PackageNotFoundError.
assert lazr.delegates.__version__ == "2.1.1", lazr.delegates.__version__

# --- delegate_to: class composition by delegation (docs/index.rst) ---
from zope.interface import Attribute, Interface


class IFoo0(Interface):
    one = Attribute("attribute in IFoo0")


class IFoo1(IFoo0):
    def bar():
        """A method in IFoo1"""

    baz = Attribute("attribute in IFoo1")


class Foo0:
    one = "one"


class Foo1(Foo0):
    def bar(self):
        return "bar"

    baz = "I am baz"


@delegate_to(IFoo1)
class SomeClass:
    def __init__(self, context):
        self.context = context


delegate = Foo1()
s = SomeClass(delegate)
assert s.bar() == "bar"
assert s.baz == "I am baz"
assert s.one == "one"
assert IFoo1.providedBy(s) is True

# custom context attribute name
@delegate_to(IFoo1, context="myfoo")
class SomeOtherClass:
    def __init__(self, foo):
        self.myfoo = foo


s2 = SomeOtherClass(delegate)
assert s2.bar() == "bar"
assert s2.baz == "I am baz"

# --- Passthrough: descriptor forwarding get/set to a context attr ---
class Base:
    foo = "foo from Base"

    @classmethod
    def clsmethod(cls):
        return cls.__name__


class Holder:
    context = Base()
    foo = Passthrough("foo", "context")
    clsmethod = Passthrough("clsmethod", "context")


h = Holder()
assert h.foo == "foo from Base"
assert h.clsmethod() == "Base"
h.foo = "new value"
assert h.context.foo == "new value"

# Passthrough on a plain object without adaptation (test_passthrough.py)
class Adapter:
    mycontext = Base()


p = Passthrough("foo", "mycontext")
adapter = Adapter()
assert p.__get__(adapter) == "foo from Base"

print("lazr.delegates 2.1.1 OK (version=%s)" % lazr.delegates.__version__)
