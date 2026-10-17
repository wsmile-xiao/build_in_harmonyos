#!/usr/bin/env python3
"""Consumer test for zope.interface 8.6 (pure-Python packaging, R34).

Exercises real public APIs of zope.interface — Interface class creation,
@implementer, classImplements/implementedBy, the adapter registry
(zope.interface.adapter) and component registry (zope.interface.registry),
plus verifyObject/verifyClass — and asserts the results.

The C optimizations are an optional acceleration; in this pure-Python build
they are unavailable and the pure-Python fallback is used, which is the
functionally complete path (mirrors PURE_PYTHON=1 in upstream CI).

Usage: test_zi.py <site-packages>
"""
import os
import sys


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} <site-packages>", file=sys.stderr)
        return 2
    site = sys.argv[1]
    if not os.path.isdir(os.path.join(site, "zope", "interface")):
        raise AssertionError(f"zope.interface package missing in {site}")
    # Do not write .pyc into the packaged lib/ during the consumer test
    sys.dont_write_bytecode = True
    sys.path = [site] + sys.path

    # --- 1. Interface class creation ------------------------------------
    import zope.interface
    from zope.interface import Interface, Attribute, implementer, classImplements
    from zope.interface.interface import InterfaceClass

    class IShape(Interface):
        """A shape interface."""
        name = Attribute("Name of the shape")

        def area():
            """Return the area."""

    assert isinstance(IShape, InterfaceClass)
    assert IShape.__name__ == "IShape"

    # --- 2. @implementer + implementedBy --------------------------------
    @implementer(IShape)
    class Square:
        def __init__(self, side):
            self.side = side
            self.name = "square"

        def area(self):
            return self.side * self.side

    sq = Square(3)
    assert IShape.providedBy(sq), "IShape.providedBy(sq) must be True"
    assert IShape.implementedBy(Square)
    assert Square.__implemented__ is not None
    # interface inheritance
    class IColoredShape(IShape):
        color = Attribute("color")

    assert IColoredShape.extends(IShape)
    assert IShape.isOrExtends(IShape)
    assert not IShape.isOrExtends(IColoredShape)

    # --- 3. classImplements (runtime declaration) -----------------------
    class Circle:
        def __init__(self, r):
            self.r = r
            self.name = "circle"

        def area(self):
            return 3.14159 * self.r * self.r

    classImplements(Circle, IShape)
    assert IShape.implementedBy(Circle)
    assert IShape.providedBy(Circle(1))
    assert IShape.providedBy(Circle(2))

    # --- 4. adapter registry (zope.interface.adapter) -------------------
    from zope.interface.adapter import AdapterRegistry
    from zope.interface.interfaces import IAdapterRegistry

    ar = AdapterRegistry()
    assert IAdapterRegistry.providedBy(ar)

    class IArea(Interface):
        def area():
            pass

    def area_adapter(shape):
        return shape.area()

    class IOther(Interface):
        pass

    ar.register([IShape], IArea, "", area_adapter)
    assert ar.registered([IShape], IArea, "") is area_adapter
    lookup = ar.lookup([IShape], IArea, "")
    assert lookup is area_adapter, f"lookup got {lookup!r}"
    assert ar.lookup([IOther], IArea, "") is None  # no adapter for IOther
    # multi-adapter with required types
    ar.register([IShape, IShape], IArea, "pair",
                lambda a, b: a.area() + b.area())
    assert ar.lookup([IShape, IShape], IArea, "pair")(Square(2), Square(3)) == 13

    # --- 5. component registry (zope.interface.registry) ----------------
    from zope.interface.registry import Components

    comp = Components()
    comp.registerUtility(42, provided=Interface, name="answer")
    assert comp.queryUtility(Interface, name="answer", default=None) == 42
    assert comp.queryUtility(Interface, name="missing", default="none") == "none"

    comp.registerAdapter(area_adapter, (IShape,), IArea)
    adapted = comp.queryAdapter(Square(4), IArea)
    assert adapted == 16, f"queryAdapter got {adapted!r}"

    # --- 6. verify + document smoke --------------------------------------
    from zope.interface.exceptions import MultipleInvalid
    from zope.interface.verify import verifyObject, verifyClass

    class BadSquare:
        def __init__(self):
            self.name = "bad"

    assert verifyObject(IShape, sq), "verifyObject must pass for Square"
    assert verifyClass(IShape, Square), "verifyClass must pass for Square"
    try:
        verifyObject(IShape, BadSquare())
    except MultipleInvalid:
        pass  # expected: BadSquare does not implement area()
    else:
        raise AssertionError("verifyObject must fail for BadSquare")

    # --- C-optimization availability (informational) --------------------
    try:
        from zope.interface import _zope_interface_coptimizations  # noqa
        c_opt = True
    except ImportError:
        c_opt = False
    print(f"zope.interface 8.6 OK (C optimizations available: {c_opt})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
