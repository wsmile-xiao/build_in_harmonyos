#!/usr/bin/env python3
"""Conan recipe for contourpy 1.2.1 on HarmonyOS PC (OHOS aarch64).

contourpy renders contour lines and polygons (used by matplotlib).
Pure C++ extension via meson + pybind11; runtime dependency: numpy.

OHOS adaptations (same family as the numpy 2.5.2 recipe):
  - posix_spawn does not search PATH -> sitecustomize.py shim
  - musl does not export main exe symbols -> -lpython3.12
  - lld default linker (DevBox auto-signs outputs; NEVER -fuse-ld=bfd)
  - meson install --no-rebuild (conan package() env strips PATH)
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches
from conan.tools.layout import basic_layout


class ContourpyConan(ConanFile):
    name = "contourpy"
    version = "1.2.1"
    description = "Python library for calculating contours in 2D quadrilateral grids"
    license = "BSD-3-Clause"
    homepage = "https://github.com/contourpy/contourpy"
    url = "https://github.com/contourpy/contourpy"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    _hnp_bin = "/data/service/hnp/bin"

    def requirements(self):
        # Bare reference: the ohpcd registry publishes numpy/2.5.2 without
        # namespace (matplotlib 3.11.1 recipe, CI #49397: namespaced
        # numpy/2.5.2@ohpcd/stable does not resolve from the registry).
        self.requires("numpy/2.5.2")

    def build_requirements(self):
        # ninja for meson; comes from the ohpcd registry (CI capability matrix).
        self.tool_requires("ninja/1.12.1")

    def layout(self):
        basic_layout(self, src_folder="src")

    def validate(self):
        # R32: platform check must use `in ("Linux", "OHOS")`
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"contourpy 1.2.1 only supports Linux/OHOS, got {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        source = self.source_folder
        hnp_bin = self._hnp_bin

        # OHOS shim: sitecustomize patches subprocess PATH search + auto-sign.
        shim_dir = os.path.join(self.build_folder, "_ohos_shim")
        self._create_sitecustomize(shim_dir)

        # Bootstrap python build deps (meson/meson-python/pybind11/setuptools)
        # for bare target pythons (CI workers ship HNP python without them).
        python3 = self._target_python()
        boot_dir = os.path.join(self.build_folder, "_pybootstrap")
        os.makedirs(boot_dir, exist_ok=True)
        import subprocess as _sp
        need = []
        for mod, pkg in (
            ("mesonbuild", "meson"),
            ("mesonpy", "meson-python"),
            ("pybind11", "pybind11"),
            ("setuptools", "setuptools"),
            ("pyproject_metadata", "pyproject-metadata"),
        ):
            r = _sp.run([python3, "-c", f"import {mod}"], capture_output=True)
            if r.returncode != 0:
                need.append(pkg)
        for pkg in need:
            self.output.info(f"bootstrapping {pkg} (missing in target python)")
            r = _sp.run(
                [python3, "-m", "pip", "install", "--no-deps",
                 "--target", boot_dir, pkg,
                 "-i", "https://pypi.tuna.tsinghua.edu.cn/simple",
                 "--trusted-host", "pypi.tuna.tsinghua.edu.cn"],
                capture_output=True, text=True)
            if r.returncode != 0:
                self.output.warning(f"pip install {pkg}: {r.stderr[:150]}")

        python_lib = self._python_lib_dir()
        libcxx = self._libcxx_dir()

        # Write meson native file (build runs ON the OHOS device).
        native_file = os.path.join(shim_dir, "ohos-native.ini")
        self._write_native_file(native_file, hnp_bin, python_lib)

        # The target python's meson (pip) drives the build (contourpy has no
        # vendored meson; needs plain meson >= 1.2).
        # PKG_CONFIG_PATH: meson's dependency('pybind11') tries pkg-config
        # first; pybind11 ships a .pc in site-packages/pybind11/share/pkgconfig.
        pkg_parts = []
        pybind11_pc = os.path.join(
            os.path.dirname(os.path.dirname(python3)), "lib",
            "python3.12", "site-packages", "pybind11", "share", "pkgconfig")
        if os.path.isdir(pybind11_pc):
            pkg_parts.append(pybind11_pc)
        # Bootstrapped pybind11 (CI bare target pythons) also ships a .pc.
        boot_pc = os.path.join(boot_dir, "pybind11", "share", "pkgconfig")
        if os.path.isdir(boot_pc) and boot_pc not in pkg_parts:
            pkg_parts.append(boot_pc)
        pkg_config_path = os.environ.get("PKG_CONFIG_PATH", "")
        if pkg_parts:
            os.environ["PKG_CONFIG_PATH"] = (
                ":".join(pkg_parts) + (f":{pkg_config_path}" if pkg_config_path else ""))

        old_pythonpath = os.environ.get("PYTHONPATH", "")
        old_ld = os.environ.get("LD_LIBRARY_PATH")
        try:
            # numpy importable at build time (build_config probe imports the
            # mesonpy module only, but meson's python.find_installation runs
            # sanity probes against the target interpreter; keep numpy on the
            # path for consistency with the matplotlib recipe family).
            py_parts = [shim_dir]
            numpy_pkg = self._dep_package_folder("numpy")
            numpy_sp = self._site_packages_of(numpy_pkg) if numpy_pkg else ""
            if numpy_sp:
                py_parts.append(numpy_sp)
            os.environ["PYTHONPATH"] = ":".join(py_parts)
            existing = os.environ.get("LD_LIBRARY_PATH", "")
            for lib in (python_lib, libcxx):
                if lib and lib not in existing:
                    existing = f"{lib}:{existing}" if existing else lib
            if numpy_pkg and numpy_pkg not in existing:
                existing = f"{numpy_pkg}/lib:{existing}" if existing else f"{numpy_pkg}/lib"
            os.environ["LD_LIBRARY_PATH"] = existing

            # Environment on the COMMAND LINE (conan env wrapper strips
            # os.environ edits — matplotlib/numpy recipe family lesson):
            # PYTHONPATH = boot_dir first (bootstrap modules shadow stale
            # copies) + shim + numpy site-packages.
            pkg_path = os.environ.get("PKG_CONFIG_PATH", "")
            py_path_cmd = os.environ.get("PYTHONPATH", "")
            if boot_dir not in py_path_cmd:
                py_path_cmd = f"{boot_dir}:{py_path_cmd}" if py_path_cmd else boot_dir
            # LD_LIBRARY_PATH: python lib + libcxx + libxml2 (ld.lld NEEDs
            # libxml2.so.16 on some CI workers; matplotlib CI #50368) +
            # numpy package libs; APPEND $LD_LIBRARY_PATH to keep any
            # conan buildenv contributions.
            ld_parts = [p for p in (
                *self._libxml2_dirs(), libcxx, python_lib,
                f"{numpy_pkg}/lib" if numpy_pkg else "",
                os.environ.get("LD_LIBRARY_PATH", "")) if p]
            ld_path_cmd = ":".join(ld_parts)
            setup_cmd = (
                f'PKG_CONFIG_PATH="{pkg_path}" PYTHONPATH="{py_path_cmd}" '
                f'LD_LIBRARY_PATH="{ld_path_cmd}" '
                f'"{python3}" -m mesonbuild.mesonmain '
                f'setup "{os.path.join(self.build_folder, "builddir")}" '
                f'"{source}" --prefix="{self.package_folder}" '
                f'--buildtype=release -Dcpp_std=c++17 '
                f'--native-file="{native_file}"'
            )

            self.run(setup_cmd, cwd=self.build_folder)
            self.run(
                f'LD_LIBRARY_PATH="{ld_path_cmd}" '
                f'ninja -C "{os.path.join(self.build_folder, "builddir")}"',
                cwd=self.build_folder)
        finally:
            if old_pythonpath:
                os.environ["PYTHONPATH"] = old_pythonpath
            else:
                os.environ.pop("PYTHONPATH", None)
            if old_ld is not None:
                os.environ["LD_LIBRARY_PATH"] = old_ld
            else:
                os.environ.pop("LD_LIBRARY_PATH", None)
            if pkg_config_path:
                os.environ["PKG_CONFIG_PATH"] = pkg_config_path
            else:
                os.environ.pop("PKG_CONFIG_PATH", None)

    def package(self):
        source = self.source_folder
        python3 = self._target_python()
        # boot_dir is a build()-local name; recompute the same deterministic
        # path here (NameError on the build()-local variable otherwise —
        # matplotlib 3.11.1 recipe precedent).
        boot_dir = os.path.join(self.build_folder, "_pybootstrap")
        # --no-rebuild: build tree is fresh from build(); skips the pre-install
        # rebuild whose ninja PATH lookup breaks under conan's env wrapper.
        self.run(
            f'PYTHONPATH="{boot_dir}" '
            f'"{python3}" -m mesonbuild.mesonmain '
            f'install --no-rebuild -C "{os.path.join(self.build_folder, "builddir")}"',
            cwd=self.build_folder)
        if self.settings.os == "OHOS":
            # lld auto-signing is unreliable for extension .so outputs
            # (numpy/matplotlib recipe family): re-sign all packaged .so
            # files explicitly (idempotent). Without this dlopen fails
            # with EACCES even though a .codesign section exists.
            import glob
            import subprocess
            sign_tool = "/data/service/hnp/bin/binary-sign-tool"
            for so in glob.glob(os.path.join(
                    self.package_folder, "lib", "python*", "site-packages",
                    "contourpy", "**", "*.so"), recursive=True):
                r = subprocess.run(
                    [sign_tool, "sign", "-inFile", so, "-outFile", so,
                     "-selfSign", "1", "-signAlg", "SHA256withECDSA"],
                    capture_output=True, text=True)
                if r.returncode != 0:
                    self.output.warning(f"re-sign failed for {so}: {r.stderr[:100]}")
                else:
                    self.output.info(f"re-signed {os.path.basename(so)}")

    def package_info(self):
        # Consumed via PYTHONPATH (site-packages), not linked as C libs.
        self.cpp_info.libs = []
        import glob
        for site_packages in sorted(glob.glob(
                os.path.join(self.package_folder, "lib", "python*", "site-packages"))):
            self.runenv_info.prepend_path("PYTHONPATH", site_packages)

    # ─────────────────── helpers ───────────────────

    def _dep_package_folder(self, name):
        for ref, dep in self.dependencies.items():
            # conan 2.x: ref is a Requirement; the package name lives on
            # ref.ref.name (conan 2.29).
            dep_name = getattr(getattr(ref, "ref", None), "name", None) \
                or str(ref).split("/")[0]
            if dep_name == name:
                return dep.package_folder
        return None

    def _site_packages_of(self, pkg):
        import glob
        hits = sorted(glob.glob(os.path.join(pkg, "lib", "python*", "site-packages")))
        return hits[0] if hits else ""

    def _libxml2_dirs(self):
        """ld.lld NEEDs libxml2.so.16 which lives in the SDK llvm/lib dir
        (NOT aarch64-linux-ohos). lld's RUNPATH $ORIGIN/../lib normally
        resolves it, but on CI workers the exec chain can lose $ORIGIN
        resolution (CI #50735: 'Error loading shared library libxml2.so.16
        ... needed by lld' -> meson linker detection fails -> build dies).
        Return BOTH: the SDK llvm/lib (authoritative libxml2.so.16 source)
        and hnp libxml2.org (matplotlib CI #50368 precedent)."""
        import glob
        dirs = []
        for pattern in (
            "/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib",
            "/data/service/hnp/ohos-sdk*/ohos/native/llvm/lib",
        ):
            for h in sorted(glob.glob(pattern)):
                if os.path.isfile(os.path.join(h, "libxml2.so.16")) and h not in dirs:
                    dirs.append(h)
            if dirs:
                break
        for pattern in (
            "/data/service/hnp/libxml2.org/*/lib",
            "/data/service/hnp/libxml2*/lib",
        ):
            hits = sorted(glob.glob(pattern))
            if hits and hits[-1] not in dirs:
                dirs.append(hits[-1])
        return dirs

    def _target_python(self):
        candidates = [
            os.environ.get("CONTOURPY_PYTHON") or os.environ.get("NUMPY_PYTHON"),
            os.environ.get("OHOS_PYTHON"),
            os.path.expanduser("~/usr/local/bin/python3"),
            "/storage/Users/currentUser/usr/local/bin/python3",
            shutil.which("python3") or "",
        ]
        for py in candidates:
            if py and os.path.isfile(py):
                return py
        raise ConanException("no target python3 found; set CONTOURPY_PYTHON")

    def _python_lib_dir(self):
        if self.settings.os != "OHOS":
            return ""
        py = self._target_python()
        prefix = os.path.dirname(os.path.dirname(os.path.realpath(py)))
        for libdir in (os.path.join(prefix, "lib"), os.path.join(prefix, "lib64")):
            if os.path.isdir(libdir) and any(
                    f.startswith("libpython3") for f in os.listdir(libdir)):
                return libdir
        return os.path.expanduser("~/usr/local/lib")

    def _libcxx_dir(self):
        import glob
        for pattern in (
            "/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib/aarch64-linux-ohos",
            "/data/service/hnp/ohos-sdk*/ohos/native/llvm/lib/aarch64-linux-ohos",
        ):
            hits = sorted(glob.glob(pattern))
            if hits:
                return hits[-1]
        return ""

    def _create_sitecustomize(self, directory):
        os.makedirs(directory, exist_ok=True)
        path = os.path.join(directory, "sitecustomize.py")
        content = '''"""HarmonyOS subprocess compatibility shim.

On OHOS:
1. posix_spawn does not search PATH for bare command names.
2. Unsigned ELF binaries cannot execute (EACCES).

Patches subprocess.Popen to resolve bare commands via shutil.which and
auto-sign unsigned ELF executables before first exec.
"""
import os
import shutil
import subprocess

_HNP_BIN = "/data/service/hnp/bin"
_SIGN_TOOL = os.path.join(_HNP_BIN, "binary-sign-tool")
_READELF = os.path.join(_HNP_BIN, "llvm-readelf")


def _is_unsigned_elf(path):
    if path in (_SIGN_TOOL, _READELF):
        return False
    try:
        with open(path, "rb") as fh:
            if fh.read(4) != b"\\x7fELF":
                return False
        out = subprocess.run([_READELF, "-SW", path],
                             capture_output=True, text=True)
        return ".codesign" not in out.stdout
    except Exception:
        return False


def _sign_elf(path):
    try:
        signed = path + ".signed"
        cmd = [_SIGN_TOOL, "sign", "-inFile", path, "-outFile", signed,
               "-selfSign", "1", "-signAlg", "SHA256withECDSA",
               "-keyAlias", "meson"]
        subprocess.run(cmd, capture_output=True)
        if os.path.exists(signed) and os.path.getsize(signed) > 0:
            os.replace(signed, path)
            os.chmod(path, 0o755)
            return True
    except Exception:
        pass
    return False


def _resolve_command(command):
    if not isinstance(command, (str, bytes, os.PathLike)):
        return None
    command = os.fspath(command)
    if os.path.dirname(command):
        return command if os.path.isfile(command) else None
    return shutil.which(command)


if not getattr(subprocess.Popen.__init__, "_ohos_path_fix", False):
    _orig = subprocess.Popen.__init__

    def _patched(self, args, *a, **kw):
        exe = kw.get("executable")
        target = None
        if exe is not None:
            r = _resolve_command(exe)
            if r is not None:
                kw["executable"] = r
                target = r
        elif isinstance(args, (list, tuple)) and args:
            r = _resolve_command(args[0])
            if r is not None:
                args = list(args)
                args[0] = r
                target = r
        elif isinstance(args, (str, bytes, os.PathLike)):
            r = _resolve_command(args)
            if r is not None:
                args = r
                target = r
        if target and _is_unsigned_elf(target):
            _sign_elf(target)
        _orig(self, args, *a, **kw)

    _patched._ohos_path_fix = True
    subprocess.Popen.__init__ = _patched
'''
        with open(path, "w") as f:
            f.write(content)

    def _write_native_file(self, path, hnp_bin, python_lib_dir):
        content = f"""[binaries]
c = '{hnp_bin}/clang'
cpp = '{hnp_bin}/clang++'
ar = '{hnp_bin}/llvm-ar'
ld = '{hnp_bin}/ld.lld'
ranlib = '{hnp_bin}/llvm-ranlib'
strip = '{hnp_bin}/llvm-strip'
nm = '{hnp_bin}/llvm-nm'
objcopy = '{hnp_bin}/llvm-objcopy'

[built-in options]
# NOTE: no -fuse-ld=bfd (breaks DevBox auto-signing -> EACCES).
c_link_args = ['-L{python_lib_dir}', '-lpython3.12']
cpp_link_args = ['-L{python_lib_dir}', '-lpython3.12']

[build_machine]
system = 'linux'
cpu_family = 'aarch64'
cpu = 'aarch64'
endian = 'little'

[host_machine]
system = 'linux'
cpu_family = 'aarch64'
cpu = 'aarch64'
endian = 'little'
"""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(content)
