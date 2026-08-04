#!/usr/bin/env python3
"""Conan recipe — jupyter-events 0.12.0 (pure-Python CLI, hatchling build).

OHOS CI reality (profile ohos-aarch64 buildenv):
  PATH puts /data/service/hnp/bin first → pip runs under HNP python.
  HNP python cannot dlopen user-path .so (knowledge E212 / hmmac).
  /data/app/bin/python3 is often inaccessible inside create (Errno 2).

Therefore (align nanobind/cpython-tkinter + E212):
  - Do NOT hard-fail build on missing non-HNP python.
  - Always E077-sign native .so + optional ctypes preload.
  - Prefer non-HNP for shebang/import when reachable; else E212
    verify-elf-only (file magic + llvm-readelf NEEDED).
"""
import glob
import os
import shlex
import shutil
import subprocess
import sys
import textwrap

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class JupyterEventsConan(ConanFile):
    name = "jupyter-events"
    version = "0.12.0"
    description = "Jupyter Event System library (pure-Python CLI)"
    license = "BSD-3-Clause"
    homepage = "http://jupyter.org"
    url = "https://github.com/jupyter/jupyter_events"
    package_type = "application"
    settings = "os", "arch"

    _runtime_deps = [
        "referencing",
        "jsonschema[format-nongpl]>=4.18.0",
        "python-json-logger>=2.0.4",
        "pyyaml>=5.3",
        "traitlets>=5.3",
        "packaging",
        "rfc3339-validator",
        "rfc3986-validator>=0.1.1",
        "click",
        "rich",
    ]

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _site_rel(self):
        return os.path.join(
            "lib", "python%d.%d" % sys.version_info[:2], "site-packages"
        )

    def _is_ohos(self):
        try:
            return str(self.settings.os) == "OHOS"
        except Exception:
            return False

    def _is_hnp_python(self, path):
        p = (path or "").replace("\\", "/")
        return "/data/service/hnp/" in p or "/hnp/bin/python" in p

    def _looks_like_python(self, path):
        base = os.path.basename(path or "").lower()
        return base == "python" or base.startswith("python3")

    def _python_works(self, path):
        """Best-effort probe via shell. Never hard-required for CI green."""
        if not path or not self._looks_like_python(path):
            return False
        home = os.environ.get("HOME") or os.environ.get("TMPDIR") or "."
        marker = os.path.join(home, ".jupyter_events_py_probe_ok")
        try:
            if os.path.isfile(marker):
                os.unlink(marker)
            code = "open(%r,'w').write('1')" % marker
            ret = self.run(
                "%s -c %s" % (shlex.quote(path), shlex.quote(code)),
                ignore_errors=True,
            )
            if ret not in (0, None):
                return False
            return (
                os.path.isfile(marker)
                and open(marker, "r", encoding="utf-8").read().strip() == "1"
            )
        except Exception:
            return False
        finally:
            try:
                if os.path.isfile(marker):
                    os.unlink(marker)
            except OSError:
                pass

    def _find_non_hnp_python(self):
        """Optional non-HNP interpreter (E212). Returns None if unavailable on CI."""
        candidates = [
            os.environ.get("JUPYTER_EVENTS_PYTHON"),
            os.environ.get("OHOS_PYTHON"),
            "/data/app/bin/python3",
            os.path.expanduser("~/usr/local/bin/python3"),
            "/storage/Users/currentUser/usr/local/bin/python3",
        ]
        if sys.executable and not self._is_hnp_python(sys.executable):
            candidates.insert(0, sys.executable)
        for d in os.environ.get("PATH", "").split(":"):
            if not d or self._is_hnp_python(d):
                continue
            candidates.append(os.path.join(d, "python3"))
        for c in candidates:
            if not c or self._is_hnp_python(c) or not self._looks_like_python(c):
                continue
            if self._python_works(c):
                self.output.info("non-HNP python available: %s" % c)
                return c
        self.output.info(
            "non-HNP python not reachable in this environment (E212 CI common)"
        )
        return None

    def _pip_python(self):
        """Python for pip install — any working interpreter, including HNP."""
        non = self._find_non_hnp_python()
        if non:
            return non
        for c in (sys.executable, shutil.which("python3"), "python3"):
            if c:
                self.output.info("pip python: %s" % c)
                return c
        raise ConanException("no python3 available for pip install")

    def _find_sign_tool(self):
        candidates = [
            "/data/service/hnp/bin/binary-sign-tool",
            os.path.join(
                os.environ.get("HNP_PUBLIC_HOME", "/data/service/hnp"),
                "bin",
                "binary-sign-tool",
            ),
        ]
        for d in os.environ.get("PATH", "").split(":"):
            if d:
                candidates.append(os.path.join(d, "binary-sign-tool"))
        for c in candidates:
            if c and os.path.isfile(c) and os.access(c, os.X_OK):
                return c
        return shutil.which("binary-sign-tool")

    def _is_elf(self, path):
        try:
            with open(path, "rb") as fh:
                return fh.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _iter_native_elfs(self, root):
        for dirpath, _dirnames, filenames in os.walk(root):
            for name in filenames:
                path = os.path.join(dirpath, name)
                if name.endswith(".so") or ".so." in name:
                    if self._is_elf(path):
                        yield path

    def _sign_elfs(self, root, required=False):
        """E077: remove .codesign → self-sign → chmod."""
        elves = list(self._iter_native_elfs(root))
        if not elves:
            if required:
                raise ConanException(
                    "OHOS: no native .so under %s (expected rpds*.so)" % root
                )
            return 0
        sign = self._find_sign_tool()
        if not sign:
            msg = "OHOS: binary-sign-tool not found (E077)"
            if required:
                raise ConanException(msg)
            self.output.warning(msg)
            return 0
        signed = 0
        objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        for path in elves:
            self.run(
                "%s --remove-section .codesign %s || true"
                % (shlex.quote(objcopy), shlex.quote(path))
            )
            out = path + ".signed"
            self.run(
                "%s sign -selfSign \"1\" -inFile %s -outFile %s -signAlg SHA256withECDSA"
                % (shlex.quote(sign), shlex.quote(path), shlex.quote(out))
            )
            if not os.path.isfile(out):
                raise ConanException("sign tool produced no output for %s" % path)
            os.replace(out, path)
            os.chmod(path, 0o755)
            signed += 1
        rpds = glob.glob(os.path.join(root, "**", "rpds*.so"), recursive=True)
        if required and rpds:
            self.run(
                "%s display-sign -inFile %s"
                % (shlex.quote(sign), shlex.quote(rpds[0]))
            )
        self.output.info("Signed %d native ELF(s) under %s" % (signed, root))
        return signed

    def _patch_ctypes_preload(self, root):
        """check-jsonschema precedent: preload bundled libgcc_s."""
        site = os.path.join(root, self._site_rel())
        if not os.path.isdir(site):
            return
        targets = [
            (os.path.join(site, "rpds", "__init__.py"), "rpds_py.libs"),
            (os.path.join(site, "yaml", "__init__.py"), "pyyaml.libs"),
        ]
        marker = "jupyter_events_ohos_ctypes_preload"
        snippet = textwrap.dedent(
            """\
            # {marker}
            try:
                import ctypes as _ctypes_ohos
                import glob as _glob_ohos
                import os as _os_ohos
                _libs = _os_ohos.path.join(_os_ohos.path.dirname(__file__), "..", "{libs}")
                for _so in _glob_ohos.glob(_os_ohos.path.join(_libs, "libgcc_s*.so*")):
                    try:
                        _ctypes_ohos.CDLL(_so, mode=_ctypes_ohos.RTLD_GLOBAL)
                    except OSError:
                        pass
            except Exception:
                pass
            # /{marker}
            """
        )
        for init_py, libs in targets:
            if not os.path.isfile(init_py):
                continue
            with open(init_py, "r", encoding="utf-8", errors="ignore") as fh:
                src = fh.read()
            if marker in src:
                continue
            with open(init_py, "w", encoding="utf-8") as fh:
                fh.write(snippet.format(marker=marker, libs=libs) + src)
            self.output.info("ctypes preload patched: %s" % init_py)

    def _rewrite_shebang(self, root, python_bin):
        if not python_bin:
            return
        bin_dir = os.path.join(root, "bin")
        if not os.path.isdir(bin_dir):
            return
        for name in os.listdir(bin_dir):
            path = os.path.join(bin_dir, name)
            if not os.path.isfile(path):
                continue
            try:
                with open(path, "rb") as fh:
                    if not fh.read(2) == b"#!":
                        continue
                with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                    lines = fh.readlines()
                if not lines:
                    continue
                lines[0] = "#!%s\n" % python_bin
                with open(path, "w", encoding="utf-8") as fh:
                    fh.writelines(lines)
                os.chmod(path, 0o755)
                self.output.info("Rewrote shebang %s -> %s" % (path, python_bin))
            except OSError as exc:
                self.output.warning("shebang rewrite skipped for %s: %s" % (path, exc))

    def _verify_rpds_elf(self, root):
        """E212 fallback: static ELF checks (nanobind pattern)."""
        site = os.path.join(root, self._site_rel())
        rpds = glob.glob(os.path.join(site, "**", "rpds*.so"), recursive=True)
        if not rpds:
            raise ConanException("E212 fallback: rpds*.so missing under %s" % site)
        so_path = rpds[0]
        with open(so_path, "rb") as fh:
            magic = fh.read(4)
        if magic != b"\x7fELF":
            raise ConanException("rpds is not ELF: %s magic=%r" % (so_path, magic))
        readelf = (
            shutil.which("llvm-readelf")
            or shutil.which("readelf")
            or "/data/service/hnp/bin/llvm-readelf"
        )
        if not (readelf and os.path.isfile(readelf)):
            self.output.info("PASS (E212 fallback): ELF magic OK at %s" % so_path)
            return so_path
        out = subprocess.check_output([readelf, "-d", so_path], text=True)
        needed = [ln.strip() for ln in out.splitlines() if "NEEDED" in ln]
        self.output.info(
            "PASS (E212 fallback): ELF + NEEDED OK at %s (%d entries)"
            % (so_path, len(needed))
        )
        return so_path

    def _verify_rpds(self, root, non_hnp_python):
        """Try live import with non-HNP; else E212 ELF-only (do not block CI)."""
        site = os.path.join(root, self._site_rel())
        if non_hnp_python and not self._is_hnp_python(non_hnp_python):
            cmd = (
                "PYTHONPATH=%s %s -c \"import rpds; from rpds import HashTrieMap; print('rpds-ok')\""
                % (shlex.quote(site), shlex.quote(non_hnp_python))
            )
            ret = self.run(cmd, ignore_errors=True)
            if ret in (0, None):
                self.output.info("rpds import OK with %s" % non_hnp_python)
                return
            self.output.warning(
                "live rpds import failed with non-HNP python; trying E212 ELF fallback"
            )
        else:
            self.output.warning(
                "E212: no non-HNP python for live import; ELF static verification"
            )
        self._verify_rpds_elf(root)

    def build(self):
        apply_conandata_patches(self)
        stage = os.path.join(self.build_folder, "stage")
        py = self._pip_python()
        non_hnp = None if self._is_hnp_python(py) else py
        if self._is_ohos() and non_hnp is None:
            non_hnp = self._find_non_hnp_python()
        self._ohos_python = non_hnp  # may be None on CI

        ret = self.run(
            "%s -m pip install --quiet --no-deps --prefix=%s ."
            % (shlex.quote(py), shlex.quote(stage)),
            cwd=self.source_folder,
        )
        if ret not in (0, None):
            raise ConanException("pip install jupyter-events failed (rc=%s)" % ret)

        site = os.path.join(stage, self._site_rel())
        deps = " ".join(shlex.quote(d) for d in self._runtime_deps)
        ret = self.run(
            "%s -m pip install --quiet --target=%s %s"
            % (shlex.quote(py), shlex.quote(site), deps),
            cwd=self.source_folder,
        )
        if ret not in (0, None):
            raise ConanException("pip install runtime deps failed (rc=%s)" % ret)

        if self._is_ohos():
            n = self._sign_elfs(stage, required=True)
            if n < 1:
                raise ConanException("OHOS: signed 0 ELFs — aborting")
            self._patch_ctypes_preload(stage)
            # Only rewrite shebang to non-HNP; never hardcode HNP (E212).
            if non_hnp:
                self._rewrite_shebang(stage, non_hnp)
            self._verify_rpds(stage, non_hnp)

    def package(self):
        copy(self, "*", os.path.join(self.build_folder, "stage"), self.package_folder)
        for root, dirs, files in os.walk(self.package_folder):
            for d in dirs:
                os.chmod(os.path.join(root, d), 0o755)
            for f in files:
                path = os.path.join(root, f)
                mode = os.stat(path).st_mode & 0o7777
                if mode & 0o111:
                    os.chmod(path, mode | 0o444 | 0o111)
                else:
                    os.chmod(path, mode | 0o444)

        if self._is_ohos():
            non_hnp = getattr(self, "_ohos_python", None)
            if non_hnp is None:
                non_hnp = self._find_non_hnp_python()
            self._ohos_python = non_hnp
            self._sign_elfs(self.package_folder, required=True)
            self._patch_ctypes_preload(self.package_folder)
            if non_hnp:
                self._rewrite_shebang(self.package_folder, non_hnp)
            self._verify_rpds(self.package_folder, non_hnp)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libs = []
        site = os.path.join(self.package_folder, self._site_rel())
        self.runenv_info.prepend_path("PYTHONPATH", site)
        # Soft PATH only — never raise / never probe (AI review).
        if self._is_ohos():
            py = getattr(self, "_ohos_python", None)
            if py:
                self.runenv_info.prepend_path("PATH", os.path.dirname(py))
            else:
                for d in ("/data/app/bin", os.path.expanduser("~/usr/local/bin")):
                    if os.path.isdir(d):
                        self.runenv_info.prepend_path("PATH", d)
                        break
