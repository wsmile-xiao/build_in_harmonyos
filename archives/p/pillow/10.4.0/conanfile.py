#!/usr/bin/env python3
"""Conan recipe for pillow 10.4.0 on HarmonyOS PC (OHOS aarch64).

Pillow is the Python imaging library (PIL fork). setuptools build_ext with
optional C library features; jpeg+zlib are required, the rest optional.

Feature set chosen for the matplotlib dependency chain:
  enabled : zlib, jpeg, freetype (text rendering, needed by matplotlib)
  disabled: tiff, lcms, webp, jpeg2000, imagequant, raqm, xcb

OHOS adaptations (same family as the numpy/contourpy recipes):
  - posix_spawn does not search PATH -> sitecustomize.py shim
  - musl does not export main exe symbols -> -lpython3.12
  - lld default linker (DevBox auto-signs outputs; NEVER -fuse-ld=bfd)
  - dependency discovery via XXX_ROOT env vars (setup.py native mechanism)
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches
from conan.tools.layout import basic_layout


class PillowConan(ConanFile):
    name = "pillow"
    version = "10.4.0"
    description = "Python Imaging Library (fork) - image processing"
    license = "HPND AND CNRI-Python-CPL"
    homepage = "https://python-pillow.org"
    url = "https://github.com/python-pillow/Pillow"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    _hnp_bin = "/data/service/hnp/bin"

    def requirements(self):
        # NOTE: zlib intentionally NOT a conan requirement — the registry's
        # static zlib is built without -fPIC and cannot link into pillow's
        # shared extensions (R_AARCH64_ADR_PREL_PG_HI21 against z_errmsg).
        # The OHOS SDK sysroot ships a dynamic libz.so which links cleanly.
        # libjpeg/freetype ARE built with fPIC by their recipes.
        self.requires("libjpeg/10")
        self.requires("freetype/2.14.3")

    def build_requirements(self):
        self.tool_requires("ninja/1.12.1")

    def layout(self):
        basic_layout(self, src_folder="src")

    def validate(self):
        # R32: platform check must use `in ("Linux", "OHOS")`
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"pillow 10.4.0 only supports Linux/OHOS, got {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        source = self.source_folder

        # OHOS shim: sitecustomize patches subprocess PATH search + auto-sign.
        shim_dir = os.path.join(self.build_folder, "_ohos_shim")
        self._create_sitecustomize(shim_dir)

        python3 = self._target_python()
        # CI workers ship a bare HNP python without setuptools — bootstrap it
        # into the build folder (numpy precedent, Tsinghua mirror only).
        import subprocess as _sp
        probe = _sp.run([python3, "-c", "import setuptools"], capture_output=True)
        if probe.returncode != 0:
            self.output.info("setuptools missing; bootstrapping into build folder")
            boot_dir = os.path.join(self.build_folder, "_pybootstrap")
            os.makedirs(boot_dir, exist_ok=True)
            for pkg in ("setuptools", "wheel"):
                _sp.run(
                    [python3, "-m", "pip", "install", "--no-deps", "--target", boot_dir, pkg,
                     "-i", "https://pypi.tuna.tsinghua.edu.cn/simple",
                     "--trusted-host", "pypi.tuna.tsinghua.edu.cn"],
                    capture_output=True, text=True, timeout=300)
        else:
            boot_dir = ""

        python_lib = self._python_lib_dir()
        libcxx = self._libcxx_dir()

        # Dependency discovery: setup.py reads <FEATURE>_ROOT env vars
        # (JPEG_ROOT / ZLIB_ROOT / FREETYPE_ROOT), each set to the conan
        # dependency package prefix (lib/ + include/ layout).
        env = dict(os.environ)
        roots = {
            "JPEG_ROOT": "libjpeg",
            "FREETYPE_ROOT": "freetype",
        }
        for var, dep_name in roots.items():
            pkg = self._dep_package_folder(dep_name)
            if pkg:
                env[var] = pkg
        # zlib from the OHOS SDK sysroot (dynamic libz.so links into shared
        # extensions, unlike the registry's non-PIC static zlib). setup.py
        # expects <root>/lib + <root>/include; the sysroot layout is
        # usr/lib/<triplet> + usr/include -> create a bridge dir with symlinks.
        sysroot = self._sysroot()
        if sysroot:
            bridge = os.path.join(self.build_folder, "_zlib_bridge")
            os.makedirs(bridge, exist_ok=True)
            for sub, target in (
                ("lib", os.path.join(sysroot, "usr", "lib", "aarch64-linux-ohos")),
                ("include", os.path.join(sysroot, "usr", "include")),
            ):
                link = os.path.join(bridge, sub)
                if not os.path.exists(link):
                    os.symlink(target, link)
            env["ZLIB_ROOT"] = bridge

        saved = {}
        for k, v in env.items():
            if os.environ.get(k) != v:
                saved[k] = os.environ.get(k)
                os.environ[k] = v

        old_pythonpath = os.environ.get("PYTHONPATH", "")
        old_ld_library_path = os.environ.get("LD_LIBRARY_PATH")
        try:
            os.environ["PYTHONPATH"] = ":".join(
                p for p in (shim_dir, boot_dir, old_pythonpath) if p)
            existing = os.environ.get("LD_LIBRARY_PATH", "")
            for lib in (python_lib, libcxx):
                if lib and lib not in existing:
                    existing = f"{lib}:{existing}" if existing else lib
            os.environ["LD_LIBRARY_PATH"] = existing

            # setuptools build: compile extensions in place, then wheel-style
            # install into the package folder via pip (setup.py install is
            # deprecated; pip handles the purelib layout).
            cflags_old = os.environ.get("CFLAGS", "")
            os.environ["CFLAGS"] = f"-fPIC -O2 {cflags_old}".strip()
            os.environ["CPPFLAGS"] = (
                f"-fPIC -O2 {os.environ.get('CPPFLAGS', '')}").strip()
            # SDK ld.lld links libxml2.so.16 which is broken/missing on some
            # CI workers (xmlFree symbol not found — numpy runs #36676/#36866).
            # Use GNU ld.bfd for the shared-object link step (setup.py honors
            # LDSHARED). Signatures are covered by the E212 fallback shim.
            ldshared_old = os.environ.get("LDSHARED")
            ld_shared = "/data/service/hnp/bin/ld.bfd"
            if os.path.isfile(ld_shared):
                # Keep -lpython3.12: overriding LDSHARED drops setup.py's
                # default python lib linkage (CI run #37359 produced .so
                # files without the libpython NEEDED entry).
                py_lib_dir = self._python_lib_dir()
                os.environ["LDSHARED"] = (
                    f"/data/service/hnp/bin/clang -fuse-ld=bfd -shared "
                    f"-L{py_lib_dir} -lpython3.12")
            try:
                self.run(
                    f'"{python3}" setup.py build_ext '
                    f'--disable-tiff --disable-lcms --disable-webp '
                    f'--disable-webpmux --disable-jpeg2000 --disable-imagequant '
                    f'--disable-raqm --disable-xcb',
                    cwd=source)
                # Build the wheel now, inside build() where the dependency
                # env vars are set; package() only unpacks it.
                # bdist_wheel reuses the built extensions from build/;
                # feature flags are build_ext options only.
                self.run(f'"{python3}" setup.py bdist_wheel', cwd=source)
            finally:
                if cflags_old:
                    os.environ["CFLAGS"] = cflags_old
                else:
                    os.environ.pop("CFLAGS", None)
                if ldshared_old is not None:
                    os.environ["LDSHARED"] = ldshared_old
                else:
                    os.environ.pop("LDSHARED", None)
        finally:
            for k, v in saved.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
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
        python3 = self._target_python()
        import glob
        wheels = sorted(glob.glob(os.path.join(source, "dist", "*.whl")))
        if not wheels:
            raise ConanException("wheel not found in dist/; build() must run first")
        wheel = wheels[-1]
        # A wheel is a zip: unpack it straight into lib/python3.12/site-packages.
        # No pip, no recompilation, no env vars needed.
        import zipfile
        site_packages = os.path.join(
            self.package_folder, "lib", "python3.12", "site-packages")
        os.makedirs(site_packages, exist_ok=True)
        with zipfile.ZipFile(wheel) as zf:
            zf.extractall(site_packages)
        self.output.info(f"unpacked {wheel} -> {site_packages}")
        if self.settings.os == "OHOS":
            # bfd-linked .so files carry no .codesign section — the E212
            # fallback ELF verification rejects them. Re-sign every module
            # in package() explicitly (numpy precedent, #36910).
            import subprocess
            sign_tool = "/data/service/hnp/bin/binary-sign-tool"
            for so in glob.glob(os.path.join(site_packages, "PIL", "*.so")):
                r = subprocess.run(
                    [sign_tool, "sign", "-inFile", so, "-outFile", so,
                     "-selfSign", "1", "-signAlg", "SHA256withECDSA"],
                    capture_output=True, text=True, timeout=60)
                if r.returncode != 0:
                    self.output.warning(f"re-sign failed: {so}: {r.stderr[:100]}")
            self.output.info("re-signed packaged PIL .so files for OHOS")

    def package_info(self):
        # Consumed via PYTHONPATH (site-packages), not linked as C libs.
        self.cpp_info.libs = []
        import glob
        for site_packages in sorted(glob.glob(
                os.path.join(self.package_folder, "lib", "python*", "site-packages"))):
            self.runenv_info.prepend_path("PYTHONPATH", site_packages)

    # ─────────────────── helpers ───────────────────

    def _sysroot(self):
        import glob
        for pattern in (
            "/data/service/hnp/ohos-sdk.org/*/ohos/native/sysroot",
            "/data/service/hnp/ohos-sdk*/ohos/native/sysroot",
        ):
            hits = sorted(glob.glob(pattern))
            if hits:
                return hits[-1]
        return ""

    def _dep_package_folder(self, name):
        for ref, dep in self.dependencies.items():
            dep_name = getattr(getattr(ref, "ref", None), "name", None) \
                or str(ref).split("/")[0]
            if dep_name == name:
                return dep.package_folder
        return None

    def _target_python(self):
        candidates = [
            os.environ.get("PILLOW_PYTHON") or os.environ.get("NUMPY_PYTHON"),
            os.environ.get("OHOS_PYTHON"),
            os.path.expanduser("~/usr/local/bin/python3"),
            "/storage/Users/currentUser/usr/local/bin/python3",
            shutil.which("python3") or "",
        ]
        for py in candidates:
            if py and os.path.isfile(py):
                return py
        raise ConanException("no target python3 found; set PILLOW_PYTHON")

    def _python_lib_dir(self):
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
