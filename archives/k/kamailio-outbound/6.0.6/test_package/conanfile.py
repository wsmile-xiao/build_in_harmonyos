import os
import re
import shutil
import sys

from conan import ConanFile
from conan.tools.env import Environment


class KamailioOutboundTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _c_compiler(self):
        """定位 C 编译器：profile 的 compiler_executables → CC → OHOS SDK → PATH。

        与同族 kamailio 模块（unixodbc/debugger）用例保持同一查找链，避免依赖
        构建机上未导出的 shell 变量（R33）。
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
        # R34 实质验证：消费者视角校验打包产物 outbound.so
        package_folder = self.dependencies[self.tested_reference_str].package_folder
        module = os.path.join(package_folder, "lib", "kamailio", "modules", "outbound.so")
        assert os.path.isfile(module), f"outbound.so not found at {module}"
        self.output.info(f"outbound.so found: {module}")

        checker = os.path.join(self.source_folder, "check_outbound.py")
        env = Environment()
        env.define("OUTBOUND_MODULE", module)
        env.define("OUTBOUND_PACKAGE_FOLDER", package_folder)

        # 1) 产物面校验：ELF 架构 / 模块导出符号 / OpenSSL 静态吸收 / 许可证 / RPATH
        with env.vars(self).apply():
            self.run(f'"{sys.executable}" "{checker}"')

        # 2) 消费者端到端用例：真实 dlopen 加载 outbound.so，走
        #    exports → mod_init → bind_ob → encode/decode flow-token → destroy 全链路
        #    （含 HMAC 篡改、非法长度、空 token 等负例）。
        cc = self._c_compiler()
        assert cc is not None, "no C compiler available for the consumer end-to-end test"
        self.output.info(f"consumer e2e compiler: {cc}")

        build_dir = os.path.join(self.build_folder, "outbound_consumer_e2e")
        os.makedirs(build_dir, exist_ok=True)
        binary = os.path.join(build_dir, "outbound_e2e")
        log = os.path.join(build_dir, "e2e-run.log")

        sources = [
            os.path.join(self.source_folder, name)
            for name in ("test_outbound_e2e.c", "kamailio_core_stub.c")
        ]
        for path in sources:
            assert os.path.isfile(path), f"consumer test source missing: {path}"

        # --export-dynamic：用例把 core 符号层（桩）导出给 dlopen 的模块解析
        # （OHOS/musl 无惰性绑定，RTLD_NOW 需要全部未定义符号可解析）。
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
        self.output.info(f"outbound consumer e2e: {passed} passed, {failed} failed")
        assert failed == 0, f"{failed} consumer end-to-end assertions failed"
        assert passed >= 60, f"unexpectedly few end-to-end assertions: {passed}"
