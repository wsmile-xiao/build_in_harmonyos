#!/usr/bin/env python3
"""Conan recipe - rgxg 0.1.2 (ReGular eXpression Generator).

rgxg is a small C library (plus a CLI of the same name) that turns CIDR
notation and integer ranges into regular expressions.  The 0.1.2 release
tarball ships pregenerated Autotools files, so the recipe configures, builds
and runs the upstream test suite without bootstrapping autoconf/automake.

Dependencies: none for the library itself.  check/0.15.2 is a test-only
dependency; it drives the single upstream suite (tests/check_rgxg.c) that
`make check` runs from build().

OHOS adaptations:
  - the 2020 config.guess/config.sub in the tarball cannot name the HongMeng
    kernel, so only the build triple is pinned on the command line (no
    --host: autoconf feeds a user-supplied --host through config.sub, whose
    2020 table rejects "linux-ohos"); same approach as pexec/1.0;
  - the release tarball's configure is executed through `sh` because OHOS
    blocks shebang execution of scripts in the build domain;
  - `umask 077` is removed from configure (E114: HMDFS makes the 0700 mktemp
    directory unwritable even for its owner, so config.status cannot re-read
    conf*/subs*.sed);
  - PKG_CHECK_MODULES(CHECK) is fed CHECK_CFLAGS/CHECK_LIBS derived from the
    conan dependency instead of probing for a pkg-config binary: the CI
    workers have pkg-config under /data/service/hnp but real devices do not,
    and a miss there would silently set HAVE_CHECK=false and drop every
    upstream test;
  - make runs with -j1 (E074: the HMDFS jobserver fifo returns EPERM).
"""
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rm,
)
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"

# config.guess of 2020 predates HarmonyOS support and its config.sub rejects an
# "linux-ohos" kernel field, so pin the *build* triple on the configure command
# line (which overrides whatever config.guess would print) and leave --host out
# entirely: autoconf only feeds a user-supplied --host through config.sub, and
# the 2020 table cannot parse it.  Same approach as pexec/1.0.  The compiler is
# the OHOS SDK clang either way, so the objects are AArch64/musl regardless.
BUILD_TRIPLE = "aarch64-unknown-linux-gnu"

# config.status re-execs itself under $SHELL; /bin/sh is the one interpreter
# that is always launchable from the build domain on OHOS.
SHELL_FIX = "env -u CONFIG_SHELL SHELL=/bin/sh"


