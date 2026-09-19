#!/usr/bin/env python3
"""Conan recipe — uftrace 0.19

uftrace is a function (graph) tracer for userspace C/C++/Rust programs.
It is written in C and uses a hand-written `configure` script (NOT autotools)
that generates a `.config` file consumed by the Makefile.

Build system: hand-written ./configure + make
Dependencies: none mandatory — libelf/libdw (elfutils), ncurses, capstone,
              libpython, libluajit, libunwind and libtraceevent are all
              optional.  This first-pass recipe builds the core `uftrace`
              binary plus its five `libmcount*.so` instrumentation libraries
              with every optional feature disabled, for a minimal, robust
              OHOS build.  Optional features can be re-enabled incrementally
              (elfutils 0.195, capstone 5.0.7 and ncurses 6.6 are already
              adapted in this repo).

License: GPL-2.0
Homepage: https://github.com/namhyung/uftrace
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.layout import basic_layout


class UftraceConan(ConanFile):
    name = "uftrace"
    version = "0.19"
    description = "Function (graph) tracer for userspace C/C++/Rust programs"
    license = "GPL-2.0"
    homepage = "https://github.com/namhyung/uftrace"
    url = ""  # CI fills this

    # uftrace produces a CLI executable plus private libmcount*.so
    # instrumentation libraries (loaded via LD_PRELOAD / -pg), not a
    # consumer-linked library.
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        # uftrace is Linux-only (the hand-written configure guards on
        # uname -s).  OHOS is Linux-compatible after our patch.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"uftrace supports only Linux/OHOS, got os={self.settings.os}"
            )

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # No mandatory third-party dependencies.  All optional features are
        # disabled in this first-pass build (see _configure_args()).
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # uftrace's hand-written configure does not consume an
        # AutotoolsToolchain; the compiler is passed directly in build().
        pass

    @property
    def _cc(self):
        # R33: get the compiler from Conan conf — never use a bare ${CC}.
        comp_execs = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        return comp_execs.get("c") or "clang"

    @property
    def _config_shell(self):
        # uftrace's configure is `#!/usr/bin/env bash`; invoke it through an
        # explicit shell so it works regardless of shebang resolution on OHOS.
        return os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "sh"

    @property
    def _ld_library_path(self):
        # OHOS SDK's ld.lld depends on libxml2.so.16 from the SDK llvm/lib
        # (same fix as etsh/abuild/babeld).  Prepend it so lld can load its
        # shared deps; without it clang fails with "unable to execute command".
        if self.settings.os == "OHOS":
            return (
                "LD_LIBRARY_PATH="
                "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib"
                ":$LD_LIBRARY_PATH "
            )
        return ""

    def _configure_args(self):
        return [
            "--prefix=" + self.package_folder,
            "--arch=aarch64",
            # Disable every optional feature for a minimal, deterministic
            # OHOS build.  Each maps to a check-deps probe (see configure's
            # IGNORE handling); leaving them unset would let the probe try to
            # link against system libraries that are not part of this build.
            "--without-libelf",
            "--without-libdw",
            "--without-libpython",
            "--without-libluajit",
            "--without-libncurses",
            "--without-libunwind",
            "--without-libtraceevent",
            "--without-libstdc++",
            "--without-capstone",
        ]

    def build(self):
        apply_conandata_patches(self)

        ld_library_path = self._ld_library_path

        # OHOS toolchain lives in /data/service/hnp/bin (llvm-ar, ld.lld, nm,
        # strip, ...) which is NOT on the default PATH.  The compiler is passed
        # as an absolute path via conf, but uftrace's Makefile invokes `ar`
        # (and configure defaults AR=<cross>ar) by bare name — E012.  Inject
        # the toolchain dir into PATH and pin AR to llvm-ar.
        tool_env = ""
        if self.settings.os == "OHOS":
            tool_env = (
                'PATH="/data/service/hnp/bin:$PATH" '
                'AR="/data/service/hnp/bin/llvm-ar" '
            )

        # The hand-written configure reads CC/ARCH from the environment and
        # writes a .config consumed by make.  Build in-source (objdir defaults
        # to ${PWD}) so products land in the source tree.
        configure_cmd = (
            f'{ld_library_path}{tool_env}CC="{self._cc}" ARCH=aarch64 '
            f'"{self._config_shell}" ./configure {" ".join(self._configure_args())}'
        )
        self.run(configure_cmd, cwd=self.source_folder)

        # R9: single-threaded make (OHOS forbids make's FIFO jobserver).
        self.run(f'{ld_library_path}{tool_env}make -j1', cwd=self.source_folder)

        # Upstream unit tests (unittest binary, 96 TEST_CASEs of pure logic,
        # no perf_event required).  Run them so the PR has real upstream-test
        # evidence (rule4); the runtest.py functional suite needs perf_event
        # dynamic tracing and is excluded from the build-time gate.
        #
        # Why -no-pie (patch 0005 forces load_base=0 in unittest.c):
        #   * OHOS's dl_iterate_phdr reports a bogus heap dlpi_addr for the
        #     main program, so unittest.c's own load_base derivation turns
        #     every func_* test pointer into a wild pointer (SIGSEGV on blr).
        #   * With -no-pie the symbol table's st_value is already an absolute
        #     address, so load_base must simply stay 0.
        # The upstream fork-based test isolation works on a signed OHOS binary,
        # so the original fork+wait flow is kept (no in-process hack), which
        # keeps per-test global state isolated and lets all 96 cases run.
        if self.settings.os == "OHOS":
            # Compile the unittest binary via the top-level Makefile target
            # (so srcdir/objdir/TEST_CFLAGS are exported), passing a filter
            # that matches no test so the run step is a no-op — we sign the
            # binary before actually running it.
            self.run(f'{ld_library_path}{tool_env}make unittest '
                     f'TESTARG="__compile_only__" '
                     f'TEST_CFLAGS="-g -include \\"{self.source_folder}/tests/unittest.h\\" '
                     f'-Wno-sign-compare -std=gnu11 -D_GNU_SOURCE -O2 -DDEBUG_MODE=0 '
                     f'-iquote \\"{self.source_folder}\\" '
                     f'-iquote \\"{self.source_folder}\\" '
                     f'-iquote \\"{self.source_folder}/arch/aarch64\\" '
                     f'-W -Wall -Wno-unused-parameter -Wno-missing-field-initializers '
                     f'-Wdeclaration-after-statement -Wstrict-prototypes -Wno-array-bounds '
                     f'-DUNIT_TEST" '
                     f'TEST_LDFLAGS="-ldl -pthread -Wl,-z,noexecstack -no-pie -lm"',
                     cwd=self.source_folder)

            # OHOS rejects unsigned ELF exec with a signal (E077); the build
            # tree binary is not signed by package().  Sign it before running.
            unittest_bin = os.path.join(self.source_folder, "tests", "unittest")
            objcopy = "/data/service/hnp/bin/llvm-objcopy"
            signer = "/data/service/hnp/bin/binary-sign-tool"
            self.run(f'{objcopy} --remove-section .codesign "{unittest_bin}" 2>/dev/null || true')
            self.run(f'{signer} sign -inFile "{unittest_bin}" -outFile "{unittest_bin}" -selfSign 1')

            # Run the signed unit test binary (exit != 0 on any failure).
            self.run(f'{ld_library_path}{tool_env}./unittest',
                     cwd=os.path.join(self.source_folder, "tests"))

    def package(self):
        # Manually stage the products instead of `make install`: the install
        # target also builds/installs man pages via pandoc (absent on OHOS,
        # and the doc/ dir has no pre-generated man pages) and runs ldconfig.
        # Only the uftrace binary and the five libmcount instrumentation
        # libraries are needed at runtime.
        copy(self, "uftrace", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)

        libdir = os.path.join(self.package_folder, "lib", "uftrace")
        libmcount = os.path.join(self.source_folder, "libmcount")
        for name in (
            "libmcount.so",
            "libmcount-nop.so",
            "libmcount-fast.so",
            "libmcount-single.so",
            "libmcount-fast-single.so",
        ):
            copy(self, name, src=libmcount, dst=libdir, keep_path=False)

        self._sign_binaries()

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        # HarmonyOS PC XPM requires code signing for exec binaries and
        # dlopen'd shared libraries (same as elfutils/capstone).  Sign the
        # uftrace executable and the libmcount*.so instrumentation libraries.
        import glob
        targets = glob.glob(
            os.path.join(self.package_folder, "lib", "**", "*.so"), recursive=True
        )
        targets += glob.glob(
            os.path.join(self.package_folder, "lib", "**", "*.so.*"), recursive=True
        )
        bindir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bindir):
            for name in os.listdir(bindir):
                p = os.path.join(bindir, name)
                if os.path.isfile(p) and not os.path.islink(p) and self._is_elf(p):
                    targets.append(p)
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for f in targets:
            if os.path.islink(f):
                continue
            self.run(
                '{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(
                    oc=objcopy, f=f
                )
            )
            self.run(
                '{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(
                    sg=signer, f=f
                )
            )

    def package_info(self):
        # CLI tool: expose bin/uftrace on PATH.  The libmcount*.so files under
        # lib/uftrace are private runtime instrumentation libraries injected
        # via LD_PRELOAD / -pg (found at runtime with uftrace's -L option);
        # they are not consumer link libraries.
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
