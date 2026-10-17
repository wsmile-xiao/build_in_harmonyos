#!/usr/bin/env python3
"""Conan recipe for iperf 2.2.1 — network bandwidth testing tool.

iperf is a command-line tool for measuring TCP/UDP network performance.
This recipe builds the iperf binary using autotools (configure + make).
iperf 2.x is mostly C++ (22 .cpp vs 11 .c in src/), so configure runs the
C++ compiler sanity check first (AC_PROG_CXX before AC_PROG_CC).

Platform adaptations (via patches):
  - config.guess: HarmonyOS platform detection
  - config.sub: linux-ohos triplet support
  - headers.h: sockaddr_storage conflict resolution (linux/socket.h vs sys/socket.h)
  - checksums.c: musl libc udphdr member name adaptation (uh_sum vs check)

Build issues on OHOS:
  1. mktemp -d with umask 077 creates directories that HMDFS/SELinux prevents
     writing to (chmod also doesn't work on HMDFS per E046). The config.status
     script is patched after configure to use mkdir instead of mktemp.
  2. CI worker sandbox (buildbot AppSpawn) may expose a restricted TMPDIR:
     clang writes its intermediate object files to $TMPDIR, and when that
     fails configure aborts with "C++ compiler cannot create executables"
     (same CI failure mode as archives/b/bas55/2.0). TMPDIR is therefore
     forced to the conan build folder, which is guaranteed writable.
  3. When configure fails, the relevant config.log excerpt is dumped to the
     conan output: conftest compiler errors only go to config.log, and this
     way they land in the CI log comment for direct root-cause analysis.
"""
import os
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class IperfConan(ConanFile):
    name = "iperf"
    version = "2.2.1"
    description = "Network bandwidth testing tool for TCP/UDP"
    # Upstream COPYING = University of Illinois/NCSA Open Source License
    license = "NCSA"
    homepage = "https://sourceforge.net/projects/iperf2/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: settings.os check must use "in" not "=="
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"iperf supports Linux/OHOS only, got {self.settings.os}"
            )

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # NOTE: iperf2's configure does not support --enable-static /
        # --disable-shared (libtool is not used); passing them only
        # produces "unrecognized options" warnings.
        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        # CI worker 沙箱（buildbot AppSpawn）的 TMPDIR 可能指向受限目录：
        # clang 把中间目标文件写到 $TMPDIR，失败时 configure 报
        # "C++ compiler cannot create executables"（bas55 2.0 相同故障模式）。
        # 构建目录必然可写（补丁刚应用于此），显式接管 TMPDIR。
        os.environ["TMPDIR"] = self.build_folder

        autotools = Autotools(self)

        # Run configure — on OHOS this may fail at config.status step
        # due to mktemp directory permission issues (HMDFS/SELinux).
        # config.status is still created; we patch it and re-run.
        try:
            autotools.configure()
        except Exception:
            self._dump_config_log()
            config_status = os.path.join(self.build_folder, "config.status")
            if not os.path.exists(config_status):
                raise
            self._patch_config_status(config_status)
            subprocess.run(["bash", config_status], cwd=self.build_folder, check=True)
        else:
            # On non-OHOS or if configure succeeded, check if config.status
            # needs patching (it may have succeeded partially)
            if self.settings.os == "OHOS":
                config_status = os.path.join(self.build_folder, "config.status")
                if os.path.exists(config_status):
                    makefile = os.path.join(self.build_folder, "Makefile")
                    if not os.path.exists(makefile):
                        self._patch_config_status(config_status)
                        subprocess.run(["bash", config_status], cwd=self.build_folder, check=True)

        autotools.make(args=["-j1"])

    def _dump_config_log(self):
        """configure 失败时输出 config.log 关键段落（失败的命令与编译器报错）。

        conftest 的编译错误只写入 config.log，configure 的 stdout 不含细节；
        把它带出来落在 conan create 输出里，CI 失败评论即可直接定位根因。
        """
        for path in (
            os.path.join(self.build_folder, "config.log"),
            os.path.join(self.build_folder, "build-release", "config.log"),
        ):
            if not os.path.isfile(path):
                continue
            try:
                with open(path, errors="replace") as f:
                    lines = f.readlines()
            except OSError:
                continue
            # "configure:4444: error: ..." (line numbers vary) marks the
            # failing check; the 40 preceding lines contain the failing
            # compiler command and its stderr output.
            idx = max(
                (i for i, line in enumerate(lines) if ": error:" in line),
                default=max(0, len(lines) - 40),
            )
            start = max(0, idx - 40)
            self.output.warning(f"---- config.log excerpt ({path}) ----")
            for line in lines[start: idx + 2]:
                self.output.warning(line.rstrip())
            return
        self.output.warning(
            f"configure failed but no config.log found under {self.build_folder}"
        )

    def _patch_config_status(self, config_status):
        """Patch config.status to use mkdir instead of mktemp on OHOS."""
        with open(config_status, "r") as f:
            content = f.read()
        content = content.replace(
            'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`',
            'tmp="./conftmp$$" && (umask 000 && mkdir -p "$tmp")'
        )
        content = content.replace(
            'tmp=./conf$$-$RANDOM',
            'tmp="./conftmp$$" #'
        )
        content = content.replace(
            '(umask 077 && mkdir "$tmp")',
            '(umask 000 && mkdir -p "$tmp")'
        )
        with open(config_status, "w") as f:
            f.write(content)

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = ["share"]
