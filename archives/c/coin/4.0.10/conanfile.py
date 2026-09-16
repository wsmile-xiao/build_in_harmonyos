#!/usr/bin/env python3
"""Conan recipe — coin 4.0.10 (cmake)

Coin = Coin3D core（Open Inventor 2.1 API 的高层 3D 可视化/场景图库，OpenGL 渲染）。
注意与 COIN-OR（Common Optimization Interface for OR，数值优化套件）只是同名，二者无关。

OHOS 适配要点（2026-09-09 设备真机探针实证）：
- OHOS 无桌面 libGL：Coin 的 glue 层静态引用定点管线符号（glMatrixMode/glBegin/
  glColor3f/glPushMatrix 等），/system/lib64/libGLESv3.so 不导出它们（探针链接失败），
  必须链接 gl4es/1.1.6 的 libGL.so（桌面 GL 1.5/2.1 → GLES2 翻译层，ohpcd 已发布），
  SONAME=libGL.so.1 → libCoin.so 的 DT_NEEDED=libGL.so.1（相对名，L5 合规）。
- OPENGL_INCLUDE_DIR 预置 SDK sysroot（桌面 GL/gl.h）；find_package(OpenGL) 另自动
  发现 sysroot 的 libEGL.so → COIN_BUILD_EGL=ON（默认）链 libEGL.so（真机
  eglGetDisplay(EGL_DEFAULT_DISPLAY)+eglInitialize 可用，EGL 1.4 OpenHarmony）。
- COIN_BUILD_GLX=OFF：OHOS 无 X11/GLX。
- zlib/bzip2/freetype 等走运行时 dlopen（*_RUNTIME_LINKING 默认 ON），零 conan
  requires 之外无隐式链接依赖；vendored expat 默认内置（USE_EXTERNAL_EXPAT=OFF）。
- 上游 cmake_minimum_required(3.0...3.31) 兼容 cmake 4.x，无源码补丁；仍传
  CMAKE_POLICY_VERSION_MINIMUM=3.5 兜底。
- 已知问题：SoDB::finish() 在 gl4es 栈下析构 GL glue 时 SIGSEGV（初始化/解析/渲染
  正常，进程退出不调 finish() 即可干净结束），详见 notes.md。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, get


class CoinConan(ConanFile):
    name = "coin"
    version = "4.0.10"
    description = "Coin3D core — high-level 3D visualization library with Open Inventor 2.1 API (scene graph over OpenGL)"
    license = "BSD-3-Clause"
    homepage = "https://coin3d.github.io"
    url = ""

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
        # 本版本无补丁（上游 cmake_minimum_required(3.0...3.31) 兼容 cmake 4.x）；
        # conandata.yml 由 conan 自动随配方导出
        from conan.tools.files import export_conandata_patches
        export_conandata_patches(self)

    def requirements(self):
        # 桌面 GL 符号翻译层（OHOS 只有 GLES3/EGL，无 libGL）
        self.requires("gl4es/1.1.6")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def layout(self):
        # 与 assimp 6.0.5 相同：手动 cmake 构建（自发现 ohos.toolchain.cmake），
        # 不用 conan_toolchain（os=OHOS 下 CMAKE_SYSTEM_NAME 映射不被旧 cmake 接受）。
        from conan.tools.cmake import cmake_layout
        cmake_layout(self, src_folder=".")

    def _ohos_toolchain(self):
        # 自发现 OHOS NDK 的 ohos.toolchain.cmake（① profile [conf] user_toolchain
        # ② 环境 OHOS_NDK_HOME ③ glob 设备/CI 的 SDK 布局），不依赖 CI profile host 段。
        import glob
        ut = self.conf.get("tools.cmake.cmaketoolchain:user_toolchain", default=[], check_type=list)
        ndk = os.environ.get("OHOS_NDK_HOME", "")
        for _c in list(ut) + ([os.path.join(ndk, "build/cmake/ohos.toolchain.cmake")] if ndk else []):
            if _c and os.path.isfile(_c):
                return _c
        _g = sorted(glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/build/cmake/ohos.toolchain.cmake"))
        if _g:
            return _g[-1]
        raise ConanInvalidConfiguration(
            "找不到 ohos.toolchain.cmake：设 OHOS_NDK_HOME 或 profile [conf] user_toolchain")

    def _llvm_ranlib(self, toolchain):
        # OHOS SDK 的 llvm/bin 下**只有 llvm-ar，没有 llvm-ranlib**（实证：OpenCV/
        # SuiteSparse 静态库 ENOENT）。返回 "" 表示不覆盖（SDK 自带就用它的）。
        import shutil
        sdk_bin = os.path.join(toolchain, "..", "..", "..", "llvm", "bin")
        cand = os.path.normpath(os.path.join(sdk_bin, "llvm-ranlib"))
        if os.path.isfile(cand):
            return ""
        return shutil.which("llvm-ranlib") or ""

    def build(self):
        apply_conandata_patches(self)
        toolchain = self._ohos_toolchain()
        native = os.path.abspath(os.path.join(toolchain, "..", ".."))       # <native>
        sysroot = os.path.join(native, "sysroot")
        gl4es = self.dependencies["gl4es"].package_folder
        src = os.path.join(self.source_folder, "")
        bdir = os.path.join(self.build_folder, "build-ohos")
        defs = [
            '-DCMAKE_TOOLCHAIN_FILE="{}"'.format(toolchain),
            "-DOHOS_ARCH=arm64-v8a",
            "-DCMAKE_BUILD_TYPE={}".format(self.settings.build_type),
            '-DCMAKE_INSTALL_PREFIX="{}"'.format(self.package_folder),
            "-DCMAKE_INSTALL_LIBDIR=lib",           # ohos.toolchain 64 位默认装 lib64/，须改回 lib
            "-DCMAKE_POLICY_VERSION_MINIMUM=3.5",   # 兜底 cmake 4.x（上游 3.0...3.31 本已兼容）
            "-DBUILD_SHARED_LIBS=ON",
            # GL 接线：头用 SDK sysroot 的桌面 GL/gl.h；GL 库用 gl4es 的 libGL.so
            #（系统 libGLESv3.so 缺定点管线符号，直接链会在链接期 undefined symbol）
            '-DOPENGL_INCLUDE_DIR="{}"'.format(os.path.join(sysroot, "usr", "include")),
            '-DOPENGL_gl_LIBRARY="{}/lib/libGL.so"'.format(gl4es),
            # COIN 选项：无 X11/GLX；tests/examples/cpack 关闭
            #（上游 testsuite 由移植门禁在设备上单独构建运行 CoinTests，见 notes.md）
            "-DCOIN_BUILD_GLX=OFF",
            "-DCOIN_BUILD_TESTS=OFF",
            "-DCOIN_BUILD_EXAMPLES=OFF",
            "-DCOIN_USE_CPACK=OFF",
        ]
        _rl = self._llvm_ranlib(toolchain)
        if _rl:
            defs.append('-DCMAKE_RANLIB="{}"'.format(_rl))
        self.run('cmake -B "{}" -S "{}" {}'.format(bdir, src, " ".join(defs)))
        # Coin 源文件量大（约 3300 TU），串行必超 CI 默认 3600s 超时，必须并行
        self.run('cmake --build "{}" -- -j 8'.format(bdir))

    def package(self):
        bdir = os.path.join(self.build_folder, "build-ohos")
        self.run('cmake --install "{}" --prefix "{}"'.format(bdir, self.package_folder))
        # bin/coin-config 是把 /usr/local 前缀写死的 shell 脚本（非 ELF），在 conan
        # 包内无意义且会触发 L2 冒烟 warn，按明确单文件移除
        cfg_script = os.path.join(self.package_folder, "bin", "coin-config")
        if os.path.isfile(cfg_script):
            os.remove(cfg_script)
        self._sign_binaries()

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        # 鸿蒙 PC XPM 要求 dlopen/链接加载的 .so 必须代码签名，否则报
        # "Error loading shared library"（探针实证：未签 libCoin.so.80 直接加载失败）。
        import glob
        targets = glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so"), recursive=True)
        targets += glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so.*"), recursive=True)
        bindir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bindir):
            for name in os.listdir(bindir):
                p = os.path.join(bindir, name)
                if os.path.isfile(p) and not os.path.islink(p) and self._is_elf(p):
                    targets.append(p)
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for f in targets:
            if os.path.islink(f):   # 只签真实 ELF（libCoin.so → libCoin.so.80 → libCoin.so.80.0.10）
                continue
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=f))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=f))

    def package_info(self):
        self.cpp_info.libs = ["Coin"]
        self.cpp_info.set_property("cmake_file_name", "Coin")          # find_package(Coin)
        self.cpp_info.set_property("cmake_target_name", "Coin::Coin")  # 上游 coin-export.cmake 目标名
        self.cpp_info.set_property("pkg_config_name", "Coin")          # lib/pkgconfig/Coin.pc
        self.cpp_info.resdirs = ["share"]                              # share/Coin 运行时资源
        if self.settings.os == "OHOS":
            # gl4es 运行时接线：OHOS 无 libGLESv2/libGL，GLES/EGL 走系统 libGLESv3/libEGL。
            # 消费方缺这两个变量时 SoDB::init() 内 gl4es 初始化会 SIGSEGV（真机实证）。
            self.runenv_info.define("LIBGL_GLES", "/system/lib64/libGLESv3.so")
            self.runenv_info.define("LIBGL_EGL", "/system/lib64/libEGL.so")
