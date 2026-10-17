#!/usr/bin/env python3
"""Artifact + behaviour gate for the packaged lft 3.98.

Layer 1 (artifact, 11 printed checkpoints: 5 checks x 2 executables + 1 man-page
check) inspects the *packaged* ELFs with readelf and scans their raw bytes for
host path leaks.  Layer 2 (behaviour, 8 script-counted checkpoints) executes the
programs as a real consumer.

Note on the .codesign checkpoint: CI never signs package ELFs (the signing step lives in
scripts/ohc/package_builder.py, a local-only path), so layer 1 asserts "at most one
.codesign section" on the *installed* artifact and prints the measured count, while the
"exactly one" invariant is enforced as a hard gate right after this test self-signs its
staged copy (_stage_signed).

Why the behaviour layer runs *staged, re-signed copies* instead of the package
folder: on this device executing ``<pkg>/bin/lft`` directly returns
"Operation not permitted" (measured), so the binaries are copied into a scratch
directory outside the archive tree, stripped of the old .codesign and
re-signed with ``binary-sign-tool -selfSign 1`` — the same recipe the libxft /
clxclient / aliki test packages use.  The scratch directory is removed in a
finally block, which also keeps regenerated ELFs from being folded into the PR
by ``git add archives/l/lft/`` (this window already had to undo that once).
"""
import os
import re
import shutil
import subprocess
import tempfile

from conan import ConanFile
from conan.errors import ConanException

REQUIRED_BEHAVIOURAL = 8
REQUIRED_SKIPPED = 3
SCRIPT = "test_lft.sh"


class LftTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    # -- small helpers ----------------------------------------------------

    @staticmethod
    def _exec(cmd):
        proc = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return proc.returncode, (proc.stdout or "") + (proc.stderr or "")

    @staticmethod
    def _tool(name):
        found = shutil.which(name)
        if found:
            return found
        for prefix in ("/data/service/hnp/bin", "/storage/Users/currentUser/.harmonybrew/bin"):
            cand = os.path.join(prefix, name)
            if os.path.isfile(cand):
                return cand
        raise ConanException("required tool not found: " + name)

    def _readelf(self, binary, flags):
        readelf = self._tool("llvm-readelf")
        rc, out = self._exec('%s %s "%s"' % (readelf, flags, binary))
        if rc != 0 or not out.strip():
            raise ConanException("readelf failed for " + binary)
        return out

    def _scratch_dir(self):
        for base in (tempfile.gettempdir(), os.path.expanduser("~/tmp"),
                     os.path.expanduser("~")):
            cand = os.path.join(base, "lft-smoke")
            try:
                os.makedirs(cand, exist_ok=True)
                probe = os.path.join(cand, ".w")
                with open(probe, "w") as handle:
                    handle.write("x")
                os.remove(probe)
                self._in_archive = False
                return cand
            except OSError:
                continue
        cand = os.path.join(self.build_folder, "lft-smoke")
        os.makedirs(cand, exist_ok=True)
        self._in_archive = True
        self.output.warning("scratch dir fell back inside the archive tree: "
                            + cand + " (removed at exit)")
        return cand

    def _stage_signed(self, src, dst_dir):
        name = os.path.basename(src)
        dst = os.path.join(dst_dir, name)
        for stale in (dst, dst + ".unsigned", dst + ".signed"):
            if os.path.lexists(stale):
                os.remove(stale)
        shutil.copy2(src, dst)
        os.chmod(dst, 0o755)
        if str(self.settings.os) != "OHOS":
            return dst
        objcopy = self._tool("llvm-objcopy")
        signer = self._tool("binary-sign-tool")
        self._exec('%s --remove-section .codesign "%s"' % (objcopy, dst))
        rc, out = self._exec('"%s" sign -inFile "%s" -outFile "%s" -selfSign 1'
                             % (signer, dst, dst + ".signed"))
        if rc != 0 or not os.path.isfile(dst + ".signed"):
            raise ConanException("self-sign failed for " + name + ": " + out[-400:])
        os.replace(dst + ".signed", dst)
        os.chmod(dst, 0o755)
        if self._readelf(dst, "-SW").count(".codesign") != 1:
            raise ConanException("signed copy lost its single .codesign: " + name)
        return dst

    # -- layer 1: artifact assertions -------------------------------------

    def _artifact_assertions(self, bindir):
        results = []
        for name in ("lft", "whob"):
            path = os.path.join(bindir, name)
            results.append((name + "-exists", os.path.isfile(path)))
            if not os.path.isfile(path):
                continue
            results.append((name + "-machine-aarch64",
                            "AArch64" in self._readelf(path, "-h")))
            # CI 不给产物签名：`git grep -ln 'sign_elf\|binary-sign-tool' -- ci/` 零命中，
            # 签名只挂在本地 scripts/ohc/package_builder.py ⇒ 安装包里的 ELF 在 CI 上恒为
            # 0 段。原先断言"恰好 1 段"是本地真/CI 假 —— CI build number 61499 实拍 lft 与
            # whob 两条 *-codesign-section-1 同时 FAIL，而同批 exists/machine/needed/
            # no-host-prefix-leak/man 五条全 PASS，即产物本身没问题。
            # 交付面不变量改成"至多 1 段"（0=未自签，运行前由消费者自签，正是本仓 arpoison/
            # aliki/coinutils 的做法；>=2=重签残留，必拦），并把实测值原样打印，让 CI 日志
            # 自己回答到底是几段。"恰好 1 段"仍由 _stage_signed 自签后的硬断言承载。
            sections = self._readelf(path, "-SW").count(".codesign")
            self.output.info("LFT_MEASURED_%s_codesign_sections=%d" % (name, sections))
            results.append((name + "-codesign-section-at-most-1", sections <= 1))
            needed = re.findall(r"\(NEEDED\).*\[([^\]]*)\]",
                                self._readelf(path, "-d"))
            results.append((name + "-needed-bare-sonames",
                            bool(needed) and all("/" not in n for n in needed)))
            with open(path, "rb") as handle:
                blob = handle.read().decode("utf-8", "ignore")
            results.append((name + "-no-host-prefix-leak",
                            "/storage/Users/currentUser" not in blob
                            and "/usr/local" not in blob))
        mans = set()
        for root, _, files in os.walk(os.path.join(os.path.dirname(bindir), "share")):
            for f in files:
                if f in ("lft.8", "whob.8"):
                    mans.add(f)
        results.append(("man-pages-installed", mans == {"lft.8", "whob.8"}))
        return results

    # -- entry point ------------------------------------------------------

    def test(self):
        pkg = self.dependencies["lft"].package_folder
        bindir = os.path.join(pkg, "bin")
        scratch = self._scratch_dir()
        try:
            results = self._artifact_assertions(bindir)
            for name, passed in results:
                self.output.info("LFT_ARTIFACT_%s %s"
                                 % ("PASS" if passed else "FAIL", name))
            failed = [n for n, ok in results if not ok]
            if failed:
                raise ConanException("artifact assertions failed: "
                                     + ", ".join(failed))

            staged_dir = os.path.join(scratch, "bin")
            work_dir = os.path.join(scratch, "work")
            os.makedirs(staged_dir, exist_ok=True)
            os.makedirs(work_dir, exist_ok=True)
            for name in ("lft", "whob"):
                self._stage_signed(os.path.join(bindir, name), staged_dir)

            script = os.path.join(os.path.dirname(os.path.abspath(__file__)), SCRIPT)
            os.chmod(script, 0o755)
            summary_path = os.path.join(work_dir, "summary.txt")
            rc = self.run('sh "%s" "%s" "%s"' % (script, staged_dir, work_dir),
                          env="conanrun", ignore_errors=True)
            if not os.path.isfile(summary_path):
                raise ConanException("behavioural suite wrote no summary file "
                                     "under %s (rc=%d)" % (summary_path, rc))
            summary = open(summary_path, encoding="utf-8").read().strip()
            self.output.info("behavioural summary: " + summary)
            match = re.search(r"behavioural=(\d+) skipped=(\d+) failed=(\d+)",
                              summary)
            if not match:
                raise ConanException("unparsable summary line: " + summary)
            beh, skipped, failed_n = (int(g) for g in match.groups())
            if rc != 0 or failed_n != 0:
                raise ConanException("behavioural suite failed (rc=%d failed=%d)"
                                     % (rc, failed_n))
            if beh != REQUIRED_BEHAVIOURAL or skipped != REQUIRED_SKIPPED:
                raise ConanException(
                    "declared counts do not match the run: behavioural=%d "
                    "skipped=%d, expected %d/%d"
                    % (beh, skipped, REQUIRED_BEHAVIOURAL, REQUIRED_SKIPPED))
            print("HMBS_TEST_PACKAGE_RESULT=" + str({
                "artifact_passed": sum(1 for _, ok in results if ok),
                "artifact_total": len(results),
                "behavioural_passed": beh,
                "skipped_declared": skipped,
                "executed": True,
                "passed": True,
            }))
        finally:
            shutil.rmtree(scratch, ignore_errors=True)
            if getattr(self, "_in_archive", False):
                shutil.rmtree(os.path.join(self.build_folder, "lft-smoke"),
                              ignore_errors=True)
