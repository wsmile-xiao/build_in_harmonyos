#!/usr/bin/env python3
"""Conan recipe for libextractor 1.13 — 文件元数据（关键词）提取框架。

构建系统：Autotools（configure + make + make -C src check）。
插件由 libltdl 在运行时 dlopen，所以本包必须 shared=True —— 静态构建不产出
插件 .so，所有提取用例都会拿到 0 条元数据。
"""
import os

from conan import ConanFile
from conan.tools.files import (apply_conandata_patches, copy,
                              export_conandata_patches, get,
                              replace_in_file, rm, rmdir)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.microsoft import unix_path


class LibextractorConan(ConanFile):
    name = "libextractor"
    version = "1.13"
    description = ("Simple framework for extracting various kinds of metadata items "
                   "from files (documents, images, audio, video)")
    license = "GPL-3.0-or-later"
    homepage = "https://www.libextractor.org/"
    url = "https://www.gnu.org/software/libextractor/"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # configure 硬需求：libltdl（dlopen 插件）
        self.requires("libtool/2.5.4.1")
        # zlib 必须与 libtiff/4.7.2 的 pin 一致（1.3.1.1）；glib2 链（gsf/gmime/
        # gdk-pixbuf/gtk/gstreamer）会拉 zlib/1.3.1，override 统一到 1.3.1.1 消解
        # 双轨（组图实证 rc=0/43 包，CIW-2 PR 评论 id 943afda997）
        self.requires("zlib/1.3.1.1", override=True)
        # rpm 拟 zstd/1.5.7、libarchive 链 1.5.6，override 统一到 1.5.7
        self.requires("zstd/1.5.7", override=True)
        self.requires("bzip2/1.0.8")
        self.requires("giflib/6.1.3")
        self.requires("libjpeg-turbo/3.2.0")
        self.requires("libtiff/4.7.2")
        self.requires("libarchive/3.8.7")
        # —— rule4 整改（2026-09-27 主理-72）：启用已归档且 ohpcd 二进制已发布的
        # 可选抽取器依赖，把 09-24 FAIL 的 13 项未注册收敛到真不可用项 ——
        # flac 禁用留证（2026-09-28）：flac/1.5.0 编译链接过，test_flac 运行期取不到流元数据
        # （FAIL test_flac，-k 全量普查仅此一项）→ 按交接包先例列不可启用项。
        # self.requires("flac/1.5.0")                            # 解锁 test_flac
        self.requires("libogg/1.3.6.2", override=True)         # flac 拟 1.3.5 / libvorbis 拟 1.3.6 → 统一
        self.requires("libvorbis/1.3.7")                       # 解锁 test_ogg（vorbis 系）
        self.requires("libgsf/1.14.58.1")                      # 解锁 test_gsf
        self.requires("gstreamer/1.28.3")                      # 解锁 test_gstreamer
        self.requires("gtk/3.24.43")                           # 解锁 test_gtk + test_thumbnailgtk
        self.requires("gdk-pixbuf/2.44.6.1.1", override=True)  # gtk 拟 2.44.6.1 → 统一
        self.requires("gmime/3.2.15")                          # 解锁 test_html + test_mime
        self.requires("mp4v2/2.1.3.1")                         # 解锁 test_mp4
        # rpm/6.0.2 禁用留证（2026-09-28）：编译链接均过，test_rpm 运行期 rpm 插件对
        # 6.x API 取不到 rpmlib(*) 元数据（test_rpm FAIL）→ 按交接包先例列不可启用项。
        # 仍不启用（PR 正文"未执行测试"表逐项留证）：
        #   exiv2 —— 二进制已发布，但启用后 test_exiv2 运行期 EXIF 零产出（技术
        #   缺陷非依赖面，2 轮诊断未定位，启用即 make check 红）；
        #   libmidi —— 制品仓无同名配方；libolecf —— 无二进制（test_ole2）。

    def layout(self):
        # in-source 构建（与真机探索一致：configure/Makefile 同一目录树），
        # 这样 `make -C src check` 与 libtool 的插件 .libs 路径都和实测证据同源。
        basic_layout(self, src_folder=".", build_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def _shell(self):
        for candidate in ("/bin/sh", "/system/bin/sh"):
            if os.path.isfile(candidate):
                return candidate
        return "/bin/sh"

    def _triplet(self):
        arch = str(self.settings.arch)
        machine = {"armv8": "aarch64", "armv8.3": "aarch64", "armv7": "arm"}.get(arch, arch)
        return "{}-unknown-linux-gnu".format(machine)

    def _dep_dirs(self, attr):
        dirs = []
        for dep in self.dependencies.host.values():
            for entry in getattr(dep.cpp_info, attr):
                path = entry if os.path.isabs(entry) else \
                    os.path.join(dep.package_folder, entry)
                if path not in dirs:
                    dirs.append(path)
        return dirs

    def generate(self):
        shell = self._shell()
        tc = AutotoolsToolchain(self)
        # 设备无 texinfo/makeinfo：doc 段会递归执行 makeinfo 报 Error 127。
        # 用 fake makeinfo 产出空文件跳过文档生成（同 akku/guile 配方）。
        fake_bin = os.path.join(self.build_folder, "fake-bin")
        os.makedirs(fake_bin, exist_ok=True)
        fake_makeinfo = os.path.join(fake_bin, "makeinfo")
        with open(fake_makeinfo, "w") as fh:
            fh.write('#!/bin/sh\n'
                     'out=""\n'
                     'prev=""\n'
                     'for arg in "$@"; do\n'
                     '  if [ "$prev" = "-o" ]; then out="$arg"; fi\n'
                     '  prev="$arg"\n'
                     'done\n'
                     '[ -n "$out" ] && touch "$out"\n'
                     'exit 0\n')
        os.chmod(fake_makeinfo, 0o755)
        env = tc.environment()
        env.define("MAKEINFO", fake_makeinfo)
        env.append_path("PATH", fake_bin)
        # 设备/CI profile 的 [buildenv] 把 SHELL/CONFIG_SHELL 钉在 hnp bash，
        # autoconf 用它 re-exec 自己会在 HMDFS 构建目录 getcwd 失败（E386）。
        env.define("CONFIG_SHELL", shell)
        env.define("SHELL", shell)
        incs = self._dep_dirs("includedirs")
        libs = self._dep_dirs("libdirs")
        self.output.info("libextractor dep incs={}".format(incs))
        self.output.info("libextractor dep libs={}".format(libs))
        for lib in libs:
            # 插件 .so 在 make check 阶段由 ltdl dlopen，其依赖（libtiff 等）
            # 必须可在运行时找到；musl 忽略 DT_RUNPATH，只能靠 LD_LIBRARY_PATH。
            env.append_path("LD_LIBRARY_PATH", lib)
        # glib 系探测（libgsf/gmime/gtk/gdk-pixbuf/gstreamer 的 configure 检查）
        # 走 pkg-config：不导出 PKG_CONFIG_PATH 会静默探测失败 → 插件不注册
        # （rule4 复发）。conan 依赖的 .pc 在各自包内，逐个收集。
        pc_dirs = []
        for dep in self.dependencies.host.values():
            for sub in ("lib", "share"):
                p = os.path.join(dep.package_folder or "", sub, "pkgconfig")
                if os.path.isdir(p) and p not in pc_dirs:
                    pc_dirs.append(p)
        if pc_dirs:
            env.define("PKG_CONFIG_PATH", ":".join(pc_dirs))
        # configure 的头/库探测只读 CPPFLAGS/LDFLAGS（本包 pkg-config 仅用于 glib
        # 系探测，不参与 ltdl），必须在下面这个 env 里显式导出：tc.environment() 是
        # 即时快照，其后往 extra_cflags/extra_ldflags 追加的内容不会进来，
        # 探测会退化成搜 /usr/include 并报 "checking for ltdl.h... no"
        # （单变量实测见 knowledge/drafts/DRAFT-libextractor-1.13-autotools-env-define-dep-flags）。
        env.define("CPPFLAGS", " ".join(["-I{}".format(i) for i in incs]))
        env.define("LDFLAGS", " ".join(["-L{}".format(l) for l in libs]))
        tc.generate(env=env)

    def build(self):
        apply_conandata_patches(self)
        # E011/HMDFS：configure 的 umask 077 让 config.status 建不出 subs1.awk
        # （Permission denied）。configure 是 tarball 内生成文件，按 R6 就地改、
        # 不留 patches/。
        replace_in_file(self, os.path.join(self.source_folder, "configure"),
                        "umask 077", "umask 022", strict=False)
        shell = self._shell()
        triplet = self._triplet()
        # tarball 自带 build-aux/config.sub 不认 *-linux-ohos；设备与 CI worker
        # 都在 aarch64 真机上原生构建，--build 与 --host 同值即本机，configure
        # 不进 cross_compiling，AC_TRY_RUN 类探测才能正常工作。
        configure = unix_path(self, os.path.join(self.source_folder, "configure"))
        args = " ".join([
            "--build={}".format(triplet),
            "--host={}".format(triplet),
            "--prefix=/",
            "--disable-dependency-tracking",
            "--enable-shared" if self.options.shared else "--disable-shared",
            "--disable-static" if self.options.shared else "--enable-static",
        ])
        self.run('CONFIG_SHELL="{}" SHELL="{}" sh "{}" {}'.format(
            shell, shell, configure, args), env="conanbuild")
        autotools = Autotools(self)
        autotools.make(args=["-j2", "SHELL={}".format(shell)])
        # 上游测试真实执行（R51/审查硬规则）：src/main 与 src/plugins 两棵子树
        # 各有 TESTS 注册，顶层 check 还会递归进无 makeinfo 的 doc 段。
        try:
            autotools.make(target="check", args=["-C", "src", "-j2",
                                                 "SHELL={}".format(shell)])
        except Exception:
            for log in ("src/main/test-suite.log", "src/plugins/test-suite.log"):
                path = os.path.join(self.build_folder, log)
                if os.path.isfile(path):
                    with open(path, encoding="utf-8", errors="ignore") as fh:
                        self.output.warning("upstream check log {}:\n{}".format(
                            log, fh.read()[-4000:]))
            raise

    def package(self):
        autotools = Autotools(self)
        autotools.install(args=["SHELL=/bin/sh"])
        copy(self, "COPYING",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        rm(self, "*.la", self.package_folder, recursive=True)
        for res in ("man", "info", "locale"):
            rmdir(self, os.path.join(self.package_folder, "share", res))
            rmdir(self, os.path.join(self.package_folder, "res", res))
        rmdir(self, os.path.join(self.package_folder, "share",
                                 "libextractor"))

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "libextractor")
        self.cpp_info.libs = ["extractor"]
        self.cpp_info.bindirs = ["bin"]
        plugin_dir = os.path.join(self.package_folder, "lib", "libextractor")
        # 插件目录由 ltdl 运行时定位；打包后前缀不固定，显式声明最稳。
        self.runenv_info.define_path("LIBEXTRACTOR_PREFIX", plugin_dir)
        self.buildenv_info.define_path("LIBEXTRACTOR_PREFIX", plugin_dir)