class RgxgConan(ConanFile):
    name = "rgxg"
    version = "0.1.2"
    description = (
        "rgxg - ReGular eXpression Generator: C library and CLI that build "
        "regular expressions matching CIDR blocks and integer ranges"
    )
    license = "Zlib"
    homepage = "https://rgxg.github.io"
    url = "https://github.com/rgxg/rgxg"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}
    implements = ["auto_shared_fpic"]

    # ------------------------------------------------------------------ hooks

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if str(self.settings.os) == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"rgxg/0.1.2 is validated for Linux and OHOS, not {self.settings.os}"
            )
        if str(self.settings.os) == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration(
                "rgxg/0.1.2 OHOS support is validated for armv8/AArch64 only"
            )

    def layout(self):
        basic_layout(self)

    def build_requirements(self):
        # The only upstream test suite is the Check-based tests/check_rgxg.c,
        # executed by `make check` inside build().  Test-only: it is not part
        # of the installed link interface.
        self.test_requires("check/0.15.2")

    # ------------------------------------------------------------------ source

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ---------------------------------------------------------------- helpers

    def _test_dependency(self, name):
        for group in (self.dependencies.test, self.dependencies.host,
                      self.dependencies.build):
            try:
                return group[name]
            except KeyError:
                continue
        raise ConanException(f"missing test dependency: {name}")

    def _compiler_cc(self):
        # R33: take the compiler from the toolchain conf, never from bare PATH.
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = executables.get("c")
        if cc:
            return str(cc).split()[0].strip("\"'")
        found = shutil.which("clang") or shutil.which("cc")
        if not found:
            raise ConanException("no C compiler found for the rgxg build")
        return found

    def _check_flags(self):
        """CHECK_CFLAGS/CHECK_LIBS for PKG_CHECK_MODULES(CHECK), derived from
        the conan dependency so no pkg-config binary has to be present."""
        check = self._test_dependency("check")
        include = os.path.join(
            check.package_folder, (check.cpp_info.includedirs or ["include"])[0])
        libdir = os.path.join(
            check.package_folder, (check.cpp_info.libdirs or ["lib"])[0])
        libs = " ".join(f"-l{lib}" for lib in (check.cpp_info.libs or ["check"]))
        system = " ".join(f"-l{lib}" for lib in (check.cpp_info.system_libs or []))
        return f"-I{include}", f"-L{libdir} {libs} {system}".strip(), libdir

    def _drop_umask_077(self, path):
        """E114: HMDFS forces setgid on new directories, so the `umask 077`
        mktemp dance leaves config.status unable to re-read its own sed file."""
        with open(path, "r", encoding="utf-8", errors="ignore") as handle:
            script = handle.read()
        fixed = script.replace("(umask 077 && ", "(")
        if fixed != script:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(fixed)

    def _test_env_prefix(self, check_libdir):
        """Inline assignments for the `make check` run only."""
        variables = {}
        if str(self.settings.os) == "OHOS":
            # /tmp is read-only on the target; Check 0.15.2 consults TEMP, TMP
            # and TMPDIR before P_tmpdir, so set every spelling.
            test_tmp = os.path.join(self.build_folder, "check-tmp")
            os.makedirs(test_tmp, exist_ok=True)
            variables["TEMP"] = test_tmp
            variables["TMP"] = test_tmp
            variables["TMPDIR"] = test_tmp
            # Check's forked runner creates an IPC file it then unlinks; HMDFS
            # normalises those permissions away, so run in-process instead.
            variables["CK_FORK"] = "no"
        if os.path.isdir(check_libdir):
            variables["LD_LIBRARY_PATH"] = check_libdir
        return " ".join(f"{key}={shlex.quote(val)}" for key, val in variables.items())

    # ------------------------------------------------------------------- build

    def generate(self):
        # conanbuild carries CONFIG_SHELL/SHELL from the profile's tool_requires.
        VirtualBuildEnv(self).generate()

    def build(self):
        apply_conandata_patches(self)
        source = self.source_folder
        configure = os.path.join(source, "configure")
        self._drop_umask_077(configure)

        cc = self._compiler_cc()
        check_cflags, check_libs, check_libdir = self._check_flags()
        self.output.info(f"building rgxg with CC={cc}")

        # GitHub release assets never ship an executable configure bit after
        # extraction, hence the explicit `sh`.
        arguments = " ".join(shlex.quote(arg) for arg in [
            f"--build={BUILD_TRIPLE}",
            f"--prefix={self.package_folder}",
            "--enable-static" if not self.options.shared else "--enable-shared",
            "--disable-shared" if not self.options.shared else "--disable-static",
            "--disable-dependency-tracking",
            f"CC={cc}",
            f"CHECK_CFLAGS={check_cflags}",
            f"CHECK_LIBS={check_libs}",
        ])
        self.run(f'{SHELL_FIX} sh {shlex.quote(configure)} {arguments}',
                 cwd=source, env="conanbuild")

        # A silent HAVE_CHECK=false would build and "pass" with zero upstream
        # tests, so refuse to continue in that case.
        with open(os.path.join(source, "Makefile"), encoding="utf-8",
                  errors="ignore") as handle:
            generated = handle.read()
        if "check_rgxg" not in generated:
            raise ConanException(
                "configure did not enable the upstream Check suite "
                "(HAVE_CHECK false): tests would silently not run"
            )

        # E074: parallel make hits the HMDFS jobserver fifo EPERM.
        self.run(f"{SHELL_FIX} make -j1", cwd=source, env="conanbuild")

        # Upstream official suite: two Check loop-cases that iterate the 600
        # CIDR and the 450 integer-range vectors in tests/ and compare every
        # generated regular expression against the expected one.
        self.run(f"{SHELL_FIX} {self._test_env_prefix(check_libdir)} "
                 "make -j1 check", cwd=source, env="conanbuild")

    def package(self):
        self.run(f"{SHELL_FIX} make install -j1", cwd=self.source_folder,
                 env="conanbuild")

        # Libtool archives carry the build-time absolute libdir; conan
        # consumers get their link metadata from cpp_info instead.
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

        binary = os.path.join(self.package_folder, "bin", "rgxg")
        if os.path.isfile(binary):
            os.chmod(binary, 0o755)

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "rgxg")
        self.cpp_info.set_property("cmake_file_name", "rgxg")
        self.cpp_info.set_property("cmake_target_name", "rgxg::rgxg")
        self.cpp_info.libs = ["rgxg"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
