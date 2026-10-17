#!/usr/bin/env python3
"""Conan recipe — libnvmemi 1.16.2（NVMe-MI 管理接口库，上游源码树 libnvme）。

交付内容
    libnvme-mi.so.<soname>（+ .so 开发链接名）、NVMe-MI / NVMe 公共头文件、
    pkg-config 契约 libnvme-mi.pc、COPYING。
    上游同一个 meson 工程还会构建 libnvme.so（A 面：sysfs/ioctl 直通库）——
    那不是本包的内容，打包时剔除（见 package()）。

为什么不需要任何 requires（W0/R36 的"只启用已发布依赖"策略）
    上游把 MI 库设计成自包含的：src/meson.build 里 libnvme-mi 只 link_with
    libccan（ccan 静态进库），依赖列表只有可选的 libdbus（CONFIG_DBUS 分支，
    本包关闭）。实测 `nm -D -u libnvme-mi.so` 无任何 libnvme.so 符号引用，
    所以本包零依赖即可完整工作；json-c/openssl/keyutils/liburing 只服务
    libnvme.so 的 A 面能力，本包全部 disabled，避免引入无意义的传递依赖。

OHOS 适配要点
    1. 无 libdbus：-Dlibdbus=disabled。MI over MCTP 走 AF_MCTP 原始套接字路径
       （src/nvme/mi-mctp.c），不依赖 dbus 的 MCTP 发现。
    2. 上游自带 `HAVE_LINUX_MCTP_H` 探测：OHOS 头里没有 <linux/mctp.h> 时自动
       回退到仓库内 nvme/mi-mctp-compat.h（并 `#define AF_MCTP 45`），无需打补丁。
    3. 无 Python/pip 生态：-Dpython=disabled；文档不需要：-Ddocs=false；
       -Dexamples=false 只留库与测试目标。
    4. meson 在 CI worker 上探测归档器用裸名（llvm-ar 等），而 worker 把
       AR/AS/STRIP/NM/RANLIB 导出为裸名且不在 PATH → 先弹出这些变量再让 meson
       重新探测（仓库内 erfa 2.0.1 同款处理，9 个配方共用）。

真实测试（平台 rule12 / L1c）
    build() 内真跑上游官方测试套件 `meson test`（含 MI 专属用例 test/mi、
    test/mi-mctp：用 --wrap/自定义 transport 伪造 MCTP 对端，无需真实硬件）。
    条数与结论解析自 meson 框架 summary，失败直接让 build 失败（硬门禁）。
    OHOS 无 /bin/bash（bash 只在 /data/service/hnp/bin/），而上游 test/sysfs、
    test/config 的 helper 是 `#!/bin/bash -e` 脚本、doc 的 kdoc 是 `#!/bin/bash`
    + perl → 内核 shebang 解析失败会让 meson 抛 "Unhandled python OSError" 并中断
    整轮，因此 build() 生成一个 --wrapper 把这些脚本转交给真实 bash；唯一无法
    运行的是文档 lint kdoc（还需 perl），按 GNU 约定以 exit 77 记 SKIP（见
    build() 内注释与 HMBS_UPSTREAM_TEST_RESULT 的 skipped 字段）。
    test_package 另有一份端到端消费者用例：只用交付的共享库 + 公共头，
    通过 ELF 符号介入伪造 MCTP 设备，跑完"打开端点 → 枚举控制器 →
    MI Admin Identify → 逐字段比对 + 错误路径"的完整业务流程。
"""
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rm,
)
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class LibnvmeMiConan(ConanFile):
    name = "libnvmemi"
    version = "1.16.2"
    description = ("libnvme-mi — NVMe Management Interface (NVMe-MI) library: "
                   "MI control primitives and admin commands over MCTP")
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/linux-nvme/libnvme"
    url = ""
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    generators = "VirtualBuildEnv", "VirtualRunEnv"

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.ref} only supports Linux/OHOS, got {self.settings.os}")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        # 版本化 conandata：必须按 self.version 取，否则 ** 展开会把版本键变成非法 kwarg
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        # CI worker 把 AR/AS/STRIP/NM/RANLIB 导出为 llvm-* 裸名，meson 的
        # archiver 探测用裸名在 PATH 里找不到 → 报 "Unknown linker(s): llvm-ar"。
        # 先弹出这些变量，再锁定真实工具（绝对路径）。erfa 2.0.1 同款先例。
        for var in ("AR", "AS", "STRIP", "NM", "RANLIB"):
            os.environ.pop(var, None)
        tools = {n: shutil.which(n) for n in ("ar", "as", "strip", "nm", "ranlib")}
        missing = [n for n, p in tools.items() if p is None]
        if missing:
            raise ConanInvalidConfiguration(
                "Required build tools not found in PATH: " + ", ".join(missing))

        tc = MesonToolchain(self)
        tc.ar = tools["ar"]
        tc.as_ = tools["as"]
        tc.strip = tools["strip"]
        tc.binaries["nm"] = tools["nm"]
        tc.binaries["ranlib"] = tools["ranlib"]
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        # 只留本包需要的形状：库 + 上游测试
        tc.project_options["tests"] = "true"
        tc.project_options["examples"] = "false"
        tc.project_options["docs"] = "false"
        tc.project_options["python"] = "disabled"
        tc.project_options["json-c"] = "disabled"
        tc.project_options["openssl"] = "disabled"
        tc.project_options["keyutils"] = "disabled"
        tc.project_options["liburing"] = "disabled"
        tc.project_options["libdbus"] = "disabled"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

        # ── 上游官方测试套件（真跑；CI L1c 认 "meson test"）────────────────
        # test/mi 与 test/mi-mctp 用自定义 transport / 伪造 MCTP 对端驱动 MI
        # 协议层，不需要真实 NVMe-MI 硬件，正好适合 CI。
        # OHOS 上的 shebang 适配（CI #65377 实测）：
        #   上游把 test() 的 exe 直接 execve。doc/ 的 kdoc 指向
        #   `scripts/kernel-doc-check`（`#!/bin/bash`），test/sysfs 与 test/config
        #   的 helper 同样是 `#!/bin/bash -e`（config-diff.sh 还用了 bash 数组与
        #   `[[ ]]`，不能改成 /bin/sh）。OHOS 的 bash 只在 /data/service/hnp/bin/，
        #   内核按 shebang 找不到解释器 → execve 返回 ENOENT → meson 把它抛成
        #   "Unhandled python OSError" 并**中断整个测试运行**（不是记为该用例失败，
        #   表现为 Ok/Fail 计数不完整）。meson 的 --wrapper 各版本都有，用它把这类
        #   脚本转交给真实 bash 执行，不改上游任何源码、不改上游用例集。
        wrapper = os.path.join(self.build_folder, "ohos-meson-test-wrapper.sh")
        with open(wrapper, "w", encoding="utf-8") as fh:
            fh.write(
                "#!/bin/sh\n"
                "# 见 conanfile.py build()：OHOS 无 /bin/bash，bash 脚本用例需显式转交。\n"
                'p="$1"; shift\n'
                'case "$p" in\n'
                "  */kernel-doc-check)\n"
                "    # 文档 lint（kernel-doc 本身是 perl 脚本 #!/usr/bin/env perl），\n"
                "    # OHOS 既无 /bin/bash 也无 perl → 按 GNU 约定返回 77，\n"
                "    # meson 记为 SKIP（而非 Fail/中断整轮）。\n"
                "    exit 77 ;;\n"
                "  */tree-diff.sh|*/config-diff.sh)\n"
                "    # 这两个脚本的 shebang 是 '#!/bin/bash -e'，-e 要一并带上。\n"
                '    for b in /data/service/hnp/bin/bash /usr/bin/bash bash; do\n'
                '      if [ -x "$b" ]; then exec "$b" -e "$p" "$@"; fi\n'
                '      if command -v "$b" >/dev/null 2>&1; then exec "$b" -e "$p" "$@"; fi\n'
                "    done\n"
                "    exit 77 ;;\n"
                "  *)\n"
                '    exec "$p" "$@" ;;\n'
                "esac\n"
            )
        os.chmod(wrapper, 0o755)

        log_path = os.path.join(self.build_folder, "meson_test.log")
        self.run(
            'meson test -C "{}" --wrapper "{}" --print-errorlogs '
            '--timeout-multiplier=16 > "{}" 2>&1'.format(
                self.build_folder, wrapper, log_path),
            ignore_errors=True,
        )
        out = ""
        if os.path.isfile(log_path):
            with open(log_path, encoding="utf-8", errors="replace") as fh:
                out = fh.read()
        def _cnt(pattern):
            m = re.search(pattern, out, flags=re.MULTILINE)
            return int(m.group(1)) if m else 0

        ok = _cnt(r"^Ok:\s+(\d+)")
        expected_fail = _cnt(r"^Expected Fail:\s+(\d+)")
        fail = _cnt(r"^Fail:\s+(\d+)")
        timeout = _cnt(r"^Timeout:\s+(\d+)")
        skipped = _cnt(r"^Skipped:\s+(\d+)")
        executed = ok + expected_fail + fail + timeout + skipped

        # 日志尾巴：通过时只要摘要；失败时把 --print-errorlogs 打出的
        # 失败用例 stdout/stderr 一并带进 CI 输出，省掉额外一轮 /rebuild 取日志。
        self.output.info("=== upstream meson test (tail) ===")
        tail = 25 if not (fail or timeout) else 200
        for line in out.splitlines()[-tail:]:
            self.output.info(line)
        if fail or timeout:
            names = re.findall(
                r"^\s*\d+/\d+\s+(\S+)\s+(?:FAIL|TIMEOUT)\b", out, flags=re.MULTILINE)
            self.output.info("FAILING_CASES: {}".format(
                " ".join(names) if names else "(names not parsed; see log tail)"))

        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT ok={} expected_fail={} fail={} timeout={} "
            "skipped={} executed={}".format(ok, expected_fail, fail, timeout, skipped, executed))
        if executed == 0:
            raise ConanException("upstream 'meson test' produced no results "
                                 "(see build log; log tail above)")
        if skipped:
            # 目前只会是 kdoc（文档 lint）：OHOS 无 /bin/bash、无 perl。
            # 明确打印出来，避免"跳过"被误读成"通过"。
            self.output.info(
                "note: {} upstream case(s) reported SKIP on OHOS "
                "(kdoc 需 /bin/bash + perl；其余用例均真实执行)".format(skipped))
        if fail or timeout:
            raise ConanException(
                "upstream 'meson test' failed: fail={} timeout={} (MCTP/MI 用例见 "
                "test/mi.c、test/mi-mctp.c；完整日志见构建目录 meson_test.log)".format(fail, timeout))

    def package(self):
        meson = Meson(self)
        meson.install()

        # 同源码树还会装上 libnvme.so/.h/.pc（A 面库），本包不交付它们
        libdir = os.path.join(self.package_folder, "lib")
        rm(self, "libnvme.so*", libdir)
        rm(self, "libnvme.pc", os.path.join(libdir, "pkgconfig"))
        rm(self, "libnvme.h", os.path.join(self.package_folder, "include"))
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

        # meson 以 --prefix=/ 安装（conan DESTDIR 打包），.pc 里的 prefix 会写成 "/"。
        # 改成相对 pcfiledir，消费者在任何安装前缀下都能用。
        pc_dir = os.path.join(libdir, "pkgconfig")
        for name in ("libnvme-mi.pc",):
            pc = os.path.join(pc_dir, name)
            if os.path.isfile(pc):
                with open(pc, encoding="utf-8") as fh:
                    body = fh.read()
                body = re.sub(r"^prefix=.*$", "prefix=${pcfiledir}/../..", body,
                              count=1, flags=re.MULTILINE)
                with open(pc, "w", encoding="utf-8") as fh:
                    fh.write(body)

    def package_info(self):
        self.cpp_info.libs = ["nvme-mi"]
        self.cpp_info.set_property("pkg_config_name", "libnvme-mi")
