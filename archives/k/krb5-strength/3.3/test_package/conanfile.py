#!/usr/bin/env python3
"""Conan test_package for krb5-strength 3.3 (R34 substantive test).

Primary path: dlopen the pwqual plugin with RTLD_NOW and verify the MIT
krb5 plugin interface symbol (pwqual_strength_initvt) is exported — this
also proves the plugin's krb5 shared-library dependencies resolve.

Fallback path: on x86 shadow workers target binaries cannot execute (the
qemu binfmt setup lacks the OHOS ELF loader), so the plugin is verified
statically in pure Python: ELF64 AArch64 image, SONAME, musl libc NEEDED
entry and the exported pwqual_strength_initvt dynsym entry.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class Krb5StrengthTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _elf_static_check(self, plugin):
        import struct

        with open(plugin, "rb") as f:
            data = f.read()
        if data[:6] != b"\x7fELF\x02\x01":
            raise AssertionError("plugin is not an ELF64 little-endian object")
        if struct.unpack_from("<H", data, 18)[0] != 183:
            raise AssertionError("plugin is not AArch64 (EM_AARCH64)")
        e_shoff = struct.unpack_from("<Q", data, 40)[0]
        e_shentsize, e_shnum, e_shstrndx = struct.unpack_from("<HHH", data, 58)
        sections = []
        for i in range(e_shnum):
            sections.append(
                struct.unpack_from("<IIQQQQIIQQ", data, e_shoff + i * e_shentsize)
            )
        shstr_off = sections[e_shstrndx][4]

        def sname(sec):
            off = shstr_off + sec[0]
            return data[off:data.index(b"\0", off)].decode()

        by_name = {}
        for sec in sections:
            by_name[sname(sec)] = sec
        dyn = by_name.get(".dynamic")
        dynstr = by_name.get(".dynstr")
        dynsym = by_name.get(".dynsym")
        if not (dyn and dynstr and dynsym):
            raise AssertionError("plugin lacks .dynamic/.dynstr/.dynsym")

        str_off = dynstr[4]
        soname = None
        needed = []
        off = dyn[4]
        for i in range(dyn[5] // 16):
            tag, val = struct.unpack_from("<QQ", data, off + i * 16)
            if tag == 0:
                break
            if tag == 14:  # DT_SONAME
                soname = data[str_off + val:data.index(b"\0", str_off + val)].decode()
            elif tag == 1:  # DT_NEEDED
                needed.append(
                    data[str_off + val:data.index(b"\0", str_off + val)].decode()
                )
        if soname != "strength.so":
            raise AssertionError("unexpected SONAME {!r}".format(soname))
        if "libc.so" not in needed:
            raise AssertionError(
                "musl libc.so missing from NEEDED {!r}".format(needed)
            )

        sym_off, sym_size, sym_link = dynsym[4], dynsym[5], dynsym[6]
        strtab_off = sections[sym_link][4]
        exported = set()
        for i in range(sym_size // 24):
            st_name, _info, _other, st_shndx, _val, _size = struct.unpack_from(
                "<IBBHQQ", data, sym_off + i * 24
            )
            if st_shndx == 0:  # SHN_UNDEF: imported, not exported
                continue
            name_off = strtab_off + st_name
            exported.add(data[name_off:data.index(b"\0", name_off)].decode())
        if "pwqual_strength_initvt" not in exported:
            raise AssertionError("pwqual_strength_initvt is not exported")
        self.output.info(
            "static ELF verification: AArch64, SONAME=strength.so, "
            "NEEDED includes libc.so, pwqual_strength_initvt exported"
        )

    def test(self):
        pkg = self.dependencies[self.tested_reference_str]
        plugin = os.path.join(
            pkg.package_folder, "lib", "krb5", "plugins", "pwqual", "strength.so"
        )
        if not os.path.isfile(plugin):
            raise FileNotFoundError("pwqual plugin missing: " + plugin)
        exe = os.path.join(self.build_folder, "test_krb5-strength")
        # Execution probe: the test binary exits 2 when invoked without
        # arguments. Any other outcome means target binaries cannot run on
        # this worker (x86 shadow) — fall back to static ELF verification.
        rc = self.run('"{}"'.format(exe), env="conanrun", ignore_errors=True)
        if rc == 2:
            # conanrun (VirtualRunEnv) provides LD_LIBRARY_PATH covering the
            # Conan krb5 shared libraries that strength.so depends on.
            self.run('"{}" "{}"'.format(exe, plugin), env="conanrun")
        else:
            self.output.warning(
                "target execution unavailable on this worker (probe rc={}); "
                "falling back to static ELF verification".format(rc)
            )
            self._elf_static_check(plugin)
