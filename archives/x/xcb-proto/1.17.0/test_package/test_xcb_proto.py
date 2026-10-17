#!/usr/bin/env python3
"""Independent installed-package tests for xcb-proto."""

import __main__
import argparse
import importlib.util
import tempfile
from pathlib import Path
from xml.etree import ElementTree


OUTPUT_EVENTS = []


def _output_callback(kind):
    def callback(*_args, **_kwargs):
        OUTPUT_EVENTS.append(kind)

    return callback


__main__.output = {
    kind: _output_callback(kind)
    for kind in (
        "open",
        "close",
        "simple",
        "enum",
        "struct",
        "union",
        "request",
        "event",
        "error",
        "eventstruct",
    )
}

# xcbgen binds __main__.output while importing, so these imports follow setup.
from xcbgen.align import Alignment, AlignmentLog  # noqa: E402
from xcbgen.error import ResolveException  # noqa: E402
from xcbgen.expr import Expression, Field  # noqa: E402
from xcbgen.state import Module, Namespace  # noqa: E402
from xcbgen.xtypes import Doc, Enum, PadType, PrimitiveType  # noqa: E402


PROTOCOLS = (
    "bigreq",
    "composite",
    "damage",
    "dbe",
    "dpms",
    "dri2",
    "dri3",
    "ge",
    "glx",
    "present",
    "randr",
    "record",
    "render",
    "res",
    "screensaver",
    "shape",
    "shm",
    "sync",
    "xc_misc",
    "xevie",
    "xf86dri",
    "xf86vidmode",
    "xfixes",
    "xinerama",
    "xinput",
    "xkb",
    "xprint",
    "xproto",
    "xselinux",
    "xtest",
    "xv",
    "xvmc",
)

MODULE_FILES = (
    "__init__.py",
    "align.py",
    "error.py",
    "expr.py",
    "matcher.py",
    "state.py",
    "xtypes.py",
)


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def fixture(directory, name, contents):
    path = Path(directory) / name
    path.write_text(contents, encoding="utf-8")
    return path


def test_protocol(name, package_root):
    path = package_root / "share" / "xcb" / f"{name}.xml"
    module = Module(str(path), __main__.output)
    module.register()
    module.resolve()
    require(
        path.is_file()
        and module.namespace.header == name
        and module.namespace.path == str(path)
        and len(module.all) > 0
        and len(module.types) >= 14
        and module.get_type("CARD32").fixed_size(),
        f"protocol generator validation failed for {name}",
    )


def api_alignment_primitive(_root):
    values = [Alignment.for_primitive_type(size) for size in (1, 2, 4, 8)]
    require(
        values == [Alignment(1), Alignment(2), Alignment(4), Alignment(8)],
        "primitive alignment mapping is incorrect",
    )


def api_alignment_offset(_root):
    require(
        Alignment(8, 6).align_after_fixed_size(5) == Alignment(8, 3),
        "fixed-size alignment offset is incorrect",
    )


def api_alignment_guarantee(_root):
    required = Alignment(4, 2)
    require(
        required.is_guaranteed_at(Alignment(8, 6))
        and not required.is_guaranteed_at(Alignment(2, 0)),
        "alignment guarantee relation is incorrect",
    )


def api_alignment_combine(_root):
    require(
        Alignment(8, 0).combine_with(Alignment(4, 2)) == Alignment(2, 0),
        "alignment combination is incorrect",
    )


def api_alignment_log(_root):
    log = AlignmentLog()
    log.ok(Alignment(4), "field", "Type", [], Alignment(4, 1))
    other = AlignmentLog()
    other.fail(Alignment(2), "field", "Type", [], "fixture failure")
    log.append(other)
    require(
        log.ok_count() == 1 and "fixture failure" in str(log),
        "alignment log did not retain success and failure records",
    )


def api_field_string(_root):
    field = Field(None, ("CARD8",), "opcode", True, True, False)
    field.parent = "FixtureRequest"
    require(
        str(field) == 'Field "opcode" in FixtureRequest',
        "field diagnostic string is incorrect",
    )


def api_expression_value(_root):
    expression = Expression(ElementTree.fromstring("<value>0x20</value>"), None)
    require(
        expression.fixed_size() and expression.get_value() == 32,
        "constant expression did not preserve its value",
    )


