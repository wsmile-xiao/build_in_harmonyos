"""Conan recipe for uperf 1.0.7 (network performance tool, Sun Microsystems).

Upstream tarball ships a generated `configure`, so no autoreconf is needed
(CI workers refuse to execute shebang scripts; the tarball configure is run
via `sh` explicitly).  SSL/SCTP/netstat are disabled: OHOS musl lacks
`netinet/sctp.h` and libssl is not declared for this archive, and the
netstat_kstat fallback references Solaris-only symbols.

Upstream 1.0.7's `tests/test.sh` does NOT start the uperf slave (the master
branch fixed this later), so build() orchestrates the slave lifecycle around
`make -C tests check` — see notes.md.
"""
import glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, chmod, copy, export_conandata_patches, get
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class UperfConan(ConanFile):
    name = "uperf"
    version = "1.0.7"
    description = "uperf: a network performance tool for unicast TCP/UDP transactions and throughput"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/uperf/uperf"
    url = ""
    topics = ("networking", "benchmark", "performance")
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 自含：默认配置仅依赖系统 libc；SSL/SCTP/RDS 均显式关闭或未编译
        pass

    def validate(self):
        # R32: OHOS must be matched alongside Linux, never `== "Linux"`.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"uperf supports Linux/OHOS only, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # ⚠ 本机 conan 2.29 的 tc.generate(env=X) 是**整体替换**工具链环境而非
        # 合并（实测：只传 CONFIG_SHELL/SHELL 会把 CC/CXX/CFLAGS 全部 wipe，
        # configure 报 "no acceptable C compiler found"）。正确姿势：先取
        # tc.environment()，在其上定义，再交回 generate()。
        tc = AutotoolsToolchain(self)
        env = tc.environment()
        # E386 / 经验汇总 §12.38①：压掉 hnp bash 的 CONFIG_SHELL/SHELL
        # （HMDFS 上 getcwd() 必挂）。
        env.define("CONFIG_SHELL", "/bin/sh")
        env.define("SHELL", "/bin/sh")
        tc.generate(env=env)

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder
        # E490：HMDFS 上检出内容可能丢执行位，恢复已知 autotools 脚本模式；
        # configure 本身用 sh 显式执行，config.guess/config.sub 保留执行位。
        for helper in ("configure", "config.guess", "config.sub",
                       "install-sh", "missing", "compile", "depcomp"):
            path = os.path.join(src, helper)
            if os.path.isfile(path):
                chmod(self, path, 0o755)
        # E386 §12.38①：命令内联再压一道 CONFIG_SHELL/SHELL（环境变量就近覆盖
        # buildenv）。E011 补丁已去掉 configure 的 umask 077 包裹。
        # native 构建：设备 clang 本身即 OHOS 目标，不传 --host/--build。
        self.run(
            'CONFIG_SHELL=/bin/sh SHELL=/bin/sh sh ./configure '
            "--prefix=/ "
            "'--bindir=${prefix}/bin' "
            "'--sbindir=${prefix}/bin' "
            "'--libdir=${prefix}/lib' "
            "'--includedir=${prefix}/include' "
            "'--oldincludedir=${prefix}/include' "
            "--disable-ssl --disable-sctp --disable-netstat",
            env="conanbuild",
            cwd=src,
        )
        self.run("make -j2", env="conanbuild", cwd=src)
        # 上游测试：1.0.7 的 tests/test.sh 不会自启 slave（master 分支已修），
        # 全部网络用例都会因 "Cannot connect to localhost:20000" 失败，
        # 因此 build() 负责拉起/回收 slave（127.0.0.1:20000）。
        self.run(
            "./src/uperf -s > uperf-slave.log 2>&1 & echo $! > uperf-slave.pid",
            env="conanbuild",
            cwd=src,
        )
        try:
            self.run("sleep 2 && make -C tests check", env="conanbuild", cwd=src)
        finally:
            self.run(
                "kill -9 $(cat uperf-slave.pid) 2>/dev/null || true",
                cwd=src,
            )

    def package(self):
        src = self.source_folder
        copy(self, "uperf", os.path.join(src, "src"),
             os.path.join(self.package_folder, "bin"))
        for f in ("uperf",):
            path = os.path.join(self.package_folder, "bin", f)
            if os.path.isfile(path):
                chmod(self, path, 0o755)
        copy(self, "COPYING", src, os.path.join(self.package_folder, "licenses"))
        self._sign_binaries()

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        # E077: HarmonyOS XPM requires signed executables; the hnp tools
        # resolve libc++ via their own location, so LD_LIBRARY_PATH must not
        # leak into the signer invocation.
        if self.settings.os != "OHOS":
            return
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for f in sorted(glob.glob(os.path.join(self.package_folder, "bin", "*"))):
            if not os.path.isfile(f) or os.path.islink(f) or not self._is_elf(f):
                continue
            self.run(
                'env -u LD_LIBRARY_PATH {oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=f)
            )
            self.run(
                'env -u LD_LIBRARY_PATH {sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=f)
            )

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
