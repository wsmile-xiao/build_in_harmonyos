from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy, save, load
from conan.tools.cmake import cmake_layout
import glob
import os

required_conan_version = ">=2.0"

# The six CRC lookup tables that upstream regenerates by running the
# build-time generator crc-gentab (Makefile rules `crc/*_table.c: crc-gentab`).
# Argument strings are verbatim from those Makefile rules.
CRC_TABLES = [
    ("crc16_arc", "crc16_arc 16 0x8005 reflected"),
    ("crc16_ccitt", "crc16_ccitt 16 0x1021 normal"),
    ("crc16_xmodem", "crc16_xmodem 16 0x8408 reflected"),
    ("crc32", "crc32 32 0x04C11DB7 reflected"),
    ("crc32c", "crc32c 32 0x1EDC6F41 reflected"),
    ("crc64", "crc64 64 0x42F0E1EBA9EA3693 normal"),
]


class BglibsConan(ConanFile):
    name = "bglibs"
    version = "2.04"
    description = (
        "Bruce Guenter's base function library collection (str, fmt, iobuf, "
        "adt, cdb, crc, crypto, net, unix helpers) used by cvm, vmailmgr "
        "and ucspi tools"
    )
    license = "LGPL-2.1-or-later"
    homepage = "https://untroubled.org/bglibs"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    # libtool builds both static and PIC/shared variants into .libs/; the
    # default static layout matches the djb ecosystem (cvm & friends link
    # bglibs statically).
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        # The spac Makefile drives libtool (ltcompile/ltload/makeshlib);
        # CI workers ship no system libtool (cliquer precedent).
        self.tool_requires("libtool/2.5.4")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _cc(self):
        # R33: the compiler comes from the Conan profile, never a bare env var.
        comp_exe = self.conf.get("tools.build:compiler_executables", default={})
        cc = (comp_exe or {}).get("c")
        return cc or "cc"

    def _detect_native_cc(self, src):
        # crc-gentab must run on the build machine to generate the CRC lookup
        # tables; an aarch64 OHOS binary cannot execute on an x86 CI worker.
        # Resolve a machine-resident compiler by standard name via PATH.
        script = (
            'for c in gcc clang cc; do '
            'if $c --version >/dev/null 2>&1; then printf %s "$c" > native-cc.txt; '
            "exit 0; fi; done; exit 1"
        )
        save(self, os.path.join(src, "detect-native-cc.sh"), script + "\n")
        self.run("sh detect-native-cc.sh", cwd=src)
        cc = load(self, os.path.join(src, "native-cc.txt")).strip()
        if not cc:
            raise ConanException("no native bootstrap compiler found for crc-gentab")
        return cc

    def _write_djb_conf(self, cc):
        # bglibs (spac) bakes the first line of conf-cc/conf-ld into the
        # generated compile/ltcompile/load/makeshlib wrapper scripts, so the
        # concrete compiler path is written into the conf files.
        opt = "-Os -g" if self.settings.build_type == "Release" else "-O0 -g"
        save(self, os.path.join(self.source_folder, "conf-cc"),
             "{} -W -Wall -Wshadow -Wno-unused-result {}\n".format(cc, opt))
        save(self, os.path.join(self.source_folder, "conf-ld"), cc + " -g\n")
        # libtool -rpath for the shared variant; point at a private staging
        # dir so no system path leaks into build outputs.
        save(self, os.path.join(self.source_folder, "conf-lib"),
             os.path.join(self.build_folder, "djb-stage-lib") + "\n")

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder
        # ---- Phase 1: native bootstrap of the CRC table generator ----
        native_cc = self._detect_native_cc(src)
        self._write_djb_conf(native_cc)
        self.run("make crc-gentab", cwd=src)
        for name, gen_args in CRC_TABLES:
            self.run("./crc-gentab {} > crc/{}_table.c".format(gen_args, name), cwd=src)
        # ---- Phase 2: target build with the profile toolchain ----
        self._write_djb_conf(self._cc())
        # Drop every native intermediate (the wrapper scripts regenerate from
        # the rewritten conf-cc; sysdeps.h/dl.lib/rt.lib must be re-probed for
        # the target), but keep crc-gentab and the generated tables.
        self.run(
            "rm -f sysdeps.h dl.lib rt.lib compile load ltcompile makeshlib "
            "detect-native-cc.sh native-cc.txt *.o */*.o *.lo */*.lo && "
            "rm -rf .libs",
            cwd=src,
        )
        # The tables must look newer than crc-gentab so the (cross) rebuild
        # never tries to re-run the generator.
        self.run(
            "touch " + " ".join("crc/{}_table.c".format(n) for n, _ in CRC_TABLES),
            cwd=src,
        )
        # "all" also runs selftests.sh; only build sysdeps.h + libraries.
        # This is a library package: the upstream programs (bg-installer,
        # cli-generate) and man pages are deliberately not built (they would
        # additionally require the perl-based cli-generate generator).
        self.run("make sysdeps.h libraries -j2", cwd=src)

    def package(self):
        src = self.source_folder
        inc = os.path.join(self.package_folder, "include")
        # Public headers follow the upstream INSTHIER layout:
        # include/*.h -> <prefix>/include/bglibs/, pwcmp/ and vmailmgr/
        # submodule headers into their own directories.
        copy(self, "*.h", os.path.join(src, "include"), os.path.join(inc, "bglibs"))
        for h in ("client.h", "hex.h", "module.h"):
            copy(self, h, os.path.join(src, "pwcmp"), os.path.join(inc, "pwcmp"))
        for h in ("client.h", "vpwentry.h"):
            copy(self, h, os.path.join(src, "vmailmgr"), os.path.join(inc, "vmailmgr"))
        # Generated headers that INSTHIER installs alongside include/*.h
        # (sysdeps.h is required by the public headers: __DEPRECATED__ etc).
        for h in ("sysdeps.h", "systime.h", "uintnn.h", "uint16.h", "uint32.h", "uint64.h"):
            copy(self, h, src, os.path.join(inc, "bglibs"))
        # Static archives: libbg via libtool (.libs/libbg.a) and the four
        # companion libs also produced as libtool archives by makeshlib.
        lib = os.path.join(self.package_folder, "lib")
        for a in ("libbg.a", "libbg-cli.a", "libpwcmp.a", "libpwcmp-module.a", "libvmailmgr.a"):
            copy(self, a, os.path.join(src, ".libs"), lib)
        if self.options.shared:
            # Copy full-version SONAME files (libbg.so.2.0.0 ...) and create
            # the dev symlinks (libbg.so.2, libbg.so); HMDFS forbids
            # overwriting links, so remove before creating.
            for full in sorted(glob.glob(os.path.join(src, ".libs", "lib*.so.*.*"))):
                copy(self, os.path.basename(full), os.path.join(src, ".libs"), lib)
            for full in sorted(glob.glob(os.path.join(lib, "lib*.so.*.*"))):
                name = os.path.basename(full)                # libbg.so.2.0.0
                soname = name.rsplit(".", 1)[0]              # libbg.so.2
                devname = soname.rsplit(".", 1)[0]           # libbg.so
                for link in (soname, devname):
                    target = os.path.join(lib, link)
                    if os.path.lexists(target):
                        os.remove(target)
                    os.symlink(name, target)
        # Library package: upstream bootstrap/dev tools (bg-installer,
        # cli-generate, crc-gentab) and man pages are not part of the library
        # API and are intentionally not packaged (no commands.json needed).

    def package_info(self):
        self.cpp_info.includedirs = ["include"]  # consumers: #include <bglibs/str.h>
        # Link order: dependents before providers; bg is the base library.
        self.cpp_info.libs = ["bg-cli", "pwcmp-module", "pwcmp", "vmailmgr", "bg"]
