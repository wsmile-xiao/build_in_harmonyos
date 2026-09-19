#!/usr/bin/env python3
"""Conan recipe — xylib 1.6 (Autotools).

xylib is a portable C++11 library (with C bindings) for reading files that
contain x-y data from powder diffraction, spectroscopy and other experimental
methods.  Ships libxy plus the xyconv CLI converter.

Build system: Autotools (release tarball ships a pre-generated ./configure).
Dependencies (all header/library-only on this platform):
  - Boost headers (boost/spirit, property_tree, cstdint, shared_ptr, ...)
  - zlib (reading .gz archives), bzip2 (reading .bz2 archives)
The wxWidgets GUI (xyconvert) is disabled for the HarmonyOS PC target.
"""

import os
import shutil

from conan import ConanFile
from conan.tools.build import load_toolchain_args
from conan.tools.files import apply_conandata_patches, \
    export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class XylibConan(ConanFile):
    name = "xylib"
    version = "1.6"
    description = "Portable C++ library for reading files that contain x-y " \
                  "data from powder diffraction, spectroscopy and other " \
                  "experimental methods"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/wojdyr/xylib"
    url = "https://github.com/wojdyr/xylib"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # Boost is used header-only (boost/spirit, property_tree, cstdint).
        # 1.90.0.x suffixes are this repo's packaging revisions (not upstream
        # versions); 1.90.0.4 is the revision published and consumed by
        # mailio/pinocchio on the HarmonyOS PC center.
        self.requires("boost/1.90.0.4")
        self.requires("zlib/1.3.1.1")
        self.requires("bzip2/1.0.8")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # zlib/bzip2/boost include and lib dirs flow into CPPFLAGS/LDFLAGS.
        AutotoolsDeps(self).generate()

        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--without-gui")
        if not self.options.shared:
            tc.configure_args.append("--disable-shared")
            tc.configure_args.append("--enable-static")
        tc.generate()

        # E002 readonly_tmp: HMFS 上 /tmp 只读，bash（configure 的进程替换/
        # here-doc）、mktemp、llvm-ar/llvm-ranlib 与 make 的 shell 配方都会向
        # ${TMPDIR:-/tmp} 写临时文件，落到只读 /tmp 即报
        # "can't create temporary file /tmp/XXXX.tmp" 使编译/打包终止。这里在
        # generate() 用 buildenv 定义 TMPDIR/TMP/TEMP：conan 会把它们写入
        # conanbuild 环境，autotools.configure()/make() 的 self.run(...,
        # env="conanbuild") 子进程全部继承可写临时目录（对齐 anubis 4.3 /
        # asterisk-flite 已过门禁先例）。优先复用 hmbs 注入的 HMBS_TMPDIR/
        # TMPDIR，否则回落 build 目录下自建可写 tmp。
        tmpdir = (
            os.environ.get("HMBS_TMPDIR")
            or os.environ.get("TMPDIR")
            or os.path.join(self.build_folder, "tmp")
        )
        os.makedirs(tmpdir, exist_ok=True)
        self.buildenv.define("TMPDIR", tmpdir)
        self.buildenv.define("TMP", tmpdir)
        self.buildenv.define("TEMP", tmpdir)

    def build(self):
        apply_conandata_patches(self)
        configure = os.path.join(self.source_folder, "configure")
        if os.path.isfile(configure):
            os.chmod(configure, 0o755)
        autotools = Autotools(self)
        configure_args = self._load_configure_args()

        # OHOS storage (HMFS/HMDFS) may not report a working directory for
        # `pwd`/getcwd.  Pin PWD to the build folder so configure scripts
        # that resolve the absolute source path still succeed.
        if self.settings.os == "OHOS":
            try:
                os.chdir(self.build_folder)
            except OSError:
                pass
            os.environ["PWD"] = self.build_folder

            # HMFS 上 /tmp 为只读（E002 readonly_tmp）：bash（configure 里的
            # 进程替换/here-doc 临时文件）、mktemp、llvm-ar/llvm-ranlib 与 make
            # 子进程都会向 ${TMPDIR:-/tmp} 写临时文件，落到只读 /tmp 即报
            # "can't create temporary file /tmp/XXXX.tmp" 使编译终止。优先复用
            # hmbs 注入的 TMPDIR，否则回落到 build 目录下自建可写 tmp，
            # 并同时导出 TMP/TEMP（部分工具取这三个变量）。此段在 build 进程
            # 内设置 os.environ，后续所有 self.run 子进程均继承。
            tmpdir = (
                os.environ.get("HMBS_TMPDIR")
                or os.environ.get("TMPDIR")
                or os.path.join(self.build_folder, "tmp")
            )
            os.makedirs(tmpdir, exist_ok=True)
            os.environ["TMPDIR"] = tmpdir
            os.environ["TMP"] = tmpdir
            os.environ["TEMP"] = tmpdir

            config_shell = shutil.which("bash") or "/data/service/hnp/bin/bash"
            cc = shutil.which("clang") or os.environ.get("CC", "clang")
            cxx = shutil.which("clang++") or os.environ.get("CXX", "clang++")
            ar = shutil.which("llvm-ar") or shutil.which("ar") or "ar"
            ranlib = shutil.which("llvm-ranlib") or shutil.which("ranlib") or "ranlib"
            self.run(
                f'CC="{cc}" CXX="{cxx}" AR="{ar}" RANLIB="{ranlib}" '
                f'CONFIG_SHELL="{config_shell}" '
                f'"{config_shell}" "{configure}" {configure_args}'
            )
        else:
            autotools.configure(args=configure_args)

        if str(self.settings.os) == "OHOS":
            # E182/E188: 真机 HMFS 上带 `-c` 的 install（toybox/HMBS shim）直接失败，
            # 导致 libtool 的 install_prog 拷贝 libxy.a 失败，其后的 postinstall
            # `chmod 644 .../libxy.a` 因文件不存在而报 "No such file or directory"。
            # 用 cp/mkdir shim 替换生成的 Makefile 里的 INSTALL，make install 全程
            # 不碰真机 install；HMFS 不支持 chmod（chmod+/-x 在 ELF 上返回
            # Permission denied），chmod 步骤容错跳过（同 adms 2.3.7 / libfstconst /
            # aribb24 已过门禁先例）。
            shim_dir = self._write_install_shim()
            self._redirect_install_to_shim(os.path.join(shim_dir, "install"))

        autotools.make()

    def _write_install_shim(self):
        # 用 os.open 指定 0o755 直接生成可执行 shim（HMFS 按 open mode 给权限，
        # chmod 能力为 0，不能依赖 os.chmod）。返回 shim 目录并前置到 PATH。
        shim_dir = os.path.join(self.build_folder, "_ohos_install_shim")
        os.makedirs(shim_dir, exist_ok=True)

        # 1) install shim：cp/mkdir 替代真机 install（带 -c 会失败 E182/E188）。
        install = os.path.join(shim_dir, "install")
        fd = os.open(install, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o755)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
                f.write(
                    "#!/bin/sh\n"
                    "set -eu\n"
                    "mode=\n"
                    "while [ $# -gt 0 ]; do\n"
                    "  case \"$1\" in\n"
                    "    -p|-c) shift ;;\n"
                    "    -m) [ $# -ge 2 ] || exit 2; mode=$2; shift 2 ;;\n"
                    "    -d) shift; [ $# -gt 0 ] || exit 2; mkdir -p \"$@\"; exit 0 ;;\n"
                    "    --) shift; break ;;\n"
                    "    -*) shift ;;\n"
                    "    *) break ;;\n"
                    "  esac\n"
                    "done\n"
                    "[ $# -ge 2 ] || exit 2\n"
                    "dest=\n"
                    "for arg in \"$@\"; do dest=$arg; done\n"
                    "count=$(($# - 1))\n"
                    "mkdir -p \"$(dirname \"$dest\")\"\n"
                    "i=1\n"
                    "for src in \"$@\"; do\n"
                    "  [ $i -gt $count ] && break\n"
                    "  cp -f \"$src\" \"$dest\"\n"
                    "  # HMFS 不支持 chmod，设权限失败不阻断复制。\n"
                    "  if [ -n \"$mode\" ]; then\n"
                    "    if [ -d \"$dest\" ]; then\n"
                    "      chmod \"$mode\" \"$dest/${src##*/}\" 2>/dev/null || true\n"
                    "    else\n"
                    "      chmod \"$mode\" \"$dest\" 2>/dev/null || true\n"
                    "    fi\n"
                    "  fi\n"
                    "  i=$((i + 1))\n"
                    "done\n"
                )
        except Exception:  # noqa: BLE001 - 写 shim 失败不静默，关闭 fd 后上抛
            os.close(fd)
            raise

        # 2) chmod 容错 shim：HMFS 上 chmod 是装饰性元数据（chmod 能力为 0），
        #    libtool 二进制安装的 postinstall `chmod +x <ELF>` 在 HMFS 返回
        #    Permission denied 会令 make install 失败；这里尝试真实 chmod，失败
        #    不阻断（同 install shim 内 `|| true` 的容错口径）。
        chmod = os.path.join(shim_dir, "chmod")
        cfd = os.open(chmod, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o755)
        try:
            with os.fdopen(cfd, "w", encoding="utf-8", newline="\n") as f:
                f.write("#!/bin/sh\n")
                f.write("# HMFS chmod 容错：真实 chmod 失败（如 ELF 签名文件返回\n")
                f.write("# Permission denied）不阻断构建/安装。\n")
                f.write('command chmod "$@" 2>/dev/null || true\n')
        except Exception:  # noqa: BLE001
            os.close(cfd)
            raise

        # 前置到 PATH，使 make / make install 期间的 chmod 与任何依赖 PATH 的
        # 安装子进程都走容错 shim（环境在 build→package 同一 conan 进程内延续）。
        os.environ["PATH"] = shim_dir + os.pathsep + os.environ.get("PATH", "")
        return shim_dir

    def _redirect_install_to_shim(self, shim_install):
        # 改写已生成的 Makefile：`INSTALL = <.../install -c>` → `INSTALL = <shim>`。
        # INSTALL_DATA/INSTALL_PROGRAM 引用 ${INSTALL} 自动重算，libtool 的
        # install_prog 也取 $(INSTALL)，make install 全程走 shim。
        bf = self.build_folder
        for root, _, files in os.walk(bf):
            for name in files:
                if name != "Makefile":
                    continue
                mp = os.path.join(root, name)
                with open(mp, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                if "INSTALL =" not in content:
                    continue
                lines = []
                changed = False
                for line in content.splitlines(True):
                    stripped = line.lstrip()
                    if stripped.startswith("INSTALL = ") and "/install" in stripped:
                        indent = line[:len(line) - len(stripped)]
                        lines.append(f"{indent}INSTALL = {shim_install}\n")
                        changed = True
                    else:
                        lines.append(line)
                if changed:
                    with open(mp, "w", encoding="utf-8") as f:
                        f.writelines(lines)

    def _load_configure_args(self):
        try:
            return load_toolchain_args(self.generators_folder).get("configure_args")
        except Exception:
            return []

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # Autotools installs a convenience libtool archive; remove it.
        libdir = os.path.join(self.package_folder, "lib")
        la = os.path.join(libdir, "libxy.la")
        if os.path.isfile(la):
            os.remove(la)

    def package_info(self):
        self.cpp_info.libs = ["xy"]
        self.cpp_info.set_property("cmake_file_name", "xylib")
        self.cpp_info.set_property("cmake_target_name", "xylib::xylib")
        self.cpp_info.set_property("pkg_config_name", "xylib")
        self.cpp_info.requires = ["boost::boost", "zlib::zlib", "bzip2::bzip2"]
