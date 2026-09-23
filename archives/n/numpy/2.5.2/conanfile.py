#!/usr/bin/env python3
"""Conan recipe for numpy 2.5.2 on HarmonyOS PC (OHOS aarch64).

numpy is a Python package with C extensions built via vendored meson.

Key design decisions (learned from prior attempts #3950 / #5882 / #6386):
  1. Use the official PyPI sdist, NOT the GitHub tag archive.
     The sdist ships all git submodules pre-populated (vendored-meson with
     'features' module, highway, pocketfft, pythoncapi-compat), eliminating
     fragile in-build submodule downloads from third-party mirrors.
  2. Source URL points to the Tsinghua PyPI mirror: CI Workers cannot reach
     files.pythonhosted.org (network policy), but pypi.tuna.tsinghua.edu.cn
     is reachable and serves the exact same artifact (same sha256).
  3. CPU dispatch: numpy's vendored meson handles aarch64 natively via
     meson_cpu/arm. We pin -Dcpu-baseline=min -Dcpu-dispatch= so no
     x86 SIMD (SSE/AVX/xop/fma4) is ever probed on ARM.
  4. OHOS quirks handled:
     - posix_spawn does not search PATH -> sitecustomize.py shim
     - use the default lld linker; DevBox clang auto-signs lld outputs
       (forcing -fuse-ld=bfd DISABLES auto-signing -> EACCES on every binary)
     - musl does not export main executable symbols -> -lpython3.12
     - unsigned ELF cannot execute/dlopen -> binary-sign-tool signing
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches
from conan.tools.layout import basic_layout


class NumpyConan(ConanFile):
    name = "numpy"
    version = "2.5.2"
    description = "NumPy is the fundamental package for array computing with Python"
    license = "BSD-3-Clause"
    homepage = "https://numpy.org"
    url = "https://github.com/numpy/numpy"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    _hnp_bin = "/data/service/hnp/bin"

    def requirements(self):
        self.requires("openblas/0.3.34")

    def build_requirements(self):
        # E428+ninja 探测双保险：tool_requires 让 conan 在 build/package 阶段
        # 把 ninja 注入 PATH（conanbuild env），同时保留 vendored meson 的
        # 绝对路径 fallback 补丁。CI 能力矩阵：ninja/meson ✅ 已发布。
        self.tool_requires("ninja/1.12.1")

    def layout(self):
        basic_layout(self, src_folder="src")

    def export_sources(self):
        # Patches folder kept even when empty: apply_conandata_patches() in
        # build() tolerates an empty patch list, and keeping the export rule
        # avoids a "missing patches dir" failure when patches are added later.
        patches_dir = os.path.join(self.recipe_folder, "patches")
        if os.path.isdir(patches_dir):
            copy(self, "*", patches_dir, os.path.join(self.export_sources_folder, "patches"))

    def validate(self):
        # R32: platform check must use `in ("Linux", "OHOS")`
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"numpy 2.5.2 only supports Linux/OHOS, got {self.settings.os}")

    def source(self):
        # PyPI sdist: submodules are pre-populated, vendored meson is complete.
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # R33: compiler paths come from Conan conf, never bare shell env vars.
        # The OHOS profile sets tools.build:compiler_executables for c/cpp.
        pass  # toolchain handled via meson cross/native files in build()

    def build(self):
        apply_conandata_patches(self)
        source = self.source_folder
        hnp_bin = self._hnp_bin

        # Vendored meson (ships 'features' module numpy requires) — comes
        # straight from the sdist, no download needed.
        vendored_meson = os.path.join(source, "vendored-meson", "meson", "meson.py")
        if not os.path.exists(vendored_meson):
            raise ConanException(
                "vendored meson missing from sdist — expected pre-populated submodules")
        # Absolute target python: bare "python3" may resolve to a different
        # interpreter than the one that bootstrapped cython (PATH-dependent).
        python3 = self._target_python()
        meson_cmd = f'"{python3}" "{vendored_meson}"'

        # OHOS shim: sitecustomize patches subprocess PATH search + auto-sign.
        shim_dir = os.path.join(self.build_folder, "_ohos_shim")
        self._create_sitecustomize(shim_dir)
        # Python bootstrap dir (cython/meson-python when the target python
        # is bare, e.g. CI workers).
        boot_dir = os.path.join(self.build_folder, "_pybootstrap")
        # numpy's meson build requires `cython` runnable by the TARGET python
        # (meson probes `cython -V`). The OHOS pip wrapper scripts exec
        # `python3 -m cython`, so the module must be importable by the target
        # interpreter. Verify and give a clear error early instead of letting
        # meson fail with "Unknown compiler(s): [['cython'], ['cython3']]".
        import subprocess as _sp
        probe = _sp.run(
            [python3, "-m", "cython", "--version"],
            capture_output=True, text=True)
        if probe.returncode != 0:
            # CI workers ship a bare target python without cython — bootstrap
            # into the build folder (never touch the system python) and keep
            # it on PYTHONPATH for the whole build. Tsinghua mirror only
            # (workers cannot reach files.pythonhosted.org).
            self.output.info("cython missing; bootstrapping into build folder")
            boot_dir = os.path.join(self.build_folder, "_pybootstrap")
            os.makedirs(boot_dir, exist_ok=True)
            for pkg in ("cython", "meson-python", "pyproject-metadata",
                        "setuptools-scm", "vcs-versioning", "packaging"):
                r = _sp.run(
                    [python3, "-m", "pip", "install", "--no-deps",
                     "--target", boot_dir, pkg,
                     "-i", "https://pypi.tuna.tsinghua.edu.cn/simple",
                     "--trusted-host", "pypi.tuna.tsinghua.edu.cn"],
                    capture_output=True, text=True, timeout=300)
                if r.returncode != 0:
                    self.output.warning(f"pip install {pkg}: {r.stderr[:150]}")
            reprobe = _sp.run(
                [python3, "-m", "cython", "--version"],
                capture_output=True, text=True,
                env={**os.environ, "PYTHONPATH": boot_dir})
            if reprobe.returncode == 0:
                self.output.info("cython bootstrapped OK")
            else:
                raise ConanException(
                    f"cython bootstrap failed for {python3}: "
                    f"{reprobe.stderr[:200]}")

        # Locate a usable non-HNP target python for -lpython3.12 linkage.
        python_lib_dir = self._python_lib_dir()

        # Write meson native file (build runs on the OHOS device itself).
        cross_arg = ""
        if self.settings.os == "OHOS":
            exe_wrapper = os.path.join(shim_dir, "ohos_exe_wrapper.sh")
            self._create_exe_wrapper(exe_wrapper, hnp_bin)
            native_file = os.path.join(shim_dir, "ohos-native.ini")
            self._write_native_file(native_file, hnp_bin, python_lib_dir, exe_wrapper)
            cross_arg = f'--native-file="{native_file}"'

        # Meson setup. CPU options pin aarch64-safe baselines (no x86 SIMD).
        # openblas comes from the conan requirement (virtualrunenv/pkgconf).
        setup_cmd = (
            f'{meson_cmd} setup "{os.path.join(self.build_folder, "builddir")}" '
            f'"{source}" --prefix="{self.package_folder}" '
            f'--buildtype=release -Dblas=openblas -Dlapack=openblas '
            f'-Dcpu-baseline=min -Dcpu-dispatch= '
            f'-Dcpp_std=c++17'
        )
        if cross_arg:
            setup_cmd += f" {cross_arg}"
        # put bootstrap bin/ first on PATH so meson finds the cython executable
        boot_bin = os.path.join(boot_dir, "bin")
        if os.path.isdir(boot_bin):
            setup_cmd = f'PATH="{boot_bin}:$PATH" {setup_cmd}'
        # PYTHONPATH prefix (command line, NOT os.environ — conan's env wrapper
        # strips env edits): sitecustomize shim (auto-sign for OHOS workers
        # whose lld lacks auto-signing) + bootstrap modules (cython/meson-python).
        setup_cmd = f'PYTHONPATH="{shim_dir}:{boot_dir}" {setup_cmd}'

        old_pythonpath = os.environ.get("PYTHONPATH", "")
        old_ld_library_path = os.environ.get("LD_LIBRARY_PATH")
        _path_parts = [shim_dir]
        if os.path.isdir(boot_dir):
            _path_parts.append(boot_dir)  # cython/meson-python bootstrap
        if self.settings.os == "OHOS":
            os.environ["PYTHONPATH"] = ":".join(
                _path_parts + ([old_pythonpath] if old_pythonpath else []))
            # libpython3.12.so lives in ~/usr/local/lib; sanity check and test
            # binaries link against it and need it on the loader path.
            python_lib = self._python_lib_dir()
            extra_libs = [python_lib, self._libcxx_dir(), self._libxml2_dir()]
            existing = os.environ.get("LD_LIBRARY_PATH", "")
            for lib in extra_libs:
                if lib and lib not in existing:
                    existing = f"{lib}:{existing}" if existing else lib
            os.environ["LD_LIBRARY_PATH"] = existing

        # LD_LIBRARY_PATH prefix: the SDK lld links libxml2/libc++ which are
        # not on the default loader path of some CI workers (xmlFree symbol
        # not found). Ride on the command line like everything else.
        _ld_parts = [p for p in (
            self._libxml2_dir(), self._libcxx_dir(),
            python_lib if self.settings.os == "OHOS" else "") if p]
        if _ld_parts:
            setup_cmd = (f'LD_LIBRARY_PATH="{":".join(_ld_parts)}:$LD_LIBRARY_PATH" '
                         f'{setup_cmd}')
        try:
            self.run(setup_cmd, cwd=self.build_folder)
            # Same env prefixes as setup: PATH (cython), PYTHONPATH (shim +
            # bootstrap), LD_LIBRARY_PATH (SDK lld's libxml2/libc++ deps) —
            # clang invokes lld during compilation too, not just at setup.
            boot_bin = os.path.join(boot_dir, "bin")
            ninja_env = (
                f'PATH="{boot_bin}:$PATH" '
                f'PYTHONPATH="{shim_dir}:{boot_dir}" '
                f'LD_LIBRARY_PATH="{":".join(_ld_parts)}:$LD_LIBRARY_PATH"'
                if _ld_parts else
                f'PATH="{boot_bin}:$PATH" PYTHONPATH="{shim_dir}:{boot_dir}"'
            )
            self.run(
                f'{ninja_env} ninja -C "{os.path.join(self.build_folder, "builddir")}"',
                cwd=self.build_folder)
        finally:
            if old_pythonpath:
                os.environ["PYTHONPATH"] = old_pythonpath
            else:
                os.environ.pop("PYTHONPATH", None)
            if old_ld_library_path is not None:
                os.environ["LD_LIBRARY_PATH"] = old_ld_library_path
            else:
                os.environ.pop("LD_LIBRARY_PATH", None)


    def package(self):
        source = self.source_folder
        vendored_meson = os.path.join(source, "vendored-meson", "meson", "meson.py")
        # Absolute paths everywhere: the conan package() env wrapper resets
        # PATH, so bare "python3"/"ninja" are not resolvable. meson install
        # re-invokes ninja to verify the build tree -> prepend hnp bin via the
        # command itself (self.run's env wrapper would drop os.environ edits).
        python3 = self._target_python()
        # --no-rebuild: package() runs right after build(), the build tree is
        # fresh, so meson's pre-install rebuild (which needs to locate ninja
        # through PATH that conan's env wrapper strips) is a no-op anyway.
        # Skipping it removes the ninja PATH lookup entirely (E428 root cause).
        self.run(
            f'"{python3}" "{vendored_meson}" '
            f'install --no-rebuild -C "{os.path.join(self.build_folder, "builddir")}"',
            cwd=self.build_folder)
        if self.settings.os == "OHOS":
            # CI workers' lld lacks auto-signing — every .so in the package
            # is unsigned and would fail dlopen with EACCES in test_package.
            # Re-sign all packaged .so files explicitly (idempotent).
            import glob
            import subprocess
            sign_tool = "/data/service/hnp/bin/binary-sign-tool"
            for so in glob.glob(os.path.join(
                    self.package_folder, "lib", "python*", "site-packages",
                    "numpy", "**", "*.so"), recursive=True):
                r = subprocess.run(
                    [sign_tool, "sign", "-inFile", so, "-outFile", so,
                     "-selfSign", "1", "-signAlg", "SHA256withECDSA"],
                    capture_output=True, text=True, timeout=60)
                if r.returncode != 0:
                    self.output.warning(f"re-sign failed: {so}: {r.stderr[:100]}")
            self.output.info("re-signed packaged .so files for OHOS")

    def package_info(self):
        # numpy is consumed via PYTHONPATH (site-packages), not linked as C libs.
        self.cpp_info.libs = []
        for site_packages in self._site_packages_dirs():
            self.runenv_info.prepend_path("PYTHONPATH", site_packages)

    # ─────────────────── helpers ───────────────────

    def _site_packages_dirs(self):
        import glob
        return sorted(glob.glob(os.path.join(self.package_folder, "lib", "python*", "site-packages")))

    def _target_python(self):
        """Absolute path of the non-HNP target python (used for cython probe)."""
        candidates = [
            os.environ.get("NUMPY_PYTHON"),
            os.environ.get("OHOS_PYTHON"),
            os.path.expanduser("~/usr/local/bin/python3"),
            "/storage/Users/currentUser/usr/local/bin/python3",
            shutil.which("python3") or "",
        ]
        for py in candidates:
            if py and os.path.isfile(py):
                return py
        raise ConanException("no target python3 found; set NUMPY_PYTHON")

    def _libxml2_dir(self):
        """ld.lld on some CI workers fails with 'xmlFree: symbol not found'
        (the SDK lld links libxml2 which is not in the default loader path).
        hnp ships libxml2 — surface its lib dir for LD_LIBRARY_PATH."""
        import glob
        for pattern in (
            "/data/service/hnp/libxml2.org/*/lib",
            "/data/service/hnp/libxml2*/lib",
        ):
            hits = sorted(glob.glob(pattern))
            if hits and any(f.startswith("libxml2.so") for f in os.listdir(hits[-1])):
                return hits[-1]
        return ""

    def _libcxx_dir(self):
        """libc++_shared.so dir (OHOS SDK llvm runtime)."""
        import glob as _glob
        for pattern in (
            "/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib/aarch64-linux-ohos",
            "/data/service/hnp/ohos-sdk*/ohos/native/llvm/lib/aarch64-linux-ohos",
        ):
            hits = sorted(_glob.glob(pattern))
            if hits:
                return hits[-1]
        return ""

    def _python_lib_dir(self):
        """Find the non-HNP target python library dir (libpython3.12 lives there)."""
        if self.settings.os != "OHOS":
            return ""
        candidates = []
        env_py = os.environ.get("NUMPY_PYTHON") or os.environ.get("OHOS_PYTHON")
        if env_py:
            candidates.append(env_py)
        candidates.extend([
            os.path.expanduser("~/usr/local/bin/python3"),
            "/storage/Users/currentUser/usr/local/bin/python3",
            shutil.which("python3") or "",
        ])
        seen = set()
        for py in candidates:
            if not py or not os.path.isfile(py) or py in seen:
                continue
            seen.add(py)
            prefix = os.path.dirname(os.path.dirname(os.path.realpath(py)))
            for libdir in (os.path.join(prefix, "lib"), os.path.join(prefix, "lib64")):
                if os.path.isdir(libdir) and any(
                        f.startswith("libpython3") for f in os.listdir(libdir)):
                    return libdir
        # Fall back to the wizard-installed location.
        return os.path.expanduser("~/usr/local/lib")

    def _create_sitecustomize(self, directory):
        """Patch subprocess PATH lookup + auto-sign built binaries on OHOS.

        - OHOS posix_spawn does not search PATH -> resolve via shutil.which
        - OHOS security model blocks unsigned ELF -> sign before first exec
        """
        os.makedirs(directory, exist_ok=True)
        path = os.path.join(directory, "sitecustomize.py")
        content = '''"""HarmonyOS subprocess compatibility shim.

