#!/usr/bin/env python3
"""Conan recipe — libtiff 4.7.0 (cmake).

TIFF image format library. Source: https://gitlab.com/libtiff/libtiff (tag v4.7.0).
构建方式与 4.7.2 归档同法：自发现 ohos.toolchain.cmake + 裸 cmake，绕开
conan_toolchain（os=OHOS 下它把 CMAKE_SYSTEM_NAME 映射成 cmake 不认的值，ML-0035）。
"""
import glob as _glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class LibtiffConan(ConanFile):
    name = "libtiff"
    version = "4.7.0"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # zlib 必须 1.3.1.1（-fPIC 静态）：链进 libtiff.so，用 1.3.1 会 R_AARCH64 relocation。
        self.requires("zlib/1.3.1.1")
        self.requires("libdeflate/1.25")
        self.requires("libjpeg-turbo/3.2.0")
        self.requires("zstd/1.5.7")
        self.requires("libwebp/1.6.0")
        self.requires("lerc/4.1.1")
        self.requires("jbigkit/2.1")
        self.requires("xz/5.6.2")

    def layout(self):
        # conan cmake_layout；build() 内用独立 build-ohos 子目录手跑 cmake
        cmake_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _ohos_toolchain(self):
        # 自发现 OHOS NDK 的 ohos.toolchain.cmake（① profile [conf] user_toolchain ② 环境 OHOS_NDK_HOME
        # ③ glob 设备/CI 的 SDK 布局），不依赖 CI profile host 段。
        ut = self.conf.get("tools.cmake.cmaketoolchain:user_toolchain", default=[], check_type=list)
        ndk = os.environ.get("OHOS_NDK_HOME", "")
        for _c in list(ut) + ([os.path.join(ndk, "build/cmake/ohos.toolchain.cmake")] if ndk else []):
            if _c and os.path.isfile(_c):
                return _c
        _g = sorted(_glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/build/cmake/ohos.toolchain.cmake"))
        if _g:
            return _g[-1]
        raise ConanInvalidConfiguration(
            "找不到 ohos.toolchain.cmake：设 OHOS_NDK_HOME 或 profile [conf] user_toolchain")

    def _cmake_defs(self, with_tests):
        """公共 cmake 配置：主构建（with_tests=False）与上游测试构建（True）共用。"""
        toolchain = self._ohos_toolchain()
        src = os.path.join(self.source_folder, "")
        defs = [
            '-DCMAKE_TOOLCHAIN_FILE="{}"'.format(toolchain),
            "-DOHOS_ARCH=arm64-v8a",
            "-DCMAKE_BUILD_TYPE={}".format(self.settings.build_type),
            "-DCMAKE_INSTALL_LIBDIR=lib",           # ohos.toolchain 64 位默认装 lib64/，须改回 lib
            "-DBUILD_SHARED_LIBS=ON",
        ]
        defs.append("-Dzlib=ON")
        defs.append("-Dlibdeflate=ON")
        defs.append("-Djpeg=ON")
        defs.append("-Dzstd=ON")
        defs.append("-Dwebp=ON")
        defs.append("-Dlerc=ON")
        defs.append("-Djbig=ON")
        defs.append("-Dlzma=ON")
        defs.append("-Dtiff-tools=OFF")
        defs.append("-Dtiff-tests={}".format("ON" if with_tests else "OFF"))
        defs.append("-Dtiff-docs=OFF")
        defs.append("-Dtiff-contrib=OFF")
        defs.append("-Dtiff-opengl=OFF")
        defs.append("-Dcxx=OFF")              # 4.7.0 选项名是 cxx（4.7.2 才改叫 tiff-cxx），纯 C 库不建 libtiffxx
        # 依赖接线：libtiff 全用自带 FindXxx 模块（find_path/find_library）+ 标准 FindZLIB。JPEG 无 CONFIG
        # 时回退 FindJPEG。交叉链 FIND_ROOT_PATH_MODE=ONLY 覆盖命令行 → 直接预设各模块的 find 缓存变量
        # （<pkg>/include + 实际 lib 文件）即绕过搜索（已设的 cache 变量 find_* 不再搜）。
        _wire = [
            # (conan 依赖, INCLUDE 变量, [LIBRARY 变量...], [lib 文件候选（优先 .so，回退 .a）])
            ("zlib",          "ZLIB_INCLUDE_DIR",    ["ZLIB_LIBRARY"],                                ["libz.a", "libz.so"]),
            ("libdeflate",    "Deflate_INCLUDE_DIR", ["Deflate_LIBRARY", "Deflate_LIBRARY_RELEASE"],  ["libdeflate.so", "libdeflate.a"]),
            ("libjpeg-turbo", "JPEG_INCLUDE_DIR",    ["JPEG_LIBRARY"],                                ["libjpeg.so", "libjpeg.a"]),
            ("zstd",          "ZSTD_INCLUDE_DIR",    ["ZSTD_LIBRARY", "ZSTD_LIBRARY_RELEASE"],        ["libzstd.so", "libzstd.a"]),
            ("libwebp",       "WebP_INCLUDE_DIR",    ["WebP_LIBRARY", "WebP_LIBRARY_RELEASE"],        ["libwebp.so", "libwebp.a"]),
            ("lerc",          "LERC_INCLUDE_DIR",    ["LERC_LIBRARY"],                                ["libLerc.so", "libLerc.a"]),
            ("jbigkit",       "JBIG_INCLUDE_DIR",    ["JBIG_LIBRARY", "JBIG_LIBRARY_RELEASE"],        ["libjbig.a", "libjbig.so"]),
            ("xz",            "LIBLZMA_INCLUDE_DIR", ["LIBLZMA_LIBRARY", "LIBLZMA_LIBRARY_RELEASE"],  ["liblzma.so", "liblzma.a"]),
        ]
        _ldirs = []
        for _dep, _incv, _libvs, _names in _wire:
            _pkg = self.dependencies[_dep].package_folder
            defs.append('-D{}="{}"'.format(_incv, os.path.join(_pkg, "include")))
            _lp = next((h for n in _names for h in _glob.glob(os.path.join(_pkg, "lib", n))),
                       os.path.join(_pkg, "lib", _names[0]))
            for _lv in _libvs:
                defs.append('-D{}="{}"'.format(_lv, _lp))
            _ldirs.append(os.path.join(_pkg, "lib"))
        # 链接 libtiff.so 会牵出各依赖 .so 的传递 NEEDED（lerc 的 libc++_shared 等）→ 链接期加 -L + -rpath-link。
        os.environ["LDFLAGS"] = " ".join("-L{0} -Wl,-rpath-link,{0}".format(d) for d in _ldirs) + " " + os.environ.get("LDFLAGS", "")
        return src, defs

    def build(self):
        apply_conandata_patches(self)
        # ── 主构建：产物包（8 后端全开，不含测试） ──
        src, defs = self._cmake_defs(with_tests=False)
        bdir = os.path.join(self.build_folder, "build-ohos")
        self.run('cmake -B "{}" -S "{}" {}'.format(bdir, src, " ".join(defs)))
        self.run('cmake --build "{}"'.format(bdir))
        # ── 上游测试构建+实跑（rule4：上游 C 测试程序子集真实执行，非仅 test_package 烟测） ──
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        """tiff-tests=ON 构建 23 个 C 测试程序（实际按条件编译出可运行子集）并 ctest 实跑。

        上游 test/ 的 88 个 .sh 集成脚本依赖 tiff-tools 二进制 + images/ 图像集做转换比对
        （tiff-tools=OFF 不构建），C 测试程序为纯库级测试可独立运行。此处只实跑 C 程序子集，
        .sh 类的逐项归因见 PR 正文与 reports/upstream-tests.log。
        """
        src, defs = self._cmake_defs(with_tests=True)
        tbdir = os.path.join(self.build_folder, "build-ohos-tests")
        self.run('cmake -B "{}" -S "{}" {}'.format(tbdir, src, " ".join(defs)))
        # 只构建测试目标（含 libtiff 本体），不 install
        self.run('cmake --build "{}"'.format(tbdir))
        # ctest 实跑（TiffTest.cmake 包装：STDOUT_COMMAND 模式，纯库级断言）
        # LD_LIBRARY_PATH 补系统目录：lerc 依赖 libc++_shared.so（/system/lib64）
        _env = dict(os.environ)
        _env["LD_LIBRARY_PATH"] = "/system/lib64" + (
            ":" + _env["LD_LIBRARY_PATH"] if _env.get("LD_LIBRARY_PATH") else "")
        import subprocess
        r = subprocess.run(
            ["ctest", "--output-on-failure"],
            cwd=tbdir, env=_env, capture_output=True, text=True, timeout=3600)
        log_path = os.path.join(self.build_folder, "upstream-tests.log")
        with open(log_path, "w", encoding="utf-8") as f:
            f.write("$ ctest --output-on-failure\n")
            f.write(r.stdout or "")
            if r.stderr:
                f.write("\n[stderr]\n")
                f.write(r.stderr)
        if r.returncode != 0:
            raise ConanInvalidConfiguration(
                "上游 C 测试子集 ctest 失败（rc={}），详见 {}".format(r.returncode, log_path))
        # 提取通过率摘要行打到 conan 日志（CI 可见）
        tail = "\n".join((r.stdout or "").strip().splitlines()[-6:])
        self.output.info("UPSTREAM_TESTS_SUMMARY:\n{}".format(tail))

    def package(self):
        bdir = os.path.join(self.build_folder, "build-ohos")
        self.run('cmake --install "{}" --prefix "{}"'.format(bdir, self.package_folder))
        self._sign_shared_libs()

    def _sign_shared_libs(self):
        # 鸿蒙 PC 对 dlopen 的 .so 校验代码签名：构建若在链接后改动 .so（如 zipfs 尾拼）会破坏链接器自签。
        # 剥旧 .codesign + binary-sign-tool -selfSign 1 重签。默认不需要（干净 .so 靠链接器自签，见 ML-0043）。
        libdir = os.path.join(self.package_folder, "lib")
        sos = _glob.glob(os.path.join(libdir, "**", "*.so"), recursive=True)
        sos += _glob.glob(os.path.join(libdir, "**", "*.so.*"), recursive=True)
        if not sos:
            return
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for so in sos:
            if os.path.islink(so):   # 只签真实 ELF，跳版本化 .so 的软链（否则对同一目标重复签）
                continue
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=so))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=so))

    def package_info(self):
        self.cpp_info.libs = ["tiff"]
        # 标准 CMake 消费方 find_package(TIFF) → TIFF::tiff。
        self.cpp_info.set_property("cmake_file_name", "TIFF")
        self.cpp_info.set_property("cmake_target_name", "TIFF::tiff")
        self.cpp_info.set_property("pkg_config_name", "libtiff-4")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
