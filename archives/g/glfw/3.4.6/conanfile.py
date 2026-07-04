from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import collect_libs, get
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout
from conan.tools.files import apply_conandata_patches


class GlfwConan(ConanFile):
    name = "glfw"
    version = "3.4.6"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}


    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self, src_folder=".")

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        tc.variables["GLFW_BUILD_OHOS"] = "ON"
        tc.variables["GLFW_BUILD_EXAMPLES"] = "OFF"
        tc.variables["GLFW_BUILD_TESTS"] = "OFF"
        tc.variables["GLFW_BUILD_DOCS"] = "OFF"
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        tc.variables["GLFW_LIBRARY_TYPE"] = "SHARED"
        tc.generate()

    def _ohos_toolchain(self):
        # 自发现 OHOS NDK 的 ohos.toolchain.cmake（不依赖 profile host 段有没有 user_toolchain）：
        # ① profile [conf] 已配就用；② 环境 OHOS_NDK_HOME；③ glob 设备/CI 的 SDK 布局。
        import os
        import glob
        ut = self.conf.get("tools.cmake.cmaketoolchain:user_toolchain", default=[], check_type=list)
        ndk = os.environ.get("OHOS_NDK_HOME", "")
        candidates = list(ut) + [os.path.join(ndk, "build", "cmake", "ohos.toolchain.cmake")] if ndk else list(ut)
        for cand in candidates:
            if cand and os.path.isfile(cand):
                return cand
        globbed = sorted(glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/build/cmake/ohos.toolchain.cmake"))
        if globbed:
            return globbed[-1]
        raise ConanInvalidConfiguration(
            "找不到 ohos.toolchain.cmake：设 OHOS_NDK_HOME，或在 profile [conf] 配 "
            "tools.cmake.cmaketoolchain:user_toolchain=[<sdk>/ohos/native/build/cmake/ohos.toolchain.cmake]")

    def build(self):
        # GLFW 鸿蒙后端产两个互为 DT_NEEDED 的 .so（libglfw.so ↔ libglfw_bridge.so，
        # 循环依赖，ML-0023），bridge 是独立 cmake 工程。复刻 build-ohos.sh 的 two-pass。
        import os
        import glob
        apply_conandata_patches(self)
        src = self.source_folder
        bridge_src = os.path.join(src, "bridge")
        # 直接用 OHOS NDK 的 ohos.toolchain.cmake（CMAKE_SYSTEM_NAME=OHOS + 平台模块 → SONAME/版本软链齐），
        # 而非 conan_toolchain——后者 os=OHOS 会退化成未知平台 HarmonyOS、不出 SONAME，bridge 的
        # -l:libglfw.so.3 就链接失败（ML-0035）。自发现 toolchain 使 recipe 自包含、不依赖 CI profile 的 host 段。
        toolchain = self._ohos_toolchain()
        bo = os.path.join(self.build_folder, "build-ohos")     # 主库 root 工程
        bb = os.path.join(self.build_folder, "build-bridge")   # 桥接 bridge 工程
        common = '-DCMAKE_TOOLCHAIN_FILE="{}" -DOHOS_ARCH=arm64-v8a -DCMAKE_BUILD_TYPE={}'.format(
            toolchain, self.settings.build_type)
        root_defs = ("-DGLFW_BUILD_OHOS=ON -DGLFW_BUILD_EXAMPLES=OFF "
                     "-DGLFW_BUILD_TESTS=OFF -DGLFW_BUILD_DOCS=OFF "
                     "-DBUILD_SHARED_LIBS=ON -DGLFW_LIBRARY_TYPE=SHARED")

        # Pass 1：各自编出来（-z undefs 允许跨 .so 未解析，暂不记 DT_NEEDED）
        self.run('cmake -B "{}" -S "{}" {} {}'.format(bo, src, common, root_defs))
        self.run('cmake --build "{}"'.format(bo))
        self.run('cmake -B "{}" -S "{}" {}'.format(bb, bridge_src, common))
        self.run('cmake --build "{}"'.format(bb))

        # Pass 2：互指对方目录重链，记下双向 DT_NEEDED（musl BIND_NOW dlopen 必须）。
        # 必须显式带 -S（conan 里 CWD=build 目录，省 -S 会把 CWD 当源码目录、找不到 CMakeLists）。
        # 删旧产物强制重链；final link 由链接器自签（ML-0043），无链接后二进制改动、不需重签。
        self.run('cmake -B "{}" -S "{}" {} {} -DOHOS_BRIDGE_LIBDIR="{}"'.format(bo, src, common, root_defs, bb))
        for f in glob.glob(os.path.join(bo, "src", "libglfw.so*")):
            os.remove(f)
        self.run('cmake --build "{}"'.format(bo))
        self.run('cmake -B "{}" -S "{}" {} -DOHOS_GLFW_LIBDIR="{}"'.format(bb, bridge_src, common, os.path.join(bo, "src")))
        _bridge_so = os.path.join(bb, "libglfw_bridge.so")
        if os.path.exists(_bridge_so):
            os.remove(_bridge_so)
        self.run('cmake --build "{}"'.format(bb))

    def package(self):
        import os
        import glob
        import shutil
        bo = os.path.join(self.build_folder, "build-ohos")
        bb = os.path.join(self.build_folder, "build-bridge")
        # 主库 + 头文件 + cmake/pkgconfig 由 root 的 install(TARGETS glfw) 安装
        self.run('cmake --install "{}" --prefix "{}"'.format(bo, self.package_folder))
        # 桥接库是独立 cmake 工程、无 install target → 手动拷进 lib/（保留 soname 软链）
        libdir = os.path.join(self.package_folder, "lib")
        os.makedirs(libdir, exist_ok=True)
        for f in glob.glob(os.path.join(bb, "libglfw_bridge.so*")):
            shutil.copy2(f, os.path.join(libdir, os.path.basename(f)), follow_symlinks=False)



    def package_info(self):
        explicit_libs = ['glfw']
        self.cpp_info.libs = explicit_libs or collect_libs(self)
        self.cpp_info.set_property("cmake_file_name", "glfw")
        self.cpp_info.set_property("cmake_target_name", "glfw::glfw")
        pkg = "glfw3" or self._detect_pkg_config_name()
        if pkg:
            self.cpp_info.set_property("pkg_config_name", pkg)
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ['ace_napi.z', 'ace_ndk.z', 'hilog_ndk.z']
        import os
        for _env in []:
            _k, _v = _env.split("=", 1)
            self.runenv_info.define_path(_k, os.path.join(self.package_folder, _v))

    def _detect_pkg_config_name(self):
        # 未显式给 --pkgconfig-name 时，从 install 出的 lib/pkgconfig/*.pc 取第一个文件名 stem。
        import glob
        import os
        pcs = sorted(glob.glob(os.path.join(self.package_folder, "lib", "pkgconfig", "*.pc")))
        if not pcs:
            return ""
        return os.path.splitext(os.path.basename(pcs[0]))[0]