def api_expression_binary(_root):
    expression = Expression(
        ElementTree.fromstring(
            "<op op='*'><value>4</value><value>8</value></op>"
        ),
        None,
    )
    require(
        expression.op == "*" and expression.get_multiple() == 32,
        "binary expression did not preserve multiplicity",
    )


def api_expression_unary(_root):
    expression = Expression(
        ElementTree.fromstring("<unop op='~'><value>1</value></unop>"), None
    )
    require(
        expression.op == "~" and expression.rhs.get_value() == 1,
        "unary expression was not parsed",
    )


def api_expression_popcount(_root):
    expression = Expression(
        ElementTree.fromstring("<popcount><fieldref>mask</fieldref></popcount>"),
        None,
    )
    require(
        expression.op == "popcount" and expression.lenfield_name == "mask",
        "popcount expression was not parsed",
    )


def api_expression_sumof(_root):
    expression = Expression(
        ElementTree.fromstring(
            "<sumof ref='items'><listelement-ref/></sumof>"
        ),
        None,
    )
    require(
        expression.op == "sumof"
        and expression.lenfield_name == "items"
        and expression.rhs.op == "listelement-ref",
        "sumof expression was not parsed",
    )


def api_expression_listelement(_root):
    expression = Expression(ElementTree.fromstring("<listelement-ref/>"), None)
    require(
        expression.op == "listelement-ref" and expression.contains_listelement_ref,
        "list-element reference was not marked",
    )


def api_expression_enumref(_root):
    marker = object()

    class Types:
        @staticmethod
        def get_type(name):
            return marker if name == "Mode" else None

    expression = Expression(
        ElementTree.fromstring("<enumref ref='Mode'>Enabled</enumref>"), None
    )
    expression.resolve(Types(), [])
    require(
        expression.lenfield_type is marker and expression.lenfield_name == "Enabled",
        "enum reference did not resolve through the module API",
    )


def api_namespace_core(_root):
    with tempfile.TemporaryDirectory() as directory:
        path = fixture(directory, "core.xml", "<xcb header='fixture_core'/>")
        namespace = Namespace(str(path))
        require(
            namespace.header == "fixture_core"
            and not namespace.is_ext
            and namespace.prefix == ("xcb",),
            "core namespace metadata is incorrect",
        )


def api_namespace_extension(_root):
    with tempfile.TemporaryDirectory() as directory:
        path = fixture(
            directory,
            "extension.xml",
            "<xcb header='fixture_ext' extension-xname='FIXTURE' "
            "extension-name='fixture' major-version='2' minor-version='1'/>",
        )
        namespace = Namespace(str(path))
        require(
            namespace.is_ext
            and namespace.ext_xname == "FIXTURE"
            and namespace.prefix == ("xcb", "fixture")
            and (namespace.major_version, namespace.minor_version) == ("2", "1"),
            "extension namespace metadata is incorrect",
        )


def api_primitive_type(_root):
    value = PrimitiveType(("uint24_t",), 3)
    require(
        value.fixed_size()
        and value.get_total_size() == 3
        and value.required_start_align == Alignment(1),
        "primitive type size or alignment is incorrect",
    )


def api_enum_type(_root):
    element = ElementTree.fromstring(
        "<enum name='Mode'>"
        "<item name='Default'/>"
        "<item name='Enabled'><value>3</value></item>"
        "<item name='Mask'><bit>2</bit></item>"
        "</enum>"
    )
    value = Enum(("xcb", "Mode"), element)
    require(
        value.values == [("Default", ""), ("Enabled", "3"), ("Mask", "4")]
        and value.bits == [("Mask", "2")],
        "enum values and bit values are incorrect",
    )


def api_pad_bytes(_root):
    value = PadType(ElementTree.fromstring("<pad bytes='3' serialize='true'/>"))
    require(
        value.fixed_size() and value.get_total_size() == 3 and value.serialize,
        "fixed byte padding metadata is incorrect",
    )


def api_pad_align(_root):
    value = PadType(ElementTree.fromstring("<pad align='8'/>"))
    require(
        not value.fixed_size()
        and value.get_alignment_after(Alignment(4, 2), [], None) == Alignment(8),
        "alignment padding did not realign the stream",
    )


