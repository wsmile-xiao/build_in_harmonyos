#!/usr/bin/env python3
"""Conan recipe — libdvdnav 7.0.0 (meson).

libdvdnav 是 VideoLAN 的 DVD 导航库，提供 DVD 菜单/多角度/交互回放的 API。
上游使用 meson 构建，依赖 libdvdread >=6.0.0（meson fallback 子项目），
可选链接 libdvdcss 以支持加密 DVD。

本配方策略（与官方 .gitlab-ci.yml 一致）：
- meson 构建，Conan MesonToolchain 注入 OHOS 工具链
- libdvdread 不在仓库归档中，按官方 CI 做法 vendoring 为
  meson subprojects/libdvdread 源码树（conandata.yml 额外 sources 条目）
- wrap_mode=nodownload，所有外部源由 conandata 提供
- 默认 shared=False（R26 系统同名库静态），可选项 shared/fPIC
- 关闭 dvdcss 直链（dvdread 通过 dlfcn 动态探测，OHOS 上 dlopen 可用）

上游无测试套件（.gitlab-ci.yml 仅 meson compile，无 meson test；
tarball 仅含 examples/ 与 doc/，无 test/）。test_package 自建真实
调用 libdvdnav API 的最小验证程序。
"""
import os

from conan import ConanFile
from conan.tools.files import (
    get,
    apply_conandata_patches,
    export_conandata_patches,
    copy,
    save,
)
from conan.errors import ConanInvalidConfiguration
from conan.tools.meson import MesonToolchain
from conan.tools.layout import basic_layout


