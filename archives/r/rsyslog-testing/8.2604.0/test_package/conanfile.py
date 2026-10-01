import os
import re
import shutil
import sys

from conan import ConanFile
from conan.tools.env import Environment


class RsyslogTestingTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _c_compiler(self):
        """定位 C 编译器：profile 的 compiler_executables → CC → OHOS SDK → PATH。

        与同族 rsyslog/kamailio 模块用例保持同一查找链，避免依赖构建机上未导出的
        shell 变量（R33）。
        """
        candidates = []
        try:
            conf = self.conf.get("tools.build:compiler_executables", default={}) or {}
            if isinstance(conf, dict) and conf.get("c"):
                candidates.append(conf["c"])
        except Exception:
            pass
        candidates += [
            os.environ.get("CC"),
            "/data/service/hnp/bin/clang",
            shutil.which("clang"),
            shutil.which("cc"),
            shutil.which("gcc"),
        ]
        for cand in candidates:
            if cand and os.path.exists(cand):
                return cand
        return None

    def test(self):
        # R34 实质验证：消费者视角校验打包产物 omtesting.so
        package_folder = self.dependencies[self.tested_reference_str].package_folder
        module = os.path.join(package_folder, "lib", "rsyslog", "omtesting.so")
        assert os.path.isfile(module), f"omtesting.so not found at {module}"
        self.output.info(f"omtesting.so found: {module}")

        checker = os.path.join(self.source_folder, "check_omtesting.py")
        env = Environment()
        env.define("OMTESTING_MODULE", module)
        env.define("OMTESTING_PACKAGE_FOLDER", package_folder)

        # 1) 产物面校验：ELF 架构 / 模块入口导出 / glibc 符号 / 无 zlib 依赖串 /
        #    无构建机路径泄漏 / 许可证 / 模块目录内容 / 动态段
        with env.vars(self).apply():
            self.run(f'"{sys.executable}" "{checker}"')

        # 2) 消费者端到端用例：真实 dlopen 加载 omtesting.so，走
        #    modInit（host 回调 objGetObjInterface / regCFSLineHdlr）
        #    → queryEtryPt 入口表 → createInstance → createWrkrInstance
        #    → isCompatibleWithFeature → tryResume → doAction(投递真实消息)
        #    → freeWrkrInstance/freeInstance/modExit 全链路。
        cc = self._c_compiler()
        assert cc is not None, "no C compiler available for the consumer end-to-end test"
        self.output.info(f"consumer e2e compiler: {cc}")

        build_dir = os.path.join(self.build_folder, "omtesting_consumer_e2e")
        os.makedirs(build_dir, exist_ok=True)
        binary = os.path.join(build_dir, "omtesting_e2e")
        log = os.path.join(build_dir, "e2e-run.log")

        sources = [
            os.path.join(self.source_folder, name)
            for name in ("test_omtesting_e2e.c", "rsyslog_core_stub.c")
        ]
        for path in sources:
            assert os.path.isfile(path), f"consumer test source missing: {path}"

        # --export-dynamic：用例把 rsyslog core 符号层（桩）导出给 dlopen 的模块
        # 解析（OHOS/musl 无惰性绑定，RTLD_NOW 需要全部未定义符号可解析）。
        compile_cmd = " ".join(
            f'"{part}"'
            for part in [
                cc,
                "-std=gnu11",
                "-O1",
                "-g",
                "-Wall",
                "-Wextra",
                "-Wl,--export-dynamic",
                "-o",
                binary,
                *sources,
            ]
        )
        self.run(compile_cmd)

        with env.vars(self).apply():
            self.run(f'"{binary}" "{module}" > "{log}" 2>&1')

        with open(log, "r", errors="replace") as fh:
            out = fh.read()
        self.output.info(out)

        m = re.search(r"E2E_ASSERTIONS_OK=(\d+) E2E_ASSERTIONS_FAILED=(\d+)", out)
        assert m, "consumer e2e summary not found in output"
        passed, failed = int(m.group(1)), int(m.group(2))
        self.output.info(f"omtesting consumer e2e: {passed} passed, {failed} failed")
        assert failed == 0, f"{failed} consumer end-to-end assertions failed"
        assert passed >= 30, f"unexpectedly few end-to-end assertions: {passed}"
