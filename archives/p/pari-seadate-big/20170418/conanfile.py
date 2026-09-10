#!/usr/bin/env python3
"""Conan recipe for PARI seadata-big 20170418 (architecture-independent data)."""

from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import http.client
import os
from pathlib import Path
import tempfile
import threading
import time
import urllib.request

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import copy, get, unzip
from conan.tools.layout import basic_layout


class PariSeadateBigConan(ConanFile):
    name = "pari-seadate-big"
    version = "20170418"
    description = "PARI/GP Atkin modular polynomials for prime levels 500 < p < 800"
    license = "GPL-2.0-or-later"
    homepage = "https://pari.math.u-bordeaux.fr/packages.html"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    # Conan 2.29 has no data-specific package type; explicit unknown carries resources.
    package_type = "unknown"
    settings = "os", "compiler", "build_type", "arch"
    no_copy_source = True
    exports_sources = "COPYING"

    def layout(self):
        basic_layout(self)

    def source(self):
        source = dict(self.conan_data["sources"])
        size = source.pop("size")
        if source["url"].startswith("file://"):
            # The CI pre-download cache still goes through Conan's SHA256 check.
            get(self, **source, strip_root=False)
            return
        archive = Path(self.source_folder) / "seadata-big.tar"
        self.output.info("Downloading official seadata-big with 8 parallel ranges (45-minute budget)")
        self._download_parallel(source["url"], archive, size, source["sha256"],
                                progress=self.output.info)
        try:
            unzip(self, str(archive))
        finally:
            archive.unlink(missing_ok=True)

    @staticmethod
    def _download_parallel(url, destination, size, expected_sha256, *, workers=8,
                           part_size=2 * 1024 * 1024, retries=3, deadline_seconds=2700,
                           progress=None):
        """Fetch exact byte ranges; expose only a completely verified archive."""
        destination = Path(destination)
        deadline = time.monotonic() + deadline_seconds
        stopped = threading.Event()

        def check_budget():
            if stopped.is_set() or time.monotonic() >= deadline:
                raise TimeoutError("PARI download budget exhausted or another range failed")

        def fetch(part, start, end):
            expected_size = end - start + 1
            request = urllib.request.Request(url, headers={
                "Range": f"bytes={start}-{end}", "Accept-Encoding": "identity",
                "User-Agent": "Conan/2 pari-seadata-big",
            })
            for attempt in range(retries):
                check_budget()
                try:
                    with urllib.request.urlopen(request, timeout=min(30, deadline - time.monotonic())) as response:
                        if (response.status != 206 or response.headers.get("Content-Range")
                                != f"bytes {start}-{end}/{size}"):
                            raise ValueError(f"Server rejected exact byte range {start}-{end}")
                        received = 0
                        with part.open("wb") as output:
                            while True:
                                check_budget()
                                # read() may wait to fill its buffer while a peer trickles bytes.
                                # read1() returns available bytes so the deadline is checked again.
                                chunk = response.read1(64 * 1024)
                                if not chunk:
                                    break
                                received += len(chunk)
                                if received > expected_size:
                                    raise ValueError(f"Oversized byte range {start}-{end}")
                                output.write(chunk)
                        if received != expected_size:
                            raise OSError(f"Truncated byte range {start}-{end}: {received} bytes")
                    return
                except (OSError, http.client.IncompleteRead) as error:
                    part.unlink(missing_ok=True)
                    check_budget()
                    if attempt + 1 == retries:
                        raise OSError(f"Failed byte range {start}-{end} after {retries} attempts") from error
                    stopped.wait(min(2 ** attempt, max(0, deadline - time.monotonic())))

        check_budget()
        with tempfile.TemporaryDirectory(prefix=".seadata-download-", dir=destination.parent) as temporary:
            root = Path(temporary)
            ranges = [(start, min(start + part_size - 1, size - 1)) for start in range(0, size, part_size)]
            parts = [root / str(index) for index in range(len(ranges))]
            with ThreadPoolExecutor(max_workers=workers) as executor:
                futures = [executor.submit(fetch, part, start, end)
                           for part, (start, end) in zip(parts, ranges)]
                try:
                    for count, future in enumerate(as_completed(futures), 1):
                        future.result()
                        if progress:
                            progress(f"Verified byte ranges: {count}/{len(parts)}")
                except Exception:
                    stopped.set()
                    for future in futures:
                        future.cancel()
                    raise
            combined = root / "archive.tar"
            digest = hashlib.sha256()
            with combined.open("wb") as output:
                for part in parts:
                    check_budget()
                    with part.open("rb") as source:
                        while chunk := source.read(1024 * 1024):
                            output.write(chunk)
                            digest.update(chunk)
            if combined.stat().st_size != size or digest.hexdigest() != expected_sha256:
                raise ValueError("PARI archive size or SHA256 mismatch")
            os.replace(combined, destination)

    def package(self):
        source = os.path.join(self.source_folder, "data", "seadata")
        target = os.path.join(self.package_folder, "share", "pari", "seadata")
        files = copy(self, "sea*.gz", src=source, dst=target)
        if len(files) != 44:
            raise ConanException(f"Expected 44 upstream modular polynomials, found {len(files)}")
        copy(self, "README.big", src=source, dst=target)
        copy(self, "README.big", src=source,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libs = []
        self.cpp_info.resdirs = [os.path.join("share", "pari")]
        # Do not replace PARI's global datadir: other optional datasets may coexist.
        self.runenv_info.define_path("PARI_SEADATA_BIG_DATADIR",
                                     os.path.join(self.package_folder, "share", "pari"))
