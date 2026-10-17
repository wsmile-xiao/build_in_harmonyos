#!/usr/bin/env python3
"""Conan test_package — yt 4.4.2 消费者验证（CI L1 门禁）。

test() 内真实执行（L0d/L1d 要求 test() 必须调用 self.run，禁止空壳/打印测试）：
  1. `python3 test_yt_consumer.py` —— 7 组真实断言：导入+版本、运行时依赖闭包、
     鸿蒙特有扩展后缀归一化、Cython 编译扩展加载、真实数据集分析（总质量/温度极值）、
     投影（编译路径）、派生字段+单位系统
  2. `bin/yt -h` —— 包内自包含 CLI 启动器可用（退出码 0）

PYTHONPATH 由 conanfile.py 的 package_info 注入；此处再显式 os.environ 注入，
保证被测脚本与 CLI 都解析到本包，而非宿主环境里可能存在的其他 yt 安装
（conan 2.29 的 self.run env 参数仅接受 list，故改用 os.environ 临时注入）。
"""
import os
import shlex
import shutil
import sys
import tempfile

from conan import ConanFile
from conan.errors import ConanException


# E212 的「加载器上下文」措辞：只有动态加载器（dlopen 阶段）才会打印这些词。
_E212_LOADER_CONTEXT = (
    "Error loading shared library",     # musl 加载器（OHOS/CI 实测措辞）
    "Error relocating",                 # musl 重定位失败，仍属 dlopen 阶段
    "cannot open shared object file",   # glibc 加载器措辞
)

# 与上述上下文**同现**才采信的 errno 后缀（区分 ENOENT「缺库」与 EACCES「拒绝」）。
_E212_ERRNO_SUFFIXES = (": Permission denied", ": EACCES")


def _is_e212(text):
    """CI worker 的 hmmac 标签拒用户目录 .so 的 dlopen（知识 E212/E502）。

    与 ELF 代码签名无关：即便 .so 已正确签名，沙箱仍报 Permission denied。

    判定采用**双条件同现**（与 conanfile.py 的 ``_is_e212`` 同策略）：

    * 条件一（加载器上下文）：同一行含加载器措辞，证明失败发生在 dlopen 阶段，
      而非普通文件读写/目录遍历被拒；
    * 条件二（errno 后缀）：同一行含 ``: Permission denied`` 或 ``: EACCES``。

    只留条件二会过宽：真机上任何权限类真实缺陷只要日志含裸 ``Permission
    denied`` 就会被误判为 E212 而走静态回退，把缺陷静默洗成 PASS。只留条件一
    则会把「缺库」（ENOENT，同样打印 ``Error loading shared library``）误判为
    E212。CI 实测原文两者同行：
    ``Error loading shared library <path>.so: Permission denied``。
    """
    for line in str(text).splitlines():
        if not any(ctx in line for ctx in _E212_LOADER_CONTEXT):
            continue
        if any(sfx in line for sfx in _E212_ERRNO_SUFFIXES):
            return True
    return False


