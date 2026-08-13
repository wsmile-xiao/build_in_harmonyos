#!/usr/bin/env python3
"""Conan recipe — megatools homebrew (meson)

megatools 是 MEGA 云存储的命令行客户端集合，上游使用 Meson 构建系统。
Homebrew 版本对应上游 1.11.1.20230212 发布 tarball。
"""
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.gnu import PkgConfigDeps


class MegatoolsConan(ConanFile):
    name = "megatools"
    version = "homebrew"
    description = "Command-line client for MEGA cloud storage"
    license = "GPL-2.0-or-later"
    homepage = "https://xff.cz/megatools/"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        # R32: 仅支持 Linux / OHOS
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "megatools 仅支持 Linux/OHOS，当前 os=%s" % self.settings.os)

    # 强制 curl 以 shared=False 构建，生成 libcurl.a 静态库——
    # OHOS musl 无法加载非系统 .so（无 RPATH 支持），ohpcd 缓存的
    # curl/8.15.0 默认 shared=True 仅含 libcurl.so，故必须强制静态。
    default_options = {
        "curl/*:shared": False,
    }

    def requirements(self):
        # gio-2.0 / glib-2.0 / gmodule 等 pkg-config 模块由 glib Conan 包提供
        # （含静态 .a + .pc），通过 PkgConfigDeps 生成到 generators_folder。
        # 不再依赖 Worker 系统预安装的 glib——CI 干净 Worker 上无该系统包。
        self.requires("glib/2.84.0", transitive_headers=True,
                      transitive_libs=True)
        # zlib：glib 的 gio-2.0.pc Requires.private 拉入 -lz，ohpcd 有静态
        # zlib/1.3.1.1，Conan 化以消除对 Worker 系统 libz.a 的依赖。
        self.requires("zlib/1.3.1.1")
        # openssl/3.5.6.1：curl/8.15.0 依赖 3.5.6.1（FD_SET 可移植性修复），
        # 对齐 curl 版本以避免图冲突。
        self.requires("openssl/3.5.6.1")
        # libcurl：megatools meson.build 硬依赖 dependency('libcurl')，
        # 通过 PkgConfigDeps 把 libcurl.pc 生成到 generators_folder，
        # Meson configure 期即可发现。curl 配方支持 shared=False，
        # 生成 libcurl.a，满足 OHOS 静态链接要求。
        self.requires("curl/8.15.0", transitive_headers=True,
                      transitive_libs=True)
        # libintl：glib 静态库有 gettext 符号的未定义引用（U bind_textdomain*
        #   dcgettext 等），需外部 -lintl，ohpcd 无 gettext/libintl Conan 包，
        #   需 Worker 预装静态 libintl.a
        # 通过 native file 的 pkg_config_path 第二项指向
        # ~/usr/local/lib/pkgconfig 由 pkg-config 发现。

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        sources = self.conan_data["sources"]
        try:
            get(self, **{key: value for key, value in sources.items()
                         if key != "backup_urls"}, strip_root=True)
        except Exception:
            backup_urls = sources.get("backup_urls", [])
            if not backup_urls:
                raise
            self.output.warning("Primary URL failed, trying backup: %s" % backup_urls[0])
            get(self, url=backup_urls[0], sha256=sources["sha256"],
                strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        tc = MesonToolchain(self)
        # 鸿蒙 PC 构建机无 docbook/xsltproc，关闭 man 页生成
        tc.project_options["man"] = "false"
        # 启用 megatools 子命令符号链接（megals/megadl/megaput 等）
        tc.project_options["symlinks"] = "true"
        tc.generate()
        # Meson 不读环境变量 PKG_CONFIG_PATH，只读 native file 的 pkg_config_path，
        # 必须在 native file 中注入系统 pkgconfig 路径，否则找不到 gio-2.0/libcurl
        self._inject_meson_native_file()

    def build(self):
        meson = Meson(self)
        meson.configure()
        meson.build()
        # OHOS musl 不搜索 LD_LIBRARY_PATH 也不支持 RPATH，
        # 动态链接非系统库的 .so 无法运行。meson 通过 pkg-config
        # 发现库时优先选 .so，这里在正常构建后获取 megatools 的链接
        # 命令，把 .so 完整路径替换为同目录 .a 重新链接，保证二进制
        # 自包含可执行（ffi/pcre2/curl 均有 .a）。
        if str(self.settings.os) in ("OHOS",):
            self._relink_static()

    def _relink_static(self):
        """获取 megatools 链接命令，把 .so 替换为 .a 重新链接。

        ninja 构建时会通过 meson regenerate 重新生成 build.ninja，
        直接 patch build.ninja 会被覆盖。这里在 build() 完成后，
        用 ninja -t commands 获取链接命令，逐个把 <path>/lib<name>.so
        替换为 <path>/lib<name>.a（仅当 .a 存在时），手动重新链接。
        """
        import subprocess
        build_folder = self.build_folder
        ninja = shutil.which("ninja") or "/data/service/hnp/bin/ninja"
        try:
            proc = subprocess.run(
                [ninja, "-t", "commands", "megatools"],
                cwd=build_folder, capture_output=True, text=True, check=True,
            )
            commands = proc.stdout.strip().split("\n")
        except Exception as exc:
            self.output.warning(f"_relink_static: ninja commands failed: {exc}")
            return
        # 找到链接命令（包含 -o megatools 的 clang 行）
        link_cmd = None
        for line in commands:
            if "clang" in line and " -o megatools " in line and ".o" in line:
                link_cmd = line
                break
        if not link_cmd:
            return
        # 把 .so 完整路径替换为 .a（仅当 .a 存在）
        static_cmd = re.sub(
            r"(/[^\s]*/lib[^\s/]+)\.so",
            lambda m: m.group(1) + ".a" if os.path.isfile(m.group(1) + ".a") else m.group(0),
            link_cmd,
        )
        if static_cmd == link_cmd:
            return  # 没有 .so 需要替换
        self.output.info("_relink_static: relinking megatools with static .a")
        self.run(f'cd "{build_folder}" && {static_cmd}')

    def _inject_meson_native_file(self):
        """注入 ar/ranlib 路径和 pkg_config_path 到 conan_meson_native.ini。

        Conan 的 MesonToolchain 生成的 native file 仅映射 c/cpp 编译器，
        不包含 ar/ranlib 和系统 pkg-config 路径，需手动补充。
        """
        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if not os.path.isfile(native_file):
            return

        with open(native_file) as handle:
            content = handle.read()

        # 1. 注入 ar/ranlib（从编译器路径推导同目录 llvm-ar/llvm-ranlib）
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
        ar = executables.get("ar")
        ranlib = executables.get("ranlib")
        if not ar:
            compiler = executables.get("c") or executables.get("cpp") or ""
            bindir = os.path.dirname(compiler) if os.path.sep in compiler else ""
            if bindir:
                candidate = os.path.join(bindir, "llvm-ar")
                if os.path.isfile(candidate):
                    ar = candidate
                    candidate_ranlib = os.path.join(bindir, "llvm-ranlib")
                    if os.path.isfile(candidate_ranlib):
                        ranlib = candidate_ranlib
        if ar and "\nar =" not in content and "[binaries]" in content:
            binaries = "[binaries]\nar = '%s'\n" % ar
            if ranlib:
                binaries += "ranlib = '%s'\n" % ranlib
            content = content.replace("[binaries]\n", binaries, 1)

        # 2. 注入 pkg_config_path（让 Meson 发现 Worker 系统预编译的 glib/gio/libcurl）
        prefix = os.path.join(os.path.expanduser("~"), "usr", "local")
        pkg_paths = [
            self.generators_folder,
            os.path.join(prefix, "lib", "pkgconfig"),
            os.path.join(prefix, "share", "pkgconfig"),
        ]
        # PkgConfigDeps 只为直接 requires 的包生成汇总 .pc（如 glib-2.0.pc），
        # 但 glib 的子模块 gio-2.0/gmodule-2.0/gobject-2.0 只存在于
        # glib 包自身的 lib/pkgconfig 下。把每个 Conan 依赖的
        # lib/pkgconfig（若存在）追加到搜索路径，Meson 才能发现这些子模块。
        for dep in self.dependencies.host.values():
            pkg = dep.package_folder
            if not pkg:
                continue
            for sub in (os.path.join("lib", "pkgconfig"),
                        os.path.join("share", "pkgconfig")):
                candidate = os.path.join(pkg, sub)
                if os.path.isdir(candidate) and candidate not in pkg_paths:
                    pkg_paths.append(candidate)
        pkg_config_line = "pkg_config_path = '%s'\n" % os.pathsep.join(pkg_paths)

        lines = content.splitlines(keepends=True)
        found_pkg_config = False
        for index, line in enumerate(lines):
            if line.startswith("pkg_config_path = "):
                lines[index] = pkg_config_line
                found_pkg_config = True
                break

        if not found_pkg_config:
            # 查找 [properties] 段，在其后插入；若无则新建
            has_properties = any(line.strip() == "[properties]" for line in lines)
            if has_properties:
                for index, line in enumerate(lines):
                    if line.strip() == "[properties]":
                        lines.insert(index + 1, pkg_config_line)
                        break
            else:
                if lines and not lines[-1].endswith("\n"):
                    lines[-1] += "\n"
                lines.append("[properties]\n")
                lines.append(pkg_config_line)

        with open(native_file, "w") as handle:
            handle.write("".join(lines))

    def package(self):
        Meson(self).install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        if str(self.settings.os) in ("OHOS",):
            # OHOS 上未签名二进制无法执行（Operation not permitted），
            # 需移除旧签名段并用 binary-sign-tool 自签名
            binary = os.path.join(self.package_folder, "bin", "megatools")
            objcopy = shutil.which("llvm-objcopy") or shutil.which("objcopy")
            signer = shutil.which("binary-sign-tool")
            if not objcopy or not signer:
                raise ConanInvalidConfiguration(
                    "OHOS packaging requires llvm-objcopy and binary-sign-tool in PATH")
            self.run(f'"{objcopy}" --remove-section .codesign "{binary}"',
                     ignore_errors=True)
            signed = binary + ".signed"
            self.run(f'"{signer}" sign -inFile "{binary}" -outFile "{signed}" -selfSign 1')
            os.replace(signed, binary)
            os.chmod(binary, 0o755)

    def package_info(self):
        # CLI 应用：无库文件，仅 bin 目录
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