class LibdvdnavConan(ConanFile):
    name = "libdvdnav"
    version = "7.0.0"
    description = "DVD navigation library (menus, multiangle, interactive playback)"
    license = "GPL-2.0-or-later"
    homepage = "https://www.videolan.org/developers/libdvdnav.html"
    url = ""  # CI fills this

    # musl off64_t 补丁内容内联在配方里——连续多轮真机预检证实 Conan copy/export 的补丁落盘路径
    # 不可预测（e/、e/patches/、recipe_folder basename 均错），无法在 build() 阶段稳定定位补丁文件。
    # 故不依赖 Conan copy/export，直接把补丁内容内联为类常量，build() 里用 save() 写盘再 patch。
    # 补丁路径写成相对于 subprojects/libdvdread/ 根（a/src/dvdread/...），patch -p1 在该子目录应用。
    _MUSL_OFF64_T_PATCH = """\
--- a/src/dvdread/dvd_filesystem.h
+++ b/src/dvdread/dvd_filesystem.h
@@ -39,6 +39,8 @@ typedef __off64_t off64_t;
 #elif defined(__APPLE__) || defined(__FreeBSD__) || defined(__OpenBSD__) || defined(__NetBSD__) || defined(__DragonFly__)
 /* off_t is already 64 bit here so off64_t is not provided. */
 typedef off_t off64_t;
+#else
+typedef off_t off64_t;
 #endif

 #define DVDREAD_NAME_MAX 255
"""

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_dvdcss": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_dvdcss": False,
    }

    def export_sources(self):
        # 补丁不以独立 .patch 文件导出——conanfile.py 的 build() 方法用内联类常量
        # _MUSL_OFF64_T_PATCH + save() + patch -p1 直接打到编译副本，从不读取 patches/ 下文件。
        # 故本方法不再 export_conandata_patches 或 copy 补丁文件，避免导出死代码。
        pass

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        # 纯 C 库
        self.settings.rm_safe("compiler.libcxx")
        self.settings.rm_safe("compiler.cppstd")

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        # 主源码 libdvdnav-7.0.0
        get(self, **self.conan_data["sources"]["libdvdnav"], strip_root=True)
        # vendored libdvdread 子项目源码（官方 .gitlab-ci.yml：
        # git clone ... subprojects/libdvdread），解到 subprojects/libdvdread/
        sub_dir = os.path.join(self.source_folder, "subprojects", "libdvdread")
        get(
            self,
            **self.conan_data["sources"]["libdvdread"],
            strip_root=True,
            destination=sub_dir,
        )
        # musl off64_t 移植补丁不以 apply_conandata_patches(self) 在 source() 阶段应用：
        # conandata.yml 的 patches 肂用非标准嵌套键 "libdvdread"（vendored 子项目名），
        # 而 Conan apply_conandata_patches 按包版本号匹配 patches 键，"libdvdread" 不匹配
        # 任何包版本——该调用是静默空操作，不应用任何补丁（连续多轮真机日志证实）。
        # 补丁实际由 build() 方法内联类常量 _MUSL_OFF64_T_PATCH + save() + patch -p1 直接打到
        # self.source_folder/subprojects/libdvdread/ 编译副本（build 阶段 = b/src），详见该方法注释。
        # vendored meson 构建工具源码：hmbs 预检真机 HMBS_PYTHON3 的 site-packages 无 mesonbuild，
        # 解压 meson 1.11.2 源码到 source_folder/meson-vendor/，build() 时把该目录前置 PYTHONPATH。
        mv = os.path.join(self.source_folder, "meson-vendor")
        get(
            self,
            **self.conan_data["sources"]["meson"],
            strip_root=True,
            destination=mv,
        )

    # 真机 meson 嫑本运行所需前缀（directx-headers/facad notes 已验证）
    _MESON_SITE = "/storage/Users/currentUser/usr/local/lib/python3.12/site-packages"
    _PY_HOME = "/data/service/hnp/python.org/python_3.12"
    _PY_LIB = "/data/service/hnp/python.org/python_3.12/lib"

    def _meson_cmd(self, meson_argv):
        # hmbs 预检真机 HMBS_PYTHON3（3.12.9）的 site-packages 无 mesonbuild（诊断已证实），
        # Conan self.run(env=list) 设的 PYTHONPATH 未传到子进程（sys.path 不含它）。
        # 故绕过 PYTHONPATH：用 `python3 -c` 脚本在进程内 sys.path.insert(0, vendored meson)，
        # 再调 mesonmain.main()。mesonmain.main() 无参（读 sys.argv），故 argv 注入 sys.argv。
        # sys.argv[0] 是程序名占位（meson 跳过），真参数从 argv[1] 起——故前置 "meson" 占位。
        # argv 直接编成 Python list 字面量（json.dumps 产生合法 list literal）。
        # 脚本整体用单引号包成一个 shell 参数（含空格，不引号会被 sh 按空格拆成多参数）。
        py = os.environ.get("HMBS_PYTHON3") or "python3"
        mv = os.path.join(self.source_folder, "meson-vendor")
        import json as _json
        # 前置 "meson" 占 argv[0] 程序名位，meson_argv 是真参数（argv[1] 起）
        argv_lit = _json.dumps(["meson"] + list(meson_argv))
        mv_lit = _json.dumps(mv)  # 合法 Python 字符串字面量："..."
        script = (
            "import sys;"
            f"sys.path.insert(0,{mv_lit});"
            f"sys.argv={argv_lit};"
            "from mesonbuild import mesonmain;"
            "rc=mesonmain.main();"
            "sys.exit(rc or 0)"
        )
        # 用单引号包住脚本（脚本内只有双引号字面量，无单引号，故单引号安全）
        return py, ["-c", f"'{script}'"]

    def _meson_env(self, extra=None):
        # Conan 2.x self.run(env=...) 要 list（["KEY=VALUE", ...]），不是 dict。
        # PYTHONPATH 前置 vendored meson 源码目录（含 mesonbuild/ 包），让 HMBS_PYTHON3 能导入。
        env = {"PATH": os.environ.get("PATH", "")}
        mv = os.path.join(self.source_folder, "meson-vendor")
        pp = os.environ.get("PYTHONPATH", "")
        env["PYTHONPATH"] = (mv + ":" + pp).strip(":") if pp else mv
        # PYTHONHOME：python3.12 需要（facad notes #28）
        env["PYTHONHOME"] = self._PY_HOME
        # LD_LIBRARY_PATH：libpython3.12.so.1.0 缺失修复（facad notes #27），前置真机 lib
        ll = os.environ.get("LD_LIBRARY_PATH", "")
        env["LD_LIBRARY_PATH"] = (self._PY_LIB + ":" + ll).strip(":")
        # 保留真机注入的工具路径变量，供 ninja 调 meson 内部命令时用
        for k in ("HMBS_CMAKE", "HMBS_MAKE", "HMBS_NINJA", "HMBS_PYTHON3"):
            if k in os.environ:
                env[k] = os.environ[k]
        if extra:
            env.update(extra)
        return [f"{k}={v}" for k, v in env.items()]

    def generate(self):
        tc = MesonToolchain(self)
        # 禁止 meson 联网下载 wrap 子项目，所有源码已 vendoring
        tc.project_options["wrap_mode"] = "nodownload"
        # 不构建示例/文档（避免额外依赖与无关产物）
        tc.project_options["enable_examples"] = "false"
        tc.project_options["enable_docs"] = "false"
        # R26：系统同名库默认静态
        if self.options.shared:
            tc.project_options["default_library"] = "shared"
        else:
            tc.project_options["default_library"] = "static"
        # 注：libdvdnav 顶层 meson_options.txt 只有 enable_docs/enable_examples，
        # 无 libdvdcss（它是 vendored libdvdread 子项目的选项）。
        # 顶层 meson.build 用 dependency('dvdread', fallback: 'libdvdread') 调子项目，
        # libdvdread 默认用 dlfcn 动态探测 dvdcss（OHOS 有 dlopen），无需在配方层显式禁用。
        tc.generate()
        # 静态库归档器：真机 PATH 无 ar/llvm-ar，meson 探测失败（default_library=static 需 ar）。
        # 写补充 native file 指定 ar=llvm-ar（clang 工具链同目录），build() 时叠加传给 meson setup。
        ar_nf = os.path.join(self.generators_folder, "conan_meson_ar_native.ini")
        with open(ar_nf, "w", encoding="utf-8") as f:
            f.write("[binaries]\n")
            f.write("ar = '/data/service/hnp/bin/llvm-ar'\n")
        self._ar_native_file = ar_nf

    def build(self):
        # Conan 在 build() 阶段把 source() 阶段已补丁的源码 copy 到 build folder 的新源码副本
        # （真机日志 "Copying sources to build folder" + meson "Source dir: .../b/src"），
        # 该副本未带补丁。连续多轮试错证实 Conan copy/export 的补丁落盘路径不可预测
        # （e/、e/patches/、recipe_folder basename 均错），无法在 build() 阶段稳定定位补丁文件。
        # 故放弃 Conan copy/export 机制，直接把 musl off64_t 补丁内容内联为类常量 _MUSL_OFF64_T_PATCH，
        # build() 里用 save() 写盘到 generators folder 的临时文件，再用 patch -p1 打到
        # self.source_folder 的 subprojects/libdvdread/ 子目录（build 阶段 = b/src 编译副本）。
        # 补丁路径写成相对于 subprojects/libdvdread/ 根（a/src/dvdread/...），patch 在该子目录应用。
        sub_dir = os.path.join(self.source_folder, "subprojects", "libdvdread")
        pf = os.path.join(self.generators_folder, "libdvdread-7.1.1-musl-off64_t.patch")
        save(self, pf, self._MUSL_OFF64_T_PATCH)
        self.run(f'cd "{sub_dir}" && patch -p1 < "{pf}"')
        # 不用 Conan Meson 工具（裸名 `meson` 不在真机 PATH），
        # 改用 vendored meson 通过 `python3 -c` 脚本调 mesonmain.main(argv)，
        # 与 MesonToolchain 生成的 native file 配合。
        env = self._meson_env()
        nf = os.path.join(self.generators_folder, "conan_meson_native.ini")
        bdir = self.build_folder
        sdir = self.source_folder
        # configure（meson setup <source_dir> <build_dir> [options]）
        # 显式传源目录，避免 meson 把 cwd（build 文件夹）当源目录与 build_dir 冲突。
        # 传两个 native file：Conan 生成的 + 补充的 ar 配置（meson 支持多 native file 叠加）。
        native_args = ["--native-file", nf]
        ar_nf = getattr(self, "_ar_native_file", None)
        if ar_nf and os.path.isfile(ar_nf):
            native_args += ["--native-file", ar_nf]
        py, margs = self._meson_cmd(["setup", sdir, bdir, "--prefix=/"] + native_args)
        self.run(f'"{py}" {" ".join(margs)}', env=env)
        # build（ninja，真机注入 HMBS_NINJA 绝对路径）
        ninja = os.environ.get("HMBS_NINJA") or "ninja"
        self.run(f'"{ninja}" -C "{bdir}" -j1', env=env)

    def package(self):
        # meson install（DESTDIR staging 到 package_folder）。
        # 经验：Conan self.run(env=...) 注入的 DESTDIR 环境变量未可靠到达 vendored meson install
        # 子进程（真机日志证实 meson install 仍尝试写 /lib/libdvdread.a，触发只读文件系统 Errno 30）。
        # 上游 glib 2.84.0 配方惯用做法：传 --destdir 为 CLI 标志（minstall.py 优先读 option，
        # 不依赖 os.environ）。配合 setup 阶段的 --prefix=/，安装产物落到 package_folder/lib/。
        bdir = self.build_folder
        py, margs = self._meson_cmd(
            ["install", "-C", bdir, "--no-rebuild", "--destdir", self.package_folder]
        )
        self.run(f'"{py}" {" ".join(margs)}', env=self._meson_env())
        # 拷贝版权/说明文档
        for fn in ("AUTHORS", "COPYING", "ChangeLog", "README.md", "TODO"):
            src = os.path.join(self.source_folder, fn)
            if os.path.isfile(src):
                copy(self, fn, src, os.path.join(self.package_folder, "share", "doc", "libdvdnav"))

    def package_info(self):
        # libdvdnav.a 静态依赖 vendored libdvdread.a 的符号（DVDCloseFile/ifoClose/ifoOpenVMGI 等，
        # 均由 libdvdread 源码提供）。真机日志证实两个 .a 均装到 package_folder/lib/。
        # 必须把 "dvdread" 声明为 cpp_info.libs 的一员，CMakeDeps 生成的
        # libdvdnav::libdvdnav 目标链接行才会带上 libdvdread.a，test_package 链接才不报 undefined symbol。
        self.cpp_info.libs = ["dvdnav", "dvdread"]
        # libdvdnav 公开头装在 include/dvdnav/，libdvdread 公开头装在 include/dvdread/
        self.cpp_info.includedirs = ["include", "include/dvdnav", "include/dvdread"]
        # 链接系统线程库（POSIX）
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]
        # pkg-config / cmake 名
        self.cpp_info.set_property("pkg_config_name", "dvdnav")
        self.cpp_info.set_property("cmake_file_name", "libdvdnav")
        self.cpp_info.set_property("cmake_target_name", "libdvdnav::libdvdnav")
