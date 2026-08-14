#!/usr/bin/env python3
"""Conan test_package for ncmdump 1.5.1 — L1 consumer test.

test() fetches the upstream official test.ncm fixture at run time
(taurusxin/ncmdump test/test.ncm, sha256-verified) so no binary fixture
is committed to the repo, then runs test.sh which drives the packaged
ncmdump binary: `ncmdump -v` plus a real decryption of the fixture.
"""
import hashlib
import os
import tempfile
import urllib.request

from conan import ConanFile


class NcmdumpTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _fetch_test_ncm(self):
        # 上游官方样例 test.ncm（taurusxin/ncmdump 1.5.1 test/ 目录）。
        # 已知 SHA-256（设备端已独立校验）：
        # a1586bbbbad95019eee566411de58a57c3a3bd7c86d97f2c3c82427efce8964b
        expect_sha = "a1586bbbbad95019eee566411de58a57c3a3bd7c86d97f2c3c82427efce8964b"
        workdir = tempfile.mkdtemp(prefix="ncmdump-test-")
        dst = os.path.join(workdir, "test.ncm")
        url = "https://raw.githubusercontent.com/taurusxin/ncmdump/1.5.1/test/test.ncm"
        try:
            urllib.request.urlretrieve(url, dst)
        except Exception as exc:  # noqa: BLE001 - 网络失败给出明确错误
            raise RuntimeError(f"failed to download test.ncm from {url}: {exc}")
        with open(dst, "rb") as fh:
            actual_sha = hashlib.sha256(fh.read()).hexdigest()
        if actual_sha != expect_sha:
            raise RuntimeError(
                f"test.ncm sha256 mismatch: got {actual_sha}, expected {expect_sha}"
            )
        return dst

    def test(self):
        ncm_path = self._fetch_test_ncm()
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        test_sh = os.path.join(self.source_folder, "test.sh")
        self.run(f'"{bash}" "{test_sh}" "{ncm_path}"', env="conanrun")
