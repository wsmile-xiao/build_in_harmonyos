#!/usr/bin/env python3
"""Conan recipe — minisign 0.12 (CMake, application).

minisign signs files and verifies signatures using the Ed25519 public-key
signature system.  Builds as a command-line tool (application package) and
links against libsodium.

libsodium 1.0.22 未发布到 ohpcd 制品仓（R36），真机又无法访问 github.com
下载 conancenter 配方的 libsodium 源码（E017，RemoteDisconnected）。故按仓库
既有先例（minisign 0.12-r1、gdnsd、rsync/gadap）使用 cmd-pkgs 预编译的系统
libsodium（安装于 ~/usr/local，静态库可用，见 archives/l/libsodium），
不再声明 conan 依赖，避免任何外部下载。真机预检环境不预装系统 libsodium，
故 generate() 中若缺失则按 abook/acedb 先例从 cmd-pkgs 预编译包按需安装
（用 conan.tools.files.download 下载，不依赖 curl / urllib —— OHOS 上
urllib 默认 SSL 上下文无 CA 证书会报 CERTIFICATE_VERIFY_FAILED）。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


def _get_prefix():
    """Get the prefix for installing/finding system dependencies.

    Uses DEFAULT_PREFIX env var (set by CI/HNP environment) or ~/usr/local
    (same as abook/acedb recipes).
    """
    prefix = os.environ.get("DEFAULT_PREFIX")
    if prefix:
        return prefix
    return os.path.join(os.path.expanduser("~"), "usr", "local")


def _install_cmd_pkg(conanfile, name, version, prefix):
    """Download and install a cmd-pkgs prebuilt package via Conan's download.

    真机/CI worker 环境可能无 curl（acedb 先例），且 OHOS 上 Python 标准库
    urllib 的默认 SSL 上下文没有系统 CA 证书，直连 https 会报
    CERTIFICATE_VERIFY_FAILED（chicken 5.4.0 E034/E185 先例：禁用 TLS 校验
    的手段已废弃，禁止复用）。故改用 conan.tools.files.download —— 与
    source() 的 get() 同一 HTTP 栈（requests + certifi），真机日志已证实
    同一台机器上 HTTPS 下载成功（minisign 源码包即由此下载）。包为扁平布局
    （include/ lib/ 顶层），tarfile 解压到 prefix 即可，不依赖 curl / install.sh。
    """
    import tarfile

    from conan.tools.files import download

    url = ("https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/"
           f"{name}-{version}-ohos-aarch64.tar.gz")
    os.makedirs(prefix, exist_ok=True)
    tarball = os.path.join(prefix, f".install-{name}-{version}.tar.gz")
    try:
        download(conanfile, url, tarball)
        with tarfile.open(tarball, "r:gz") as tar:
            # HMDFS 上覆盖已有文件会失败（Operation not permitted），
            # 先删除将被覆盖的目标文件（与 install.sh 的 rm-then-copy 策略一致）
            for m in tar.getmembers():
                target = os.path.join(prefix, m.name)
                if os.path.isfile(target):
                    try:
                        os.remove(target)
                    except OSError:
                        pass
            tar.extractall(prefix)
    finally:
        try:
            os.remove(tarball)
        except OSError:
            pass


class MinisignConan(ConanFile):
    name = "minisign"
    version = "0.12"
    description = "A dead simple tool to sign files and verify signatures"
    license = "ISC"
    homepage = "https://jedisct1.github.io/minisign/"
    url = "https://github.com/jedisct1/minisign"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _find_libsodium(self):
        """Locate the cmd-pkgs prebuilt libsodium (same layout as 0.12-r1/gdnsd).

        Returns (include_dir, library_file). Prefers the static archive:
        HarmonyOS dynamic-library loading is restricted (archives/l/libsodium
        README: 建议优先使用静态库链接方式), and 0.12-r1 had to create
        libsodium.so soname symlinks manually.

        真机预检/CI worker 环境不预装系统 libsodium，缺失时按 abook/acedb
        先例从 cmd-pkgs 预编译包按需安装到 prefix（幂等：装好后下次直接命中）。
        """
        prefix = _get_prefix()
        inc_dir = os.path.join(prefix, "include")
        lib_dir = os.path.join(prefix, "lib")
        if not os.path.exists(os.path.join(inc_dir, "sodium.h")):
            self.output.info(
                "system libsodium not found under %s; installing cmd-pkgs "
                "prebuilt libsodium 1.0.22" % prefix
            )
            _install_cmd_pkg(self, "libsodium", "1.0.22", prefix)
        if not os.path.exists(os.path.join(inc_dir, "sodium.h")):
            raise ConanInvalidConfiguration(
                "system libsodium 1.0.22 not found under %s after cmd-pkgs "
                "install; check archives/l/libsodium" % prefix
            )
        for name in ("libsodium.a", "libsodium.so"):
            lib_file = os.path.join(lib_dir, name)
            if os.path.exists(lib_file):
                return inc_dir, lib_file
        raise ConanInvalidConfiguration(
            "libsodium headers found but no libsodium.a/.so under %s/lib" % lib_dir
        )

    def generate(self):
        tc = CMakeToolchain(self)
        # 上游 CMakeLists.txt 用 pkg-config 或 find_path/find_library 定位
        # libsodium（E001/E075：OHOS 可能无 pkg-config），且系统 libsodium
        # 装在非标准路径 ~/usr/local，CMake 默认搜索路径不含它，故显式传
        # SODIUM_INCLUDE_DIR / SODIUM_LIBRARY（同 0.12-r1 做法）。
        inc_dir, lib_file = self._find_libsodium()
        tc.variables["SODIUM_INCLUDE_DIR"] = inc_dir
        tc.variables["SODIUM_LIBRARY"] = lib_file
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # 上游无测试套件（审计见 test_package/MANIFEST.yml），不调用 cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # E077: OHOS 内核要求可执行 ELF 含有效 .codesign 签名段；上游 CMakeLists 的
        # POST_BUILD strip（及 install 改写）会使链接期自签失效，内核拒绝执行
        # （Operation not permitted，chmod 无法恢复）。按 acme/acsccid/ad2vcf 先例
        # 剥旧签名段后 binary-sign-tool -selfSign 1 重签并恢复 755。
        bin_dir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bin_dir):
            for name in sorted(os.listdir(bin_dir)):
                self._sign_elf(os.path.join(bin_dir, name))

    def _sign_elf(self, path):
        """E077: 重新签名打包的可执行 ELF（剥旧 .codesign → sign → chmod 755）。"""
        if str(self.settings.os) != "OHOS" or not os.path.isfile(path):
            return
        try:
            if open(path, "rb").read(4) != b"\x7fELF":
                return
        except OSError:
            return
        hnp = "/data/service/hnp/bin"
        objcopy = os.path.join(hnp, "llvm-objcopy")
        signer = os.path.join(hnp, "binary-sign-tool")
        if not os.path.isfile(signer):
            self.output.warning("binary-sign-tool 不可用，跳过 ELF 重签: %s" % path)
            return
        if os.path.isfile(objcopy):
            self.run('"%s" --remove-section .codesign "%s" 2>/dev/null || true' % (objcopy, path),
                     quiet=True)
        tmp = path + ".signed"
        self.run('"%s" sign -inFile "%s" -outFile "%s" -selfSign 1' % (signer, path, tmp),
                 quiet=True)
        if os.path.isfile(tmp):
            os.replace(tmp, path)
        os.chmod(path, 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
