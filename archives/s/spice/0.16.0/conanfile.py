#!/usr/bin/env python3
"""Conan recipe — spice 0.16.0 (Meson, libspice-server)

SPICE 远程桌面协议的 server 侧库（libspice-server.so，平台规范单一无版本文件命名，见补丁 0005）。
上游基于 meson（C+C++），tarball 内置 spice-common subproject 实体目录（无 .wrap，
无子模块网络更新：build-aux/meson/check-spice-common 在非 git 目录下自动跳过）。

OHOS aarch64 适配要点
- 依赖全部走 Conan 制品：glib / pixman / openssl / libjpeg-turbo / zlib / lz4 /
  spice-protocol（<spice/macros.h> 等公开头来源）；threads/rt/m 为设备系统库，
  实测 find_library 可用，无需补丁。全部 requires 显式
  transitive_headers=True / transitive_libs=True（平台惯例，全仓 412 处同款）：
  本 conan 默认不向消费者传播静态依赖与 header-only 依赖，公共头链
  spice-core.h → spice/qxl_dev.h（spice-protocol）要求消费者可见（G2 实测）。
- 桌面环境强相关功能关闭：gstreamer / sasl / opus / smartcard / manual(asciidoc) /
  instrumentation；保留 lz4（aarch64 链接器实测可接受 Conan lz4 静态库）与
  上游测试套件（tests=true，R34/测试门禁）。
- MesonToolchain 不写 ar/ranlib（OHOS profile 的 compiler_executables 只有
  c/cpp），cross 侧还缺 pkg-config：_inject_meson_binaries() 从编译器同目录
  推导 llvm-ar/llvm-ranlib 并注入 conan_meson_native.ini / conan_meson_cross.ini
  （先例 archives/g/glib/2.84.0.1、archives/p/pixman/0.46.4.1）。
- spice 请求 dependency('liblz4')，Conan lz4 配方经 PkgConfigDeps 只生成 lz4.pc：
  _alias_lz4_pc() 复制为 liblz4.pc 并改 Name（先例 glib _alias_pcre2_pc）；
  libjpeg 的 .pc 名由 libjpeg-turbo 配方从安装产物动态检测为 libjpeg.pc，
  与上游请求一致，无需处理。
- spice-common 构建期以 custom_target 运行 python3 spice_codegen.py 生成
  Marshallers（codegen → spice_parser → pyparsing，缺模块直接 exit(1)，上游
  python-checks 也因此默认校验）。宿主 python3 未必带该模块：source() 按
  conandata 的 pyparsing 源下载固定版本 sdist（纯 python，MIT；条目前先例
  glib proxy-libintl 第二源），build() 将其目录前置进 PYTHONPATH 供 configure
  期 python-checks 与构建期 codegen 使用——不修改上游源码、不依赖宿主环境。
- build() 内真实执行上游 meson 测试套件（server/tests + spice-common/tests）；
  cross 跳过执行（OHOS 二进制无法在构建宿主运行），native OHOS 加
  --timeout-multiplier=16（先例 glib）。
- 真机平台差异以补丁修正（patches/0003、0004、0005）：OHOS 对 AF_UNIX
  socket 的 IPPROTO_TCP 选项返回 ENOPROTOOPT（上游 keepalive 容错仅覆盖
  ENOTSUP/EOPNOTSUPP），对 unix 连接误报警告致测试框架判死；hmdfs 家目录
  不支持路径式 unix socket（bind 返回 EPERM），test-listen 探测 cwd 后回退
  抽象命名空间；hmdfs 同样拒绝符号链接（ln -s EPERM），meson 探测后跳过
  全部符号链接，versioned 共享库因此缺少 .so 开发链接（消费者 CMakeDeps
  find_library 与链接器 -lspice-server 均不可解析），补丁 0005 按平台规范
  （no-versioned-soname.cmake：单一无版本文件）去掉 version 参数。
  详见 conandata.yml 中各 patch_description。
- package() 后对 lib/**/*.so* 做 OHOS 重签名（binary-sign-tool，先例 glib）。
"""
import glob
import os
import shutil
import sys

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class SpiceConan(ConanFile):
    name = "spice"
    version = "0.16.0"
    description = "SPICE — remote desktop server library (libspice-server)"
    license = "LGPL-2.1"
    homepage = "https://www.spice-space.org/"
    url = ""
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # 版本与制品仓 / 真机缓存对齐（W0 依赖预检结论）。
        # transitive_headers/transitive_libs=True：平台配方惯例（全仓 412 处同款）。
        # 本平台 conan 默认不向消费者传播静态依赖与 header-only 依赖：实测消费者
        # 侧 CMakeDeps 仅生成 GLib/pixman/libjpeg-turbo（共享库），spice-protocol
        # （header-library）被丢弃 → test_package 编译 <spice-server/spice-core.h>
        # 时其 #include <spice/qxl_dev.h> 无法解析（G2 实测）。
        self.requires("glib/2.84.0.1", transitive_headers=True, transitive_libs=True)
        self.requires("pixman/0.46.4.1", transitive_headers=True, transitive_libs=True)
        self.requires("openssl/3.5.6", transitive_headers=True, transitive_libs=True)
        self.requires("libjpeg-turbo/3.2.0", transitive_headers=True, transitive_libs=True)
        self.requires("zlib/1.3.1.1", transitive_headers=True, transitive_libs=True)
        self.requires("lz4/1.10.0.3", transitive_headers=True, transitive_libs=True)
        self.requires("spice-protocol/0.14.5", transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # 构建期 codegen 依赖（见文件头 docstring）：strip_root 解包后目录根部
        # 即 pyparsing.py 单文件模块，可直接作为 PYTHONPATH 目录。
        py = dict(self.conan_data["pyparsing"])
        dest = os.path.join(self.source_folder, "python-deps")
        if not os.path.isfile(os.path.join(dest, "pyparsing.py")):
            get(self, **py, destination=dest, strip_root=True)

    def _alias_lz4_pc(self):
        # Meson 侧 dependency('liblz4')；Conan lz4 配方经 PkgConfigDeps 生成 lz4.pc，
        # 复制为 liblz4.pc 并改 Name（先例 glib _alias_pcre2_pc）。
        gens = self.generators_folder
        src = os.path.join(gens, "lz4.pc")
        dst = os.path.join(gens, "liblz4.pc")
        if os.path.isfile(src) and not os.path.isfile(dst):
            shutil.copy(src, dst)
            text = open(dst).read()
            if "Name:" in text:
                lines = []
                for line in text.splitlines(True):
                    if line.startswith("Name:"):
                        lines.append("Name: liblz4\n")
                    else:
                        lines.append(line)
                open(dst, "w").write("".join(lines))

    def _inject_meson_binaries(self):
        # MesonToolchain omits ar/ranlib; cross builds also omit pkg-config, so
        # Meson reports "Found pkg-config: NO" and cannot see PkgConfigDeps .pc files.
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        ar = ce.get("ar")
        rl = ce.get("ranlib")
        if not ar:
            cc = ce.get("c") or ""
            bindir = os.path.dirname(cc) if os.path.sep in cc else ""
            if bindir:
                for name in ("llvm-ar", "ar"):
                    cand = os.path.join(bindir, name)
                    if os.path.isfile(cand):
                        ar = cand
                        break
                for name in ("llvm-ranlib", "ranlib"):
                    rlc = os.path.join(bindir, name)
                    if os.path.isfile(rlc):
                        rl = rlc
                        break
        pkg_config = self.conf.get("tools.gnu:pkg_config", default=None)
        if not pkg_config or not os.path.isfile(str(pkg_config)):
            pkg_config = shutil.which("pkg-config") or shutil.which("pkgconf")
        # glib-mkenums（meson gnome 模块生成 spice-server-enums.c/h 的工具）：
        # OHOS 内核禁止 shebang 脚本直接 execve（真机实测 EACCES），而 meson 的
        # ModuleState.find_tool 对 'glib-mkenums' 先查 machine file [binaries]
        # 再退 pkgconfig 变量/PATH——后两者拿到的都是原样脚本。此处注入命令数组
        # [python3, <glib 包内脚本>]，用当前解释器显式执行（真机/CI 通吃）。
        mkenums = None
        try:
            glib_pkg = self.dependencies["glib"].package_folder
            cand = os.path.join(glib_pkg, "bin", "glib-mkenums")
            if os.path.isfile(cand):
                mkenums = cand
        except Exception:
            mkenums = None
        if not mkenums:
            # fallback：从 PkgConfigDeps 生成的 glib-2.0.pc 解析 prefix。
            pc = os.path.join(self.generators_folder, "glib-2.0.pc")
            if os.path.isfile(pc):
                for line in open(pc).read().splitlines():
                    if line.startswith("prefix="):
                        cand = os.path.join(line.split("=", 1)[1].strip(),
                                            "bin", "glib-mkenums")
                        if os.path.isfile(cand):
                            mkenums = cand
                        break
        mkenums_entry = None
        if mkenums:
            mkenums_entry = "glib-mkenums = ['%s', '%s']" % (sys.executable, mkenums)
        for nf_name in ("conan_meson_native.ini", "conan_meson_cross.ini"):
            nf = os.path.join(self.generators_folder, nf_name)
            if not os.path.isfile(nf):
                continue
            with open(nf) as f:
                content = f.read()
            if "[binaries]" not in content:
                continue
            extras = []
            if ar and "\nar =" not in content:
                extras.append("ar = '%s'" % ar)
                if rl:
                    extras.append("ranlib = '%s'" % rl)
            if pkg_config and "\npkg-config =" not in content and "\npkgconfig =" not in content:
                extras.append("pkg-config = '%s'" % pkg_config)
            if mkenums_entry and "\nglib-mkenums =" not in content:
                extras.append(mkenums_entry)
            if not extras:
                continue
            content = content.replace("[binaries]\n", "[binaries]\n" + "\n".join(extras) + "\n", 1)
            with open(nf, "w") as f:
                f.write(content)

    def generate(self):
        PkgConfigDeps(self).generate()
        self._alias_lz4_pc()
        tc = MesonToolchain(self)
        tc.project_options["wrap_mode"] = "nodownload"
        # spice 0.16 的 C++ 迁移版在 meson.build:218 无条件定义 SPICE_USE_SAFER_CONTAINEROF，
        # spice-protocol 的 SPICE_CONTAINEROF 随之走 GNU 语句表达式 + typeof 分支
        # （server/red-common.h 的 SPICE_UPCAST 经 spice-common verify.h 也依赖该路径）。
        # 上游未指定 cpp_std，实际以编译器默认 GNU 方言构建（gcc/clang 默认 gnu++17）；
        # 若用 strict c++17，clang 关闭 GNU 关键字（typeof 不可用）导致 server 编译失败。
        # 故显式固定 gnu++17（覆盖 conan 由 profile compiler.cppstd=17 映射出的 c++17）。
        tc.cpp_std = "gnu++17"
        tc.project_options["gstreamer"] = "no"
        tc.project_options["lz4"] = "true"
        tc.project_options["sasl"] = "false"
        tc.project_options["opus"] = "disabled"
        tc.project_options["smartcard"] = "disabled"
        tc.project_options["manual"] = "false"
        tc.project_options["instrumentation"] = "no"
        tc.project_options["alignment-checks"] = "false"
        tc.project_options["extra-checks"] = "false"
        tc.project_options["statistics"] = "false"
        tc.project_options["tests"] = "true"   # 上游测试套件在 build() 内真实执行
        tc.generate()
        self._inject_meson_binaries()

    def _export_pyparsing(self):
        # configure 期（python-checks）与构建期（codegen custom_target）都以
        # 环境继承方式找到 pyparsing：conan run() 从 os.environ 拷贝基础环境。
        py_deps = os.path.join(self.source_folder, "python-deps")
        prev = os.environ.get("PYTHONPATH", "")
        os.environ["PYTHONPATH"] = py_deps + (os.pathsep + prev if prev else "")

    def build(self):
        apply_conandata_patches(self)
        self._export_pyparsing()
        meson = Meson(self)
        meson.configure()
        meson.build()
        # ── 上游官方测试（ADAPTATION_GUIDE Step 3 / TEST_QUALITY_SPEC §3）──
        # cross 构建跳过执行（OHOS 二进制无法在 Linux 构建宿主运行）。
        # native OHOS：meson test 加 --timeout-multiplier=16（先例 glib）。
        if cross_building(self):
            self.output.info(
                "cross-building: skip meson.test() (OHOS binaries not runnable on build host)"
            )
        else:
            if os.uname().sysname in ("OHOS", "HarmonyOS"):
                build_folder = self.build_folder

                def _ohos_meson_test():
                    self.run(
                        'meson test -v -C "{}" --timeout-multiplier=16 '
                        "--no-rebuild".format(build_folder)
                    )

                meson.test = _ohos_meson_test
            meson.test()

    def _sign_shared_libs(self):
        # Native OHOS worker: re-sign after meson install rewrites rpath.
        # Cross Docker SDK (oh_compile): binary-sign-tool may be absent — skip.
        libdir = os.path.join(self.package_folder, "lib")
        sos = glob.glob(os.path.join(libdir, "**", "*.so"), recursive=True)
        sos += glob.glob(os.path.join(libdir, "**", "*.so.*"), recursive=True)
        if not sos:
            return
        candidates_objcopy = [
            "/data/service/hnp/bin/llvm-objcopy",
            shutil.which("llvm-objcopy") or "",
        ]
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = ce.get("c") or ""
        if cc:
            candidates_objcopy.insert(0, os.path.join(os.path.dirname(cc), "llvm-objcopy"))
        objcopy = next((p for p in candidates_objcopy if p and os.path.isfile(p)), None)
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            self.output.warning("binary-sign-tool not found; skip OHOS codesign (cross/SDK env)")
            return
        for so in sos:
            if objcopy:
                self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=so))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=so))

    def package(self):
        Meson(self).install()
        self._sign_shared_libs()

    def package_info(self):
        self.cpp_info.libs = ["spice-server"]
        self.cpp_info.set_property("cmake_file_name", "spice-server")
        self.cpp_info.set_property("cmake_target_name", "spice-server::spice-server")
        self.cpp_info.set_property("pkg_config_name", "spice-server")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread"]
