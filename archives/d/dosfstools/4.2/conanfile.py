#!/usr/bin/env python3
"""Conan recipe for dosfstools 4.2 — FAT filesystem tools (mkfs.fat / fsck.fat / fatlabel).

Upstream: https://github.com/dosfstools/dosfstools (release v4.2, 2021-01-31),
Autotools, release tarball ships a pre-generated configure.

HarmonyOS PC adaptations (recipe/environment level only; upstream sources,
test scripts and build files are NOT patched, no entries under patches/):

1. config.guess does not recognise the "HarmonyOS" uname and aborts with
   "cannot guess build type; you must specify one". The build is native
   aarch64, so the canonical GNU build triple is passed explicitly.
2. The device has no `gcc`/`cc` (only clang in /data/service/hnp/bin) and
   autoconf's AC_PROG_CC only probes gcc then cc => pass CC/CXX explicitly,
   reading tools.build:compiler_executables from conf first (R33).
3. HMDFS umask-077 temp-dir bug (E011/E114): configure's `umask 077` is
   rewritten to `umask 022` in the build copy before ./configure runs.
   Without it config.status dies with
   `can't create ./confXXXXXX/subs1.awk: Permission denied`.
4. Device tooling is toybox (0.8.12), upstream tests need GNU semantics:
   - `xxd -r <infile> <outfile>` — toybox xxd accepts a single file argument
     only (measured: "xxd: Max 1 argument"). A wrapper that redirects stdout
     reproduces the vim CLI; the reverse decode itself is byte-identical to
     an address-seeking reference implementation (measured: 1000000 bytes,
     identical).
   - `cmp --bytes=N` — toybox cmp has no --bytes option (measured:
     "cmp: Unknown option 'bytes=1M'"), so 5 mkfs reference tests ERROR
     without a wrapper.
   Both wrappers are written into the build folder and prepended to PATH.
   No upstream test file is touched and no patch is added.
5. VPATH (out-of-source) layout: upstream test-fsck reads "<test>.args" from
   the CWD instead of $srcdir, so the three first_cluster tests would run
   without their `-F 1` argument and die with "Both FATs appear to be
   corrupt". The three *.args data files are staged into the build tests
   directory (copies of the upstream files, unmodified).
6. Upstream `make check` (automake TESTS in tests/: test-mkfs, test-fsck,
   test-label drivers, 40 cases) runs inside build().
7. The host profile's [buildenv] pins CONFIG_SHELL/SHELL to the device
   hnp bash, which cannot getcwd() in any directory; autoconf re-execs into
   CONFIG_SHELL and dies with "configure: error: working directory cannot be
   determined" (knowledge entry E386). Setting os.environ is not enough (the
   profile buildenv is re-applied afterwards), so configure/make/install run
   through `env -u CONFIG_SHELL SHELL=/bin/sh …` at exec time.
"""
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    replace_in_file,
)
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout

XXD_SHIM = """#!/usr/bin/env python3
# Environment-only CLI adapter for the upstream dosfstools tests.
# Device xxd (toybox) accepts a single file argument; the tests call
# `xxd -r <infile> <outfile>` (vim xxd convention). Reverse decoding is
# delegated to the device xxd, which matches an address-seeking reference
# implementation byte for byte (verified on check-fat12_first_cluster).
import os
import subprocess
import sys

REAL_XXD = os.environ.get("REAL_XXD", "/usr/bin/xxd")

def main(argv):
    args = argv[1:]
    if args[:1] == ["-r"] and len(args) == 3:
        with open(args[2], "wb") as out:
            proc = subprocess.run([REAL_XXD, "-r", args[1]], stdout=out,
                                  stderr=sys.stderr)
        return proc.returncode
    return subprocess.run([REAL_XXD] + args).returncode

if __name__ == "__main__":
    sys.exit(main(sys.argv))
"""

