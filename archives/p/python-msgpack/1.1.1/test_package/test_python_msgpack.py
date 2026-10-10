#!/usr/bin/env python3
"""Consumer test for packaged python-msgpack 1.1.1 — real API (R34).

packb/unpackb roundtrips incl. the options cachecontrol's Serializer uses
(use_bin_type / raw / strict_map_key), plus pure-Python fallback assertion.
"""
import io
import sys

site = sys.argv[1]
if site not in sys.path:
    sys.path.insert(0, site)

import msgpack  # noqa: E402
import msgpack.fallback  # noqa: E402


def main():
    assert msgpack.version == (1, 1, 1), msgpack.version

    payload = {"str": "hello", "int": 42, "list": [1, 2, 3],
               "nested": {"a": True, "b": None}}
    blob = msgpack.packb(payload, use_bin_type=True)
    assert isinstance(blob, bytes)
    assert msgpack.unpackb(blob, raw=False) == payload

    # cachecontrol Serializer style: bin-typed bytes keys survive raw=False
    blob2 = msgpack.packb({b"k": b"v"}, use_bin_type=True)
    assert msgpack.unpackb(blob2, raw=False, strict_map_key=False) == \
        {b"k": b"v"}

    # Unpacker streaming API (used by cachecontrol deserialize path)
    unpacker = msgpack.Unpacker(io.BytesIO(blob), raw=False)
    assert unpacker.unpack() == payload

    # pure-Python fallback engine present and functional
    assert hasattr(msgpack.fallback, "Packer")
    fb = msgpack.fallback.Packer().pack(payload)
    assert msgpack.unpackb(fb, raw=False) == payload

    print("test_python_msgpack: OK (version, roundtrip, cachecontrol "
          "options, streaming unpacker, fallback engine)")


if __name__ == "__main__":
    main()
