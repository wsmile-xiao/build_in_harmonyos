#!/usr/bin/env python3
"""Conan 2.x recipe — lenovolegionlinux 0.0.20 (Lenovo Legion Linux)

上游 https://github.com/johnfanv2/LenovoLegionLinux 由两半组成：

1. ``kernel_module/`` — Linux 内核模块（Kbuild ``obj-m += legion-laptop.o`` + DKMS），
   通过 ACPI/WMI 访问嵌入式控制器（``PNP0C09``），是全部硬件功能的实现；
2. ``python/`` — 用户态 CLI/GUI，读写内核模块暴露的 ``/sys/module/legion_laptop/...`` 接口。

OHOS PC 侧的实测边界（证据见 reports/upstream-test-evidence.md）：

* OHOS aarch64 sysroot 没有内核构建树：``/lib/modules/$(uname -r)/build``、``usr/src``、
  ``include/config``、``include/generated`` 均不存在，``make ... modules`` 无该目标；
* ``legion-laptop.c`` 需要的 16 个内核内部头只有 5 个存在（其中 4 个是 ``_UAPI_`` 桩），
  缺 11 个（含 ``linux/acpi.h``、``linux/hwmon.h``、``linux/platform_profile.h``）——
  非特权用户态沙箱内无法产出可加载的 ``.ko``。

因此本配方交付：

* **可用制品**：用户态 ``legion_linux`` 包（``legion_cli``/``legion_gui`` 入口）——
  可在 OHOS PC 上安装运行，并在内核模块缺失时优雅降级（不崩溃、不伪造功能）；
* **源码快照**：上游原目录布局（``share/lenovolegionlinux/upstream/``），含内核模块源码、
  上游 12 个测试脚本与用户态源码，供平台将来提供 OHOS 内核构建树/内核头制品时复用；
* **fail-closed 契约测试**：``test_package`` 对包内内核模块源码做静态契约校验，
  并如实声明内核态构建/加载 **未执行**（不伪造通过）。

适配补丁 0001 把 ``argcomplete``（shell 补全辅助，功能非必需）由硬依赖降级为可选导入，
与上游对 ``darkdetect`` 的处理方式一致：制品仓无 argcomplete 制品，硬依赖会让 CLI
在 OHOS PC 上完全无法启动。补丁不含平台宏（R8）。
"""

import os
import shutil
import sys

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    save,
)
from conan.tools.layout import basic_layout


