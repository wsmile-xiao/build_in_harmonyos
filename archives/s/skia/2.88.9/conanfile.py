import os
import shutil
import textwrap

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import build_jobs
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    mkdir,
    save,
)

required_conan_version = ">=2.0"


class SkiaConan(ConanFile):
    name = "skia"
    version = "2.88.9"
    # skia 产出静态库 libskia.a（complete static lib，已含全部第三方源码目标）+ 公共头。
    package_type = "static-library"
    description = (
        "Skia 2D graphics library: CPU rasterization core (core/effects/codecs/fonts/pdf) "
        "plus the Ganesh GL(GLES/EGL) backend, adapted to HarmonyOS PC (OHOS aarch64)."
    )
    license = "BSD-3-Clause"
    url = "https://github.com/mono/skia"
    homepage = "https://skia.org"
    topics = ("graphics", "2d", "rasterization", "skia", "gn", "ninja")

    settings = "os", "compiler", "build_type", "arch"

    # with_tests：是否额外构建上游测试二进制（dm + tests）。默认关 —— CI 只跑 conan create +
    # test_package，不运行上游单测；而 dm/tests 的编译+链接占整条流水线的大头，会顶到 CI 默认
    # 3600 s 构建超时。本地复现上游全量测试用：
    #   conan create . -o "&:with_tests=True"
    options = {"with_tests": [True, False]}
    default_options = {"with_tests": False}

    # 产品件（CPU 光栅化核心面「零裁剪」：core/effects/codecs/fonts/pdf + Ganesh GL 后端全部编入）
    _PRODUCT_TARGETS = ["skia"]

    # 上游测试二进制（with_tests=True 时构建；宿主侧实测见 notes.md §5）
    _TEST_TARGETS = ["dm", "tests"]

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        # CI worker 的 PATH 不含 hnp/bin，裸名探 ninja 会失败；用 tool_requires 提供绝对路径。
        self.tool_requires("ninja/1.13.2")

    def validate(self):
        if self.settings.os != "OHOS":
            raise ConanInvalidConfiguration(
                "skia 2.88.9 recipe 仅支持 OHOS (HarmonyOS PC / aarch64)"
            )

    # ------------------------------------------------------------------ source
    def _filename(self, name, fmt, explicit=""):
        """codeload 的 URL 末段是 SHA（无扩展名），必须显式给出带扩展名的文件名，
        否则 conan 的 get() 无法识别归档格式。"""
        if explicit:
            return explicit
        ext = {"tar.gz": ".tar.gz", "zip": ".zip", "tgz": ".tgz"}.get(fmt, "")
        return "".join(c if c.isalnum() or c in "._-" else "_" for c in name) + ext

    def source(self):
        src = self.conan_data["sources"]
        get(self, url=src["url"], sha256=src.get("sha256", ""),
            filename=self._filename("skia", src.get("tar_format", "tar.gz"),
                                    src.get("filename", "")),
            destination=self.source_folder, strip_root=True)

        # GN 工具链：skia 的 bin/fetch-gn 走 chrome-infra-packages（OHOS 不可达/预编译为 x86），
        # 故从 gn 源码自举（与 perfetto 先例同一 revision）。
        gn = self.conan_data["build_tools"]["gn"]
        get(self, url=gn["url"], sha256=gn.get("sha256", ""),
            filename=self._filename("gn", gn.get("tar_format", "tar.gz"),
                                    gn.get("filename", "")),
            destination=os.path.join(self.source_folder, "_gn"), strip_root=True)

        # ICU 头补齐（见 conandata.yml 说明 + patches/0002）
        icu = self.conan_data["icu_headers"]
        icu_tmp = os.path.join(self.source_folder, "_icu")
        get(self, url=icu["url"], sha256=icu.get("sha256", ""),
            filename=self._filename("icu", icu.get("tar_format", "tar.gz"),
                                    icu.get("filename", "")),
            destination=icu_tmp, strip_root=True)
        for part, sub in (("common", icu["common_dir"]), ("i18n", icu["i18n_dir"])):
            copy(self, "*", src=os.path.join(icu_tmp, sub),
                 dst=os.path.join(self.source_folder, "third_party", "icu-headers", part, "unicode"))

        # third_party/externals/*（DEPS 的第三方源码，全部 GitHub 镜像 + sha256 pin）
        for dep in self.conan_data["externals"]:
            dst = os.path.join(self.source_folder, "third_party", "externals", dep["name"])
            mkdir(self, dst)
            get(self, url=dep["url"], sha256=dep.get("sha256", ""),
                filename=self._filename(dep["name"], dep.get("tar_format", "tar.gz"),
                                        dep.get("filename", "")),
                destination=dst, strip_root=dep.get("strip_root", True))

        apply_conandata_patches(self)

    # ------------------------------------------------------------------ helpers
    def _toolchain(self):
        """返回 (cc, cxx, ar) 绝对路径，取自 profile 的 compiler_executables。"""
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c") or shutil.which("clang") or "clang"
        cxx = compilers.get("cpp") or shutil.which("clang++") or "clang++"
        # OHOS python subprocess 不做 PATH 搜索，gn 的 ar 必须给绝对路径。
        ar = os.path.join(os.path.dirname(cc), "llvm-ar")
        if not os.path.exists(ar):
            ar = shutil.which("llvm-ar") or shutil.which("ar") or "ar"
        return cc, cxx, ar

    def _ninja(self):
        ninja = os.path.join(self.dependencies.build["ninja"].cpp_info.bindir, "ninja")
        return ninja if os.path.exists(ninja) else (shutil.which("ninja") or "ninja")

    def _jobs(self, cap):
        """ninja 并发上限。OHOS worker 上进程创建走 posix_spawn，并发过高会
        `ninja: fatal: posix_spawn: Resource temporarily unavailable`（资源型 EAGAIN，
        CI 实测于 gn 自举步）。统一封顶，避免自造过载（本机 8 核不复现）。"""
        return min(build_jobs(self), cap)

    def _gn_args(self):
        cc, cxx, ar = self._toolchain()
        # CPU 光栅化核心面零裁剪；GPU 后端保留（Ganesh GL，接口走 OHOS EGL）。
        # skia_use_egl=true：OHOS sysroot 提供 EGL/GLES 头 + libEGL.so，是唯一在无 X11 的
        # OHOS 上可构建的 GL 原生接口（glx 分支需要 X11 头，不可用）。
        return " ".join(
            [
                "is_debug=false",
                "is_official_build=false",
                f'cc="{cc}"',
                f'cxx="{cxx}"',
                f'ar="{ar}"',
                "skia_enable_gpu=true",
                "skia_use_gl=true",
                "skia_use_egl=true",
                "skia_use_x11=false",
                "skia_use_fontconfig=false",
                # PDF 字体子集走 harfbuzz（skia 自带 hb-subset），避开 sfntly 对 ICU C++ 头的依赖
                "skia_pdf_subset_harfbuzz=true",
                # OHOS 无系统 freetype，显式关闭上游 Linux 的 system_freetype2 默认，改从源码编
                "skia_use_system_freetype2=false",
                "skia_use_system_zlib=false",
                "skia_use_system_libpng=false",
                "skia_use_system_libjpeg_turbo=false",
                "skia_use_system_libwebp=false",
                "skia_use_system_harfbuzz=false",
                "skia_use_system_expat=false",
                # OHOS sysroot 自带 libicu.so（ICU 72.1），头由 patches/0002 补齐
                "skia_use_system_icu=true",
                # musl 无 __WORDSIZE（glibc <bits/wordsize.h> 专有）；dng_sdk / libjpeg-turbo 用它做 64 位判定。
                # OHOS 系统字体在 /system/fonts（上游默认 /usr/share/fonts 在该平台不存在）：
                # 走构建期 -D 注入（源文件 SkFontMgr_custom_directory_factory.cpp 有
                # #ifndef SK_FONT_FILE_PREFIX 守卫），避免在 patches/ 中引入平台条件编译宏（R8）。
                'extra_cflags=["-D__WORDSIZE=64", "-DSK_FONT_FILE_PREFIX=\\"/system/fonts/\\""]',
            ]
        )

    # ------------------------------------------------------------------- build
    def generate(self):
        cc, cxx, ar = self._toolchain()
        env = Environment()
        env.define("CC", cc)
        env.define("CXX", cxx)
        env.define("AR", ar)
        env.vars(self).save_script("conanbuild_ccenv")

    def build(self):
        ninja = self._ninja()
        envs = ["conanbuild", "conanbuild_ccenv"]

        # 1) 自举 GN（OHOS clang 链接期自动加 .codesign，产物可直接执行）
        gn_dir = os.path.join(self.source_folder, "_gn")
        # 显式 --platform=linux：CI 的 python3 报告 sys.platform=='ohos'，而 gn 的
        # build/gen.py 只识别 linux/darwin/...，其模板字典会 KeyError: 'ohos'。
        # OHOS 宿主即 linux-like，此参数使 CI 与本机自举行为完全一致。
        self.run("python3 build/gen.py --no-last-commit-position --platform=linux",
                 cwd=gn_dir, env=envs)
        # gen.py 无 git 元数据时不会生成该头，需手工补（否则 scope_per_file_provider.cc 报错）
        save(
            self,
            os.path.join(gn_dir, "out", "last_commit_position.h"),
            textwrap.dedent(
                """\
                // Generated by build/gen.py.
                #ifndef OUT_LAST_COMMIT_POSITION_H_
                #define OUT_LAST_COMMIT_POSITION_H_
                #define LAST_COMMIT_POSITION_NUM 0
                #define LAST_COMMIT_POSITION "0 (unknown)"
                #endif  // OUT_LAST_COMMIT_POSITION_H_
                """
            ),
        )
        # 只建 gn 本体（不建 gn_unittests，省 CI 时间）；限并发避免 posix_spawn EAGAIN
        self.run(f'"{ninja}" -C out -j{self._jobs(8)} gn', cwd=gn_dir, env=envs)
        gn = os.path.join(gn_dir, "out", "gn")

        # skia 的 gen/skia.h action 通过 //bin/gn 调用 gn desc（上游由 bin/fetch-gn 下载
        # 该二进制）。把自举出的 gn 放到源码树内约定位置。
        bin_gn = os.path.join(self.source_folder, "bin", "gn")
        shutil.copy2(gn, bin_gn)
        os.chmod(bin_gn, 0o755)

        # 2) 生成 skia 构建文件（--args 用单引号包裹，避免 shell 吞掉内层 ""）
        # --script-executable=python3：gn 的 exec_script（//gn/is_clang.py、gn/checkpath.py 等）
        # 默认执行裸名 `python`；CI worker 的 PATH 只有 `python3`（/data/app/bin/python3），
        # 裸 `python` 会 rc=127（“Returned 127”）。显式指定解释器，消除该跨环境差异。
        self.run(f"\"{gn}\" gen out/ohos --script-executable=python3 '--args={self._gn_args()}'",
                 cwd=self.source_folder, env=envs)

        # 3) 构建：产品件（零裁剪）+ 可选上游测试二进制（默认不建，见 with_tests 说明）
        jobs = self._jobs(16)
        targets = list(self._PRODUCT_TARGETS)
        if self.options.with_tests:
            targets += self._TEST_TARGETS
        self.run(f'"{ninja}" -C out/ohos -j{jobs} ' + " ".join(targets),
                 cwd=self.source_folder, env=envs)

    # ----------------------------------------------------------------- package
    def package(self):
        od = os.path.join(self.build_folder, "out", "ohos")
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

        copy(self, "*.a", src=od, dst=os.path.join(self.package_folder, "lib"))

        # 公共头保持 skia 源码根的相对布局（skia 头内部以 "include/core/..." 互相引用），
        # 故把源码 include/ 放到包的 include/ 下，并在 package_info 里以包根为 include 根。
        copy(self, "*", src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include", "include"),
             keep_path=True)
        for mod in ("svg", "skottie", "skshaper", "skparagraph", "skresources"):
            mod_inc = os.path.join(self.source_folder, "modules", mod, "include")
            if os.path.isdir(mod_inc):
                copy(self, "*", src=mod_inc,
                     dst=os.path.join(self.package_folder, "include", "modules", mod, "include"),
                     keep_path=True)

    def package_info(self):
        # skia 的公共头以 "include/core/SkX.h" / "modules/svg/include/SkY.h" 形式互相引用，
        # 因此 include 根必须是「类 skia 源码根」目录（= 包内 include/）。
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.libs = ["skia"]
        # libskia.a 为 complete static lib（已含 freetype/harfbuzz/png/jpeg/webp/zlib/expat/… 目标对象），
        # 消费者只需补平台库：
        #   - EGL/GLESv2：GPU 后端（Ganesh GL）的 EGL 原生接口对 GL 符号是直接引用
        #   - icu：文本路径（harfbuzz 的 hb-icu / SkShaper）在 OHOS 上用系统 libicu.so
        self.cpp_info.system_libs = ["pthread", "dl", "m", "EGL", "GLESv2", "icu"]
