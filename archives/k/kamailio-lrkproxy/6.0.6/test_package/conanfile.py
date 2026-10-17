import os
import subprocess
import sys

from conan import ConanFile
from conan.tools.env import Environment


class KamailioLrkproxyTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R34 实质验证：对打包产物 lrkproxy.so 做真实检查
        # （ELF 架构 / 模块符号 / 无 RPATH 泄漏 / 零外部依赖确认）
        package_folder = self.dependencies[self.tested_reference_str].package_folder
        module = os.path.join(package_folder, "lib", "kamailio", "modules", "lrkproxy.so")
        assert os.path.isfile(module), f"lrkproxy.so not found at {module}"
        self.output.info(f"lrkproxy.so found: {module}")

        checker = os.path.join(self.source_folder, "check_lrkproxy.py")
        env = Environment()
        env.define("KAMAILIO_LRKPROXY_MODULE", module)
        with env.vars(self).apply():
            self.run(f'"{sys.executable}" "{checker}"')

        # rule12 鸿蒙特有端到端消费者用例：以 kamailio core 的 loadmodule 真实
        # 消费路径走通完整生命周期（dlopen → dlsym(exports) → 参数 setter →
        # mod_init → mod_destroy → dlclose），core ABI 由 lrkproxy_core_stub.c
        # 提供（musl 急切绑定）。编译器解析：profile 的 conf 绝对路径优先，回退
        # OHOS SDK 固定路径（CI harness 导出的 CC 是裸名且 SDK bin 不在 PATH，
        # kamailio-unixodbc #61596 同因已验证此修法）。
        e2e_src = os.path.join(self.source_folder, "test_lrkproxy_e2e.c")
        stub_src = os.path.join(self.source_folder, "lrkproxy_core_stub.c")
        e2e_bin = os.path.join(self.build_folder, "test_lrkproxy_e2e")
        # Conan 2 的 tools.build:compiler_executables 是 dict conf（无 ":c" 后缀键），
        # 取值链：conf["c"] → 环境变量 CC → 裸名 clang（PATH 解析）
        compilers = self.conf.get("tools.build:compiler_executables", default={})
        cc = compilers.get("c") if isinstance(compilers, dict) else None
        cc = cc or os.environ.get("CC") or "clang"
        if not os.path.isabs(cc) or not os.path.isfile(cc):
            sdk_cc = ("/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18"
                      "/ohos/native/llvm/bin/aarch64-unknown-linux-ohos-clang")
            if os.path.isfile(sdk_cc):
                cc = sdk_cc
        cmd = [cc, "-std=c11", e2e_src, stub_src, "-o", e2e_bin, "-ldl",
               "-Wl,--export-dynamic"]
        subprocess.run(cmd, check=True)
        with env.vars(self).apply():
            self.run(f'"{e2e_bin}" "{module}"')
