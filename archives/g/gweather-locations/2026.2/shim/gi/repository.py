"""gi.repository shim — exposes a minimal GLib module.

Implements GLib.Variant serialisation (GVariant serialised format,
little-endian, normal form) for the subset of the type grammar used by
gweather-locations' gen_locations_variant.py:

    types: y b n q i u t x d s (tuples) {kv} (dict entry) aX (arrays)
    values: int / float / str / bool / tuple / list (dicts: list of 2-tuples)

Format rules implemented (GVariant Serialisation Format spec):
  - children of a container are aligned relative to the container start
  - tuples/dict entries: framing offsets for every non-fixed-size child
    except the last; arrays of non-fixed-size elements: one framing offset
    per element (including the last); offsets appended at the end, little
    endian, sized to the smallest of 1/2/4/8 bytes that can express the
    container size.
"""
import struct as _struct


class _ShimError(Exception):
    pass


def _align_up(pos, a):
    return (pos + a - 1) & ~(a - 1)


_SIMPLE_ALIGN = {"y": 1, "b": 1, "n": 2, "q": 2, "i": 4, "u": 4,
                 "x": 8, "t": 8, "d": 8, "s": 1, "o": 1, "g": 1}

_SIMPLE_FIXED = {"y": 1, "b": 1, "n": 2, "q": 2, "i": 4, "u": 4,
                 "x": 8, "t": 8, "d": 8}


def _parse_type(s, i):
    """Parse one complete type string starting at index i.

    Returns (type_string, next_index)."""
    c = s[i]
    if c == "a":
        et, j = _parse_type(s, i + 1)
        return "a" + et, j
    if c in "({":
        depth = 0
        j = i
        while j < len(s):
            if s[j] in "({":
                depth += 1
            elif s[j] in ")}":
                depth -= 1
                if depth == 0:
                    return s[i:j + 1], j + 1
            j += 1
        raise _ShimError("unbalanced container in type: %r" % s)
    if c in "ybnqiuxtdsog":
        return c, i + 1
    raise _ShimError("unsupported type char %r in %r" % (c, s))


def _split_children(body):
    """Split the inside of a tuple/dict-entry type string into child types."""
    children = []
    i = 0
    while i < len(body):
        t, i = _parse_type(body, i)
        children.append(t)
    return children


def _align_of(t):
    c = t[0]
    if c in _SIMPLE_ALIGN:
        return _SIMPLE_ALIGN[c]
    if c == "a":
        return _align_of(t[1:])
    if c == "h":
        return 4
    if c in "(v{":
        if c == "v":
            return 8
        return max(_align_of(ct) for ct in _split_children(t[1:-1]))
    raise _ShimError("unsupported type %r" % t)


def _fixed_size(t):
    """Return the fixed byte size of type t (size fully determined by the
    type), or None if variable-size. Arrays are always variable: their size
    depends on the element count, so parents need a framing offset for them;
    the array itself only needs internal offsets when its ELEMENT type is
    variable."""
    c = t[0]
    if c in _SIMPLE_FIXED:
        return _SIMPLE_FIXED[c]
    if c in "sog":
        return None
    if c == "a":
        return None
    if c == "h":
        return 4
    if c in "(v{":
        if c == "v":
            return None
        return _fixed_size_tuple(_split_children(t[1:-1]))
    raise _ShimError("unsupported type %r" % t)


def _fixed_size_tuple(children):
    """Fixed size of a tuple with alignment-aware packing, or None."""
    total = 0
    for ct in children:
        s = _fixed_size(ct)
        if s is None:
            return None
        total = _align_up(total, _align_of(ct)) + s
    return total


