#!/usr/bin/env python3
"""Conan recipe for hwdata 0.411 — hardware identification databases.

Why this package exists
-----------------------
`hwdata` carries the canonical PCI/USB/PNP identifier databases. Two consumers
in this archive already needed pieces of it:

  * `hwdata-usb/0.409` — packages **only** `usb.ids`, for its own consumers;
  * `libdisplay-info/0.3.0` — needs **`pnp.ids`** and, because no `hwdata`
    conan package existed, its recipe documents a manual workaround: fetch
    `pnp.ids` straight from GitHub and hand-write a `hwdata.pc` into the
    generators folder. That bypass is exactly what this package replaces:
    with `hwdata` published, a consumer only has to `self.requires("hwdata/...")`
    and meson's `dependency('hwdata')` resolves through the packaged .pc.

Packaging scope
---------------
The full upstream data set is shipped (upstream's own `IDFILES`), installed to
`<pkg>/share/hwdata/<file>` with `hwdata.pc` at `<pkg>/share/pkgconfig/`, i.e.
the same layout upstream's `make install` produces. `pkgdatadir` in the .pc
points at the packaged data directory so consumers locate `pnp.ids` without
any hard-coded path.

Data files are architecture independent, so `package_id()` is cleared to keep
a single binary package per recipe revision.
"""
import os
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout

# Upstream Makefile: IDFILES = pci.ids usb.ids oui.txt iab.txt pnp.ids
ID_FILES = ("pci.ids", "usb.ids", "oui.txt", "iab.txt", "pnp.ids")


