#!/usr/bin/env python3
"""Verify the installed libkkc-data model files.

Model generation is deterministic, so every shipped file must match the
reference exactly in size and SHA256.
"""
import hashlib
import json
import os
import sys

EXPECTED = {
    "data.input": (269624, "5E3CBF0E40AEB01692A66244E08A237148C5FF0FF41EBE4ECB6D6308C99F997A"),
    "data.1gram.index": (1167040, "30276087EAA39109DAB10526C3FF18D20724B286C8618D4B7B6B70A7B605BA7A"),
    "data.1gram": (709998, "9103A8156DE0D7D94D5DB59AAA49F44101242F4F16409AF125DE11B8AEF302B9"),
    "data.2gram": (9304968, "7FC84A2EC66846A7F557676C67BAE686BC31131D6081EF7FDC25789CCCE2AEAE"),
    "data.2gram.filter": (643968, "642F7F10E52F000A54216EAA97084F77F5C0EF75E5D564B89D312B5AAAAA6CCA"),
    "data.3gram": (17768780, "901D447EC7564EE21243444557784ADD17D83E4AE0EC8929C24261B3A4F5C3E1"),
    "data.3gram.filter": (1475666, "32492D9A8832E7AFC9D1F0A7501B2545D3AE33368B6EF7027C27883C1E0C476C"),
    "metadata.json": (102, "CFE7E8F16A19BEEAB0AA61FB8DF83517CA50BCE5C70331286C6A3596E12CAB07"),
}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def main():
    if len(sys.argv) != 2:
        sys.exit("usage: test_verify.py <package_root>")
    root = sys.argv[1]
    models = os.path.join(root, "lib", "libkkc", "models", "sorted3")
    if not os.path.isdir(models):
        sys.exit("ERROR: models dir not found: %s" % models)

    checked = 0
    for name, (size, digest) in sorted(EXPECTED.items()):
        path = os.path.join(models, name)
        if not os.path.isfile(path):
            sys.exit("ERROR: missing model file: %s" % path)
        actual_size = os.path.getsize(path)
        if actual_size != size:
            sys.exit("ERROR: %s size mismatch: got %d, expected %d"
                     % (name, actual_size, size))
        actual_digest = sha256(path)
        if actual_digest != digest:
            sys.exit("ERROR: %s sha256 mismatch:\n  got      %s\n  expected %s"
                     % (name, actual_digest, digest))
        checked += 1

    with open(os.path.join(models, "metadata.json"), "r", encoding="utf-8") as f:
        meta = json.load(f)
    if meta.get("type") != "sorted3":
        sys.exit("ERROR: unexpected metadata type: %r" % meta)
    checked += 1

    print("OK: %d model files verified (size + sha256) and metadata parsed"
          % (checked - 1))


if __name__ == "__main__":
    main()