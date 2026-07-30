#!/usr/bin/env python3
"""Sample-driven validation of dtfabric schema definitions.

This test verifies dtfabric's ability to:
1. Load YAML definition files (data type definitions)
2. Map byte streams to typed field representations
3. Verify structure offset/size calculations
4. Handle nested structures, sequences, unions, and padding
5. Validate little-endian mapping

Validates that a schema/definition class library can be verified on OHOS
using sample-driven (known-answer) test data.
"""

import io
import os
import sys
import traceback

# Add dtfabric source to path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ARCHIVE_DIR = os.path.dirname(SCRIPT_DIR)  # archives/d/dtfabric/20251118/

# Resolve dtfabric source from known build_in_harmonyos location
_BUILD_ROOT = None
for _candidate in (
    os.path.join(os.path.dirname(SCRIPT_DIR), '..', '..', '..', '..', 'tmp', 'dtfabric-20251118'),
    os.path.join(os.path.dirname(SCRIPT_DIR), '..', '..', '..', 'tmp', 'dtfabric-20251118'),
    os.path.join(os.path.dirname(SCRIPT_DIR), '..', '..', 'tmp', 'dtfabric-20251118'),
):
    _p = os.path.abspath(_candidate)
    if os.path.isdir(os.path.join(_p, 'dtfabric')):
        _BUILD_ROOT = _p
        break

if not _BUILD_ROOT:
    for _root in ('/storage/Users/currentUser/junshi_liu/build_in_harmonyos',
                  os.path.expanduser('~/build_in_harmonyos')):
        _p = os.path.join(_root, 'tmp', 'dtfabric-20251118')
        if os.path.isdir(os.path.join(_p, 'dtfabric')):
            _BUILD_ROOT = _p
            break

if _BUILD_ROOT:
    sys.path.insert(0, _BUILD_ROOT)

from dtfabric import data_types
from dtfabric import definitions as defs
from dtfabric import errors
from dtfabric import reader
from dtfabric import registry
from dtfabric.runtime import data_maps

PASS = 0
FAIL = 0


