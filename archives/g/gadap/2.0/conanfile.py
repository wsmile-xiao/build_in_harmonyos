#!/usr/bin/env python3
"""Conan recipe for gadap 2.0 — GADAP (Generic Adaptable Data Parser).

GrADS Client Interface for accessing OPeNDAP in-situ data (station data).
Build system: autotools (configure + make). Depends on libdap, libxml2,
curl and libtirpc (libdap's XDR dependency).

License: GPL-2.0-or-later
"""
import io
import os
import ssl
import tarfile
import urllib.request

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class GadapConan(ConanFile):
    name = "gadap"
    version = "2.0"
    description = "GADAP: GrADS Client Interface for OPeNDAP in-situ data"
    license = "GPL-2.0-or-later"
    homepage = "http://cola.gmu.edu/grads/"
    url = "https://salsa.debian.org/science-team/gadap"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # libdap/curl/libtirpc 未发布到制品仓（无 conan 配方），由系统预编译包
        # 提供（cmd-pkgs，安装于 ~/usr/local）；libxml2 已发布 conan 配方，
        # 走 registry 依赖（不要再从 cmd-pkgs 安装 —— 双源并存会导致 SDK lld
        # 运行时加载 ~/usr/local/lib 的 libxml2.so.16 与自身 NEEDED 符号集
        # 不匹配，configure 报 Error 77: C++ compiler cannot create executables）。
        self.requires("libxml2/2.15.3", transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self)

    def validate(self):
        # R32: platform check uses in ("Linux", "OHOS"), never == "Linux"
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"gadap requires Linux or OHOS, got {self.settings.os}")

    def source(self):
        # strip_root 对带 "./gadap-2.0/" 前缀的 tar 条目不生效（OHOS conan 2.29），
        # 手动剥离顶层目录，使源码直接落在 source_folder，补丁路径才能命中。
        get(self, **self.conan_data["sources"])
        import shutil
        src = self.source_folder
        sub = os.path.join(src, "gadap-2.0")
        if os.path.isdir(sub):
            for f in os.listdir(sub):
                shutil.move(os.path.join(sub, f), os.path.join(src, f))
            os.rmdir(sub)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: System-name libraries default to static
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        else:
            tc.configure_args.append("--enable-shared")
            tc.configure_args.append("--disable-static")
        # R33: 编译器必须从 Conan conf 获取，显式传给 configure（CI 环境
        # AutotoolsToolchain 不会自动注入 CC/CXX/CXXFLAGS 到 configure 命令）
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict)
        if compilers.get("c"):
            tc.configure_args.append(f"CC={compilers['c']}")
        if compilers.get("cpp"):
            tc.configure_args.append(f"CXX={compilers['cpp']}")
        # CI 上 CXXFLAGS 环境变量未生效，显式注入编译器选项（含系统预编译包 include 路径）
        pkg_prefix = os.path.expanduser("~/usr/local")
        tirpc_inc = f"-I{pkg_prefix}/include/tirpc"
        # libxml2 头文件走 conan 依赖（registry 包），不从 cmd-pkgs 安装，
        # 避免 ~/usr/local 出现第二份 libxml2.so.16 干扰 SDK lld 运行时加载
        xml2_dep = self.dependencies["libxml2"]
        xml2_inc = f"-I{os.path.join(xml2_dep.package_folder, 'include', 'libxml2')}"
        # libxml2 库也走 conan 依赖：dap-config 硬编码了 -L~/usr/local/lib -lxml2，
        # 但 ~/usr/local 已无 cmd-pkgs libxml2.so.16（否则与 SDK lld 冲突），
        # 必须把 conan 依赖包的 lib 目录并入链接路径，否则链接 test 报
        # "unable to find library -lxml2"（CI #18011 / 本地复现均验证）。
        xml2_libdir = os.path.join(xml2_dep.package_folder, "lib")
        ldflags = [f"-L{xml2_libdir}", f"-L{pkg_prefix}/lib"]
        tc.extra_ldflags = ldflags
        tc.configure_args.append(f"LDFLAGS={' '.join(ldflags)}")
        cxxflags = []
        if str(self.settings.compiler.libcxx):
            cxxflags.append(f"-stdlib={self.settings.compiler.libcxx}")
        if str(self.settings.compiler.cppstd):
            cxxflags.append(f"-std=c++{self.settings.compiler.cppstd}")
        cxxflags.append(f"-O{'3' if self.settings.build_type == 'Release' else '0'}")
        # configure 命令行 CXXFLAGS 会覆盖环境变量 CXXFLAGS，必须把 include 路径一并传入，
        # 否则编译 libdap 头文件时报 rpc/types.h not found
        cxxflags.append(tirpc_inc)
        cxxflags.append(xml2_inc)
        if cxxflags:
            tc.configure_args.append(f"CXXFLAGS={' '.join(cxxflags)}")
        # libdap/curl/libtirpc 由系统预编译包提供（cmd-pkgs → ~/usr/local）
        tc.extra_cppflags = [tirpc_inc, xml2_inc]
        tc.extra_cflags = [tirpc_inc, xml2_inc]
        tc.extra_cxxflags = [tirpc_inc, xml2_inc]
        tc.generate()
        # 实际设置 PKG_CONFIG_PATH，让 configure 的 dap-config/pkg-config 找到系统预编译包
        self.buildenv_info.prepend_path("PKG_CONFIG_PATH",
                                         f"{pkg_prefix}/lib/pkgconfig")
        self.output.info(f"PKG_CONFIG_PATH={pkg_prefix}/lib/pkgconfig")
        # E002: /tmp 只读 — configure 编译测试程序时 clang 需可写 TMPDIR，
        # CI 干净环境下 TMPDIR 指向只读路径会导致
        # "clang: error: unable to make temporary file: Read-only file system"
        # 注意：不能使用 ~/tmp —— HMDFS 上该目录 owner 映射为 20001006，
        # CI worker 进程 uid 不在 file_manager 组时不可写（本地模拟无法复现）。
        # 改用 build_folder 下的子目录：conan 刚把源码拷贝进 build_folder，
        # 该目录对构建进程必然可写。
        # 但 CI worker umask 077 时 os.makedirs 创建的目录权限 700，HMDFS
        # owner 映射 20001006 后当前 uid 不可写 → 先 umask(0) 再创建（SGID
        # 强制 group 可写），创建后恢复 umask。
        tmpdir = os.path.join(self.build_folder, "tmp")
        _old_umask = os.umask(0)
        try:
            os.makedirs(tmpdir, exist_ok=True)
        finally:
            os.umask(_old_umask)
        self.buildenv_info.define("TMPDIR", tmpdir)
        self.output.info(f"TMPDIR={tmpdir}")

    def _ensure_system_deps(self):
        """Install missing system libraries from cmd-pkgs.

        libdap/curl/libtirpc 无 conan 配方，由 cmd-pkgs 预编译包提供
        （https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs）。CI worker 是
        干净环境，需在此自动安装，否则 configure 报 Cannot find libdap。

        下载完整性由 HTTPS 证书验证（ssl.create_default_context()）保障，
        禁用 TLS 验证会导致供应链投毒风险（P1 已修复）。
        """
        import hashlib
        prefix = os.path.expanduser("~/usr/local")
        bin_dir = os.path.join(prefix, "bin")
        inc_dir = os.path.join(prefix, "include")

        # (probe_file, cmd_pkgs_name, cmd_pkgs_version)
        # 注意：libxml2 不在其中 —— 它有 conan 配方（requirements 已依赖
        # libxml2/2.15.3），若再从 cmd-pkgs 安装一份到 ~/usr/local/lib，
        # 会与 SDK lld 的 NEEDED libxml2.so.16 冲突（configure Error 77）。
        deps = [
            (os.path.join(bin_dir, "dap-config"), "libdap", "3.21.1"),
            (os.path.join(inc_dir, "tirpc", "rpc", "types.h"), "libtirpc", "1.3.3"),
            (os.path.join(inc_dir, "curl", "curl.h"), "curl", "8.19.0"),
        ]

        def _present(probe):
            return os.path.exists(probe) or os.path.islink(probe)

        missing = [(pkg, ver) for probe, pkg, ver in deps if not _present(probe)]
        if not missing:
            self.output.info("All system dependencies present")
            return

        ctx = ssl.create_default_context()

        for pkg, ver in missing:
            self.output.info(f"Installing {pkg} {ver} from cmd-pkgs...")
            url = (
                "https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/"
                f"download/pkgs/{pkg}-{ver}-ohos-aarch64.tar.gz"
            )
            try:
                req = urllib.request.urlopen(url, context=ctx, timeout=120)
                try:
                    data = req.read()
                    tf = tarfile.open(fileobj=io.BytesIO(data), mode="r:gz")
                    tf.extractall(prefix)
                    tf.close()
                finally:
                    req.close()
                self.output.info(f"  Installed {pkg} {ver} from cmd-pkgs")
            except Exception as e:
                # P2: 依赖安装失败必须终止构建，静默继续会掩盖根因
                raise ConanInvalidConfiguration(
                    f"Failed to install system dependency {pkg} {ver} from cmd-pkgs: {e}")

    def _ensure_openssl_links(self):
        """Create libssl.so/libcrypto.so symlinks in ~/usr/local/lib.

        cmd-pkgs 的 libdap 包 dap-config 硬编码了
        /storage/Users/currentUser/usr/local/lib/libssl.so 与 libcrypto.so
        的绝对路径（libdap 的 openssl 依赖），CI 干净环境没有这两个文件，
        链接 test 时 clang 报 "no such file or directory: .../libssl.so"
        （本机靠 08-02 手动创建的 symlink 才通过）。系统提供
        /usr/lib/libssl.so.3 与 /usr/lib/libcrypto.so.3，这里自动补建。
        """
        prefix = os.path.expanduser("~/usr/local")
        lib_dir = os.path.join(prefix, "lib")
        pairs = [
            ("libssl.so", "/usr/lib/libssl.so.3"),
            ("libcrypto.so", "/usr/lib/libcrypto.so.3"),
        ]
        for name, syspath in pairs:
            link = os.path.join(lib_dir, name)
            if os.path.exists(link) or os.path.islink(link):
                continue
            if not os.path.exists(syspath):
                self.output.info(f"  WARN: system lib missing {syspath} for {name}")
                continue
            try:
                os.symlink(syspath, link)
                self.output.info(f"  Linked {link} -> {syspath}")
            except OSError as e:
                self.output.info(f"  WARN: failed to link {link}: {e}")

    def build(self):
        # E002: /tmp 只读 — configure 编译测试程序时 clang 需可写 TMPDIR，
        # CI 干净环境下 TMPDIR 指向只读路径会报
        # "clang: error: unable to make temporary file: Read-only file system"
        # 用 build_folder 子目录而非 ~/tmp（HMDFS owner 映射 20001006，
        # CI worker 进程 uid 不在 file_manager 组时 ~/tmp 不可写）。
        # CI worker umask 077 时 os.makedirs 创建目录权限 700，HMDFS
        # owner 映射后不可写 → umask(0) 创建（SGID 强制 group 可写）。
        tmpdir = os.path.join(self.build_folder, "tmp")
        _old_umask = os.umask(0)
        try:
            os.makedirs(tmpdir, exist_ok=True)
        finally:
            os.umask(_old_umask)
        os.environ["TMPDIR"] = tmpdir
        # 诊断：确认 TMPDIR 与 clang 可写性（CI 上 configure 编译器测试失败定位用）
        import subprocess
        self.output.info(f"DIAG build_folder={self.build_folder}")
        self.output.info(f"DIAG TMPDIR={tmpdir}")
        try:
            ls = subprocess.run(["ls", "-ld", tmpdir], capture_output=True, text=True, timeout=10)
            self.output.info(f"DIAG ls -ld tmpdir: {ls.stdout.strip()} {ls.stderr.strip()}")
        except Exception as e:
            self.output.info(f"DIAG ls failed: {e}")
        with open(os.path.join(tmpdir, "diag.cpp"), "w") as f:
            f.write("int main(){return 0;}\n")
        try:
            cxx = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict).get("cpp", "clang++")
            r = subprocess.run(
                [cxx, "-stdlib=libc++", "-std=c++17", "-o", os.path.join(tmpdir, "diag.out"),
                 os.path.join(tmpdir, "diag.cpp")],
                capture_output=True, text=True, timeout=30,
                env=dict(os.environ, TMPDIR=tmpdir))
            self.output.info(f"DIAG clang rc={r.returncode} out={r.stdout.strip()[:200]} err={r.stderr.strip()[:300]}")
        except Exception as e:
            self.output.info(f"DIAG clang test failed: {e}")
        # CI worker 干净环境无 libdap/curl/libtirpc 预编译包，先自动安装
        self._ensure_system_deps()
        # dap-config 硬编码 libssl.so/libcrypto.so 绝对路径，CI 缺文件需补 symlink
        self._ensure_openssl_links()
        apply_conandata_patches(self)
        autotools = Autotools(self)
        try:
            autotools.configure()
        except Exception:
            # 定位 configure 失败（Error 77）根因：输出 config.log 中
            # conftest 编译相关的错误行（错误在 config.log 中部，tail 看不到）
            for cfg in ("config.log",):
                p = os.path.join(self.build_folder, cfg)
                if os.path.isfile(p):
                    with open(p, "r", errors="replace") as f:
                        lines = f.readlines()
                    # 输出 conftest/error/checking C++ 相关的上下文行
                    keys = ("error", "conftest", "cannot", "Permission",
                            "Read-only", "No such", "checking for C++ compiler")
                    for i, ln in enumerate(lines):
                        if any(k.lower() in ln.lower() for k in keys):
                            start = max(0, i - 2)
                            end = min(len(lines), i + 3)
                            snippet = "".join(lines[start:end])
                            self.output.info(f"===== config.log near line {i+1} =====\n{snippet}")
                    self.output.info(f"===== config.log tail =====\n{''.join(lines[-2000:])}")
            raise
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["gadap"]
        self.cpp_info.requires = ["libxml2::libxml2"]
        # libdap/curl/libtirpc 无 conan 配方，由系统预编译包提供（cmd-pkgs → ~/usr/local）
        prefix = os.path.expanduser("~/usr/local")
        self.cpp_info.system_libs = ["dap", "dapserver", "dapclient", "curl", "tirpc"]
        link_flags = [f"-L{prefix}/lib64", f"-L{prefix}/lib"]
        self.cpp_info.exelinkflags = link_flags
        self.cpp_info.sharedlinkflags = link_flags
        # 运行期：系统预编译包位于 ~/usr/local/lib，需加入 LD_LIBRARY_PATH
        for libdir in ("lib64", "lib"):
            p = os.path.join(prefix, libdir)
            if os.path.isdir(p):
                self.runenv_info.prepend_path("LD_LIBRARY_PATH", p)
