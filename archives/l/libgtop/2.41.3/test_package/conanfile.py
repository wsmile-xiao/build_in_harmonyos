from conan import ConanFile


class LibgtopTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "PkgConfigDeps", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # 编译消费者冒烟测试与鸿蒙专项测试。注意：PKG_CONFIG_PATH 必须 export
        # 后再做命令替换（`VAR=x cmd $(pkg-config ...)` 中替换在赋值前展开，
        # 找不到 .pc）。编译器用 clang（profile buildenv PATH 提供），
        # env=conanbuild 应用该 PATH。
        _gens = self.generators_folder
        for _src in ("test_consumer.c", "ohos_platform_test.c"):
            _bin = _src.replace(".c", "")
            done = self.run(
                "export PKG_CONFIG_PATH={}; clang {} -o {} $(pkg-config --cflags --libs libgtop-2.0)".format(_gens, _src, _bin),
                env="conanbuild")
            if done != 0:
                raise Exception("compile failed: {}".format(_src))

    def test(self):
        for _bin in ("./test_consumer", "./ohos_platform_test"):
            done = self.run(_bin, env="conanrun")
            if done != 0:
                raise Exception("run failed: {}".format(_bin))