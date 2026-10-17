#!/usr/bin/env python3
"""Conan recipe — gpgmepy 2.0.0 (GPGME Python bindings) on HarmonyOS PC (aarch64).

gpgmepy is a SWIG-generated Python extension (``gpg._gpgme``) plus the pure
Python package ``gpg/`` that wraps libgpgme.  Upstream builds with autotools
+ ``setup.py build``; this recipe bypasses autotools entirely (no automake /
libtool on OHOS PC) and drives setuptools directly:

1. ``setup.py.in`` placeholders are substituted at build time with the
   Conan-provided gpgme / libgpg-error CFLAGS & LIBS (mirrors what the
   upstream configure would produce via gpgme-config / gpg-error-config).
2. The SWIG-generated module is built with the Conan-managed Python 3.12.9
   interpreter (``setup.py build --build-base=...``).
3. The resulting ``gpg/`` package (pure Python + ``_gpgme*.so``) is installed
   to ``<pkg>/lib/python3.12/site-packages/gpg`` and the extension is
   self-signed for dlopen on HMDFS (E212, same pattern as lxml).

License: GPL-2.0 (gpgmepy is part of the GnuPG ecosystem).
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import (apply_conandata_patches, copy, download,
                               export_conandata_patches, get)
from conan.tools.layout import basic_layout

# setuptools is not bundled with the conan Python package; the pinned
# wheel (pure Python, py3-none-any) is fetched from PyPI at build time
# (CI has network, like source() fetching the upstream tarball) and
# unpacked into the build folder.
_SETUPTOOLS_WHEEL = "setuptools-84.0.0-py3-none-any.whl"
_SETUPTOOLS_SHA256 = "51a52592b3b99e102b609654876bd65f19f999935166d1352678931132b0c670"
_SETUPTOOLS_URL = (
    "https://files.pythonhosted.org/packages/95/9c/"
    "c510029fc6ef33a6275cd2c5d3cecd6613dfd6aa401d57c54f1c18852ccf/"
    + _SETUPTOOLS_WHEEL
)
_PY_VERSION = "3.12"
_SITE_PKG = "lib/python{}/site-packages".format(_PY_VERSION)


class GpgmepyConan(ConanFile):
    name = "gpgmepy"
    version = "2.0.0"
    description = "Python bindings for GPGME (gpg._gpgme SWIG extension + gpg package)"
    license = "GPL-2.0-or-later"
    homepage = "https://gnupg.org/software/gpgme/"
    url = "https://codeload.github.com/gpg/gpgmepy/tar.gz/refs/tags/gpgmepy-2.0.0"

    # Python distribution with a compiled C extension (like aggdraw):
    # "application" avoids the mandatory `shared` option of "library".

    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires("gpgme/1.24.0")
        self.requires("libgpg-error/1.55")
        self.requires("python/3.12.9")
        # swig is a build-time CLI, but it is declared as a host requires
        # (not tool_requires) on purpose: the CI cache only holds the
        # host-profile binary (os.version=6.0), and the mandated
        # `conan create ... -pr ohos-aarch64` command does not define a
        # build profile, so a build-context resolution would be Invalid.
        self.requires("swig/4.4.1")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        # The codeload URL basename has no .tar.gz suffix, so conan's format
        # auto-detection would fail (BadZipFile) — pin the filename explicitly.
        get(self, **self.conan_data["sources"],
            filename="gpgmepy-{}.tar.gz".format(self.version),
            strip_root=True)

    def generate(self):
        env = VirtualBuildEnv(self)
        env.generate()

    # ------------------------------------------------------------------ #
    # build helpers
    # ------------------------------------------------------------------ #
    def _dep_lib_dirs(self):
        dirs = []
        for dep in self.dependencies.values():
            pf = dep.package_folder
            if pf:
                dirs.append(os.path.join(pf, "lib"))
        return dirs

    def _dep_include_dirs(self):
        dirs = []
        for dep in self.dependencies.values():
            pf = dep.package_folder
            if pf:
                dirs.append(os.path.join(pf, "include"))
        return dirs

    def _setup_py(self, build_dir):
        """Substitute setup.py.in placeholders (autotools bypass, E217)."""
        src = os.path.join(self.source_folder, "setup.py.in")
        with open(src, "r", encoding="utf-8") as f:
            text = f.read()

        gpgme = self.dependencies["gpgme"].package_folder
        gpg_error = self.dependencies["libgpg-error"].package_folder
        substitutions = {
            "@VERSION@": self.version,
            # The packaged gpgme-config does not report its own include dir
            # (E217) — provide the include dirs explicitly.
            "@GPGME_CFLAGS@": "-I{}".format(os.path.join(gpgme, "include")),
            "@GPGME_LIBS@": "-L{} -lgpgme".format(os.path.join(gpgme, "lib")),
            "@GPG_ERROR_CFLAGS@": "-I{}".format(
                os.path.join(gpg_error, "include")),
            "@GPG_ERROR_LIBS@": "-L{} -lgpg-error".format(
                os.path.join(gpg_error, "lib")),
        }
        for key, value in substitutions.items():
            text = text.replace(key, value)

        dst = os.path.join(build_dir, "setup.py")
        with open(dst, "w", encoding="utf-8") as f:
            f.write(text)
        self.output.info("setup.py generated in build dir")

    def _version_py(self, build_dir):
        src = os.path.join(self.source_folder, "version.py.in")
        dst = os.path.join(build_dir, "version.py")
        with open(src, "r", encoding="utf-8") as f:
            text = f.read()
        with open(dst, "w", encoding="utf-8") as f:
            f.write(text.replace("@VERSION@", self.version))

    def _copy_build_inputs(self, build_dir):
        """setup.py build assumes an in-tree layout (autotools `copystamp`):
        gpgme.i/helpers.* in the CWD and a `gpg` symlink to the source
        package tree (src/)."""
        for name in ("gpgme.i", "helpers.c", "helpers.h", "private.h"):
            shutil.copy2(os.path.join(self.source_folder, name), build_dir)
        gpg_link = os.path.join(build_dir, "gpg")
        if not os.path.exists(gpg_link):
            os.symlink(os.path.join(self.source_folder, "src"), gpg_link)

    def _ensure_setuptools(self):
        """Make setuptools importable for the conan Python 3.12.9.

        The conan python/3.12.9 package does not ship setuptools.  A
        setuptools wheel is a plain zip, so we download the pinned wheel
        from PyPI at build time (CI has network, like source()) and
        unpack it into the build folder, then point PYTHONPATH at it.
        """
        st_dir = os.path.join(self.build_folder, "setuptools")
        if os.path.isfile(os.path.join(st_dir, "setuptools", "__init__.py")):
            self.output.info(
                "setuptools already unpacked at {}".format(st_dir))
            return st_dir

        wheel_path = os.path.join(self.build_folder, _SETUPTOOLS_WHEEL)
        if not os.path.isfile(wheel_path):
            download(self, _SETUPTOOLS_URL, wheel_path,
                     sha256=_SETUPTOOLS_SHA256)
        os.makedirs(st_dir, exist_ok=True)
        import zipfile
        with zipfile.ZipFile(wheel_path) as zf:
            zf.extractall(st_dir)
        self.output.info(
            "Unpacked setuptools wheel into {}".format(st_dir))
        return st_dir

    # ------------------------------------------------------------------ #
    # build
    # ------------------------------------------------------------------ #
    def build(self):
        apply_conandata_patches(self)

        py = self.dependencies["python"]
        py_pkg = py.package_folder
        py_bin = os.path.join(py_pkg, "bin", "python{}".format(_PY_VERSION))
        py_lib = os.path.join(py_pkg, "lib")
        py_inc = os.path.join(py_pkg, "include", "python{}".format(_PY_VERSION))

        swig = self.dependencies["swig"]
        swig_pkg = swig.package_folder
        swig_bin_dir = os.path.join(swig_pkg, "bin")
        swig_lib = os.path.join(swig_pkg, "share", "swig", str(swig.ref.version))

        build_dir = os.path.join(self.build_folder, "pgmbuild")
        os.makedirs(build_dir, exist_ok=True)
        self._setup_py(build_dir)
        self._version_py(build_dir)
        self._copy_build_inputs(build_dir)
        st_dir = self._ensure_setuptools()

        # R33: compiler from the Conan profile conf.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compilers.get("c", "/data/service/hnp/bin/clang")

        lib_dirs = [py_lib] + self._dep_lib_dirs()
        inc_dirs = [py_inc] + self._dep_include_dirs()
        ld_path = os.pathsep.join(lib_dirs)
        inc_path = os.pathsep.join(inc_dirs)

        env = (
            'export PYTHONHOME="{py_pkg}" && '
            'export PYTHONPATH="{st}" && '
            'export LD_LIBRARY_PATH="{ld}" && '
            'export LIBRARY_PATH="{ld}" && '
            'export LDFLAGS="-fuse-ld=bfd -L{py_lib} -lpython{ver}" && '
            'export C_INCLUDE_PATH="{inc}" && '
            'export CFLAGS="-fPIC -O2 -fuse-ld=bfd" && '
            # CPP must be the *preprocessor* ("clang -E"): setup.py's
            # _read_header runs `CPP cflags include1.h` and reads the
            # preprocessed output from stdout (autotools sets CPP=CC -E).
            'export CPP="{cc} -E {incflags}" && '
            'export SWIG_LIB="{swig_lib}" && '
            'export PATH="{swig_bin}:$PATH" && '
            '"{py_bin}" setup.py build'
        ).format(
            py_pkg=py_pkg, st=st_dir, ld=ld_path, py_lib=py_lib,
            ver=_PY_VERSION, inc=inc_path,
            incflags=" ".join("-I{}".format(d) for d in inc_dirs),
            cc=cc, swig_lib=swig_lib, swig_bin=swig_bin_dir, py_bin=py_bin,
        )
        self.run(env, env="conanbuild", cwd=build_dir)

    # ------------------------------------------------------------------ #
    # package
    # ------------------------------------------------------------------ #
    def package(self):
        build_dir = os.path.join(self.build_folder, "pgmbuild")
        # build_lib is <pgmbuild>/build/lib.<platform>-gpg-less dir, e.g.
        #   build/lib.harmonyos-...-cpython-312/gpg
        matches = sorted(glob.glob(
            os.path.join(build_dir, "build", "lib*", "gpg")))
        src_gpg = None
        for full in matches:
            if os.path.isdir(full) and \
                    any(f.startswith("_gpgme") and f.endswith(".so")
                        for f in os.listdir(full)):
                src_gpg = full
                break
        if src_gpg is None:
            raise RuntimeError(
                "gpg build_lib directory with _gpgme*.so not found in "
                "{}".format(build_dir))

        dst = os.path.join(self.package_folder, _SITE_PKG, "gpg")
        # keep_path=True preserves the gpg/constants/{data,keylist,sig,tofu}
        # subpackage tree (src_gpg is the build_lib gpg/ dir).
        copy(self, "*.py", src=src_gpg, dst=dst, keep_path=True)
        copy(self, "*.so", src=src_gpg, dst=dst, keep_path=True)

        if not os.path.isfile(os.path.join(dst, "__init__.py")):
            raise RuntimeError("gpg/__init__.py missing in package folder")
        if not any(f.startswith("_gpgme") and f.endswith(".so")
                   for f in os.listdir(dst)):
            raise RuntimeError("_gpgme*.so missing in package folder")

        # Re-sign the extension AFTER copy (conan copy invalidates the ELF
        # signature; HMDFS blocks dlopen of unsigned .so — E212 pattern).
        signer = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        self.output.info("Signing _gpgme extension in package folder...")
        self.run(
            'for f in {dst}/_gpgme*.so; do '
            'chmod 755 "$f" && '
            '{objcopy} --remove-section .codesign "$f" 2>/dev/null; '
            '{signer} sign -inFile "$f" -outFile "$f.signed" -selfSign 1 && '
            'mv -f "$f.signed" "$f" && chmod 755 "$f"; '
            "done".format(dst=dst, objcopy=objcopy, signer=signer)
        )

    def package_info(self):
        # _gpgme*.so links against libpython3.12.so (NEEDED) plus the
        # gpgme/libgpg-error runtime — all three are real transitive deps.
        self.cpp_info.libs = ["gpgme", "gpg-error"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.requires = [
            "gpgme::gpgme",
            "libgpg-error::libgpg-error",
            "python::python",
            # swig is a build-time CLI only; referenced here because conan's
            # check_component_requires demands every direct host require to
            # appear in cpp_info.requires.
            "swig::swig",
        ]
        self.cpp_info.set_property("cmake_target_name", "gpgmepy::gpgmepy")
