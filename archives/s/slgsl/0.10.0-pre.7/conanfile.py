#!/usr/bin/env python3
"""Conan recipe for slgsl 0.10.0-pre.7 — GNU Scientific Library bindings for
S-Lang.

HarmonyOS (aarch64) adaptation.  slgsl is a set of dynamically loadable
S-Lang interpreter modules (gslcore, gslsf, gslrand, gslinterp, gslcdf,
gslfft, gslinteg, gsldwt, gslmatrix, …) written in C.  It ships an autotools
build (``configure`` + ``make``) that discovers S-Lang and GSL through
``--with-slanglib/--with-slanginc/--with-gsllib/--with-gslinc``.

Dependencies: ``slang/2.3.3`` (the S-Lang library, which also provides the
``slsh`` interpreter used by the upstream test suite) and ``gsl/2.8``.

Upstream tests (R51): ``src/Makefile`` has a real ``check`` target that runs
every ``src/tests/test_*.sl`` through ``slsh`` and fails on any non-zero
exit; ``build()`` invokes it for real.

Platform notes:
* OHOS's ``/tmp`` is a read-only erofs, so TMPDIR is redirected into the
  build tree (every autotools project here needs this).
* The bundled ``config.guess`` (2018) already knows aarch64; the OHOS
  triplet is handled by the repository's standard config.guess/config.sub
  patch (see patches/), applied before configure.
* Conan's ``--build`` must NOT be forced (autotools on this toolchain fails
  the compiler self-check when an explicit build triplet is passed).

R32: settings.os must check in ("Linux", "OHOS").
R38: a library package ships no bin/ executables -> no commands.json.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class SlgslConan(ConanFile):
    name = "slgsl"
    version = "0.10.0-pre.7"
    description = ("S-Lang modules binding the GNU Scientific Library (gslcore, "
                   "gslsf, gslrand, gslinterp, gslcdf, gslfft, gslinteg, "
                   "gsldwt, gslmatrix, ...)")
    license = "MIT"
    homepage = "http://space.mit.edu/cxc/software/slang/modules/gsl/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"slgsl is supported only on Linux/OHOS, got {self.settings.os}")

    def requirements(self):
        # S-Lang host library (also ships the slsh interpreter the upstream
        # test suite runs) and the GNU Scientific Library.
        self.requires("slang/2.3.3")
        self.requires("gsl/2.8")

    def layout(self):
        basic_layout(self)
        # slgsl's configure refuses out-of-source builds ("This software does
        # not support configuring from another directory", see the srcdir
        # check in configure) — build in the source tree (SDL precedent).
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = AutotoolsToolchain(self)
        slang = self.dependencies["slang"]
        gsl = self.dependencies["gsl"]
        tc.configure_args.append("--with-slanginc=%s"
                                 % slang.cpp_info.includedirs[0])
        tc.configure_args.append("--with-slanglib=%s"
                                 % slang.cpp_info.libdirs[0])
        tc.configure_args.append("--with-gslinc=%s" % gsl.cpp_info.includedirs[0])
        tc.configure_args.append("--with-gsllib=%s" % gsl.cpp_info.libdirs[0])
        # OHOS /tmp is a read-only erofs: start from a writable TMPDIR
        # (AutotoolsToolchain picks this up for the configure step too).
        tmp = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmp, exist_ok=True)
        tc.environment().define("TMPDIR", tmp)
        tc.generate()
        VirtualBuildEnv(self).generate()

    def _env(self):
        env = Environment()
        tmp = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmp, exist_ok=True)
        env.define("TMPDIR", tmp)
        env.define("TMP", tmp)
        env.define("TEMP", tmp)
        for dep in self.dependencies.values():
            if not dep.package_folder:
                continue
            env.prepend_path("LD_LIBRARY_PATH",
                             os.path.join(dep.package_folder, "lib"))
            # slsh (from slang) must be on PATH for the upstream `make check`.
            for b in dep.cpp_info.bindirs:
                env.prepend_path("PATH", b)
        # The upstream tests call prepend_to_slang_load_path(), which slsh only
        # defines when it loads its own slsh.rc; slsh finds that file through
        # SLSH_CONF_DIR, and the rc itself reads SLSH_PATH.  Without both, every
        # test dies with "prepend_to_slang_load_path is undefined"
        # (verified: both set -> the suite's test scripts run clean).
        slang = self.dependencies.get("slang")
        if slang and slang.package_folder:
            etc = os.path.join(slang.package_folder, "etc")
            if os.path.isfile(os.path.join(etc, "slsh.rc")):
                env.define("SLSH_CONF_DIR", etc)
            share = os.path.join(slang.package_folder, "share", "slsh")
            if os.path.isdir(share):
                env.define("SLSH_PATH", share)
        env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        return env

    def build(self):
        autotools = Autotools(self)
        with self._env().vars(self).apply():
            autotools.configure()
            autotools.make()
            # R51: upstream `check` runs every src/tests/test_*.sl via slsh.
            src_dir = os.path.join(self.source_folder, "src")
            self.run("make check", cwd=src_dir)

    def package(self):
        autotools = Autotools(self)
        with self._env().vars(self).apply():
            autotools.install(args=["-j1"])
        copy(self, "COPYRIGHT", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        # The compiled modules are dlopen()ed by the S-Lang interpreter, and
        # the .sl wrappers live in the shared slsh tree; consumers need both
        # search paths, plus these libs on the loader path.
        moddir = None
        base = os.path.join(self.package_folder, "lib", "slang")
        for root, _dirs, files in os.walk(base):
            if any(f.endswith("-module.so") for f in files):
                moddir = root
                break
        if moddir:
            self.runenv_info.prepend_path("SLANG_MODULE_PATH", moddir)
        slfiles = os.path.join(self.package_folder, "share", "slsh",
                               "local-packages")
        if os.path.isdir(slfiles):
            self.runenv_info.prepend_path("SLSH_PATH", slfiles)
        self.runenv_info.prepend_path("LD_LIBRARY_PATH",
                                      os.path.join(self.package_folder, "lib"))
