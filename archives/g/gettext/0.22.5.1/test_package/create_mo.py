import os
import struct
import sys


catalog = {
    "": "Content-Type: text/plain; charset=UTF-8\nPlural-Forms: nplurals=2; plural=(n != 1);\n",
    "apple\0apples": "苹果\0苹果们",
    "hello": "你好",
}
items = sorted((key.encode("utf-8"), value.encode("utf-8")) for key, value in catalog.items())
count = len(items)
original_offset = 28
translation_offset = original_offset + count * 8
string_offset = translation_offset + count * 8
originals = b""
translations = b""
original_table = []
translation_table = []

for original, translation in items:
    original_table.append((len(original), string_offset + len(originals)))
    originals += original + b"\0"

translation_string_offset = string_offset + len(originals)
for original, translation in items:
    translation_table.append((len(translation), translation_string_offset + len(translations)))
    translations += translation + b"\0"

data = struct.pack("<7I", 0x950412DE, 0, count, original_offset, translation_offset, 0, 0)
data += b"".join(struct.pack("<2I", *entry) for entry in original_table)
data += b"".join(struct.pack("<2I", *entry) for entry in translation_table)
data += originals + translations

output = sys.argv[1]
os.makedirs(os.path.dirname(output), exist_ok=True)
with open(output, "wb") as stream:
    stream.write(data)
