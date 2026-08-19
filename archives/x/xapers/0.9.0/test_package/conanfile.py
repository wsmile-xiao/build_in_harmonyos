#!/usr/bin/env python3
"""Conan test_package for xapers 0.9.0 — Python smoke test.

This is the L1 test in the five-level test system.
CI runs this automatically via `conan create` (which invokes test_package).

On OHOS CI the HNP python cannot dlopen user-path .so (E212, hmmac security
label), so `import xapers` may fail with "Permission denied" even though the
package is intact. Follow the nanobind/xapian-bindings pattern: run the live
test first, then fall back to static ELF verification when E212 is detected.
"""
import os
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException


class XapersTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _verify_package_elf(self, pkg_folder, xb_site):
        """E212 fallback: verify packaged artifacts exist and are valid ELF.

        xapers 包在自身 site-packages；xapian 绑定（_xapian*.so）位于
        xapian-bindings 依赖的 site-packages（xb_site），两者路径不同。
        """
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site = os.path.join(pkg_folder, "lib", py_ver, "site-packages")
        if not os.path.isdir(os.path.join(site, "xapers")):
            raise ConanException(f"xapers package missing in {site}")

        xapian_dir = os.path.join(xb_site, "xapian")
        if not os.path.isdir(xapian_dir):
            raise ConanException(f"xapian bindings dir missing in {xb_site}")
        # xapian bindings .so must be a valid ELF and link the runtime.
        so = next(
            (os.path.join(xapian_dir, n)
             for n in os.listdir(xapian_dir)
             if n.startswith("_xapian") and n.endswith(".so")),
            None,
        )
        if not so:
            raise ConanException(f"_xapian*.so not found under {xapian_dir}")
        with open(so, "rb") as f:
            magic = f.read(4)
        if magic != b"\x7fELF":
            raise ConanException(f"_xapian is not a valid ELF: {so} magic={magic!r}")
        self.output.info(f"PASS (E212 fallback): xapers package + ELF OK at {so}")

    def test(self):
        python_exe = sys.executable
        test_script = os.path.join(os.path.dirname(__file__), "test_xapers.py")
        try:
            self.run(f'{python_exe} "{test_script}"', env="conanrun")
            self.output.info("test_xapers.py OK")
            return
        except ConanException as exc:
            # Re-probe to classify E212 (hmmac blocks dlopen of user-path .so)
            # vs a real functional failure. The probe must replicate the
            # conanrun environment: PYTHONPATH must cover both this package's
            # site-packages and the xapian-bindings site-packages, otherwise
            # import fails with "No module named 'xapers'" instead of the E212
            # "Permission denied" we need to detect.
            py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
            pkg = self.dependencies[self.tested_reference_str].package_folder
            xb = self.dependencies["xapian-bindings"].package_folder
            paths = [
                os.path.join(pkg, "lib", py_ver, "site-packages"),
                os.path.join(xb, "lib", py_ver, "site-packages"),
            ]
            probe_env = os.environ.copy()
            existing = probe_env.get("PYTHONPATH", "")
            probe_env["PYTHONPATH"] = os.pathsep.join(paths) + (
                os.pathsep + existing if existing else ""
            )
            probe = subprocess.run(
                [python_exe, test_script],
                capture_output=True,
                text=True,
                env=probe_env,
            )
            err = (probe.stderr or "") + (probe.stdout or "") + str(exc)
            e212 = (
                "Permission denied" in err
                or "Error loading shared library" in err
                or "cannot open shared object" in err
                or "Operation not permitted" in err
            )
            if str(self.settings.os) == "OHOS" and e212:
                self.output.warning(
                    "E212: hmmac blocked dlopen of xapian bindings under user "
                    f"path ({pkg}); falling back to static ELF verification."
                )
                self._verify_package_elf(pkg, os.path.join(xb, "lib", py_ver, "site-packages"))
            else:
                raise ConanException(
                    f"test_xapers.py failed (exit={probe.returncode}): "
                    f"{err.strip() or str(exc)}"
                ) from exc
