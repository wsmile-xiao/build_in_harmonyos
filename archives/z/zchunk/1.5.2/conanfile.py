#!/usr/bin/env python3
"""Conan recipe for zchunk 1.5.2 — Meson project (vendored meson pattern).

zchunk 是分块压缩文件格式库（libzck + zck/unzck/zck_delta_size/zck_gen_zdict/
zck_read_header/zckdl 工具）。上游用 Meson 构建，依赖 zstd（必需）、
openssl（校验和，auto）、curl（zckdl 下载器，auto）、argp（工具参数解析，
glibc 自带；OHOS musl 无 argp.h → 走 argp-standalone）。

构建工具策略（astroterm/1.0.9、libdvdnav/7.0.0 已验证的 vendored meson 方案）：
真机与 CI worker 的 PATH 均无 meson 可执行文件，ohpcd/conancenter 远端无可解析
meson 工具包 → source() 下载官方 meson 1.11.2 源码到 meson-vendor/，build() 经
python3 -c 进程内 sys.path 注入调用 mesonmain.main()。

R51 上游测试：test/meson.build 注册 37 个 test()（22 无条件 + 15 仅在小端机
注册，aarch64 全部命中），build() 内经 vendored meson test 真实执行，解析
Ok:/Fail:/Skipped: 计数，失败抛错并输出 HMBS_UPSTREAM_TEST_RESULT 标记。
"""
import json
import os
import re

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout
from conan.tools.meson import MesonToolchain
from conan.tools.gnu import PkgConfigDeps


