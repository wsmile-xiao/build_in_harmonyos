#!/usr/bin/env python3
"""Conan recipe for plocate 1.1.24 — a faster locate(1) based on posting lists.

Meson + C++17. Hard deps: libzstd and threads. liburing is optional and
upstream probes it with dependency(required:false): when absent, the build
adds -DWITHOUT_URING and the same binaries fall back to complete pread()
I/O. The recipe exposes a `with_uring` option so both upstream meson paths
are really buildable/runnable.

The official release tarball registers zero meson tests (no test() in
meson.build, no tests/ directory — verified against the dist tarball), so
behavior is covered by the end-to-end test_package suite (build a database
from a plaintext file list and assert query behavior).
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class PlocateConan(ConanFile):
    name = "plocate"
    version = "1.1.24"
    description = "A faster locate, based on posting lists"
    license = "GPL-2.0-or-later"
    homepage = "https://plocate.sesse.net/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("locate", "search", "index", "filesystem")
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    options = {"with_uring": [True, False]}
    # OHOS reality check (2026-09-24, HongMeng 1.12.0): io_uring_setup()
    # succeeds from an app-shell process, but driving the ring (enter/
    # register used by liburing) is killed by seccomp with SIGSYS, so any
    # uring-backed query dies in the worker child. Default to the upstream
    # complete-pread fallback; keep the option for kernels that allow it.
    default_options = {"with_uring": False}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("plocate is packaged through its POSIX path (Linux/OHOS)")

    def requirements(self):
        self.requires("libzstd/1.5.7")
        if self.options.with_uring:
            self.requires("liburing/2.15")

    def build_requirements(self):
        # CI workers and this device have no system pkg-config on PATH;
        # meson dep lookup needs pkgconf from the registry (libapk precedent).
        self.tool_requires("pkgconf/3.0.5")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        tc = MesonToolchain(self)
        tc.project_options["install_systemd"] = False
        tc.project_options["install_cron"] = False
        tc.project_options["sharedstatedir"] = "lib"
        tc.project_options["wrap_mode"] = "nodownload"
        if self.options.with_uring:
            # Upstream expects liburing.h in a distro-devel system include
            # path; updatedb's meson target carries no uringdep, so per-target
            # include dirs never reach it. Pin the dep's include dir globally.
            ur = self.dependencies["liburing"]
            inc = os.path.join(ur.package_folder, ur.cpp_info.includedirs[0])
            tc.extra_cxxflags.append(f"-I{inc}")
        tc.generate()
        self._inject_binaries()

    def _tool_path(self, executables, conf_key, names):
        """Absolute path for an aux binutils tool, resolved in three layers.

        The shared CI profile sets tools.build:compiler_executables with only
        the c/cpp keys, so executables.get("ar") is None there and meson falls
        back to bare-name PATH lookup ('llvm-ar'), which CI workers cannot
        resolve (their PATH has no ~/usr/local/bin) -> "Unknown linker(s):
        [['llvm-ar']]" while the same recipe is green on device.
        """
        value = executables.get(conf_key)
        if value:
            return value
        for key in ("cpp", "c"):
            compiler = executables.get(key)
            if not compiler:
                continue
            for name in names:
                cand = os.path.join(os.path.dirname(compiler), name)
                if os.path.isfile(cand) and os.access(cand, os.X_OK):
                    return cand
        for name in names:
            found = shutil.which(name)
            if found:
                return found
        return None

    def _inject_binaries(self):
        # MesonToolchain locks compilers into the native file but writes no
        # [binaries] ar/pkgconfig entries; conan's build env PATH does not
        # contain the toolchain directory, so meson fails with
        # "Unknown linker(s): llvm-ar...". Pin absolute paths from the
        # profile conf (libapk precedent, minimal variant).
        import re
        executables = self.conf.get("tools.build:compiler_executables",
                                    default={}, check_type=dict) or {}
        native = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if not os.path.isfile(native):
            self.output.warning(
                "conan_meson_native.ini not found; [binaries] pinning skipped, "
                "meson will resolve ar/ranlib/strip/pkgconfig from PATH")
            return
        with open(native, encoding="utf-8") as f:
            content = f.read()
        pc = None
        if "pkgconf" in self.dependencies.build:
            binds = self.dependencies.build["pkgconf"].cpp_info.bindirs
            if binds:
                for name in ("pkgconf", "pkg-config"):
                    cand = os.path.join(self.dependencies.build["pkgconf"].package_folder,
                                        binds[0], name)
                    if os.path.isfile(cand):
                        pc = cand
                        break
        unresolved = []
        for key, names in (("ar", ("llvm-ar", "ar")),
                           ("ranlib", ("llvm-ranlib", "ranlib"))):
            value = self._tool_path(executables, key, names)
            if not value:
                unresolved.append(key)
                continue
            if re.search(r"(?m)^%s\s*=" % re.escape(key), content):
                continue
            content = content.replace("[binaries]\n",
                                      "[binaries]\n%s = '%s'\n" % (key, value), 1)
        # strip stays conf-only (never derived): the recipe signs installed
        # ELFs itself, so silently pulling in a different strip could break that.
        for key, value in (("strip", executables.get("strip")),
                           ("pkgconfig", pc)):
            if not value or re.search(r"(?m)^%s\s*=" % re.escape(key), content):
                continue
            content = content.replace("[binaries]\n",
                                      "[binaries]\n%s = '%s'\n" % (key, value), 1)
        if unresolved:
            # Never skip silently: an unpinned ar/ranlib only fails on CI.
            raise ConanException(
                "cannot resolve %s to an absolute path: "
                "tools.build:compiler_executables carries no such key, "
                "nothing executable with those names sits next to the "
                "compiler, and none is on PATH; meson would probe the bare "
                "name and fail on CI workers" % ", ".join(unresolved))
        with open(native, "w", encoding="utf-8") as f:
            f.write(content)

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()
        # Upstream release registers no automated tests (see module docstring);
        # behavioral coverage lives in test_package/test.sh end-to-end suite.

    def package(self):
        Meson(self).install()
        copy(self, "COPYING", self.source_folder, os.path.join(self.package_folder, "licenses"))
        self._sign_bins()

    def _sign_bins(self):
        # OHOS kernels only exec ELFs carrying a valid .codesign section; the
        # meson/lld path leaves the placeholder empty (abx/0.1 precedent).
        import shutil
        import subprocess
        signer = shutil.which("binary-sign-tool") or os.environ.get("OHOS_BINARY_SIGN_TOOL", "")
        if not signer or not os.path.isfile(signer):
            raise ConanInvalidConfiguration("binary-sign-tool not found on PATH (set OHOS_BINARY_SIGN_TOOL)")
        bindir = os.path.join(self.package_folder, "bin")
        for name in ("plocate", "plocate-build", "updatedb"):
            path = os.path.join(bindir, name)
            if not os.path.isfile(path):
                continue
            out = path + ".signed"
            subprocess.run([signer, "sign", "-inFile", path, "-outFile", out,
                            "-selfSign", "1"], check=True, timeout=60)
            os.chmod(out, (os.stat(path).st_mode & 0o777) | 0o055)
            os.replace(out, path)

    def package_info(self):
        self.cpp_info.bindirs = ["bin", "sbin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
