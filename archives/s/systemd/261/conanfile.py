#!/usr/bin/env python3
"""Conan recipe — systemd 261 (libsystemd client library).

systemd 是 Linux 系统与服务管理器（init 系统）。OHOS 是独立系统、不运行
systemd 守护进程，本适配按"客户端库"口径只构建 libsystemd（sd-bus/sd-event/
sd-daemon 等客户端 API），关闭 daemon（core/journald/udevd/networkd/logind
等）与缺依赖组件。

构建系统：meson。硬依赖少（glibc/musl + libcap 等），多数依赖是 feature 型
可关闭。ohpcd 可用：glib/libcap/libseccomp/libselinux/liblzma/libzstd/
libgcrypt/openssl/zlib/libxcrypt/libucontext/libidn2；缺的 libmount/libblkid/
libacl/libpcre2/libkmod/libcryptsetup/libaudit/libgnutls 全部 feature 关闭。

OHOS 适配（沿用 dconf/polkit 的 meson 依赖注入模式）：
- 依赖 .pc 复制 + prefix 改写 + PKG_CONFIG_PATH 注入全部依赖包
- 关闭 daemon 与缺依赖组件（-Dxxx=disabled）
- 上游测试：systemd 测试依赖运行中的 systemd 环境（pid1/udev/cgroup），
  OHOS 无——按 rule 1.2 如实声明平台限制
"""
import os
import re as _re
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.layout import basic_layout


def _fix_pc_prefix(pc_path, prefix):
    if not os.path.isfile(pc_path):
        return
    data = open(pc_path, encoding="utf-8", errors="replace").read()
    data = _re.sub(r"(?m)^prefix=.*$", f"prefix={prefix}", data, count=1)
    # 部分 .pc（如 libucontext.pc）把 libdir/includedir 硬编码为 /usr/lib、
    # /usr/include 而非 ${prefix}——改写为指向 conan 包实际路径，否则
    # 链接报 "unable to find library -lucontext"。
    data = _re.sub(r"(?m)^(libdir|static_libdir|includedir)=/usr/lib$",
                   rf"\1={os.path.join(prefix, 'lib')}", data)
    data = _re.sub(r"(?m)^(includedir)=/usr/include$",
                   rf"\1={os.path.join(prefix, 'include')}", data)
    open(pc_path, "w", encoding="utf-8").write(data)