def api_doc_type(_root):
    element = ElementTree.fromstring(
        "<doc><brief>Fixture</brief><description>Details</description>"
        "<field name='value'>Value field</field>"
        "<error type='BadValue'>Invalid</error>"
        "<see type='request' name='Query'/><example>query()</example></doc>"
    )
    value = Doc(("xcb", "Fixture"), element)
    require(
        value.brief == "Fixture"
        and value.description == "Details"
        and value.fields == {"value": "Value field"}
        and value.errors == {"BadValue": "Invalid"}
        and value.see == {"Query": "request"}
        and value.example == "query()",
        "documentation fields were not parsed",
    )


def api_module_generate(_root):
    with tempfile.TemporaryDirectory() as directory:
        path = fixture(
            directory,
            "generate.xml",
            "<xcb header='fixture_generate'><enum name='Mode'>"
            "<item name='Off'><value>0</value></item></enum></xcb>",
        )
        OUTPUT_EVENTS.clear()
        module = Module(str(path), __main__.output)
        module.register()
        module.resolve()
        module.generate()
        require(
            OUTPUT_EVENTS == ["open", "enum", "close"],
            f"module output callback order is incorrect: {OUTPUT_EVENTS}",
        )


def api_module_missing_type(_root):
    with tempfile.TemporaryDirectory() as directory:
        path = fixture(directory, "missing.xml", "<xcb header='fixture_missing'/>")
        module = Module(str(path), __main__.output)
        try:
            module.get_type("DOES_NOT_EXIST")
        except ResolveException as error:
            matched = str(error) == "Type DOES_NOT_EXIST not found"
        else:
            matched = False
        require(matched, "missing type did not raise ResolveException")


API_TESTS = {
    "alignment-primitive": api_alignment_primitive,
    "alignment-offset": api_alignment_offset,
    "alignment-guarantee": api_alignment_guarantee,
    "alignment-combine": api_alignment_combine,
    "alignment-log": api_alignment_log,
    "field-string": api_field_string,
    "expression-value": api_expression_value,
    "expression-binary": api_expression_binary,
    "expression-unary": api_expression_unary,
    "expression-popcount": api_expression_popcount,
    "expression-sumof": api_expression_sumof,
    "expression-listelement": api_expression_listelement,
    "expression-enumref": api_expression_enumref,
    "namespace-core": api_namespace_core,
    "namespace-extension": api_namespace_extension,
    "primitive-type": api_primitive_type,
    "enum-type": api_enum_type,
    "pad-bytes": api_pad_bytes,
    "pad-align": api_pad_align,
    "doc-type": api_doc_type,
    "module-generate": api_module_generate,
    "module-missing-type": api_module_missing_type,
}


def test_metadata(package_root):
    protocol_dir = package_root / "share" / "xcb"
    python_dir = package_root / "lib" / "python3" / "site-packages"
    module_dir = python_dir / "xcbgen"
    pc = package_root / "share" / "pkgconfig" / "xcb-proto.pc"

    actual_protocols = tuple(sorted(path.stem for path in protocol_dir.glob("*.xml")))
    actual_modules = tuple(sorted(path.name for path in module_dir.glob("*.py")))
    variables = {}
    for line in pc.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.startswith(("Name:", "Description:", "Version:")):
            key, value = line.split("=", 1)
            variables[key] = value

    spec = importlib.util.find_spec("xcbgen")
    prefix = (pc.parent / ".." / "..").resolve()
    require(
        actual_protocols == tuple(sorted(PROTOCOLS))
        and (protocol_dir / "xcb.xsd").is_file()
        and actual_modules == tuple(sorted(MODULE_FILES))
        and variables.get("prefix") == "${pcfiledir}/../.."
        and variables.get("xcbincludedir") == "${datadir}/xcb"
        and variables.get("pythondir") == "${prefix}/lib/python3/site-packages"
        and prefix == package_root.resolve()
        and spec is not None
        and Path(spec.origin).resolve().parent == module_dir.resolve(),
        "installed XML, Python, or pkg-config metadata is incomplete or non-relocatable",
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("kind", choices=("protocol", "api", "metadata"))
    parser.add_argument("case")
    parser.add_argument("package_root", type=Path)
    args = parser.parse_args()

    if args.kind == "protocol":
        if args.case not in PROTOCOLS:
            raise ValueError(f"unknown protocol: {args.case}")
        test_protocol(args.case, args.package_root)
    elif args.kind == "api":
        API_TESTS[args.case](args.package_root)
    else:
        test_metadata(args.package_root)

    print(f"PASS {args.kind}:{args.case}")


if __name__ == "__main__":
    main()
