#!/usr/bin/env python3
"""Conan recipe for AspectC++ 2.5 (ac++ / ag++) on HarmonyOS aarch64.

AspectC++ is a source-to-source weaver/compiler implemented on top of the
Clang C++ front-end.  Its build needs a full clang/LLVM 18 static library
set (libclangSema.a, libclangFrontend.a, ...) which the OHOS SDK does not
ship (SDK only has clang 15.0.4 + libclang.so, no static libs).

Upstream ships neither a woven-Puma source release for 2.5 nor prebuilt
binaries for aarch64 Linux, so a plain `make -C Puma` / `make -C
AspectC++ FRONTEND=Clang` bootstrap deadlocks.  This recipe closes the gap:

  1. Fetch a musl aarch64 clang/LLVM 18.1.8 static library set from the
     Alpine 3.21 package repository (clang18-static, llvm18-static).
  2. Build Puma in MINI=1 mode -> libMiniPuma.a (no aspect weaving
     required, so no ac++/ag++ bootstrap is needed for this step).
  3. Build the ac++ driver with FRONTEND=Clang, linking libMiniPuma plus
     the fetched clang/LLVM static libs.
  4. Build the ag++ weaver driver on top of libMiniPuma.

All C++ is compiled with the libstdc++ ABI (Alpine's libstdc++-dev static
archive) so that the fetched clang/LLVM objects (built against libstdc++)
and our own objects share one C++ ABI; the OHOS SDK default (libc++) is
incompatible with those objects.
"""

