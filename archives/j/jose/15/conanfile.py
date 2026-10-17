#!/usr/bin/env python3
"""Conan recipe for jose 15 — JOSE (JWS/JWE/JWK/JWT) C implementation for HarmonyOS PC (aarch64).

构建系统：meson (meson.build)，native build。
适配要点：
- 依赖 jansson/openssl/zlib 由 conan 提供（PkgConfigDeps 生成 .pc + Meson 交叉文件注入）
- 上游 meson.build 用 dependency('zlib'/'jansson'/'libcrypto') 探测，werror=true 默认开启，
  在 OHOS clang 15 下会因 -Wshadow/-Wstrict-prototypes 等告警失败 → -Dwerror=false
- docs 由 a2x 生成，设备无 a2x → -Ddocs=disabled
- 产物含 CLI 工具 bin/jose 与共享库 libjose.so.0 → R38 commands.json（软件级）
"""
import os
import shutil
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, chmod, copy, export_conandata_patches, get, save
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


def _ohos_sign_elf(path):
    """OHOS ELF 签名：musl 加载器仅接受带有效 .codesign 的共享库/可执行文件。

    未签名产物被 musl 拒载（dlopen 报 Permission denied / symbol not found，
    test_package 运行时失败）。参照先例 abbtr/_sign_elf_if_ohos 与
    scripts/ohc/sign_elf.py（binary-sign-tool -selfSign 1）。
    """
    try:
        if Path(path).read_bytes()[:4] != b"\x7fELF":
            return
    except OSError:
        return

    signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
    objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
    if not os.path.isfile(signer) or not os.path.isfile(objcopy):
        return

    workdir = os.path.join(os.path.dirname(path), ".ohos-sign-tmp")
    Path(workdir).mkdir(parents=True, exist_ok=True)
    tmp_in = os.path.join(workdir, os.path.basename(path))
    tmp_out = tmp_in + ".signed"
    shutil.copy2(path, tmp_in)
    subprocess.run([objcopy, "--remove-section", ".codesign", tmp_in],
                   capture_output=True, timeout=15)
    r = subprocess.run([signer, "sign", "-inFile", tmp_in, "-outFile", tmp_out,
                        "-selfSign", "1"],
                       capture_output=True, text=True, timeout=30)
    if r.returncode == 0 and os.path.isfile(tmp_out):
        shutil.move(tmp_out, path)
        os.chmod(path, 0o755)
    shutil.rmtree(workdir, ignore_errors=True)


class JoseConan(ConanFile):
    name = "jose"
    version = "15"
    description = "JOSE (JSON Object Signing and Encryption) implementation in C"
    license = "APL2"
    homepage = "https://github.com/latchset/jose"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("jansson/2.15.1.1")
        self.requires("openssl/3.5.8.1")
        # zlib 须用 1.3.1.1（-fPIC 静态库）：libz.a 静态链入 libjose.so 时非 PIC
        # 会产生 musl 无法加载的文本重定位（先例 qpdf 12.3.2.1 同证）
        self.requires("zlib/1.3.1.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # jose 上游 meson.build 用 dependency('zlib'/'jansson'/'libcrypto') 探测 →
        # 必须生成依赖的 .pc 文件供 pkg-config 查找
        PkgConfigDeps(self).generate()
        # 上游用 dependency('libcrypto')，PkgConfigDeps 仅生成 openssl.pc（按包名）→ 补齐
        openssl = self.dependencies["openssl"]
        for pc, desc, lib in (
            ("libcrypto", "OpenSSL cryptography library", "crypto"),
            ("libssl", "OpenSSL secure sockets library", "ssl"),
        ):
            save(self, "{}.pc".format(pc),
                 "prefix={}\nlibdir=${{prefix}}/lib\nincludedir=${{prefix}}/include\n\n"
                 "Name: {}\nDescription: {}\nVersion: {}\n"
                 "Libs: -L\"${{libdir}}\" -l{}\nLibs.private: -ldl -lpthread\n"
                 "Cflags: -I\"${{includedir}}\"\n".format(
                     openssl.package_folder, pc, desc, openssl.ref.version, lib))
        tc = MesonToolchain(self)
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        # werror=true 在 clang 15 下触发既有 -Wshadow 等告警 → 关闭；docs 依赖 a2x 不可用 → 禁用
        tc.project_options["werror"] = "false"
        tc.project_options["docs"] = "disabled"
        # OHOS profile 只把 clang 写入 compiler_executables，meson 探测 llvm-ar/llvm-nm 等
        # 走 PATH 会失败（E540 runner-path-prepend / E373）→ 显式注入全部 LLVM 工具链
        hnp = "/data/service/hnp/bin"
        if os.path.isdir(hnp):
            llvm = os.path.realpath(os.path.join(hnp, "clang"))
            bindir = os.path.dirname(llvm)
            tc.binaries["c"] = os.path.join(bindir, "clang")
            tc.binaries["cpp"] = os.path.join(bindir, "clang++")
            tc.binaries["ar"] = os.path.join(bindir, "llvm-ar")
            tc.binaries["ranlib"] = os.path.join(bindir, "llvm-ar")
            tc.binaries["nm"] = os.path.join(bindir, "llvm-nm")
            tc.binaries["strip"] = os.path.join(bindir, "llvm-strip")
            tc.binaries["ld"] = os.path.join(bindir, "ld.lld")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()
        # HMDFS 上 meson install 产物可能保留 750 等窄权限，导致消费者运行时
        # （CTest/conanrun 加载 libjose.so.0）无读权限 → 显式放宽为 755
        for root, _, files in os.walk(self.package_folder):
            for f in files:
                p = os.path.join(root, f)
                try:
                    if os.path.isfile(p):
                        chmod(self, p, 0o755)
                except OSError:
                    pass
        # OHOS ELF 签名：未签名共享库/可执行文件被 musl 拒载
        # （dlopen Permission denied / symbol not found），test_package 运行时会失败
        if str(self.settings.os) == "OHOS":
            for root, _, files in os.walk(self.package_folder):
                for f in files:
                    _ohos_sign_elf(os.path.join(root, f))

    def package_info(self):
        self.cpp_info.libs = ["jose"]
        self.cpp_info.bindirs = ["bin"]  # R38: 产物含 CLI bin/jose → commands.json（PF8 判定 CLI 包）
        self.cpp_info.set_property("pkg_config_name", "jose")
        # libjose 为共享库产物，消费者运行时（test_package/CTest）需能定位 libjose.so.0
        self.runenv_info.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib"))