class HwdataConan(ConanFile):
    name = "hwdata"
    version = "0.411"
    description = ("Hardware identification and configuration data: "
                   "PCI/USB/PNP identifier databases")
    license = "GPL-2.0-or-later OR XFree86-1.1"
    homepage = "https://github.com/vcrhonek/hwdata"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ── build-time verification ────────────────────────────────────────────
    def _run_upstream_checks(self):
        """Run the checks upstream's `make check` performs (R51).

        Upstream's `check` target needs `lspci` (with the pciutils dump backend)
        and the external `check-usb-ids.sh`, which drives podman. Both are
        host-tool dependent, so the parts that ARE reproducible here are run and
        the rest is reported explicitly rather than silently skipped:

          1. UTF-8 validity of every ID file     (upstream does this too)
          2. `Date:` header presence/parsability (upstream does this too)
          3. pnp.ids structural sanity — three-column records, no empties
          4. upstream's own parser: ./check-pci-ids.py
        """
        ran, skipped = [], []

        for data_file in ID_FILES:
            path = os.path.join(self.source_folder, data_file)
            if not os.path.isfile(path):
                raise ConanException(f"expected upstream data file missing: {data_file}")
            try:
                with open(path, "rb") as fh:
                    raw = fh.read()
                raw.decode("utf-8")
                ran.append(f"utf8:{data_file}")
            except UnicodeDecodeError as e:
                raise ConanException(f"{data_file} is not valid UTF-8: {e}")

        # upstream prints the Date: line of pci.ids / usb.ids
        for data_file in ("pci.ids", "usb.ids"):
            with open(os.path.join(self.source_folder, data_file),
                      encoding="utf-8", errors="replace") as fh:
                dates = [ln for ln in fh if ln.startswith("#") and "Date:" in ln]
            if not dates:
                raise ConanException(f"{data_file}: no 'Date:' header found (upstream check)")
            self.output.info(f"{data_file} {dates[0].strip()}")

        # pnp.ids: `<PNP_ID>\t<Vendor>` records, e.g. "AAA\tAvolites Ltd"
        pnp = os.path.join(self.source_folder, "pnp.ids")
        records = 0
        with open(pnp, encoding="utf-8") as fh:
            for lineno, line in enumerate(fh, 1):
                if not line.strip():
                    continue
                parts = line.rstrip("\n").split("\t")
                if len(parts) < 2 or not parts[0].strip() or not parts[1].strip():
                    raise ConanException(
                        f"pnp.ids:{lineno}: malformed record {line!r}")
                records += 1
        if records == 0:
            raise ConanException("pnp.ids contains no records")
        self.output.info(f"pnp.ids: {records} PNP ID records (tab-separated)")

        # upstream's own PCI database validator (pure python, no host tools)
        checker = os.path.join(self.source_folder, "check-pci-ids.py")
        if os.path.isfile(checker):
            res = subprocess.run([sys.executable, "check-pci-ids.py"],
                                 cwd=self.source_folder,
                                 capture_output=True, text=True, timeout=900)
            tail = (res.stdout or res.stderr or "").strip().splitlines()[-1:]
            if res.returncode != 0:
                raise ConanException(
                    f"upstream check-pci-ids.py failed: {' '.join(tail)}")
            ran.append("check-pci-ids.py")
            self.output.info(f"upstream check-pci-ids.py: {' '.join(tail)}")
        else:
            skipped.append("check-pci-ids.py (not shipped)")

        # host-tool dependent parts of upstream `make check`
        if not shutil.which("lspci"):
            skipped.append("lspci -A dump (pciutils not installed)")
        if not shutil.which("podman"):
            skipped.append("check-usb-ids.sh (podman not installed)")

        self.output.info(f"upstream checks executed: {len(ran)} -> {', '.join(ran)}")
        if skipped:
            self.output.warning(
                "host-tool dependent checks not run here: " + "; ".join(skipped))

    def build(self):
        for data_file in ID_FILES:
            if not os.path.isfile(os.path.join(self.source_folder, data_file)):
                raise ConanException(f"data file not found in source: {data_file}")
        self._run_upstream_checks()

    # ── packaging ──────────────────────────────────────────────────────────
    def package(self):
        data_dst = os.path.join(self.package_folder, "share", "hwdata")
        for data_file in ID_FILES:
            copy(self, data_file, src=self.source_folder, dst=data_dst)
        for lic in ("COPYING", "LICENSE"):
            copy(self, lic, src=self.source_folder,
                 dst=os.path.join(self.package_folder, "licenses"))

        # Ship the same hwdata.pc upstream's `make install` generates, so
        # consumers resolve `dependency('hwdata')` without a manual workaround.
        # pkgdatadir is what libdisplay-info's meson uses to locate pnp.ids.
        pkgdatadir = data_dst.replace("\\", "/")
        pc = (
            f"prefix={self.package_folder}\n"
            f"datadir=${{prefix}}/share\n"
            f"pkgdatadir={pkgdatadir}\n"
            "\n"
            "Name: hwdata\n"
            "Description: Hardware identification and configuration data\n"
            f"Version: {self.version}\n"
            "URL: https://github.com/vcrhonek/hwdata\n"
        )
        pc_dst = os.path.join(self.package_folder, "share", "pkgconfig")
        os.makedirs(pc_dst, exist_ok=True)
        with open(os.path.join(pc_dst, "hwdata.pc"), "w") as fh:
            fh.write(pc)

        # sanity: everything the .pc promises must exist
        for data_file in ID_FILES:
            if not os.path.isfile(os.path.join(data_dst, data_file)):
                raise ConanException(f"packaged data file missing: {data_file}")

    def package_id(self):
        # ID databases are plain text and architecture independent.
        self.info.clear()

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = ["share"]

        # pkg-config metadata: consumers (e.g. meson `dependency('hwdata')`)
        # read pkgdatadir from here.
        self.cpp_info.set_property("pkg_config_name", "hwdata")

        hwdata_dir = os.path.join(self.package_folder, "share", "hwdata")
        # path helpers for consumers that do not use pkg-config
        self.buildenv_info.define_path("HWDATA_DIR", hwdata_dir)
        self.runenv_info.define_path("HWDATA_DIR", hwdata_dir)
        self.runenv_info.define_path("PNP_IDS_FILE",
                                     os.path.join(hwdata_dir, "pnp.ids"))
        self.runenv_info.define_path("PCI_IDS_FILE",
                                     os.path.join(hwdata_dir, "pci.ids"))