On OHOS:
1. posix_spawn does not search PATH for bare command names.
2. Unsigned ELF binaries cannot execute (EACCES).

This module patches subprocess.Popen to:
- resolve bare commands to absolute paths via shutil.which
- auto-sign (binary-sign-tool selfSign) any ELF executable that lacks a
  code-signature section, right before it is spawned.
"""
import os
import shutil
import subprocess

_HNP_BIN = "/data/service/hnp/bin"
_SIGN_TOOL = os.path.join(_HNP_BIN, "binary-sign-tool")
_READELF = os.path.join(_HNP_BIN, "llvm-readelf")


def _is_unsigned_elf(path):
    try:
        with open(path, "rb") as fh:
            if fh.read(4) != b"\\x7fELF":
                return False
        out = subprocess.run([_READELF, "-SW", path],
                             capture_output=True, text=True, timeout=15)
        return ".codesign" not in out.stdout
    except Exception:
        return False


def _sign_elf(path):
    # timeout: a hung sign-tool would silently stall the whole build
    # (observed as an 85+ minute CI run with no output).
    try:
        signed = path + ".signed"
        cmd = [_SIGN_TOOL, "sign", "-inFile", path, "-outFile", signed,
               "-selfSign", "1", "-signAlg", "SHA256withECDSA",
               "-keyAlias", "meson"]
        subprocess.run(cmd, capture_output=True, timeout=30)
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

    def _create_exe_wrapper(self, path, hnp_bin):
        """exe_wrapper for meson: sign then run compiled test binaries."""
        content = f'''#!/data/service/hnp/bin/bash
# exe_wrapper for HarmonyOS: signs then runs compiled binaries
BINARY="$1"
shift
SIGN_TOOL="{hnp_bin}/binary-sign-tool"
if [ -f "$BINARY" ]; then
    if ! {hnp_bin}/llvm-readelf -S "$BINARY" 2>/dev/null | grep -q "ohos_code_sign"; then
        "$SIGN_TOOL" sign -inFile "$BINARY" -outFile "$BINARY" -selfSign 1 -signAlg SHA256withECDSA -keyAlias meson >/dev/null 2>&1
        chmod +x "$BINARY" 2>/dev/null
    fi
fi
exec "$BINARY" "$@"
'''
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(content)
        os.chmod(path, 0o755)

    def _write_native_file(self, path, hnp_bin, python_lib_dir, exe_wrapper):
        """Meson native file: we build ON the OHOS device (build == host)."""
        content = f"""[binaries]
c = '{hnp_bin}/clang'
cpp = '{hnp_bin}/clang++'
ar = '{hnp_bin}/llvm-ar'
ld = '{hnp_bin}/ld.bfd'
ranlib = '{hnp_bin}/llvm-ranlib'
strip = '{hnp_bin}/llvm-strip'
nm = '{hnp_bin}/llvm-nm'
objcopy = '{hnp_bin}/llvm-objcopy'
exe_wrapper = '{exe_wrapper}'

[built-in options]
# Use ld.bfd: the SDK's lld links against libxml2 which is broken/missing
# on CI workers (xmlFree symbol not found — runs #36676/#36866). bfd has no
# such dependency. bfd does NOT auto-sign outputs like the local DevBox lld
# does; that gap is covered twice: sitecustomize shim signs every binary
# before first exec (build-time sanity checks / test binaries), and
# package() re-signs every packaged .so explicitly.
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
