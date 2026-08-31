#!/usr/bin/env python3
"""Conan recipe — execstack 20130503 (autotools)

execstack is a CLI tool from the prelink package that sets/queries the
executable stack flag of ELF binaries. It is built from the prelink source
tarball but only the execstack binary is produced (not prelink itself,
which requires GLOB_BRACE and other glibc-only features not in musl).

Adaptation notes:
- musl libc lacks error.h -> patched with a minimal replacement (patches/add-error-h.patch)
- musl libc lacks argp.h -> requires argp-standalone (via elfutils dependency chain)
- prelink's gather.c uses GLOB_BRACE (glibc-only) -> only execstack target is built
- configure's config.sub is too old (2002) to recognize aarch64 -> uses aarch64-unknown-linux-gnu triplet
- configure's umask 077 in config.status breaks on OHOS filesystem -> patched to umask 022 in build()
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
import os
import sys


class ExecstackConan(ConanFile):
    name = "execstack"
    version = "20130503"
    description = "CLI tool to query or set executable stack flag of ELF binaries (from prelink)"
    license = "GPL-2.0-only"
    homepage = "https://people.redhat.com/jakub/prelink/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("elfutils/0.195")
        self.requires("argp-standalone/1.5.0")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # config.sub from 2002 doesn't recognize aarch64 or musl; use gnu triplet
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.configure_args.append("--host=aarch64-unknown-linux-gnu")
        # R33: pass dependency include/lib flags via the Conan Toolchain
        # (AutotoolsToolchain extra_cflags/extra_ldflags + Environment), not bare
        # os.environ. cpp_info.includedirs/libdirs may be relative; join with
        # package_folder for absolute paths.
        _inc, _lib, _l = [], [], []
        _ldpath_dirs = []
        for _ref, _dep in self.dependencies.items():
            ci = _dep.cpp_info
            _pf = _dep.package_folder or ""
            for _p in ci.includedirs or []:
                _abs = _p if os.path.isabs(_p) else os.path.join(_pf, _p)
                _inc.append("-I" + _abs)
            for _p in ci.libdirs or []:
                _abs = _p if os.path.isabs(_p) else os.path.join(_pf, _p)
                _lib.append("-L" + _abs)
                _ldpath_dirs.append(_abs)
            for _n in ci.libs or []:
                _l.append("-l" + _n)
        # -I flags -> CPPFLAGS (configure's AC_CHECK_HEADER presence probe runs
        # the preprocessor with CPPFLAGS, not CFLAGS; the usability probe uses
        # CFLAGS, but both must succeed for "libelf.h found").
        # -L flags -> LDFLAGS (configure link probes find libraries).
        # LIBS (-l flags) and LD_LIBRARY_PATH are also not in AutotoolsToolchain
        # defaults; add everything to the toolchain Environment so it lands in
        # the generated conanbuild env script. LD_LIBRARY_PATH is needed by
        # configure's run-time probes (e.g. AC_LIBELF_SXWORD needs libzstd.so).
        env = tc.environment()
        if _inc:
            env.append("CPPFLAGS", _inc)
        if _lib:
            env.append("LDFLAGS", _lib)
        # Do NOT set LIBS as a global env var — it pollutes configure's
        # AC_PROG_CC test ("C compiler cannot create executables").
        # When LIBS contains -ldw, the trivial conftest links against libdw.so
        # which transitively needs liblzma/libbz2/libz.  On CI those transitive
        # deps are "Skipped binaries", so the link fails.
        # Instead, store the libs string for build() to pass via the make
        # command-line, so only the final link sees them, not configure.
        self._libs_str = " ".join(_l) if _l else ""
        for _d in _ldpath_dirs:
            env.append_path("LD_LIBRARY_PATH", _d)

        # HarmonyOS default toolchain injects -fstack-protector-strong into
        # CFLAGS/LDFLAGS.  configure's AC_PROG_CC conftest then links against
        # libc symbols (__stack_chk_guard/__stack_chk_fail) that may be missing
        # from the target libc in the cross environment, producing
        # "C compiler cannot create executables".  Strip these flags so the
        # trivial conftest links cleanly.
        import re
        _sp_re = re.compile(r'(?:^|\s)-fstack-protector(?:-\S+)?\b')
        for _var in ("CFLAGS", "LDFLAGS"):
            _val = os.environ.get(_var, "")
            if "-fstack-protector" in _val:
                _cleaned = _sp_re.sub('', _val).strip()
                if _cleaned:
                    env.define(_var, _cleaned)
                else:
                    env.unset(_var)
                self.output.info(f"Stripped -fstack-protector from {_var} for conftest link")

        tc.generate(env)

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)

        # Patch configure's umask 077 -> 022 (OHOS filesystem blocks 0700 dirs in config.status)
        configure_path = os.path.join(self.source_folder, "configure")
        if os.path.isfile(configure_path):
            with open(configure_path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
            if "umask 077" in text:
                text = text.replace("umask 077 && mktemp -d", "umask 022 && mktemp -d")
                text = text.replace("umask 077 && mkdir", "umask 022 && mkdir")
                with open(configure_path, "w", encoding="utf-8") as f:
                    f.write(text)
                self.output.info("Patched configure: umask 077 -> 022")

        # configure writes a detailed log to config.log; dump it to stderr on
        # failure so CI surfaces the real link error instead of just the
        # generic "C compiler cannot create executables" message.
        try:
            autotools.configure()
        except Exception:
            config_log = os.path.join(self.build_folder, "config.log")
            if os.path.isfile(config_log):
                with open(config_log, "r", encoding="utf-8", errors="ignore") as f:
                    print(f.read(), file=sys.stderr)
            raise

        # Fix LDFLAGS in src/Makefile: AutotoolsToolchain adds relative -Llib paths
        # from cpp_info.libdirs (e.g. "-Llib") which break libtool's cd at link time.
        # Replace them with absolute paths or remove them.
        src_makefile = os.path.join(self.build_folder, "build-release", "src", "Makefile")
        if not os.path.isfile(src_makefile):
            src_makefile = os.path.join(self.build_folder, "src", "Makefile")
        if os.path.isfile(src_makefile):
            with open(src_makefile, "r", encoding="utf-8", errors="ignore") as f:
                makefile_text = f.read()
            # Remove relative -Llib entries (keep absolute -L/path ones)
            import re
            makefile_text = re.sub(r' -Llib\b', '', makefile_text)
            makefile_text = re.sub(r'-Llib\b', '', makefile_text)
            with open(src_makefile, "w", encoding="utf-8") as f:
                f.write(makefile_text)
            self.output.info("Patched src/Makefile: removed relative -Llib entries")

        # Only build execstack, not prelink (prelink's gather.c needs GLOB_BRACE unavailable in musl)
        # The execstack target is in src/Makefile. Build it directly with -j1
        # (OHOS filesystem blocks make jobserver fifos with -j2+).
        _libs = getattr(self, "_libs_str", "")
        _make_cmd = "make -C src execstack -j1"
        if _libs:
            _make_cmd += f' LIBS="{_libs}"'
        self.run(_make_cmd, env="conanbuild")

    def package(self):
        # Manual install: copy only the execstack binary (not prelink)
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        # Find the built execstack binary in the build folder
        _src = os.path.join(self.build_folder, "build-release", "src", "execstack")
        if not os.path.isfile(_src):
            _src = os.path.join(self.build_folder, "src", "execstack")
        if os.path.isfile(_src):
            copy(self, "execstack", src=os.path.dirname(_src), dst=bin_dir)
        else:
            self.output.warn(f"execstack binary not found at {_src}")

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
