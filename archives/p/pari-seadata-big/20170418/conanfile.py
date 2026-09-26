#!/usr/bin/env python3
"""Conan recipe for pari-seadata-big 20170418 — PARI/GP's large Atkin
modular-polynomial dataset (prime levels 500 < p < 800).

This is a **pure data package**: the upstream archive ships
``data/seadata/`` with 44 gzip-compressed polynomials
(``sea503.gz`` .. ``sea797.gz``, one per prime level in (500, 800)) plus
``README.big``.  There is nothing to compile, link or sign — packaging is
"unpack archive and install the data files", so the recipe is
architecture-independent (``package_id`` is cleared) and ``build()`` only
runs the deterministic data validator that is also used by
``test_package``.

Note on ``source()``: the upstream archive is 98.7 MB served by a single
host.  A plain single-connection download of this file does not finish
inside the 3600 s ``conan create`` budget (observed on pari-seadata-big
builds: ~82 MB after 3600 s), and the CI pipeline's ``curl`` pre-download
step is skipped on workers without ``curl``.  This recipe therefore fetches
exact byte ranges over several connections (``urllib`` only, no external
``curl``/``wget``) — the annotated approach of the merged sibling package
``pari-seadate-big/20170418``, hardened for CI workers whose egress drops
individual range requests: retries per range, repeated passes over whatever
is still missing, and no abort on the first range that exhausts its
attempts.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import http.client
import os
from pathlib import Path
import sys
import tempfile
import time
import urllib.request

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, get, unzip
from conan.tools.layout import basic_layout


class _DownloadBudgetExhausted(RuntimeError):
    """The upstream archive download used up its overall time budget.

    Kept separate from the built-in ``TimeoutError`` so that per-connection
    socket timeouts, which are transient and worth retrying, are not confused
    with an exhausted download budget, which is not.
    """


class PariSeadataBigConan(ConanFile):
    name = "pari-seadata-big"
    version = "20170418"
    description = (
        "PARI/GP Atkin modular polynomials for prime levels 500 < p < 800 "
        "(seadata-big), consumed by ellcard / ellmodulareqn"
    )
    license = "GPL-2.0-or-later"
    homepage = "https://pari.math.u-bordeaux.fr/packages.html#seadata"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "unknown"

    # Pure data package: no compiler touches any artifact.  The full
    # settings tuple is declared (L0p requires all four for the OHOS
    # profile), but package_id() clears the recipe below, so every
    # platform shares the same noarch package.
    settings = "os", "arch", "compiler", "build_type"

    # Byte-range fetch tuning for the 98.7 MB single-host archive.  CI workers
    # have no `curl` (the pipeline pre-download is skipped) and their egress
    # truncates individual range transfers (observed: a 2 MiB range cut at
    # ~0.5 MiB), so every range is resumable and incomplete ranges are retried
    # in further passes instead of being discarded and restarting from zero.
    _WORKERS = 8
    _PART_SIZE = 2 * 1024 * 1024
    _PART_ATTEMPTS = 3
    _PART_ROUNDS = 8
    _READ_TIMEOUT_SECONDS = 120
    _DEADLINE_SECONDS = 3000

    def export_sources(self):
        # Every module the validator imports must travel with the recipe:
        # the script itself *and* its pinned hash table.
        for name in ("verify_seadata_big.py", "hashes_seadata_big.py"):
            copy(
                self,
                name,
                src=os.path.join(self.recipe_folder, "test_package"),
                dst=os.path.join(self.export_sources_folder, "test_package"),
            )

    def layout(self):
        basic_layout(self)

    def configure(self):
        self.settings.rm_safe("os.version")
        self.settings.rm_safe("compiler.cppstd")

    def source(self):
        source = dict(self.conan_data["sources"][self.version])
        size = source.pop("size")
        archive = Path(self.source_folder) / "seadata-big.tar"
        if source["url"].startswith("file://"):
            # CI pre-download cache: Conan's get() still verifies SHA256 and
            # unpacks the archive.
            get(self, **source, strip_root=False)
            return
        self.output.info(
            "Downloading the official seadata-big archive with parallel byte "
            "ranges (45-minute budget)"
        )
        self._download_parallel(
            source["url"], archive, size, source["sha256"],
            progress=self.output.info,
        )
        try:
            unzip(self, str(archive))
        finally:
            archive.unlink(missing_ok=True)
        apply_conandata_patches(self)

    @classmethod
    def _download_parallel(cls, url, destination, size, expected_sha256, *,
                           progress=None):
        """Fetch exact byte ranges; expose only a completely verified archive.

        Ranges that exhaust their attempts are retried in further passes
        instead of aborting the build, because the failures seen on CI workers
        are transient and hit a different range on every run.
        """
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        deadline = time.monotonic() + cls._DEADLINE_SECONDS
        ranges = [(start, min(start + cls._PART_SIZE - 1, size - 1))
                  for start in range(0, size, cls._PART_SIZE)]

        with tempfile.TemporaryDirectory(prefix=".seadata-download-",
                                         dir=destination.parent) as temporary:
            root = Path(temporary)
            parts = [root / str(index) for index in range(len(ranges))]
            missing = list(range(len(ranges)))
            errors = {}

            for round_index in range(cls._PART_ROUNDS):
                if not missing:
                    break
                if time.monotonic() >= deadline:
                    raise _DownloadBudgetExhausted(
                        "PARI download budget exhausted between range passes"
                    )
                failures = []
                with ThreadPoolExecutor(max_workers=cls._WORKERS) as executor:
                    futures = {
                        executor.submit(cls._fetch_range, url, parts[index],
                                        *ranges[index], size, deadline): index
                        for index in missing
                    }
                    for future in as_completed(futures):
                        index = futures[future]
                        error = future.result()
                        if error is None:
                            if progress:
                                progress(
                                    f"Verified byte range {index + 1}/{len(ranges)}"
                                )
                        else:
                            failures.append(index)
                            errors[index] = error
                missing = failures
                if missing and round_index + 1 < cls._PART_ROUNDS:
                    if progress:
                        done = sum(p.stat().st_size for p in parts if p.exists())
                        progress(
                            f"Range pass {round_index + 1}: "
                            f"{done // 1048576} MiB of {size // 1048576} MiB "
                            f"downloaded, {len(missing)} range(s) still "
                            f"incomplete (e.g. {errors[missing[0]]!r})"
                        )
                    time.sleep(min(2 ** round_index, 8))

            if missing:
                raise OSError(
                    f"{len(missing)} byte range(s) never completed, e.g. "
                    f"{errors[missing[0]]!r}"
                )

            combined = root / "archive.tar"
            digest = hashlib.sha256()
            with combined.open("wb") as output:
                for part in parts:
                    with part.open("rb") as source:
                        while chunk := source.read(1024 * 1024):
                            output.write(chunk)
                            digest.update(chunk)
            if combined.stat().st_size != size or digest.hexdigest() != expected_sha256:
                raise ValueError("PARI archive size or SHA256 mismatch")
            os.replace(combined, destination)

    @classmethod
    def _fetch_range(cls, url, part, start, end, size, deadline):
        """Fetch one exact byte range, resuming after a dropped connection.

        Returns ``None`` once the whole range is on disk, or the last error seen
        so the caller can schedule another pass.  Bytes already received are
        kept: CI egress truncates range transfers mid-flight (observed: a 2 MiB
        range cut at ~0.5 MiB), and restarting from zero on every cut never
        finishes inside the ``conan create`` budget.
        """
        expected_size = end - start + 1
        last_error = None
        for attempt in range(cls._PART_ATTEMPTS):
            if time.monotonic() >= deadline:
                raise _DownloadBudgetExhausted(
                    "PARI download budget exhausted during a byte range"
                )
            have = part.stat().st_size if part.exists() else 0
            if have >= expected_size:
                return None
            first = start + have
            wanted = expected_size - have
            request = urllib.request.Request(url, headers={
                "Range": f"bytes={first}-{end}",
                "Accept-Encoding": "identity",
                "User-Agent": "Conan/2 pari-seadata-big",
            })
            try:
                with urllib.request.urlopen(
                        request, timeout=cls._READ_TIMEOUT_SECONDS) as response:
                    if (response.status != 206
                            or response.headers.get("Content-Range")
                            != f"bytes {first}-{end}/{size}"):
                        raise ValueError(
                            f"status={response.status} "
                            f"content-range="
                            f"{response.headers.get('Content-Range')!r}"
                        )
                    received = 0
                    with part.open("ab" if have else "wb") as output:
                        while True:
                            if time.monotonic() >= deadline:
                                raise _DownloadBudgetExhausted(
                                    "PARI download budget exhausted during a "
                                    "byte range transfer"
                                )
                            # read1() returns whatever has already arrived, so
                            # the deadline is re-checked while a peer trickles.
                            chunk = response.read1(64 * 1024)
                            if not chunk:
                                break
                            received += len(chunk)
                            if received > wanted:
                                raise ValueError(
                                    f"oversized range ({received} > {wanted})"
                                )
                            output.write(chunk)
                if received == wanted:
                    return None
                last_error = OSError(f"truncated range ({received} != {wanted})")
            except _DownloadBudgetExhausted:
                raise
            except (OSError, http.client.HTTPException, ValueError) as error:
                last_error = error
            if attempt + 1 < cls._PART_ATTEMPTS:
                time.sleep(min(2 ** attempt, 4))
        return last_error

    @property
    def _validator(self):
        return os.path.join(
            self.export_sources_folder,
            "test_package",
            "verify_seadata_big.py",
        )

    def build(self):
        # Deterministic data validation on the unpacked source tree, run
        # during create() so a corrupt download fails the build (R34: a
        # data package has no callable API, integrity checking replaces
        # the compile smoke test).
        self.run(
            f'"{sys.executable}" "{self._validator}" '
            f'--source-root "{self.source_folder}"'
        )

    def package(self):
        data_dir = os.path.join(
            self.package_folder, "share", "pari", "seadata"
        )
        docs_dir = os.path.join(
            self.package_folder, "share", "doc", "pari-seadata-big"
        )

        copy(
            self,
            "sea*.gz",
            src=os.path.join(self.source_folder, "data", "seadata"),
            dst=data_dir,
            keep_path=False,
        )
        copy(
            self,
            "README.big",
            src=os.path.join(self.source_folder, "data", "seadata"),
            dst=docs_dir,
            keep_path=False,
        )
        # The archive carries no COPYING file; README.big states the
        # package is GPL-2.0-or-later (same as PARI/GP itself).  Package
        # the README as the license reference.
        copy(
            self,
            "README.big",
            src=os.path.join(self.source_folder, "data", "seadata"),
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.resdirs = ["share"]

        data_dir = os.path.join(
            self.package_folder, "share", "pari", "seadata"
        )
        # The consumer merges these files into PARI's `seadata` data
        # directory (which must also provide the base sea0 index).
        self.buildenv_info.define_path("PARI_SEADATA_BIG_DIR", data_dir)
        self.runenv_info.define_path("PARI_SEADATA_BIG_DIR", data_dir)
        self.conf_info.define("user.pari-seadata-big:data_dir", data_dir)