def check(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  [PASS] {name}")
    else:
        FAIL += 1
        print(f"  [FAIL] {name}  --  {detail}")


def load_definitions(yaml_path):
    """Load YAML definitions from a file."""
    path = os.path.join(ARCHIVE_DIR, yaml_path)
    reg = registry.DataTypeDefinitionsRegistry()
    file_reader = reader.YAMLDataTypeDefinitionsFileReader()
    with open(path, 'rb') as f:
        file_reader.ReadFileObject(reg, f)
    return reg


# ---------------------------------------------------------------------------
# Part 1: Integer definitions (definitions/integers.yaml)
# ---------------------------------------------------------------------------
def test_integer_definitions():
    print("\n=== Part 1: Integer Definitions ===")
    reg = load_definitions('test_data/definitions/integers.yaml')

    int_types = {
        'int8':  (1, defs.FORMAT_SIGNED),
        'int32': (4, defs.FORMAT_SIGNED),
        'uint8': (1, defs.FORMAT_UNSIGNED),
        'uint16':(2, defs.FORMAT_UNSIGNED),
    }
    for name, (expected_size, expected_fmt) in int_types.items():
        d = reg.GetDefinitionByName(name)
        check(f"{name} defined", d is not None, f"name={name}")
        if d:
            check(f"{name} type=integer",
                  d.TYPE_INDICATOR == defs.TYPE_INDICATOR_INTEGER)
            check(f"{name}.size == {expected_size}",
                  getattr(d, 'size', None) == expected_size,
                  f"got size={getattr(d, 'size', None)}")
            check(f"{name}.format == {expected_fmt}",
                  getattr(d, 'format', None) == expected_fmt,
                  f"got format={getattr(d, 'format', None)}")

    int32 = reg.GetDefinitionByName('int32')
    check("int32 aliases contain LONG",
          int32 is not None and int32.aliases is not None and 'LONG' in int32.aliases)
    check("int32 byte_order is little-endian",
          int32 is not None and int32.byte_order == defs.BYTE_ORDER_LITTLE_ENDIAN)

    uint16 = reg.GetDefinitionByName('uint16')
    check("uint16 byte_order is little-endian",
          uint16 is not None and uint16.byte_order == defs.BYTE_ORDER_LITTLE_ENDIAN)


# ---------------------------------------------------------------------------
# Part 2: Structure with 3D point (structure.yaml)
# ---------------------------------------------------------------------------
def test_structure():
    print("\n=== Part 2: Structure with Nested Types ===")
    reg = load_definitions('test_data/structure.yaml')

    names = ['int32', 'point3d', 'triangle3d', 'box3d', 'sphere3d']
    for n in names:
        d = reg.GetDefinitionByName(n)
        check(f"{n} defined", d is not None)

    point3d = reg.GetDefinitionByName('point3d')
    if point3d and hasattr(point3d, 'members') and point3d.members:
        member_names = [m.name for m in point3d.members]
        check("point3d members: x, y, z", member_names == ['x', 'y', 'z'],
              f"got {member_names}")
        check("point3d byte_order is little-endian",
              point3d.byte_order == defs.BYTE_ORDER_LITTLE_ENDIAN)

    sm = data_maps.StructureMap(point3d)
    byte_stream = bytes([
        0x01, 0x00, 0x00, 0x00,  # x = 1
        0x02, 0x00, 0x00, 0x00,  # y = 2
        0x03, 0x00, 0x00, 0x00,  # z = 3
    ])
    struct = sm.MapByteStream(byte_stream)
    check("point3d mapped", struct is not None)
    if struct:
        check("point3d.x == 1", struct.x == 1, f"got {struct.x}")
        check("point3d.y == 2", struct.y == 2, f"got {struct.y}")
        check("point3d.z == 3", struct.z == 3, f"got {struct.z}")

    # triangle3d = 3 x point3d = 36 bytes
    triangle3d = reg.GetDefinitionByName('triangle3d')
    tm = data_maps.StructureMap(triangle3d)
    tri_bytes = bytes([
        0x01, 0x00, 0x00, 0x00,  # a.x=1
        0x00, 0x00, 0x00, 0x00,  # a.y=0
        0x00, 0x00, 0x00, 0x00,  # a.z=0
        0x02, 0x00, 0x00, 0x00,  # b.x=2
        0x00, 0x00, 0x00, 0x00,  # b.y=0
        0x00, 0x00, 0x00, 0x00,  # b.z=0
        0x03, 0x00, 0x00, 0x00,  # c.x=3
        0x00, 0x00, 0x00, 0x00,  # c.y=0
        0x00, 0x00, 0x00, 0x00,  # c.z=0
    ])
    tri = tm.MapByteStream(tri_bytes)
    check("triangle3d mapped", tri is not None)
    if tri:
        check("triangle3d.a.x == 1", tri.a.x == 1, f"got {tri.a.x}")
        check("triangle3d.b.x == 2", tri.b.x == 2, f"got {tri.b.x}")
        check("triangle3d.c.x == 3", tri.c.x == 3, f"got {tri.c.x}")


# ---------------------------------------------------------------------------
# Part 3: Structure with padding (structure_with_padding.yaml)
# ---------------------------------------------------------------------------
def test_padding():
    print("\n=== Part 3: Structure with Padding ===")
    reg = load_definitions('test_data/structure_with_padding.yaml')

    swp = reg.GetDefinitionByName('structure_with_padding')
    check("structure_with_padding defined", swp is not None)
    if swp and hasattr(swp, 'members') and swp.members:
        padding_member = swp.members[1]
        check("padding member type is padding",
              padding_member.TYPE_INDICATOR == defs.TYPE_INDICATOR_PADDING)

    sm = data_maps.StructureMap(swp)
    # uint16=0x0100(256LE) + 6 padding bytes
    byte_stream = bytes([0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07])
    struct = sm.MapByteStream(byte_stream)
    check("padding structure mapped", struct is not None)
    if struct:
        check("padding.data_size == 256 (0x0100 LE)",
              struct.data_size == 256, f"got {struct.data_size}")
        check("padding returns raw bytes after data_size",
              struct.padding == b'\x02\x03\x04\x05\x06\x07',
              f"got {repr(struct.padding)}")


# ---------------------------------------------------------------------------
# Part 4: Structure with sequence (structure_with_sequence.yaml)
# ---------------------------------------------------------------------------
def test_sequence():
    print("\n=== Part 4: Structure with Sequence ===")
    reg = load_definitions('test_data/structure_with_sequence.yaml')

    ext = reg.GetDefinitionByName('extension_block')
    check("extension_block defined", ext is not None)

    sm = data_maps.StructureMap(ext)
    # size=260 (0x0104 LE), then 256 data bytes
    byte_values = [0x04, 0x01, 0x00, 0x00]
    for v in range(256):
        byte_values.append(v)
    byte_stream = bytes(bytearray(byte_values))

    struct = sm.MapByteStream(byte_stream)
    check("extension_block mapped", struct is not None)
    if struct:
        check("extension_block.size == 260",
              struct.size == 260, f"got {struct.size}")
        check("extension_block.data[0] == 0",
              struct.data[0] == 0, f"got {struct.data[0]}")
        check("extension_block.data[-1] == 255",
              struct.data[-1] == 255, f"got {struct.data[-1]}")
        check("len(data) == 256",
              len(struct.data) == 256, f"got {len(struct.data)}")


# ---------------------------------------------------------------------------
# Part 5: Structure with union (structure_with_union.yaml)
# ---------------------------------------------------------------------------
def test_union():
    print("\n=== Part 5: Structure with Union ===")
    reg = load_definitions('test_data/structure_with_union.yaml')

    # Check basic types
    for name in ('uint32', 'float32', 'intfloat32'):
        d = reg.GetDefinitionByName(name)
        check(f"{name} defined", d is not None)

    intfloat = reg.GetDefinitionByName('intfloat32')
    check("intfloat32 TYPE_INDICATOR is structure",
          intfloat is not None and
          intfloat.TYPE_INDICATOR == defs.TYPE_INDICATOR_STRUCTURE)
    # Union as inner member type
    check("intfloat32 has members",
          intfloat and hasattr(intfloat, 'members') and intfloat.members)
    if intfloat and hasattr(intfloat, 'members') and intfloat.members:
        union_member = intfloat.members[0]
        check("inner member type is union",
              union_member.TYPE_INDICATOR == defs.TYPE_INDICATOR_UNION)
        if hasattr(union_member, 'members') and union_member.members:
            names = [m.member_data_type for m in union_member.members]
            check("union members reference uint32 and float32",
                  'uint32' in names and 'float32' in names,
                  f"got member_data_types={names}")
    else:
        check("cannot verify union members (intfloat32 has no members)", False)


# ---------------------------------------------------------------------------
# Part 6: Byte-level validation (integer<->byte mapping via struct format)
# ---------------------------------------------------------------------------
def test_format_strings():
    print("\n=== Part 6: Struct Format String Verification ===")
    reg = load_definitions('test_data/definitions/integers.yaml')

    checks = [
        ('int8',   'b'),
        ('int16',  'h'),
        ('int32',  'i'),
        ('int64',  'q'),
        ('uint8',  'B'),
        ('uint16', 'H'),
        ('uint32', 'I'),
        ('uint64', 'Q'),
    ]
    for name, expected_fmt in checks:
        d = reg.GetDefinitionByName(name)
        if d:
            im = data_maps.IntegerMap(d)
            fmt = im.GetStructFormatString()
            check(f"{name} format='{fmt}'",
                  fmt == expected_fmt,
                  f"expected '{expected_fmt}' got '{fmt}'")


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
def main():
    print("=" * 60)
    print("dtfabric Sample-Driven Validation")
    print("=" * 60)
    print(f"PYTHONPATH: {_BUILD_ROOT or 'not found'}")
    print(f"Archive dir: {ARCHIVE_DIR}")

    test_integer_definitions()
    test_structure()
    test_padding()
    test_sequence()
    test_union()
    test_format_strings()

    total = PASS + FAIL
    print(f"\n{'=' * 60}")
    print(f"Results: {PASS}/{total} passed, {FAIL}/{total} failed")
    print(f"{'=' * 60}")

    return 0 if FAIL == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
