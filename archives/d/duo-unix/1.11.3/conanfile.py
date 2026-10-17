#!/usr/bin/env python3
"""Conan recipe for duo-unix 1.11.3 — Duo Security two-factor authentication for Unix.

duo-unix provides the libduo library and the login_duo CLI tool for Duo
two-factor authentication. The only required external dependency is OpenSSL
(libssl/libcrypto); PAM support is optional and disabled by default.

Build system: Autotools (configure.ac + Makefile.am). The GitHub archive tag
does not ship a pre-generated configure script, so autoreconf is run during
the build via tool_requires on automake/libtool.
"""
import os
import glob
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    collect_libs,
    copy,
    export_conandata_patches,
    get,
    load,
    save,
)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class DuoUnixConan(ConanFile):
    name = "duo-unix"
    version = "1.11.3"
    description = "Duo Security two-factor authentication for Unix systems"
    license = "BSD-2-Clause"
    homepage = "https://github.com/duosecurity/duo_unix"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: settings.os 判断必须 in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"duo-unix only supports Linux/OHOS, got {self.settings.os}"
            )

    def requirements(self):
        self.requires("openssl/3.5.6")

    def build_requirements(self):
        # GitHub archive 不含 configure（只是 git tree 快照），须 autoreconf 自举；
        # CI 设备缺 automake/libtool，通过 tool_requires 用 build profile 解析。
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # OpenSSL 路径（Conan 依赖）
        openssl = self.dependencies["openssl"].package_folder
        tc.configure_args.extend([
            f"--with-openssl={openssl}",
            "--without-pam",
        ])
        # OHOS 交叉编译：config.sub 需识别 ohos triplet（见 _patch_config_for_ohos）
        if self.settings.os == "OHOS":
            tc.configure_args.extend([
                "--build=aarch64-unknown-linux-gnu",
                "--host=aarch64-unknown-linux-ohos",
            ])
        if not self.options.shared:
            tc.configure_args.extend(["--enable-static", "--disable-shared"])
        tc.generate()
        AutotoolsDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        # GitHub archive 无 configure（autoreconf 产物不进版本库），先自举
        # -vfi: verbose/force/install；-I autotools: 加载本地 m4 宏（ax_check_openssl 等）
        if not os.path.isfile(os.path.join(self.source_folder, "configure")):
            # 交叉编译补丁：ax_check_x509.m4 用 AC_RUN_IFELSE 运行测试程序，
            # 交叉编译时报 "cannot run test program while cross compiling"。
            # 改用 AC_LINK_IFELSE 仅检查符号能否链接，不需真正运行。
            self._patch_x509_cross_compile()
            self.output.info("源码树无 configure（GitHub archive），先 autoreconf 自举")
            autotools.autoreconf(args=["-vfi", "-I", "autotools"])
        # autoreconf 后修补 config.sub/guess 以识别 OHOS triplet
        self._patch_config_for_ohos()
        # HMDFS 上 config.status 用 umask 077 创建临时目录，导致 subs1.awk
        # 无执行权限（Permission denied）。configure 内部会跑 config.status，
        # 该步失败但 config.status 文件已生成 —— 先 configure（允许失败），
        # 修复 config.status 后手动重跑生成 Makefile。
        try:
            autotools.configure()
        except ConanException:
            cs = os.path.join(self.build_folder, "config.status")
            if not os.path.exists(cs):
                raise
            self.output.info("configure 内部 config.status 失败，尝试 HMDFS 修复后重跑")
        self._fix_config_status()
        mk = os.path.join(self.build_folder, "Makefile")
        if not os.path.exists(mk):
            self.run("cd " + self.build_folder + " && bash config.status")
        autotools.make(args=["-j1"])

    def _patch_x509_cross_compile(self):
        """Patch ax_check_x509.m4 to use AC_LINK_IFELSE instead of AC_RUN_IFELSE.

        原始宏用 AC_RUN_IFELSE 运行 X509_TEA_set_state(0) 测试程序，
        交叉编译（OHOS aarch64）时无法运行目标平台二进制而报错。
        改用 AC_LINK_IFELSE 仅检查符号能否链接即可满足检测目的。
        """
        m4_path = os.path.join(self.source_folder, "autotools", "ax_check_x509.m4")
        if not os.path.isfile(m4_path):
            return
        try:
            with open(m4_path, "r", encoding="utf-8") as f:
                content = f.read()
        except OSError:
            return
        if "AC_LINK_IFELSE" in content:
            return  # 已 patch 过
        if "AC_RUN_IFELSE" not in content:
            return  # 不含 AC_RUN_IFELSE，无需处理
        content = content.replace("AC_RUN_IFELSE", "AC_LINK_IFELSE")
        with open(m4_path, "w", encoding="utf-8") as f:
            f.write(content)
        self.output.info(
            "Patched ax_check_x509.m4: AC_RUN_IFELSE→AC_LINK_IFELSE "
            "for cross-compile"
        )

    def _patch_config_for_ohos(self):
        """Patch generated config.sub/config.guess to recognize the OHOS triplet.

        autoreconf 从 automake 安装的 config.sub/guess 拷贝而来，较新版本可能
        已支持 ohos；若不支持则按 patch-autotools-ohos.pl 的逻辑手动添加。
        """
        if self.settings.os != "OHOS":
            return
        for cs_path in glob.glob(
            os.path.join(self.source_folder, "**", "config.sub"), recursive=True
        ):
            try:
                with open(cs_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            except OSError:
                continue
            if "ohos" in content:
                continue
            changed = False
            # 1. ohos* 加入 OS 类型列表（gnu* | android* → gnu* | android* | ohos*）
            if "gnu* | android*" in content and "ohos*" not in content:
                content = content.replace(
                    "gnu* | android*", "gnu* | android* | ohos*", 1
                )
                changed = True
            # 2. linux-ohos 加入 kernel-OS 校验列表
            if "linux-uclibc" in content and "linux-ohos" not in content:
                content = content.replace(
                    "linux-uclibc*)", "linux-uclibc* | linux-ohos*)", 1
                )
                changed = True
            # 3. 添加 ohos-linux) 映射（紧跟 android-linux 块之后）
            if "ohos-linux)" not in content and "android-linux)" in content:
                anchor = "android-linux)\n"
                # 在 android-linux 块的 ;; 之后插入 ohos-linux 块
                idx = content.find(anchor)
                if idx != -1:
                    end = content.find(";;", idx)
                    if end != -1:
                        insert_pos = end + len(";;") + 1
                        ohos_block = (
                            "\tohos-linux)\n"
                            "\t\tbasic_machine=$field1-unknown\n"
                            "\t\tbasic_os=linux-ohos\n"
                            "\t\t;;\n"
                        )
                        content = content[:insert_pos] + ohos_block + content[insert_pos:]
                        changed = True
            if changed:
                with open(cs_path, "w", encoding="utf-8") as f:
                    f.write(content)
                self.output.info(f"Patched config.sub for OHOS: {cs_path}")

        for cg_path in glob.glob(
            os.path.join(self.source_folder, "**", "config.guess"), recursive=True
        ):
            try:
                with open(cg_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            except OSError:
                continue
            if "HarmonyOS" in content:
                continue
            changed = False
            # __OHOS__ LIBC 检测（紧跟 __ANDROID__）
            if "__OHOS__" not in content and "__ANDROID__" in content:
                content = content.replace(
                    "#if defined(__ANDROID__)\n    LIBC=android",
                    "#if defined(__ANDROID__)\n    LIBC=android\n#elif defined(__OHOS__)\n    LIBC=ohos",
                    1,
                )
                changed = True
            if changed:
                with open(cg_path, "w", encoding="utf-8") as f:
                    f.write(content)
                self.output.info(f"Patched config.guess for OHOS: {cg_path}")

    def _fix_config_status(self):
        """修复 config.status 在 HMDFS 上的临时目录权限问题。

        autoconf 生成的 config.status 用 `umask 077 && mktemp -d` 创建临时
        目录（如 confGOfMgj），HMDFS 文件系统对该权限模式创建的子目录
        不授予执行权限，导致内部 awk 脚本（subs1.awk 等）无法执行，报：
            ./config.status: line 822: ./confGOfMgj/subs1.awk: Permission denied
            config.status: error: could not setup config files machinery

        修复策略：
        1. 移除 `umask 077` 前缀，让 mktemp/mkdir 用默认权限（0755）；
        2. 在 ac_tmp 赋值后追加 `chmod 755 "$tmp"`，确保临时目录可进入；
        3. 重跑 config.status 重新生成 Makefile/config.h。

        config.status 是 configure 生成的文件，不在源码 tarball 中，
        因此无法通过 conandata.yml 的 patches 修复，必须就地处理。
        """
        path = os.path.join(self.build_folder, "config.status")
        if not os.path.exists(path):
            return
        content = load(self, path)
        original = content
        # 1. 移除 umask 077 前缀（autoconf 的 ac_cs_awk_cr 临时目录创建逻辑）
        content = content.replace("umask 077 && mktemp", "mktemp")
        content = content.replace("umask 077 && mkdir", "mkdir")
        # 2. 在 ac_tmp=$tmp 之后追加 chmod，确保临时目录可执行
        content = content.replace(
            "ac_tmp=$tmp",
            'ac_tmp=$tmp\nchmod 755 "$tmp" 2>/dev/null',
        )
        if content != original:
            save(self, path, content)
            self.output.info(f"Patched config.status for HMDFS: {path}")

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # libtool 的 make install 只装 .la 元数据，不装实际的 .a 静态库。
        # 手动从 build 目录的 .libs/ 复制 libduo.a 到 package_folder/lib/。
        if not self.options.shared:
            build_lib = os.path.join(self.build_folder, "lib", ".libs")
            pkg_lib = os.path.join(self.package_folder, "lib")
            if os.path.isdir(build_lib):
                os.makedirs(pkg_lib, exist_ok=True)
                for name in os.listdir(build_lib):
                    if name.endswith(".a"):
                        src = os.path.join(build_lib, name)
                        dst = os.path.join(pkg_lib, name)
                        if os.path.isfile(src):
                            shutil.copy2(src, dst)
                            self.output.info(f"Packaged static lib: {name}")
            # libduo.a 引用 libcompat.a 的符号（match_pattern/ga_*），
            # 用 llvm-ar 把 libcompat.a 的对象合并进 libduo.a，避免
            # 下游消费者需要额外链接 libcompat。
            libduo = os.path.join(pkg_lib, "libduo.a")
            libcompat = os.path.join(
                self.build_folder, "compat", ".libs", "libcompat.a"
            )
            if os.path.isfile(libduo) and os.path.isfile(libcompat):
                ar = "llvm-ar"
                # 解开 libcompat.a 到临时目录再合并
                import tempfile
                with tempfile.TemporaryDirectory() as td:
                    compat_objs = []
                    # MRSP 临时目录权限：先展开对象文件到 td
                    self.run(f'{ar} x "{libcompat}"', cwd=td)
                    for obj in glob.glob(os.path.join(td, "*.o")):
                        compat_objs.append(obj)
                    if compat_objs:
                        # 合并对象到 libduo.a
                        obj_list = " ".join(f'"{o}"' for o in compat_objs)
                        self.run(f'{ar} rcs "{libduo}" {obj_list}')
                        self.output.info("Merged libcompat.a into libduo.a")
        # login_duo 安装到 sbin/，CI L2 烟雾测试扫描 bin/ —— 移动过去
        sbin = os.path.join(self.package_folder, "sbin")
        bindir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(sbin):
            os.makedirs(bindir, exist_ok=True)
            for name in os.listdir(sbin):
                src = os.path.join(sbin, name)
                dst = os.path.join(bindir, name)
                if os.path.isfile(src):
                    shutil.move(src, dst)
            try:
                os.rmdir(sbin)
            except OSError:
                pass
        # 清理 sysconfdir 中安装的默认配置文件（不属于 Conan 产物）
        etc_duo = os.path.join(self.package_folder, "etc", "duo")
        if os.path.isdir(etc_duo):
            shutil.rmtree(etc_duo, ignore_errors=True)
        etc_dir = os.path.join(self.package_folder, "etc")
        if os.path.isdir(etc_dir) and not os.listdir(etc_dir):
            os.rmdir(etc_dir)
        self._sign_binaries()

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        # 鸿蒙 PC XPM 要求 dlopen 的 .so 和被 exec 的可执行文件都要代码签名
        if self.settings.os != "OHOS":
            return
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(objcopy) or not os.path.isfile(signer):
            self.output.warn("签名工具不存在，跳过 ELF 签名 (XPM 可能阻止执行)")
            return
        targets = glob.glob(
            os.path.join(self.package_folder, "lib", "**", "*.so"), recursive=True
        )
        targets += glob.glob(
            os.path.join(self.package_folder, "lib", "**", "*.so.*"), recursive=True
        )
        bindir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bindir):
            for name in os.listdir(bindir):
                p = os.path.join(bindir, name)
                if os.path.isfile(p) and not os.path.islink(p) and self._is_elf(p):
                    targets.append(p)
        for f in targets:
            if os.path.islink(f):
                continue
            # objcopy: 移除已有 .codesign 段；首次签名的 ELF 无此段，
            # llvm-objcopy 返回非零是预期行为，仅 info 不阻断
            try:
                self.run('{oc} --remove-section .codesign "{f}"'.format(
                    oc=objcopy, f=f
                ))
            except ConanException:
                self.output.info(f"无 .codesign 段可移除（首次签名），跳过: {f}")
            # 签名步骤必须成功 — 未签名 ELF 在 OHOS XPM 下无法执行，
            # 失败时 ConanException 直接阻断构建（不吞没 stderr/退出码）
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(
                sg=signer, f=f
            ))

    def package_info(self):
        self.cpp_info.libs = ["duo"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
        # CMake 集成：test_package 通过 find_package(duo-unix REQUIRED CONFIG) 查找
        self.cpp_info.set_property("cmake_file_name", "duo-unix")
        self.cpp_info.set_property("cmake_target_name", "duo-unix::duo-unix")
        # libduo 依赖 OpenSSL，Conan 2.x 通过 self.requires() 自动传递依赖链