CMP_SHIM = """#!/usr/bin/env python3
# Environment-only adapter for `cmp --bytes=N`: toybox cmp (0.8.12) has no
# --bytes/-n option, upstream test-mkfs compares the first N bytes only.
import os
import subprocess
import sys

REAL_CMP = os.environ.get("REAL_CMP", "/usr/bin/cmp")

def main(argv):
    args = argv[1:]
    limit = None
    files = []
    i = 0
    while i < len(args):
        a = args[i]
        if a.startswith("--bytes="):
            limit = a.split("=", 1)[1]
            i += 1
        elif a == "-n" and i + 1 < len(args):
            limit = args[i + 1]
            i += 2
        elif a == "-l":
            # not used by this test suite; delegate would lose the limit
            sys.stderr.write("cmp shim: -l unsupported\\n")
            return 2
        else:
            files.append(a)
            i += 1
    if limit is None or len(files) != 2:
        return subprocess.run([REAL_CMP] + args).returncode
    factor = {"K": 1 << 10, "M": 1 << 20, "G": 1 << 30}
    suffix = limit[-1].upper()
    if suffix in factor:
        n = int(limit[:-1]) * factor[suffix]
    else:
        n = int(limit)
    with open(files[0], "rb") as a, open(files[1], "rb") as b:
        first, second = a.read(n), b.read(n)
    if first != second:
        # a shorter file yields a shorter slice, so length drift lands here too
        window = min(len(first), len(second))
        idx = next((i for i in range(window) if first[i] != second[i]), window)
        sys.stderr.write("%s %s differ: byte %d\\n"
                         % (files[0], files[1], idx + 1))
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv))
"""

INSTALL_SHIM = '''#!/usr/bin/env python3
# Environment-only `install` adapter: this device ships GNU coreutils under
# the g-prefixed name (`ginstall`) and has no `install` binary, while
# automake's install rules invoke `install` (measured: "/bin/sh: install:
# inaccessible or not found", Error 127). Prefer the real GNU implementation
# when present, otherwise fall back to a small POSIX copy implementation
# covering exactly the operations the upstream install rules use.
import os
import shutil
import subprocess
import sys

def main(argv):
    args = argv[1:]
    real = shutil.which("ginstall")
    if real:
        return subprocess.run([real] + args).returncode
    mode = 0o755
    dirs_only = False
    files = []
    i = 0
    while i < len(args):
        a = args[i]
        if a == "-m" and i + 1 < len(args):
            mode = int(args[i + 1], 8)
            i += 2
        elif a == "-d":
            dirs_only = True
            i += 1
        elif a in ("-o", "-g") and i + 1 < len(args):
            i += 2
        elif a.startswith("-"):
            i += 1
        else:
            files.append(a)
            i += 1
    if not files:
        sys.stderr.write("install: missing file operand\\n")
        return 1
    if dirs_only:
        for d in files:
            os.makedirs(d, exist_ok=True)
        return 0
    dest = files[-1]
    sources = files[:-1]
    if len(sources) > 1 or os.path.isdir(dest):
        os.makedirs(dest, exist_ok=True)
        for src in sources:
            target = os.path.join(dest, os.path.basename(src))
            shutil.copyfile(src, target)
            os.chmod(target, mode)
    else:
        parent = os.path.dirname(dest)
        if parent:
            os.makedirs(parent, exist_ok=True)
        shutil.copyfile(sources[0], dest)
        os.chmod(dest, mode)
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv))
'''