import os
import shlex
import shutil
import subprocess
import tarfile
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    download,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class AspectCppConan(ConanFile):
    name = "aspectc"
    version = "2.5"
    description = "AspectC++ 2.5 source-to-source weaver / compiler (ac++, ag++)"
    license = "GPL-2.0-or-later"
    homepage = "https://www.aspectc.org"
    url = "https://www.aspectc.org"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    _clang_version = "18.1.8"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os != "OHOS" or self.settings.arch != "armv8":
            raise ConanInvalidConfiguration(
                "aspectc 2.5 currently supports only OHOS armv8"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        src = self.conan_data["sources"]
        # Upstream ships ac-2.5.tar.gz as bzip2 despite the .tar.gz name;
        # conan's get() would mis-detect by extension, so download the raw
        # bytes and let tarfile sniff the real compression.  The archive has
        # a single top-level "aspectc++" dir; strip it.
        ac = src["aspectc"]
        archive = Path(self.source_folder) / ac["filename"]
        if str(ac["url"]).startswith("file://"):
            shutil.copy2(Path(ac["url"].removeprefix("file://")), archive)
        else:
            download(self, ac["url"], ac["filename"], sha256=ac["sha256"])
        # Extract into a scratch dir, then move the tarball's single
        # top-level "aspectc++" dir's contents up.  This must NOT extract
        # straight into source_folder and move from there: OHOS' filesystem
        # is case-insensitive, so "aspectc++" (the unpack dir) and the
        # "AspectC++" subdir collide and shutil.move would fail.  Use a
        # dot-named scratch dir inside source_folder (build_folder is not
        # set during source()).
        scratch = Path(self.source_folder) / ".ac_extract"
        with tarfile.open(str(archive), "r:*") as handle:
            handle.extractall(str(scratch), filter="data")
        top = scratch / "aspectc++"
        if top.is_dir():
            for item in top.iterdir():
                shutil.move(str(item), self.source_folder)
            shutil.rmtree(scratch)
        self._fetch_alpine_toolchain(src)
        apply_conandata_patches(self)

    # ------------------------------------------------------------------ #
    #  Toolchain provisioning                                            #
    # ------------------------------------------------------------------ #

    def _fetch_alpine_toolchain(self, src):
        """Download + extract the Alpine aarch64 musl clang/LLVM 18.1.8
        static library set, libstdc++, zstd and libxml2 headers into the
        source tree under a local prefix."""
        tc = Path(self.source_folder) / ".ohos-toolchain"
        for key in (
            "clang18-static",
            "llvm18-static",
            "clang18-dev",
            "llvm18-dev",
            "libstdcxx-dev",
            "zstd-static",
            "libxml2-dev",
        ):
            entry = src[key]
            archive = Path(self.source_folder) / entry["filename"]
            if str(entry["url"]).startswith("file://"):
                shutil.copy2(Path(entry["url"].removeprefix("file://")), archive)
            else:
                # download() + tarfile (not get()): Alpine .apk files are
                # gzip-compressed tarballs, but conan's get() does not know
                # the .apk extension and would try to unzip them as a plain
                # zip, failing with "File is not a zip file".
                download(self, entry["url"], entry["filename"], sha256=entry["sha256"])
            with tarfile.open(str(archive), "r:*") as handle:
                handle.extractall(str(tc), filter="data")

    # ------------------------------------------------------------------ #
    #  Build                                                             #
    # ------------------------------------------------------------------ #

    def _prep_toolchain(self):
        """Stage the fetched Alpine static libs + headers into one prefix,
        and emit an llvm-config shim and a secure_getenv stub (musl on
        OHOS lacks glibc's secure_getenv)."""
        tc = Path(self.source_folder) / ".ohos-toolchain"
        prefix = Path(self.build_folder) / "llvm18"
        (prefix / "lib").mkdir(parents=True, exist_ok=True)
        (prefix / "include").mkdir(parents=True, exist_ok=True)
        libs = 0
        headers = 0
        for libdir in tc.rglob("usr/lib/llvm18/lib"):
            for archive in libdir.glob("*.a"):
                shutil.copy2(archive, prefix / "lib")
                libs += 1
        # Alpine also installs libstdc++.a under /usr/lib
        for libstdcxx in tc.rglob("usr/lib/libstdc++.a"):
            shutil.copy2(libstdcxx, prefix / "lib")
        for includedir in tc.rglob("usr/lib/llvm18/include"):
            for header in includedir.rglob("*"):
                if header.is_file():
                    rel = header.relative_to(includedir)
                    target = prefix / "include" / rel
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(header, target)
                    headers += 1
        for zstd in tc.rglob("usr/lib/libzstd.a"):
            shutil.copy2(zstd, prefix / "lib")
        # aspectc's Makefile links -latomic (a gcc workaround); aarch64
        # implements the atomics inline so an empty archive suffices.
        atomic_cc = Path(self.build_folder) / "atomic_dummy.c"
        atomic_cc.write_text("int __aspectc_atomic_dummy;\n", encoding="utf-8")
        atomic_obj = Path(self.build_folder) / "atomic_dummy.o"
        self.run(f"{self._cxx()} -c {atomic_cc} -o {atomic_obj}")
        self.run(f"ar rcs {prefix / 'lib' / 'libatomic.a'} {atomic_obj}")
        # libxml2 headers (only the include tree; linking uses hnp libxml2)
        for xmlinc in tc.rglob("usr/include/libxml2"):
            for header in xmlinc.rglob("*"):
                if header.is_file():
                    rel = header.relative_to(xmlinc)
                    target = prefix / "include" / "libxml2" / rel
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(header, target)
                    headers += 1
        self.output.info(f"staged {libs} static libs + {headers} headers into {prefix}")

        # llvm-config shim: aspectc's Makefile asks for version/cppflags/
        # libs via $(LLVMCONF).  The Alpine binary is a dynamic musl ELF
        # that cannot exec on OHOS, so emit a shell shim instead.
        bindir = prefix / "bin"
        bindir.mkdir(parents=True, exist_ok=True)
        llvm_config = bindir / "llvm-config"
        llvm_config.write_text(
            "#!/bin/sh\n"
            f'DIR={prefix}\n'
            'case "$1" in\n'
            '  --version) echo "18.1.8";;\n'
            f'  --cppflags) echo "-I$DIR/include";;\n'
            '  --ldflags) echo "-L$DIR/lib";;\n'
            '  --libdir) echo "$DIR/lib";;\n'
            '  --libs|--system-libs)\n'
            '     libs=""\n'
            '     for f in "$DIR"/lib/libclang*.a "$DIR"/lib/libLLVM*.a; do\n'
            '       b=$(basename "$f" .a); libs="$libs -l${b#lib}"\n'
            '     done\n'
            '     echo "-L$DIR/lib -Wl,--start-group $libs -Wl,--end-group -L$DIR/lib -lstdc++ -latomic -lpthread -lz -lzstd -ldl -lm"\n'
            '     ;;\n'
            '  *) echo "$1: unknown" >&2; exit 1;;\n'
            'esac\n',
            encoding="utf-8",
        )
        os.chmod(llvm_config, 0o755)

        # xml2-config shim: point at OHOS-provided libxml2 runtime.
        xml2_config = bindir / "xml2-config"
        xml2_config.write_text(
            "#!/bin/sh\n"
            'D=/data/service/hnp/libxml2.org/libxml2_2.11.9\n'
            f'H={prefix}/include/libxml2\n'
            'case "$1" in\n'
            '  --cflags) echo "-I$H";;\n'
            '  --libs) echo "-L$D/lib -lxml2";;\n'
            '  --version) echo "2.11.9";;\n'
            '  *) exit 1;;\n'
            'esac\n',
            encoding="utf-8",
        )
        os.chmod(xml2_config, 0o755)

        # secure_getenv shim object (glibc extension absent in OHOS musl).
        stub = Path(self.build_folder) / "secure_getenv_stub.cc"
        stub.write_text(
            "#include <stdlib.h>\n"
            'extern "C" char *secure_getenv(const char *name) { return getenv(name); }\n',
            encoding="utf-8",
        )
        self.run(f"{self._cxx()} -c {stub} -o {stub.with_suffix('.o')}")

        # CXX link-wrapper: aspectc's own LDFLAGS put -lstdc++ (from
        # llvm-config --libs) BEFORE the libacmodel/libMiniPuma archives it
        # appends afterwards, so lld's single scan never back-fills the
        # libstdc++ symbols those archives need.  Appending libstdc++.a +
        # the secure_getenv stub at the very end of every *link* fixes it.
        # -nostdlib++ stops the clang++ driver from additionally pulling in
        # the SDK's libc++/libc++abi, which would collide with libstdc++.a
        # (duplicate __cxxabiv1 symbols).  Compile-only invocations pass
        # through untouched.  A link is detected by the --start-group that
        # aspectc's --libs output always contains (a plain `-c -o foo.o`
        # compile never has one).
        wrapper = bindir / "cxx-link-wrapper"
        wrapper.write_text(
            "#!/bin/sh\n"
            'case " $* " in\n'
            '  *--start-group*)\n'
            f'    exec {self._cxx()} -nostdlib++ "$@" {prefix / "lib" / "libstdc++.a"} {stub.with_suffix(".o")};;\n'
            '  *)\n'
            f'    exec {self._cxx()} "$@";;\n'
            'esac\n',
            encoding="utf-8",
        )
        os.chmod(wrapper, 0o755)
        self.output.info(f"staged link wrapper at {wrapper}")
        return prefix

    def _cxx(self):
        execs = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        return execs.get("cpp") or "clang++"

    def _stdcxx_flags(self):
        """Flags to compile with the libstdc++ ABI instead of the SDK's
        libc++ (the fetched clang/LLVM objects use libstdc++)."""
        tc = Path(self.source_folder) / ".ohos-toolchain"
        candidates = sorted(tc.rglob("usr/include/c++/*"), key=lambda p: str(p))
        inc_root = None
        for path in candidates:
            if (path / "cstddef").exists():
                inc_root = path
                break
        if inc_root is None:
            raise ConanInvalidConfiguration(
                "libstdc++ headers not found in staged Alpine toolchain"
            )
        triples = sorted(
            d.name
            for d in inc_root.iterdir()
            if d.is_dir() and not d.name in ("backward", "ext", "tr1", "debug", "parallel")
        )
        flags = ["-nostdinc++"]
        flags.append(f"-isystem {inc_root}")
        for triple in triples:
            flags.append(f"-isystem {inc_root / triple}")
        if (inc_root / "backward").is_dir():
            flags.append(f"-isystem {inc_root / 'backward'}")
        return " ".join(flags)

    def _run_make(self, directory, *targets, extra=None):
        prefix = Path(self.build_folder) / "llvm18"
        std_flags = self._stdcxx_flags()
        libxml_inc = "-I" + str(prefix / "include" / "libxml2")
        # CXX goes through the link-wrapper so every link appends
        # libstdc++.a + the secure_getenv stub at the end (see
        # _prep_toolchain).
        cxx = (
            f"{prefix / 'bin' / 'cxx-link-wrapper'} {std_flags} {libxml_inc} -DMAX_PATH=4096"
        )
        command = ["make", "-C", directory]
        command.extend(targets)
        command.extend(
            [
                "TARGET=linux-release",
                "SHARED=1",
                f'CXX="{cxx}"',
                f'CC="{self._cxx()} -DMAX_PATH=4096"',
                f"LLVMCONF={prefix / 'bin' / 'llvm-config'}",
                f"XML2CONF={prefix / 'bin' / 'xml2-config'}",
            ]
        )
        if extra:
            command.extend(extra)
        # Run from the source tree: the sub-makefiles resolve each other via
        # relative paths (../Puma, ../AspectC++, ../acmodel).  Do NOT pass
        # env as a KEY=VALUE list here: Conan 2's self.run() treats the env
        # argument as environment *file* names (e.g. "conanbuild"), so a
        # KEY=VALUE list is silently dropped AND prevents the conanbuild
        # environment (profile [buildenv], notably LD_LIBRARY_PATH pointing
        # at the SDK llvm/lib for lld's libxml2.so.16) from being loaded.
        # Rely on the default "conanbuild" env instead.
        self.run(" ".join(command), cwd=self.source_folder)

    def build(self):
        prefix = self._prep_toolchain()
        # 1) Puma MINI=1 -> libMiniPuma.a (no aspect weaving bootstrap)
        self._run_make("Puma", "MINI=1")
        # 2) ac++ driver (Clang front-end)
        self._run_make("AspectC++", "FRONTEND=Clang")
        # 3) ag++ weaver driver
        std_flags = self._stdcxx_flags()
        stub = Path(self.build_folder) / "secure_getenv_stub.o"
        ag_ldflags = (
            "-Wl,-Bstatic -L../Puma/lib/linux-release -lMiniPuma -Wl,-Bdynamic "
            f"{prefix / 'lib' / 'libstdc++.a'} {stub} "
            f"-L{prefix / 'lib'} -latomic"
        )
        self._run_make(
            "Ag++",
            extra=[f'LDFLAGS="{ag_ldflags}"'],
        )

    # ------------------------------------------------------------------ #
    #  Package                                                           #
    # ------------------------------------------------------------------ #

    def package(self):
        bin_src = os.path.join(self.source_folder, "AspectC++", "bin", "linux-release")
        copy(self, "ac++", src=bin_src, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "ag++", src=bin_src, dst=os.path.join(self.package_folder, "bin"))
        # The ac++/ag++ drivers are OHOS ELF tools and must be signed
        # (plus get a RUNPATH to the OHOS libxml2/libz/libc++ runtime).
        self._make_elf_tool_runnable(
            os.path.join(self.package_folder, "bin", "ac++")
        )
        self._make_elf_tool_runnable(
            os.path.join(self.package_folder, "bin", "ag++")
        )
        # g++/gcc shims: ag++ spawns a backend compiler named "g++" to
        # compile the woven .acc files; OHOS has no g++ so point at the
        # SDK clang++ with the same libstdc++ flags used for the build.
        self._install_compiler_shims()
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def _make_elf_tool_runnable(self, tool):
        # OHOS requires .codesign to exec (see astap/evince precedents);
        # RUNPATH must be set before signing (signing then editing breaks
        # .codesign).  Use $ORIGIN-free absolute hnp paths.
        libxml = "/data/service/hnp/libxml2.org/libxml2_2.11.9/lib"
        libcxx = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/aarch64-linux-ohos"
        self.run(f'patchelf --set-rpath "{libxml}:{libcxx}" "{tool}"')
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        self.run(f'{objcopy} --remove-section .codesign "{tool}" 2>/dev/null || true')
        signed = tool + ".signed"
        self.run(f'{signer} sign -inFile "{tool}" -outFile "{signed}" -selfSign 1')
        if os.path.isfile(signed):
            os.replace(signed, tool)
        os.chmod(tool, 0o755)

    def _install_compiler_shims(self):
        bindir = os.path.join(self.package_folder, "bin")
        tc = Path(self.source_folder) / ".ohos-toolchain"
        std_flags = self._stdcxx_flags()
        stub = Path(self.build_folder) / "secure_getenv_stub.o"
        gxx_shim = os.path.join(bindir, "g++")
        with open(gxx_shim, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(
                "#!/bin/sh\n"
                f"exec {self._cxx()} -stdlib=libc++ {std_flags} {stub} {tc}/usr/lib/libstdc++.a \"$@\"\n"
            )
        os.chmod(gxx_shim, 0o755)
        gcc_shim = os.path.join(bindir, "gcc")
        with open(gcc_shim, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(f"#!/bin/sh\nexec {self._cxx()} \"$@\"\n")
        os.chmod(gcc_shim, 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