class SystemdConan(ConanFile):
    name = "systemd"
    version = "261"
    package_type = "library"
    license = "LGPL-2.1-or-later"
    homepage = "https://systemd.io"
    description = "systemd — libsystemd client library (sd-bus/sd-event/sd-daemon)"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": True}
    exports_sources = "patches/*"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"systemd does not support os={self.settings.os}")

    def requirements(self):
        self.requires("libcap/2.69")
        self.requires("liblzma/5.8.1")
        self.requires("libzstd/1.5.7")
        self.requires("zlib/1.3.1")
        # ohpcd 包名是 libxcrypt（无 libcrypt）
        self.requires("libxcrypt/4.5.2")
        self.requires("libucontext/1.5.2")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        # OHOS sysroot 的内核风格头（mtd-abi.h 等）用 __user/__force/__iomem
        # 注解，musl 不定义这些宏——编译 mtd_probe 等报 "expected ';'"。置空
        # 定义（与内核编译时的空宏一致）。
        for _k in ("__user", "__force", "__iomem", "__kernel"):
            tc.c_args.append(f"-D{_k}=")
        # OHOS 定制 musl 的 sysroot malloc.h 已自带 mallinfo2（0005 补丁用
        # `#ifndef HAVE_MALLINFO2` 能力探测宏，R8 合规不含平台宏）——这里注入
        # -DHAVE_MALLINFO2=1 让 OHOS 下跳过 systemd 的 mallinfo2 定义，
        # 避免 redefinition；标准 musl/glibc 下不注入则补上。
        if self.settings.os == "OHOS":
            tc.c_args.append("-DHAVE_MALLINFO2=1")
        tc.project_options.update({
            # OHOS 用 musl libc——systemd 靠 -Dlibc=musl 启用 src/libc/musl
            # 兼容层（printf.c 提供 printf.h 的 parse_printf_format、
            # string.c 提供 explicit_bzero 等 glibc 特有 API 的 musl 版）
            "libc": "musl",
            # 关闭 daemon / 服务组件（OHOS 不运行 systemd）
            "mode": "release",
            "split-bin": "false",
            # 关闭缺依赖的 feature（libmount/blkid/acl/pcre2 等）
            "libmount": "disabled",
            "blkid": "disabled",
            "acl": "disabled",
            "pcre2": "disabled",
            "kmod": "disabled",
            "libcryptsetup": "disabled",
            "audit": "disabled",
            "gnutls": "disabled",
            "bpf-framework": "disabled",
            "selinux": "disabled",
            "apparmor": "disabled",
            "polkit": "disabled",
            # 关闭可选压缩后端（libsystemd 客户端库不需 journal 压缩；xz/lz4/zstd
            # 头文件路径未进编译导致 lzma.h not found）
            "xz": "disabled",
            "lz4": "disabled",
            "zstd": "disabled",
            # 关闭文档/测试构建（沙箱无 makeinfo 等）；rule 4 逐类归因实测
            # 数据已固化在 manifest/notes/PR 描述，build() 不跑 meson test
            # （避免触发全量 1281 测试目标构建超时）。
            "man": "disabled",
            "html": "disabled",
            "tests": "false",
        })
        tc.generate()
        # 真机 hnp 工具链的 ar/llvm-ar 不在 PATH（E012 变体）——meson 报
        # "Unknown linker(s): llvm-ar/ar"。把探测到的 ar/ranlib 全路径注入
        # conan_meson_native.ini（dconf/pycairo/polkit 同款）。
        self._inject_meson_archiver()
        # 依赖 .pc：复制各依赖包 pkgconfig 目录的 .pc 到 generators_folder
        # 并改写 prefix，保证 meson 的 dependency() 可解析（含 Requires 链）。
        for dep in self.dependencies.values():
            try:
                dep_pkg = dep.package_folder
            except Exception:
                continue
            if not dep_pkg:
                continue
            src_pc = os.path.join(dep_pkg, "lib", "pkgconfig")
            if not os.path.isdir(src_pc):
                continue
            for name in os.listdir(src_pc):
                if name.endswith(".pc"):
                    d = os.path.join(self.generators_folder, name)
                    if not os.path.exists(d):
                        shutil.copy2(os.path.join(src_pc, name), d)
                    _fix_pc_prefix(d, dep_pkg)

    # --- 归档器探测（真机 hnp 工具链 ar 不在 PATH，须给 meson 绝对路径） ---
    def _probe_archiver(self):
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = ce.get("c") or os.environ.get("CC") or ""
        bindir = os.path.dirname(cc) if (cc and ("/" in cc or os.path.sep in cc)) else ""
        dirs = []
        for d in (bindir, "/data/service/hnp/bin", "/data/service/hnp/llvm/bin",
                  os.path.expanduser("~/usr/local/bin")):
            if d and d not in dirs:
                dirs.append(d)
        cands = []
        for d in dirs:
            for n in ("llvm-ar", "llvm-ar-15", "ar"):
                p = os.path.join(d, n)
                if os.path.isfile(p):
                    cands.append(p)
        for n in ("llvm-ar", "llvm-ar-15", "ar", "gar"):
            p = shutil.which(n)
            if p:
                cands.append(p)
        seen, ar = set(), None
        for p in cands:
            if p not in seen:
                seen.add(p)
                ar = p
                break
        if not ar:
            return None, None
        base = os.path.dirname(ar)
        is_llvm = os.path.basename(ar).startswith("llvm")
        rl_names = ("llvm-ranlib", "ranlib") if is_llvm else ("ranlib", "llvm-ranlib")
        rl = None
        for n in rl_names:
            p = os.path.join(base, n)
            if os.path.isfile(p):
                rl = p
                break
        if not rl:
            for n in rl_names:
                p = shutil.which(n)
                if p:
                    rl = p
                    break
        return ar, rl

    def _inject_meson_archiver(self):
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        ar, rl = ce.get("ar"), ce.get("ranlib")
        if not ar:
            ar, rl = self._probe_archiver()
        nf = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if not (ar and os.path.isfile(nf)):
            return
        with open(nf, encoding="utf-8") as f:
            content = f.read()
        if "\nar =" in content or "[binaries]" not in content:
            return
        ins = "[binaries]\nar = '%s'\n" % ar
        if rl:
            ins += "ranlib = '%s'\n" % rl
        with open(nf, "w", encoding="utf-8") as f:
            f.write(content.replace("[binaries]\n", ins, 1))

    def build(self):
        apply_conandata_patches(self)
        # PKG_CONFIG_PATH 注入 os.environ 保证 meson 子进程解析依赖 .pc
        # （meson 的 PKG_CONFIG_PATH 由 conan 工具链固定指向 generators_folder，
        # 但额外注入全部依赖包目录，保证 Requires 链可直接解析）。
        pkgconfig_dirs = []
        for dep in self.dependencies.values():
            try:
                dep_pkg = dep.package_folder
            except Exception:
                continue
            if not dep_pkg:
                continue
            pc_dir = os.path.join(dep_pkg, "lib", "pkgconfig")
            if os.path.isdir(pc_dir) and pc_dir not in pkgconfig_dirs:
                pkgconfig_dirs.append(pc_dir)
        if pkgconfig_dirs:
            cur = os.environ.get("PKG_CONFIG_PATH", "")
            merged = [d for d in pkgconfig_dirs if d not in cur.split(os.pathsep)]
            if merged:
                os.environ["PKG_CONFIG_PATH"] = (os.pathsep.join(merged) +
                                                 (os.pathsep + cur if cur else ""))
            self.output.info("systemd: PKG_CONFIG_PATH=%s"
                             % os.environ["PKG_CONFIG_PATH"])
        meson = Meson(self)
        meson.configure()
        # 只构建 libsystemd 目标（1540 个目标全构建超时；daemon/工具非所需）。
        # ninja 目标名带版本后缀（libsystemd.so.0.44.0）。
        self.run("ninja -C {} libsystemd.so.0.44.0".format(self.build_folder),
                 env="conanbuild")
        # ── 上游测试（rule 4 逐类归因）──
        # systemd 测试依赖运行中的 systemd 环境（pid1/udev/cgroup/namespace），
        # OHOS 无——按 rule 1.2 如实声明平台限制（非跳过）。不在此处跑
        # "meson test"（会触发全部 1281 测试目标构建导致超时）；逐类归因
        # 实测数据（编译 235 可编译/17 编译失败 + 运行 120 通过/14 跳过/
        # 38 失败，通过率按全量 252 = 47.6%）已固化在 manifest.yaml /
        # notes.md / test_package/MANIFEST.yml / PR 描述。

    def package(self):
        # 不用 meson.install()（会触发全部 1281 install 目标构建导致超时）——
        # 手动复制 libsystemd 产物：.so 版本链 + 公开头文件 + pc。
        pkg_lib = os.path.join(self.package_folder, "lib")
        os.makedirs(pkg_lib, exist_ok=True)
        shutil.copy2(os.path.join(self.build_folder, "libsystemd.so.0.44.0"),
                     os.path.join(pkg_lib, "libsystemd.so.0.44.0"))
        for link, target in (("libsystemd.so.0", "libsystemd.so.0.44.0"),
                             ("libsystemd.so", "libsystemd.so.0")):
            os.symlink(target, os.path.join(pkg_lib, link))
        systemd_inc = os.path.join(self.source_folder, "src", "systemd")
        pkg_inc = os.path.join(self.package_folder, "include", "systemd")
        os.makedirs(pkg_inc, exist_ok=True)
        for h in sorted(os.listdir(systemd_inc)):
            if h.endswith(".h"):
                shutil.copy2(os.path.join(systemd_inc, h), os.path.join(pkg_inc, h))
        os.makedirs(os.path.join(self.package_folder, "lib", "pkgconfig"),
                    exist_ok=True)
        pc_src = os.path.join(self.build_folder, "libsystemd.pc")
        if os.path.isfile(pc_src):
            shutil.copy2(pc_src,
                         os.path.join(self.package_folder, "lib", "pkgconfig",
                                      "libsystemd.pc"))
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # CI：OHOS 拒绝加载未签名 .so——test_package 的 dlopen 报
        # "Permission denied"（E318 同类）。与 cairo-gobject/pcaudiolib 同款：
        # 用 OHOS 的 binary-sign-tool 对 libsystemd.so 自签名。
        # 不依赖 settings.os 判定（CI 的 os 设置可能不同导致签名未执行），
        # 改为：工具存在即签名，工具缺失则跳过（方法内 guard）。
        self._sign_shared_libs()

    def _sign_shared_libs(self):
        import glob as _glob
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            self.output.info("systemd: binary-sign-tool not found, skip signing")
            return
        targets = _glob.glob(os.path.join(self.package_folder, "lib", "**",
                                          "*.so"), recursive=True)
        targets += _glob.glob(os.path.join(self.package_folder, "lib", "**",
                                           "*.so.*"), recursive=True)
        for target in targets:
            if os.path.islink(target):
                continue
            self.run(f'{objcopy} --remove-section .codesign "{target}" '
                     f'2>/dev/null || true')
            self.run(f'{signer} sign -inFile "{target}" -outFile "{target}" '
                     f'-selfSign 1')

    def package_info(self):
        self.cpp_info.libs = ["systemd"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = ["include"]
