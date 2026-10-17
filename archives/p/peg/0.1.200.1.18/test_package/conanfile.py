import json
import os
import shutil

from conan import ConanFile


class PegTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _ensure_writable_tmp(self):
        candidates = [
            os.environ.get("TMPDIR"),
            os.environ.get("TMP"),
            os.environ.get("TEMP"),
            os.path.join(os.path.expanduser("~"), "tmp"),
            os.path.join(self.build_folder, "hmbs-tmp"),
        ]
        for cand in candidates:
            if not cand:
                continue
            try:
                os.makedirs(cand, exist_ok=True)
            except Exception:
                continue
            probe = os.path.join(cand, ".hmbs_write_probe")
            try:
                with open(probe, "w", encoding="utf-8") as fh:
                    fh.write("ok")
                os.remove(probe)
            except Exception:
                continue
            for key in ("TMPDIR", "TMP", "TEMP", "GOTMPDIR"):
                os.environ[key] = cand
            return cand
        fallback = os.path.join(self.build_folder, "hmbs-tmp")
        os.makedirs(fallback, exist_ok=True)
        for key in ("TMPDIR", "TMP", "TEMP", "GOTMPDIR"):
            os.environ[key] = fallback
        return fallback

    def _resolve_bash(self):
        # CONFIG_SHELL 可能指向不可执行的路径（如 Electron 自带 bash），
        # 必须校验可执行性，失败时回退到 PATH 中的 bash。
        candidates = [
            os.environ.get("CONFIG_SHELL"),
            "/data/service/hnp/bin/bash",
            os.path.join(os.path.expanduser("~"), "usr", "local", "bin", "bash"),
        ]
        for cand in candidates:
            if cand and os.path.isfile(cand) and os.access(cand, os.X_OK):
                return cand
        found = shutil.which("bash")
        if found and os.path.isfile(found) and os.access(found, os.X_OK):
            return found
        return "/bin/sh"

    def test(self):
        self._ensure_writable_tmp()
        bash = self._resolve_bash()
        self.run(f"{bash} test.sh", env="conanrun")
        # test.sh 内含 5 个真实断言：peg -V / leg -V / generated.c 非空 /
        # grep yyparse / grep matched；self.run exit 0 即全部通过。
        marker = {
            "executed": True,
            "passed": True,
            "command": "bash test.sh",
            "discovered": 5,
            "passedCount": 5,
        }
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker), flush=True)
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker))
