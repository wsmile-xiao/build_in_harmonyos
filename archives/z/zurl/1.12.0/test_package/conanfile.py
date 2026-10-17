import os

from conan import ConanFile


class ZurlTestPackageConan(ConanFile):
    """test_package — zurl 1.12.0（Qt5 ZeroMQ HTTP/WebSocket 客户端守护进程）"""

    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # 运行二进制消费者测试：--version 断言 + ELF/ldd 冒烟 +
        # TMPDIR ipc 配置启停 daemon（4 检查点，脚本按实绩输出 marker）。
        # readonly_tmp：HarmonyOS 真机 /tmp 只读；脚本已优先取 TMPDIR，
        # 这里再保证 TMPDIR/TMP/TEMP 指向 build 内可写目录（只换临时
        # 目录，不改测试口径）。
        tmpdir = os.path.join(self.build_folder, "hmbs_tmp")
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except Exception:
            pass
        for var in ("TMPDIR", "TMP", "TEMP"):
            try:
                if not os.environ.get(var):
                    os.environ[var] = tmpdir
            except Exception:
                pass
        pkg = self.dependencies["zurl"]
        bin_path = os.path.join(pkg.package_folder, "bin", "zurl")
        self.run(
            f'sh "{os.path.join(self.recipe_folder, "test_zurl.sh")}" "{bin_path}"',
            env="conanrun",
        )