def _check(value, t):
    c = t[0]
    # PyGObject semantics: a nested GLib.Variant may be embedded where its
    # exact type is expected (gen_locations_variant.py relies on this).
    if isinstance(value, Variant):
        if value.get_type_string() != t:
            raise _ShimError("nested Variant type %s does not match %s"
                             % (value.get_type_string(), t))
        return
    if c in "ynqiuxt":
        if not isinstance(value, int) or isinstance(value, bool):
            raise _ShimError("type %s expects int, got %r" % (t, value))
        return
    if c == "d":
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise _ShimError("type d expects float, got %r" % (value,))
        return
    if c == "b":
        if not isinstance(value, bool):
            raise _ShimError("type b expects bool, got %r" % (value,))
        return
    if c in "sog":
        if not isinstance(value, str):
            raise _ShimError("type %s expects str, got %r" % (t, value))
        return
    if c == "a":
        if not isinstance(value, (list, tuple)):
            raise _ShimError("type %s expects list" % t)
        et = t[1:]
        if et[0] == "{":
            kt, vt = _split_children(et[1:-1])
            for pair in value:
                if not isinstance(pair, (list, tuple)) or len(pair) != 2:
                    raise _ShimError("dict entry must be a 2-tuple: %r" % (pair,))
                _check(pair[0], kt)
                _check(pair[1], vt)
        else:
            for v in value:
                _check(v, et)
        return
    if c == "(":
        children = _split_children(t[1:-1])
        if not isinstance(value, (list, tuple)) or len(value) != len(children):
            raise _ShimError("tuple %s expects %d children, got %r"
                             % (t, len(children), value))
        for cv, ct in zip(value, children):
            _check(cv, ct)
        return
    if c == "{":
        kt, vt = _split_children(t[1:-1])
        if not isinstance(value, (list, tuple)) or len(value) != 2:
            raise _ShimError("dict entry %s expects 2 children" % t)
        _check(value[0], kt)
        _check(value[1], vt)
        return
    raise _ShimError("unsupported type %r" % t)


def _append_offsets(data, ends):
    offsize = 1
    while True:
        total = len(data) + offsize * len(ends)
        if total <= (1 << (8 * offsize)) - 1 or offsize == 8:
            break
        offsize *= 2
    offs = b"".join(v.to_bytes(offsize, "little") for v in ends)
    return data + offs


def _ser(value, t):
    """Serialise value of type t to GVariant normal-form bytes."""
    if isinstance(value, Variant):
        return _ser(value._value, t)
    c = t[0]
    if c == "y":
        return _struct.pack("<B", value)
    if c == "b":
        return b"\x01" if value else b"\x00"
    if c == "n":
        return _struct.pack("<h", value)
    if c == "q":
        return _struct.pack("<H", value)
    if c == "i":
        return _struct.pack("<i", value)
    if c == "u":
        return _struct.pack("<I", value)
    if c == "x":
        return _struct.pack("<q", value)
    if c == "t":
        return _struct.pack("<Q", value)
    if c == "d":
        return _struct.pack("<d", value)
    if c in "sog":
        return value.encode("utf-8") + b"\x00"
    if c == "a":
        et = t[1:]
        elem_fixed = _fixed_size(et)
        ea = _align_of(et)
        data = bytearray()
        ends = []
        for v in value:
            eb = _ser(v, et)
            if elem_fixed is None or (len(eb) % ea) != 0:
                pos = _align_up(len(data), ea)
                data.extend(b"\x00" * (pos - len(data)))
            data.extend(eb)
            ends.append(len(data))
        if elem_fixed is None:
            if not ends:
                return b""
            data = _append_offsets(data, ends)
        return bytes(data)
    if c in "({":
        if c == "(":
            children = _split_children(t[1:-1])
            vals = list(value)
        else:  # dict entry '{kv}'
            kt, vt = _split_children(t[1:-1])
            children = [kt, vt]
            vals = [value[0], value[1]]
        if len(children) != len(vals):
            raise _ShimError("value/type mismatch for %s" % t)
        data = bytearray()
        offsets = []
        n = len(children)
        for idx, (ct, cv) in enumerate(zip(children, vals)):
            a = _align_of(ct)
            pos = _align_up(len(data), a)
            data.extend(b"\x00" * (pos - len(data)))
            data.extend(_ser(cv, ct))
            if _fixed_size(ct) is None and idx != n - 1:
                offsets.append(len(data))
        if offsets:
            # GVariant stores tuple framing offsets in REVERSE child order
            # (the first non-last child's offset is the last byte of the
            # container); array offsets stay in forward order.
            data = _append_offsets(data, offsets[::-1])
        return bytes(data)
    raise _ShimError("unsupported type %r" % t)


class Bytes:
    def __init__(self, data):
        self._data = bytes(data)

    def get_data(self):
        return self._data

    def get_size(self):
        return len(self._data)


class VariantType:
    def __init__(self, type_string):
        self.type_string = type_string


class Variant:
    def __init__(self, type_string, value):
        _check(value, type_string)
        self._type = type_string
        self._value = value

    def get_type_string(self):
        return self._type

    def print_(self, type_annotate=False):
        return repr((self._type, self._value))

    def get_data_as_bytes(self):
        return Bytes(_ser(self._value, self._type))

    def byteswap(self):
        raise _ShimError("byteswap not supported by shim (the generator only "
                         "byteswaps on big-endian hosts and discards the "
                         "result on little-endian)")


class GLib:
    Variant = Variant
    Bytes = Bytes
    VariantType = VariantType