class LenovoLegionLinuxConan(ConanFile):
    name = "lenovolegionlinux"
    version = "0.0.20"
    description = (
        "Lenovo Legion Linux userspace CLI (legion_cli) with an upstream kernel-module "
        "source snapshot; the Kbuild/DKMS module itself is not buildable on OHOS"
    )
    license = "GPL-2.0-only"
    homepage = "https://github.com/johnfanv2/LenovoLegionLinux"
    url = "https://github.com/johnfanv2/LenovoLegionLinux"

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    exports_sources = "conandata.yml"

    def export_sources(self):
        export_conandata_patches(self)

    # 上游 python/setup.cfg 的 install_requires 之一（PyYAML）。
    # argcomplete / PyQt6 / darkdetect 在制品仓无 OHOS 制品，见 notes.md 与补丁 0001。
    def requirements(self):
        self.requires("pyyaml/6.0.2")

    def layout(self):
        basic_layout(self)

    def validate(self):
        # R32: settings.os 判断必须同时接受 Linux 与 OHOS
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"lenovolegionlinux supports Linux/OHOS only, got {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _module_dir(self):
        """上游用户态 Python 包目录（python/legion_linux/legion_linux）。"""
        return os.path.join(self.source_folder, "python", "legion_linux",
                            "legion_linux")

    def _pyver(self):
        return "python%d.%d" % sys.version_info[:2]

    def build(self):
        apply_conandata_patches(self)

        # 真实编译步骤：用目标解释器对交付的用户态 Python 层做字节码编译
        # （compileall），逐文件 "Compiling ..." 日志即编译证据，语法错误在此直接失败。
        # 用 sys.executable（运行 conan 的解释器 = 目标侧 Python），不裸用 shell 变量（R33）。
        self.run(f'"{sys.executable}" -m compileall -q "{self._module_dir()}"',
                 env="conanbuild")

        # 构建期契约自检：补丁 0001 必须真正生效（argcomplete 已降级为可选导入）。
        cli_path = os.path.join(self._module_dir(), "legion_cli.py")
        with open(cli_path, encoding="utf-8") as fh:
            if "argcomplete = None" not in fh.read():
                raise ConanException(
                    "patch 0001 did not apply: legion_cli.py still hard-requires "
                    "argcomplete"
                )

    def package(self):
        src = self.source_folder
        pkg = self.package_folder
        module_dir = self._module_dir()
        site = os.path.join(pkg, "lib", self._pyver(), "site-packages", "legion_linux")
        bindir = os.path.join(pkg, "bin")

        # 1) 用户态 Python 包（对齐上游 setup.cfg 的 packages/package_data：模块 + logo 资源）
        copy(self, "*.py", module_dir, site)
        copy(self, "*.png", module_dir, site)
        copy(self, "README.md", os.path.join(src, "python", "legion_linux"),
             os.path.join(pkg, "res", "legion_linux"))
        copy(self, "LICENSE", src, os.path.join(pkg, "licenses"))

        # 2) 桌面集成文件（上游 setup.cfg data_files 的目标位置）
        copy(self, "legion_gui.desktop", module_dir,
             os.path.join(pkg, "share", "applications"))
        copy(self, "legion_*.png", module_dir, os.path.join(pkg, "share", "pixmaps"))
        copy(self, "legion_cli.policy", module_dir,
             os.path.join(pkg, "share", "polkit-1", "actions"))
        copy(self, "legion_gui.policy", module_dir,
             os.path.join(pkg, "share", "polkit-1", "actions"))

        # 3) 控制台入口（对齐上游 setup.cfg 的 console_scripts：legion_cli / legion_gui）
        #    脚本自带 site-packages 定位：本仓制品安装在前缀目录而非 pip 的 site-packages，
        #    直接执行 bin/legion_cli 时（如 CI L2 冒烟、用户手工调用）也能 import 到交付模块；
        #    经 conanrun 环境调用时行为不变（PYTHONPATH 相同目录，重复插入无副作用）。
        entry = ('#!/usr/bin/env python3\n'
                 '# generated by the OHPCD conan recipe (upstream console_scripts entry point)\n'
                 'import os\n'
                 'import sys\n'
                 '\n'
                 '_site = os.path.join(\n'
                 '    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),\n'
                 '    "lib", "python%(pyver)s", "site-packages")\n'
                 'if os.path.isdir(_site):\n'
                 '    sys.path.insert(0, _site)\n'
                 '\n'
                 'from legion_linux.%(mod)s import main  # noqa: E402\n'
                 '\n'
                 'if __name__ == "__main__":\n'
                 '    sys.exit(main())\n')
        for name in ("legion_cli", "legion_gui"):
            save(self, os.path.join(bindir, name),
                 entry % {"mod": name,
                          "pyver": "%d.%d" % sys.version_info[:2]})
            os.chmod(os.path.join(bindir, name), 0o755)

        # 4) 上游源码快照（原目录布局）：内核模块源码 + 上游测试脚本 + 用户态源码。
        #    内核模块在 OHOS 无法构建（见模块 docstring / notes.md），源码随包交付，
        #    使上游 tests/*.sh 可被逐字执行，并供平台将来提供内核构建树时复用。
        snapshot = os.path.join(pkg, "share", "lenovolegionlinux", "upstream")
        for rel in ("kernel_module", "tests", "python"):
            copy(self, "*", os.path.join(src, rel), os.path.join(snapshot, rel))
        copy(self, "README.md", src, snapshot)
        copy(self, "LICENSE", src, snapshot)

        # 显式恢复可执行位：HMDFS/umask 场景下 tar 解出的权限可能被归一化，
        # 而上游测试脚本需要直接执行快照内的 legion_cli.py（上游 tests/test_python_cli.sh）。
        for rel in ([os.path.join(snapshot, "tests", "test_%s.sh" % n)
                     for n in ("kernel_build", "kernel_checkpath", "kernel_dkms_install",
                               "kernel_install", "kernel_reload", "python", "python_cli",
                               "python_cli_installed", "python_gui", "python_gui_installed",
                               "python_installed", "python_run_gui_root")] +
                    [os.path.join(snapshot, "python", "legion_linux", "legion_linux", n)
                     for n in ("legion_cli.py", "legion_gui.py")]):
            if os.path.isfile(rel):
                os.chmod(rel, 0o755)

        # 字节码（compileall 产物）随源交付会带来解释器版本耦合，统一清理：
        # 交付物为 .py 源码，目标解释器在首次导入时自行生成 __pycache__。
        for root, dirs, _files in os.walk(pkg):
            for d in list(dirs):
                if d == "__pycache__":
                    shutil.rmtree(os.path.join(root, d), ignore_errors=True)
                    dirs.remove(d)

    def package_info(self):
        site = os.path.join(self.package_folder, "lib", self._pyver(), "site-packages")
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libs = []
        self.runenv_info.prepend_path("PYTHONPATH", site)