class ZchunkConan(ConanFile):
    name = "zchunk"
    version = "1.5.2"
    description = (
        "A file format that is designed for efficient deltas of compressed files"
    )
    license = "MIT"
    homepage = "https://github.com/zchunk/zchunk"
    url = "https://github.com/zchunk/zchunk"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} not supported")

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires("zstd/1.5.7.1")
        # 与 curl/8.15.0.1 的 openssl 钉版保持一致，避免图中版本冲突
        self.requires("openssl/3.5.6.1")
        self.requires("curl/8.15.0.1")
        self.requires("argp-standalone/1.4.1")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # vendored meson 构建工具源码（astroterm/1.0.9 已验证方案）
        mv = os.path.join(self.source_folder, "meson-vendor")
        get(self, **self.conan_data["meson_source"], strip_root=True, destination=mv)

    # 真机 python3.12 运行 vendored meson 所需前缀（libdvdnav/astroterm 已验证）
    _PY_HOME = "/data/service/hnp/python.org/python_3.12"
    _PY_LIB = "/data/service/hnp/python.org/python_3.12/lib"
    _HNP_BIN = "/data/service/hnp/bin"

    def _python3(self):
        cand = os.path.join(self._HNP_BIN, "python3")
        return cand if os.path.isfile(cand) else "python3"

    def _ninja(self):
        cand = os.path.join(self._HNP_BIN, "ninja")
        return cand if os.path.isfile(cand) else "ninja"

    def _meson_cmd(self, meson_argv):
        # HMBS_PYTHON3 的 site-packages 无 mesonbuild，且 Conan self.run(env=)
        # 设的 PYTHONPATH 传不到子进程 sys.path → 用 python3 -c 进程内注入。
        # mesonmain.main() 无参（读 sys.argv），argv 前置 "meson" 占位程序名。
        py = self._python3()
        mv = os.path.join(self.source_folder, "meson-vendor")
        argv_lit = json.dumps(["meson"] + list(meson_argv))
        mv_lit = json.dumps(mv)
        script = (
            "import sys;"
            f"sys.path.insert(0,{mv_lit});"
            f"sys.argv={argv_lit};"
            "from mesonbuild import mesonmain;"
            "rc=mesonmain.main();"
            "sys.exit(rc or 0)"
        )
        return py, ["-c", f"'{script}'"]

    def _meson_env(self, extra=None):
        # Conan 2.x self.run(env=...) 要 list（["KEY=VALUE", ...]）。
        env = {"PATH": os.environ.get("PATH", "")}
        # vendored meson 的 ninja 后端：真机在 /data/service/hnp/bin
        if os.path.isdir(self._HNP_BIN):
            env["PATH"] = self._HNP_BIN + ":" + env["PATH"]
        mv = os.path.join(self.source_folder, "meson-vendor")
        pp = os.environ.get("PYTHONPATH", "")
        env["PYTHONPATH"] = (mv + ":" + pp).strip(":") if pp else mv
        if os.path.isdir(self._PY_HOME):
            env["PYTHONHOME"] = self._PY_HOME
        ll = os.environ.get("LD_LIBRARY_PATH", "")
        if os.path.isdir(self._PY_LIB):
            env["LD_LIBRARY_PATH"] = (self._PY_LIB + ":" + ll).strip(":")
        # PkgConfigDeps 把全部依赖的 .pc 聚合到 generators 目录，是
        # meson dependency('libzstd'/'libcurl'/'openssl'/'argp-standalone')
        # 的解析入口（依赖名与上游 meson.build 的 pkg-config 查找逐一对应）。
        env["PKG_CONFIG_PATH"] = self.generators_folder
        for k in ("HMBS_CMAKE", "HMBS_MAKE", "HMBS_NINJA", "HMBS_PYTHON3"):
            if k in os.environ:
                env[k] = os.environ[k]
        if extra:
            env.update(extra)
        return [f"{k}={v}" for k, v in env.items()]

    def generate(self):
        tc = MesonToolchain(self)
        # 上游 feature 选项：强制启用三个可选依赖（默认 auto，缺失时静默
        # 降级会砍掉 zckdl 与部分测试），并开启上游测试套件
        tc.project_options["with-zstd"] = "enabled"
        tc.project_options["with-curl"] = "enabled"
        tc.project_options["with-openssl"] = "enabled"
        tc.project_options["tests"] = True
        tc.project_options["docs"] = False
        if not self.options.shared:
            tc.project_options["default_library"] = "static"
        tc.generate()
        # 生成 libzstd/libcurl/openssl/argp-standalone 的 .pc 到 generators
        # 目录（_meson_env 的 PKG_CONFIG_PATH 指向它，上游 meson.build 的
        # dependency() 全部按 pkg-config 名查找）
        PkgConfigDeps(self).generate()
        self._inject_meson_archiver()

    def _inject_meson_archiver(self):
        # meson checklist：CI worker PATH 无裸 llvm-ar/llvm-ranlib，需在
        # native file 写绝对路径（astroterm/1.0.9 同款）
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        ar = executables.get("ar")
        ranlib = executables.get("ranlib")
        if not ar:
            compiler = executables.get("cpp") or executables.get("c") or ""
            bindir = os.path.dirname(compiler)
            candidate = os.path.join(bindir, "llvm-ar") if bindir else ""
            if candidate and os.path.isfile(candidate):
                ar = candidate
                candidate_ranlib = os.path.join(bindir, "llvm-ranlib")
                if os.path.isfile(candidate_ranlib):
                    ranlib = candidate_ranlib
        native_file = os.path.join(
            self.generators_folder, "conan_meson_native.ini"
        )
        if not ar or not os.path.isfile(native_file):
            return
        with open(native_file, encoding="utf-8") as handle:
            content = handle.read()
        if "\nar =" in content or "[binaries]" not in content:
            return
        binaries = "[binaries]\nar = '%s'\n" % ar
        if ranlib:
            binaries += "ranlib = '%s'\n" % ranlib
        with open(native_file, "w", encoding="utf-8") as handle:
            handle.write(content.replace("[binaries]\n", binaries, 1))

    def build(self):
        apply_conandata_patches(self)
        env = self._meson_env()
        nf = os.path.join(self.generators_folder, "conan_meson_native.ini")
        bdir = self.build_folder
        sdir = self.source_folder
        py, margs = self._meson_cmd(
            ["setup", sdir, bdir, "--prefix=/", "--native-file", nf]
        )
        self.run(f'"{py}" {" ".join(margs)}', env=env)
        ninja = self._ninja()
        self.run(f'"{ninja}" -C "{bdir}" -j1', env=env)
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        """R51：build() 内真实执行上游 meson test 套件，解析框架汇总计数
        （Ok:/Fail:/Skipped:），失败抛错。计数取自 meson 汇总行，非硬编码。"""
        log_path = os.path.join(self.build_folder, "meson_test.log")
        py, margs = self._meson_cmd(
            ["test", "-v", "-C", self.build_folder,
             "--timeout-multiplier=16", "--no-rebuild", "--print-errorlogs"]
        )
        test_cmd = f'"{py}" {" ".join(margs)} > "{log_path}" 2>&1'
        self.run(test_cmd, env=self._meson_env(), ignore_errors=True)
        out = ""
        if os.path.isfile(log_path):
            with open(log_path, encoding="utf-8", errors="replace") as f:
                out = f.read()
        self.output.info("=== upstream meson test (tail) ===")
        for line in (out.splitlines() or [])[-25:]:
            self.output.info(line)

        def _cnt(pat):
            m = re.search(pat, out, flags=re.MULTILINE)
            return int(m.group(1)) if m else 0

        ok = _cnt(r"^Ok:\s+(\d+)")
        fail = _cnt(r"^Fail:\s+(\d+)")
        skipped = _cnt(r"^Skipped:\s+(\d+)")
        timeout = _cnt(r"^Timeout:\s+(\d+)")
        not_run = _cnt(r"^Not run:\s+(\d+)")
        executed = ok + fail + skipped + timeout + not_run
        gate_ok = executed > 0 and fail == 0 and skipped == 0 \
            and timeout == 0 and not_run == 0
        ut_status = "passed" if gate_ok else "failed"
        ut_result = {
            "status": ut_status,
            "framework": "meson",
            "command": test_cmd,
            "discovered": executed,
            "executed": executed,
            "passed": ok,
            "failed": fail,
            "skipped": skipped,
        }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(ut_result, ensure_ascii=False)
        )
        if ut_status != "passed":
            raise RuntimeError(
                "upstream meson tests failed: executed=%d failed=%d skipped=%d"
                % (executed, fail, skipped)
            )

    def package(self):
        # meson install 用 --destdir CLI 标志（Conan self.run(env=...) 注入的
        # DESTDIR 不可靠到达 vendored meson 子进程，libdvdnav 已验证），配合
        # setup 阶段的 --prefix=/，产物直接落 package_folder 根。
        bdir = self.build_folder
        py, margs = self._meson_cmd(
            ["install", "-C", bdir, "--no-rebuild", "--destdir",
             self.package_folder]
        )
        self.run(f'"{py}" {" ".join(margs)}', env=self._meson_env())

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.libs = ["zck"]
        self.cpp_info.set_property("pkg_config_name", "zck")
        # R38: 同时产出 zck/unzck/zck_delta_size/zck_gen_zdict/zck_read_header/
        # zckdl CLI 工具（软件级 commands.json 已声明）
        self.cpp_info.bindirs = ["bin"]