class YtTestConan(ConanFile):
    settings = "os", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies[self.tested_reference_str].package_folder
        site_packages = os.path.join(
            pkg, "lib",
            "python{}.{}".format(sys.version_info.major, sys.version_info.minor),
            "site-packages")
        cli = os.path.join(pkg, "bin", "yt")
        consumer = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "test_yt_consumer.py")

        # 测试日志一律写入独立临时目录（tempfile 基于 TMPDIR），绝不落在
        # test_package/ 内。原因：本配方经 `conan test <path>` / `conan create`
        # 执行时，实测 self.build_folder 就等于 test_package 源目录
        # （“Test package build folder: .../test_package”），若按
        # `self.build_folder or tempfile.gettempdir()` 写日志，日志会落进源树；
        # 且 test() 在非 E212 失败分支会 `raise ConanException`（早于末尾的
        # os.remove），把一份「全失败」日志留在源树里被误提交——历史上入库的
        # test_package/yt-consumer.log（7/7 FAILED, ModuleNotFoundError）正是
        # 这样产生的。故改用 mkdtemp 生成唯一临时目录，运行结束 rmtree 清理。
        log_dir = tempfile.mkdtemp(prefix="yt-test-package-")

        old_env = os.environ.get("PYTHONPATH")
        old_expected = os.environ.get("YT_EXPECTED_SITE_PACKAGES")
        old_version = os.environ.get("YT_EXPECTED_VERSION")
        os.environ["PYTHONPATH"] = site_packages + (os.pathsep + old_env if old_env else "")
        os.environ["YT_EXPECTED_SITE_PACKAGES"] = site_packages
        # E212 静态回退分支会核对包 API 版本（yt/_version.py 的 __version__ 与
        # dist-info 元数据）：把被测引用的版本显式传下去，否则该断言就退化成
        # 「读包内自述文件」式的自证，回归了也照过。
        os.environ["YT_EXPECTED_VERSION"] = str(
            self.dependencies[self.tested_reference_str].ref.version)
        try:
            # 1) 真实消费者集成测试（导入/分析/鸿蒙扩展后缀/依赖闭包）。
            #    脚本自身处理 E212（CI hmmac 拒 dlopen 用户目录 .so，知识
            #    E212/E502）：命中时改为静态 ELF/.codesign 校验并以 0 退出，
            #    否则照常断言失败。stdout/stderr 合并重定向到日志文件后读回，
            #    既把消费者脚本的真实输出回显到 conan 日志（满足 L1e/PF3 对
            #    真实 self.run 的要求，仓库先例：archives/b/bpytop/1.0.68
            #    test_package），又能在 self.run 非零退出时检查输出里的 errno
            #    具体标记来识别 E212——而不是只看退出码（conan 的 self.run
            #    默认 ignore_errors=False，非零会直接抛 ConanException，
            #    根本不给检查输出的机会；CI round 3，PR #10561 即此）。
            consumer_log = os.path.join(log_dir, "yt-consumer.log")
            ret = self.run("%s %s >%s 2>&1"
                           % (shlex.quote(sys.executable),
                              shlex.quote(consumer),
                              shlex.quote(consumer_log)),
                           ignore_errors=True)
            try:
                with open(consumer_log, encoding="utf-8", errors="replace") as handle:
                    consumer_output = handle.read()
            except OSError:
                consumer_output = ""
            if consumer_output.strip():
                self.output.info(consumer_output.rstrip())
            if ret != 0:
                if _is_e212(consumer_output):
                    # E212（CI hmmac 拒 dlopen 用户目录 .so，与 ELF 签名无关）：
                    # 消费者脚本可能未能自行静态回退（例如 numpy 把 errno 标记
                    # 藏进 __cause__ 异常链导致其判定漏检），此处按与构建期
                    # 自检 _self_check 完全相同的策略兜底执行静态 ELF/.codesign
                    # 校验；校验通过则 conan create 继续，否则抛错。
                    self.output.info(
                        "yt/4.4.2: consumer test hit E212 - CI hmmac denies "
                        "dlopen of user-path .so (signing cannot fix); "
                        "running static ELF/.codesign verification")
                    self._e212_static_verify(consumer, consumer_output)
                else:
                    raise ConanException(
                        "yt consumer test failed with exit code %s:\n%s"
                        % (ret, consumer_output.strip()))
            try:
                os.remove(consumer_log)
            except OSError:
                pass
            # 2) 自包含 CLI 启动器（bin/yt，相对路径定位包内 site-packages）。
            #    启动器会 import yt，CI 下同样可能被 E212 拒绝；此时跳过该
            #    冒烟（消费脚本已完成静态校验），其它失败仍抛错。
            cli_log = os.path.join(log_dir, "yt-cli-smoke.log")
            # 用 sys.executable 直接跑启动器，绕开 bin/yt 的
            # `#!/usr/bin/env python3` shebang（宿主可能没有 python3 或指向错误
            # 解释器）；路径一律 shlex.quote 防空格/特殊字符注入。
            ret = self.run("%s %s -h >%s 2>&1"
                           % (shlex.quote(sys.executable), shlex.quote(cli),
                              shlex.quote(cli_log)),
                           ignore_errors=True)
            if ret != 0:
                try:
                    with open(cli_log, encoding="utf-8", errors="replace") as handle:
                        cli_output = handle.read()
                except OSError:
                    cli_output = ""
                if _is_e212(cli_output):
                    self.output.info(
                        "yt/4.4.2: CLI smoke skipped - E212 hmmac denies dlopen "
                        "of user-path .so (signing cannot fix); static ELF/.codesign "
                        "verification already applied by the consumer test")
                else:
                    raise ConanException(
                        "yt CLI (-h) failed with exit code %s:\n%s"
                        % (ret, cli_output.strip()))
            try:
                os.remove(cli_log)
            except OSError:
                pass
        finally:
            for key, value in (("PYTHONPATH", old_env),
                               ("YT_EXPECTED_SITE_PACKAGES", old_expected),
                               ("YT_EXPECTED_VERSION", old_version)):
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
            # 运行成功/失败/E212 各路径都清掉 TMPDIR 下的日志临时目录，
            # 既不污染源树、也不残留临时文件。
            shutil.rmtree(log_dir, ignore_errors=True)

    def _e212_static_verify(self, consumer, reason):
        """E212 兜底：复用消费者脚本的静态 ELF/.codesign 校验。

        与构建期自检 ``YtConan._self_check``（命中 E212 后调用
        ``_e212_static_verify``）采用完全相同的「errno 后缀判定 + 静态校验」
        策略。这里以 importlib 从文件加载 test_yt_consumer.py 并调用其
        ``_e212_static_fallback``（其顶层 numpy 导入已被 try/except 包裹，
        加载安全），避免在 runner 里重复整套校验逻辑。返回非零视为包损坏。
        """
        import importlib.util

        spec = importlib.util.spec_from_file_location("_yt_test_consumer", consumer)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if module._e212_static_fallback(reason) != 0:
            raise ConanException(
                "yt E212 static verification failed (see output above)")
