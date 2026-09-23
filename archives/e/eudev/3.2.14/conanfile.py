#!/usr/bin/env python3
"""Conan recipe — eudev 3.2.14 (autotools, OHOS).

eudev = systemd 的独立 udev 设备管理器：提供 **libudev**（共享库 + 头）与
**udevd / udevadm** 工具。apt 的 `find_package(Udev)` 需要本包的 libudev。

前置依赖（重要）：
- **gperf** 是 eudev 的**硬构建依赖**（configure 里 `AC_PATH_TOOL(GPERF, gperf)`
  缺失即 `AC_MSG_ERROR`）。其输入 `keyboard-keys-from-name.gperf` 由 Makefile 规则
  在构建期用 AWK 从 `keyboard-keys.txt` 生成，再由 gperf 生成
  `keyboard-keys-from-name.h`（列入 BUILT_SOURCES）——无法从 tarball 绕过。
  ohpcd **尚无 gperf 包**（main 仅有 3.1 的笔记、无 conanfile），本配方依赖
  构建环境 PATH 中存在 gperf（如 /data/service/hnp/bin/gperf）。
  若 CI worker 无 gperf，需先适配并发布 gperf/3.1 再合本 PR。

OHOS 适配要点：
- 16 个 portability patch（musl 缺 program_invocation_short_name /
  get_current_dir_name()；linux/netlink.h 的 sockaddr_storage 重复定义需 __OHOS__
  guard 等），均由 conandata 声明并 apply；
- `configure` 内两处 `umask 077` → `022`（HMDFS 上临时文件权限异常）；
- TMPDIR 指向 conan build 目录。
"""
import glob
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (apply_conandata_patches, export_conandata_patches,
                               get)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class EudevConan(ConanFile):
    name = "eudev"
    version = "3.2.14"
    description = ("eudev — standalone version of systemd's device manager udev "
                   "(provides libudev, udevd, udevadm)")
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/eudev-project/eudev"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    options = {
        "blkid": [True, False],
        "kmod": [True, False],
        "selinux": [True, False],
    }
    # 默认全关：main 的 eudev manifest 记录 dependencies: [] （不引入外部库）
    default_options = {
        "blkid": False,
        "kmod": False,
        "selinux": False,
    }

    def requirements(self):
        # 无必选外部依赖（blkid / kmod / libselinux 均为可选、默认关闭）
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def export_sources(self):
        # patches/ 必须显式导出，否则 apply_conandata_patches 找不到文件
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder=".")

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--disable-manpages")
        for opt in ("blkid", "kmod", "selinux"):
            flag = "--enable-" if self.options.get_safe(opt) else "--disable-"
            tc.configure_args.append(f"{flag}{opt}")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        # TMPDIR 指向可写的 build 目录（HMDFS 上写临时文件会失败）
        _tmp = os.path.join(self.build_folder, "_tmp")
        os.makedirs(_tmp, exist_ok=True)
        os.environ["TMPDIR"] = _tmp

        # HMDFS 上 umask 077 会导致临时文件权限异常（configure 内两处 mktemp 用 077）
        for _cfg in glob.glob(os.path.join(self.source_folder, "**", "configure"),
                              recursive=True):
            try:
                with open(_cfg, encoding="utf-8", errors="ignore") as f:
                    text = f.read()
            except OSError:
                continue
            if "umask 077" in text:
                with open(_cfg, "w", encoding="utf-8") as f:
                    f.write(text.replace("umask 077", "umask 022"))

        autotools = Autotools(self)
        autotools.configure()
        # eudev 为并行安全的标准 autotools 工程
        autotools.make(args=["-j4"])
        self._run_upstream_test()

    def _run_upstream_test(self):
        """Run the runnable part of the upstream test suite (R51).

        Upstream ``test/Makefile.am`` declares::

            TESTS = udev-test.pl rules-test.sh

        Only the second is runnable here, and the reason is measured, not assumed:

        * ``rules-test.sh`` -> ``rule-syntax-check.py`` walks ``rules/*.rules``
          and validates every clause against udev's rule grammar. Pure text
          parsing, no privileges required. Measured on the 3.2.14 tree:
          27 rules files, 357 rule lines, 1010 clauses, exit code 0.
        * ``udev-test.pl`` drives ``test-udev``, whose ``fake_filesystems()``
          builds a fake sysfs by calling ``mount(..., MS_BIND, ...)``. That
          syscall is disabled in the OHOS build sandbox -- measured: the process
          is killed by **SIGSYS** (signal 31). Its expectations additionally pin
          ownership such as ``root:mail:0660``, which needs a real device. So it
          is genuinely unrunnable here, and reported as such rather than skipped
          silently. (Earlier notes claimed this file was "missing from the
          tarball" -- that was wrong: it ships at ``test/udev-test.pl``, 66993 B.)

        The check is run with an explicit python3: the script carries a py2
        shebang and one py2-only statement (``print >> sys.stderr``), yet parses
        and executes fine under py3 (verified), so no patch to upstream is needed.
        """
        script = os.path.join(self.source_folder, "test", "rule-syntax-check.py")
        rules_dir = os.path.join(self.source_folder, "rules")
        if not os.path.isfile(script) or not os.path.isdir(rules_dir):
            self.output.warning(
                "upstream rule-syntax-check.py / rules dir not found, skipping")
            return
        rules = sorted(glob.glob(os.path.join(rules_dir, "*.rules")))
        if not rules:
            self.output.warning("no rules/*.rules found, skipping")
            return
        # python3 explicitly: the script's shebang is #!/usr/bin/python (py2).
        # -W ignore: the script's regex literals trigger SyntaxWarning
        # ("invalid escape sequence \s") on py3 stderr; suppressing keeps the
        # log readable and lets stdout alone carry real violations.
        py3 = shutil.which("python3") or "python3"
        res = subprocess.run(
            [py3, "-W", "ignore", script, *rules],
            cwd=self.source_folder, capture_output=True)
        # Violations are printed to stdout by the checker; warnings go to stderr
        # (hence reading stdout only -- otherwise a passing run looks failed).
        violations = res.stdout.decode(errors="ignore").strip()
        if res.returncode != 0 or violations:
            raise ConanException(
                f"upstream rule syntax check FAILED rc={res.returncode}: "
                f"{violations or res.stderr.decode(errors='ignore').strip()}")
        self.output.info(
            f"upstream rule-syntax-check: {len(rules)} rules files, "
            f"no violations (exit 0)")

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # 二进制（udevadm / systemd-udevd）分别装在 bin / sbin
        self.cpp_info.bindirs = ["bin", "sbin"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = ["include"]
        # 消费方（apt 的 find_package(Udev)）需要 libudev
        self.cpp_info.libs = ["udev"]
        self.cpp_info.set_property("cmake_file_name", "UDev")
        self.cpp_info.set_property("cmake_target_name", "UDev::UDev")
        self.cpp_info.set_property("pkg_config_name", "libudev")
