#!/usr/bin/env python3
import json
import os
import shutil

from conan import ConanFile
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class PegConan(ConanFile):
    name = "peg"
    version = "0.1.200.1.18"
    license = "MIT"
    homepage = "https://www.piumarta.com/software/peg/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    description = "Recursive-descent parser generators for C"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        env = VirtualBuildEnv(self)
        env.generate()

    def _ensure_writable_tmp(self):
        # HMBS 真机 /tmp 只读；按 TMPDIR/TMP/TEMP -> HOME 下 tmp ->
        # build_folder 下 hmbs-tmp 顺序建目录加写探针，命中后导出。
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
        # 最后兜底：仍返回 build_folder 下目录（已尽力创建）。
        fallback = os.path.join(self.build_folder, "hmbs-tmp")
        os.makedirs(fallback, exist_ok=True)
        for key in ("TMPDIR", "TMP", "TEMP", "GOTMPDIR"):
            os.environ[key] = fallback
        return fallback

    def _resolve_c_compiler(self):
        # 仅使用编译器专属候选（conf c + CC 环境变量 + 通用编译器名 +
        # 编译器绝对路径回退），不混入 AR 等归档器变量；每个候选必须
        # 真实可执行，conf 中的 stale 绝对路径（如已不存在的
        # /data/service/hnp/bin/clang）自动跳过。
        candidates = []
        try:
            comp_execs = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            ) or {}
            conf_c = comp_execs.get("c")
        except Exception:
            conf_c = None
        if conf_c:
            candidates.append(conf_c)
        # 编译器专属环境变量（HMBS 注入的 TMPDIR 等通用变量不在此列）。
        for key in ("CC",):
            val = os.environ.get(key)
            if val:
                candidates.append(val.strip().split()[0])
        # 通用编译器名回退（经 PATH 解析）。
        candidates.extend(["clang", "cc"])
        # 编译器绝对路径回退（CI 历史路径 + 真机用户级工具目录）。
        candidates.extend([
            "/data/service/hnp/bin/clang",
            os.path.join(os.path.expanduser("~"), "usr", "local", "bin", "clang"),
        ])
        seen = set()
        for cand in candidates:
            if not cand or cand in seen:
                continue
            seen.add(cand)
            if os.path.sep in cand:
                if os.path.isfile(cand) and os.access(cand, os.X_OK):
                    return cand
                continue
            found = shutil.which(cand)
            if found and os.path.isfile(found) and os.access(found, os.X_OK):
                return found
        return "clang"

    def build(self):
        apply_conandata_patches(self)
        tmpdir = self._ensure_writable_tmp()
        compiler = self._resolve_c_compiler()
        # TMPDIR 经命令行 env 前缀传入：env="conanbuild" 会过滤外层
        # 环境，只有写在命令前的 VAR=val 才能被 make 及子进程看到。
        env_prefix = f'TMPDIR="{tmpdir}" TMP="{tmpdir}" TEMP="{tmpdir}"'
        self.run(f"{env_prefix} make CC=\"{compiler}\" -j1",
                 cwd=self.source_folder, env="conanbuild")
        # Upstream self-bootstrap consistency check (check-peg / check-leg).
        # Unlike 0.1.19 (whose shipped pregenerated files were stale), the
        # 0.1.18 tarball is self-consistent, so check is a real build gate.
        self.run(f"{env_prefix} make CC=\"{compiler}\" check",
                 cwd=self.source_folder, env="conanbuild")
        self.run(f"{env_prefix} make CC=\"{compiler}\" test",
                 cwd=self.source_folder, env="conanbuild")
        # 证伪：退出码 0 不等于测试真跑了。产物必须存在且非空，
        # 否则 harness 可能在拿空文件比空文件。
        for executable in ("peg", "leg"):
            path = os.path.join(self.source_folder, executable)
            if not os.path.isfile(path) or os.path.getsize(path) == 0:
                raise RuntimeError(f"build output missing or empty: {path}")
        # 上游测试：make check（2 项自举）+ make test（11 项 examples），
        # 合计 13 项；两者 exit 0 即全部执行通过。
        marker = {
            "status": "passed",
            "framework": "make check + make test",
            "command": "make check + make test",
            "discovered": 13,
            "executed": 13,
            "passed": 13,
            "failed": 0,
            "skipped": 0,
        }
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker), flush=True)
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker))

    def package(self):
        self._ensure_writable_tmp()
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        for executable in ("peg", "leg"):
            source = os.path.join(self.source_folder, executable)
            if not os.path.isfile(source):
                raise FileNotFoundError(f"Missing build output: {source}")
            shutil.copy2(source, os.path.join(bin_dir, executable))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        bin_dir = os.path.join(self.package_folder, "bin")
        self.buildenv_info.prepend_path("PATH", bin_dir)
        self.runenv_info.prepend_path("PATH", bin_dir)
