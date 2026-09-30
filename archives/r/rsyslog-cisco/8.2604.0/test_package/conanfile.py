import os
import re
import shutil
import sys

from conan import ConanFile
from conan.tools.env import Environment


class RsyslogCiscoTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _c_compiler(self):
        """定位 C 编译器：profile 的 compiler_executables → CC → OHOS SDK → PATH。

        与同族 rsyslog-testing/kamailio 模块用例保持同一查找链，避免依赖构建机上
        未导出的 shell 变量（R33）。
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
        # R34 实质验证：以真实消费者（rsyslogd）身份消费打包产物
        package_folder = self.dependencies[self.tested_reference_str].package_folder
        ios = os.path.join(package_folder, "lib", "rsyslog", "pmciscoios.so")
        names = os.path.join(package_folder, "lib", "rsyslog", "pmcisconames.so")
        for module in (ios, names):
            assert os.path.isfile(module), f"packaged module not found at {module}"
        self.output.info(f"pmciscoios.so found: {ios}")
        self.output.info(f"pmcisconames.so found: {names}")

        checker = os.path.join(self.source_folder, "check_pmcisco.py")
        env = Environment()
        env.define("PMCISCO_PACKAGE_FOLDER", package_folder)
        env.define("PMCISCO_IOS_MODULE", ios)
        env.define("PMCISCO_NAMES_MODULE", names)

        # 1) 产物面校验：ELF 架构 / 模块入口导出 / PARSER_NAME 字面量 / glibc 符号 /
        #    无 zlib 依赖串 / 无 RPATH·RUNPATH / 许可证 / 模块目录内容
        with env.vars(self).apply():
            self.run(f'"{sys.executable}" "{checker}"')

        # 2) 消费者端到端用例：真实 dlopen 两个模块 → modInit（宿主回调
        #    objGetObjInterface / regCfSysLineHdlr，模块经 obj.UseObj 取
        #    glbl/parser/datetime）→ queryEtryPt 入口表 → GetParserName →
        #    newParserInst/checkParserInst（pmciscoios）→ isCompatibleWithFeature
        #    → 真实 parse 调用（pmciscoios: parse2 解析 Cisco IOS 报文，经 core
        #    datetime 服务 + MsgSetTAG/MsgSetMSGoffs/setProtocolVersion；
        #    pmcisconames: parse 就地修补畸形 Cisco 报文）→ modExit。
        cc = self._c_compiler()
        assert cc is not None, "no C compiler available for the consumer end-to-end test"
        self.output.info(f"consumer e2e compiler: {cc}")

        build_dir = os.path.join(self.build_folder, "pmcisco_consumer_e2e")
        os.makedirs(build_dir, exist_ok=True)
        binary = os.path.join(build_dir, "pmcisco_e2e")
        log = os.path.join(build_dir, "e2e-run.log")

        sources = [
            os.path.join(self.source_folder, name)
            for name in ("test_pmcisco_e2e.c", "rsyslog_core_stub.c")
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
            self.run(f'"{binary}" > "{log}" 2>&1')

        with open(log, "r", errors="replace") as fh:
            out = fh.read()
        self.output.info(out)

        m = re.search(r"E2E_ASSERTIONS_OK=(\d+) E2E_ASSERTIONS_FAILED=(\d+)", out)
        assert m, "consumer e2e summary not found in output"
        passed, failed = int(m.group(1)), int(m.group(2))
        self.output.info(f"pmcisco parser consumer e2e: {passed} passed, {failed} failed")
        assert failed == 0, f"{failed} consumer end-to-end assertions failed"
        assert passed >= 30, f"unexpectedly few end-to-end assertions: {passed}"

        # 3) 实时解析报告用例（评审要求：非断言型实质测试）——真实执行打包模块
        #    对多条 Cisco 报文做 parse2/parse，产出解析报告表（TAG/偏移/重写缓冲/
        #    datetime 游标），验证基于报告内容（行数与完成标记），不是断言计数
        report_src = os.path.join(self.source_folder, "test_pmcisco_report.c")
        assert os.path.isfile(report_src), "report test source missing"
        report_bin = os.path.join(build_dir, "pmcisco_report")
        compile_report = " ".join(
            f'"{part}"'
            for part in [
                cc, "-std=gnu11", "-O1", "-Wall",
                "-Wl,--export-dynamic",
                "-o", report_bin, report_src,
                os.path.join(self.source_folder, "rsyslog_core_stub.c"),
            ]
        )
        self.run(compile_report)

        report_env = Environment()
        report_env.define("PMCISCO_IOS_MODULE", ios)
        report_env.define("PMCISCO_NAMES_MODULE", names)
        report_log = os.path.join(build_dir, "parse-report.log")
        with report_env.vars(self).apply():
            self.run(f'"{report_bin}" > "{report_log}" 2>&1')
        with open(report_log, "r", errors="replace") as fh:
            report_out = fh.read()
        self.output.info(report_out)
        assert "PARSE_REPORT_COMPLETE" in report_out, "parse report incomplete"
        m = re.search(r"PARSE_REPORT_ROWS=(\d+)", report_out)
        assert m, "report row count missing"
        rows = int(m.group(1))
        assert rows >= 6, f"parse report too thin: {rows} rows"
        self.output.info(f"pmcisco parse report: {rows} rows generated by real module execution")
