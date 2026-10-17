#!/usr/bin/env python3
"""bpack consumer test (R34): real API usage — descriptor + struct codec."""

import sys


def main():
    import bpack
    import bpack.st

    if bpack.__version__ != "1.3.0":
        print("FAIL: bpack version %r" % bpack.__version__, file=sys.stderr)
        return 1

    @bpack.st.decoder
    @bpack.descriptor(baseunits=bpack.EBaseUnits.BYTES)
    class Record:
        field_1: int = bpack.field(size=4, default=1)
        field_2: int = bpack.field(size=4, default=2)

    # 1. descriptor registered
    assert bpack.is_descriptor(Record), "Record is not a descriptor"
    print("check1 descriptor ok")

    # 2. calcsize: 2 x 4 bytes = 8
    size = bpack.calcsize(Record)
    assert size == 8, "calcsize=%r" % size
    print("check2 calcsize ok: %d" % size)

    # 3. decode known payload (little-endian native default)
    import struct

    payload = struct.pack("ii", 10, 20)
    rec = Record.frombytes(payload)
    assert (rec.field_1, rec.field_2) == (10, 20), "decode=%r" % (rec,)
    print("check3 decode ok: %r" % ((rec.field_1, rec.field_2),))

    # 4. encode roundtrip via struct backend
    @bpack.st.encoder
    @bpack.descriptor(baseunits=bpack.EBaseUnits.BYTES)
    class WRecord:
        field_1: int = bpack.field(size=4, default=7)
        field_2: int = bpack.field(size=4, default=9)

    data = WRecord().tobytes()
    assert data == struct.pack("ii", 7, 9), "encode=%r" % (data,)
    print("check4 encode ok")

    print("OK: bpack 1.3.0 struct codec roundtrip ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