class DosfstoolsConan(ConanFile):
    name = "dosfstools"
    version = "4.2"
    description = "DOS/FAT filesystem utilities (mkfs.fat, fsck.fat, fatlabel)"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/dosfstools/dosfstools"
    url = ""  # CI fills this

    # CLI tool, not a library (R38: commands.json declared at software level)
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"dosfstools is only supported on Linux/OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _toolchain(self) -> AutotoolsToolchain:
        """Configure arguments shared by generate() and the pinned build()."""
        tc = AutotoolsToolchain(self)
        # config.guess bails out on the HarmonyOS uname (E007 family); the
        # device build is native aarch64, pin the canonical GNU triple.
        if os.uname().sysname == "HarmonyOS":
            tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        # R33: compiler from Conan conf first, clang fallback (device has no
        # gcc/cc and autoconf's AC_PROG_CC only probes those two).
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        tc.configure_args.append(f"CC={compilers.get('c') or 'clang'}")
        tc.configure_args.append(f"CXX={compilers.get('cpp') or 'clang++'}")
        # Upstream defaults compat symlinks OFF (configure.ac:
        # [symlinks=false]); the deliverable is mkfs.vfat/fsck.vfat, so turn
        # the upstream install-exec-hook on instead of post-processing.
        tc.configure_args.append("--enable-compat-symlinks")
        return tc

    @staticmethod
    def _pin(cmd: str) -> str:
        """E386: the host profile's [buildenv] pins CONFIG_SHELL/SHELL to the
        device hnp bash, which cannot getcwd() in any directory; autoconf
        re-execs into CONFIG_SHELL and dies with "working directory cannot be
        determined", and make would route every recipe through it too.
        Unsetting CONFIG_SHELL and pinning SHELL at exec time is the E386
        recipe-level remedy (os.environ changes lose: the profile buildenv is
        re-applied after them)."""
        return f"env -u CONFIG_SHELL SHELL=/bin/sh {cmd}"

    def generate(self):
        self._toolchain().generate()

    def build(self):
        apply_conandata_patches(self)

        # E490: keep the generated autotools helpers executable — extraction
        # modes are reported as a G0 risk on this platform (no-op when the
        # tarball already carries the bits).
        for helper in ("configure", "config.guess", "config.sub",
                       "install-sh", "missing", "compile", "depcomp"):
            path = os.path.join(self.source_folder, helper)
            if os.path.isfile(path):
                os.chmod(path, 0o755)

        # E011/E114: HMDFS makes umask-077 config temp dirs unwritable for
        # their owner (drwx--S---), config.status then cannot create
        # ./confXXXXXX/subs1.awk. Keep the real temp-dir creation intact.
        replace_in_file(
            self,
            os.path.join(self.source_folder, "configure"),
            "umask 077",
            "umask 022",
        )

        # Environment-level tooling adapters for `make check` (see docstring)
        env_bin = os.path.join(self.build_folder, "env-bin")
        os.makedirs(env_bin, exist_ok=True)
        for tool, script in (("xxd", XXD_SHIM), ("cmp", CMP_SHIM),
                             ("install", INSTALL_SHIM)):
            path = os.path.join(env_bin, tool)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(script)
            os.chmod(path, 0o755)
        os.environ["PATH"] = env_bin + os.pathsep + os.environ.get("PATH", "")

        # VPATH staging: upstream test-fsck reads <test>.args from the CWD
        tests_build = os.path.join(self.build_folder, "tests")
        tests_src = os.path.join(self.source_folder, "tests")
        os.makedirs(tests_build, exist_ok=True)
        for name in sorted(os.listdir(tests_src)):
            if name.endswith(".args"):
                dst = os.path.join(tests_build, name)
                if not os.path.exists(dst):
                    shutil.copy2(os.path.join(tests_src, name), dst)

        # configure + make + make check, each with the E386 shell pin (see
        # _pin). R9/E074: serial make — a parallel jobserver fifo hits HMDFS
        # EPERM. The upstream test suite runs for real; a failure fails the
        # build.
        configure = os.path.join(self.source_folder, "configure")
        args = " ".join(shlex.quote(a) for a in self._toolchain().configure_args)
        self.run(self._pin(f'"{configure}" {args}'))
        self.run(self._pin("make -j1"))
        self.run(self._pin("make -j1 check"))

    def package(self):
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        # conan's Autotools.install() semantics: make install with
        # DESTDIR=<package_folder> (configure ran with --prefix=/).
        self.run(self._pin(
            f'make -j1 install DESTDIR="{self.package_folder}"'
        ))

    def package_info(self):
        # Standalone binaries (sbin_PROGRAMS, conan AutotoolsToolchain forces
        # --sbindir=<prefix>/bin so mkfs.fat/fsck.fat/fatlabel land in bin/)
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
