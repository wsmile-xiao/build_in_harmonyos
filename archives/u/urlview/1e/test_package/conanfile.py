import os

from conan import ConanFile


class UrlviewTestConan(ConanFile):
    """urlview/1e 消费者测试：驱动 test_package/test.sh 真跑包里的 urlview 二进制。

    行为断言全部实装在同目录的 `test.sh`（10 次真运行 + 5 条安装面，共 25 条），
    本文件只负责把它接进 conan 的生命周期：
      1. 以 explicit 方式依赖被测 reference（`self.tested_reference_str`）；
      2. 定位装好的 `bin/urlview` 与包根目录，作为参数交给 test.sh；
      3. 在 `conanrun` env 下执行 —— urlview 链接 ncurses/6.5，只有这条 env
         能把 PATH / LD_LIBRARY_PATH 摆到构建机能跑真运行的形态。
    `self.run()` 对非 0 退出码直接抛 ConanException ⇒ 任一断言不符即整包失败，
    不靠人工读日志。

    走的是 urlview.c:425 `if(getenv("URLVIEW_DEBUG") || !isatty(1))` 这条无头分支
    （只抽取、打 stdout、return 0），因此不碰 /dev/tty、不需要 curses 真开屏幕；
    每条期望值都是先在同一台机器上实测取回的，不是照正则猜的（用例来源见 notes.md §7.3）。
    """

    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["urlview"].package_folder.replace("\\", "/")
        urlview = "%s/bin/urlview" % pkg
        script = os.path.join(self.source_folder, "test.sh").replace("\\", "/")
        # 被测二进制与包根都用绝对路径传进去：cwd 是 test_package/，
        # 但 test.sh 校验的是**安装面**，不能沾源码树。
        self.run(
            'sh "%s" "%s" "%s"' % (script, urlview, pkg),
            cwd=self.source_folder,
            env="conanrun",
        )
