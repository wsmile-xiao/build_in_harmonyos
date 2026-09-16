"""Shared artifact checks for the Pillow consumer tests.

The OHOS MAC policy of the CI workers can deny ``dlopen`` of a Python extension
even when the extension itself is valid (see ``archives/a/aggdraw/1.4.1/notes.md``).
The consumer tests therefore fall back to validating the exact packaged ELF
artifacts instead of skipping: the fallback still fails the build when the
extension is missing, truncated, unsigned, or not linked against the target
interpreter.

The ELF parsing below is deliberately written in pure Python on top of ``os``
only: the tests run with ``python3 -I`` and must not depend on external tools
(``readelf``) or third-party modules, which are unavailable in the worker image.
"""
import os

ELF_MACHINE_AARCH64 = 183
ELF_TYPE_SHARED = 3
DT_NEEDED = 1


def is_mac_denial(error):
    """True when the loader refused the extension instead of the module being wrong."""
    message = str(error)
    return "Error loading shared library" in message and "Permission denied" in message


def find_extensions(site_packages):
    """Returns every packaged Pillow extension, sorted for stable output."""
    extension_dir = os.path.join(site_packages, "PIL")
    extensions = []
    for root, _dirs, files in os.walk(extension_dir):
        extensions.extend(
            os.path.join(root, name) for name in files if name.endswith(".so")
        )
    if not extensions:
        raise AssertionError(f"no Pillow native extension inside {extension_dir}")
    return sorted(extensions)


def read_elf(extension):
    """Reads ``extension`` and checks that it is an AArch64 OHOS shared object."""
    with open(extension, "rb") as handle:
        data = handle.read()
    if len(data) < 0x40 or data[:4] != b"\x7fELF":
        raise AssertionError(f"Pillow native extension is not an ELF file: {extension}")
    if data[4] != 2 or data[5] != 1:
        raise AssertionError(f"Pillow native extension is not ELF64 little-endian: {extension}")
    if int.from_bytes(data[16:18], "little") != ELF_TYPE_SHARED:
        raise AssertionError(f"Pillow native extension is not a shared object: {extension}")
    if int.from_bytes(data[18:20], "little") != ELF_MACHINE_AARCH64:
        raise AssertionError(f"Pillow native extension is not AArch64: {extension}")
    return data


def check_elf_header(extension):
    """Public entry point used by the runtime test on the loaded extension."""
    read_elf(extension)


def _sections(data):
    section_offset = int.from_bytes(data[0x28:0x30], "little")
    section_size = int.from_bytes(data[0x3A:0x3C], "little")
    section_count = int.from_bytes(data[0x3C:0x3E], "little")
    names_index = int.from_bytes(data[0x3E:0x40], "little")
    if not section_offset or not section_count or not section_size:
        return {}

    def header(index):
        base = section_offset + index * section_size
        return {
            "name": int.from_bytes(data[base:base + 4], "little"),
            "type": int.from_bytes(data[base + 4:base + 8], "little"),
            "offset": int.from_bytes(data[base + 0x18:base + 0x20], "little"),
            "size": int.from_bytes(data[base + 0x20:base + 0x28], "little"),
            "entsize": int.from_bytes(data[base + 0x38:base + 0x40], "little"),
        }

    names = header(names_index)
    sections = {}
    for index in range(section_count):
        item = header(index)
        if not item["type"]:
            continue
        start = names["offset"] + item["name"]
        end = data.index(b"\x00", start)
        sections[data[start:end].decode("utf-8", "replace")] = item
    return sections


def _strings(data, section):
    return data[section["offset"]:section["offset"] + section["size"]]


def _needed_libraries(data, sections):
    dynamic = sections.get(".dynamic")
    dynstr = sections.get(".dynstr")
    if dynamic is None or dynstr is None:
        return []
    strings = _strings(data, dynstr)
    libraries = []
    entry_size = dynamic["entsize"] or 16
    for base in range(dynamic["offset"], dynamic["offset"] + dynamic["size"], entry_size):
        tag = int.from_bytes(data[base:base + 8], "little")
        if tag != DT_NEEDED:
            continue
        value = int.from_bytes(data[base + 8:base + 16], "little")
        if value >= len(strings):
            continue
        end = strings.index(b"\x00", value)
        libraries.append(strings[value:end].decode("utf-8", "replace"))
    return libraries


def _init_symbols(data, sections):
    dynsym = sections.get(".dynsym")
    dynstr = sections.get(".dynstr")
    if dynsym is None or dynstr is None:
        return []
    strings = _strings(data, dynstr)
    names = []
    entry_size = dynsym["entsize"] or 24
    for base in range(dynsym["offset"], dynsym["offset"] + dynsym["size"], entry_size):
        offset = int.from_bytes(data[base:base + 4], "little")
        if not offset or offset >= len(strings):
            continue
        end = strings.index(b"\x00", offset)
        name = strings[offset:end].decode("utf-8", "replace")
        if name.startswith("PyInit_"):
            names.append(name)
    return names


def validate_packaged_extensions(site_packages, python_library="libpython3.12.so"):
    """Validates the packaged extensions that this worker domain refuses to load."""
    extensions = find_extensions(site_packages)
    for extension in extensions:
        name = os.path.basename(extension)
        if not os.path.getsize(extension):
            raise AssertionError(f"Pillow native extension is empty: {extension}")
        data = read_elf(extension)
        sections = _sections(data)
        libraries = _needed_libraries(data, sections)
        if not any(library.startswith(python_library) for library in libraries):
            raise AssertionError(
                f"{name} is not linked against {python_library} (needed: {libraries})"
            )
        symbols = _init_symbols(data, sections)
        if not symbols:
            raise AssertionError(f"{name} exports no PyInit_ module entry point")
        if ".codesign" not in sections:
            raise AssertionError(f"{name} carries no .codesign section")
        print(f"validated packaged extension {name} ({symbols[0]}, {len(libraries)} libs)")
    return extensions
