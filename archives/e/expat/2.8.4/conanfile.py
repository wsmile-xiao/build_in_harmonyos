from conan import ConanFile
from conan.tools.files import collect_libs, get
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import cmake_layout
from conan.tools.files import apply_conandata_patches


class ExpatConan(ConanFile):
    name = "expat"
    version = "2.8.4"
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
        # 不用 conan 的 CMakeToolchain：os=OHOS 下它把 CMAKE_SYSTEM_NAME 映射成 cmake 不认的值
        # （ML-0035），产物**不带 SONAME**、也不生成版本化软链。后果很隐蔽——链接器遇到无 SONAME 的
        # 被链库时，会把**该库的路径**写进消费方的 DT_NEEDED，使消费方二进制不可重定位：
        # fontconfig 链本包后 DT_NEEDED 变成 `/…/expat<hash>/p/lib/libexpat.so`，一旦 expat 落到
        # 别的包目录哈希就报 `Error loading shared library` + 一串 XML_* symbol not found。
        # 改用本仓已验证的「自发现 ohos.toolchain + 裸 cmake」路子（glfw/libjpeg-turbo/zstd/opus 同法）。
        pass

    def _ohos_toolchain(self):
        # ① profile [conf] user_toolchain ② 环境 OHOS_NDK_HOME ③ glob 设备/CI 的 SDK 布局
        import glob
        import os
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

    def build(self):
        import os
        apply_conandata_patches(self)
        removed = [
            name
            for name in ("LD_LIBRARY_PATH", "PYTHONHOME")
            if os.environ.pop(name, None) is not None
        ]
        if removed:
            self.output.info(
                "Cleared inherited runtime variables before CMake configure: "
                + ", ".join(removed)
            )
        toolchain = self._ohos_toolchain()
        # git 归档源码树里 CMakeLists 在子目录 expat/（顶层是仓库根，非 expat 项目根）。
        src = os.path.join(self.source_folder, "expat")
        bdir = os.path.join(self.build_folder, "build-ohos")
        defs = [
            '-DCMAKE_TOOLCHAIN_FILE="{}"'.format(toolchain),
            "-DOHOS_ARCH=arm64-v8a",
            "-DCMAKE_BUILD_TYPE={}".format(self.settings.build_type),
            "-DCMAKE_INSTALL_LIBDIR=lib",      # ohos.toolchain 64 位默认装 lib64/
            "-DCMAKE_PLATFORM_NO_VERSIONED_SONAME=ON",
            "-DCMAKE_SHARED_LIBRARY_SONAME_C_FLAG=-Wl,-soname,",
            "-DEXPAT_BUILD_TOOLS=OFF",
            "-DEXPAT_BUILD_EXAMPLES=OFF",
            "-DEXPAT_BUILD_TESTS=ON",
            "-DEXPAT_BUILD_DOCS=OFF",
            "-DEXPAT_SHARED_LIBS=ON",
            "-DEXPAT_BUILD_PKGCONFIG=ON",
            # 熵源：设备上 getrandom 已被 cmake 检出，但 expat 默认 EXPAT_WITH_*=OFF 不启用任何源
            # → 运行期缺熵。显式开 getrandom（由 expat 构建系统一致定义，避免手工 XML_DEV_URANDOM
            # 造成 writeRandomBytes_* 悬空符号）。
            "-DEXPAT_WITH_GETRANDOM=ON",
        ]
        self.run('cmake -B "{}" -S "{}" {}'.format(bdir, src, " ".join(defs)))
        self.run('cmake --build "{}"'.format(bdir))
        if can_run(self):
            self._run_upstream_tests(bdir)
        else:
            self.output.info("Cross-building: skip the target Expat test runner")

    def package(self):
        import os
        self.run('cmake --install "{}" --prefix "{}"'.format(
            os.path.join(self.build_folder, "build-ohos"), self.package_folder))
        self._sign_binaries()

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        # cmake 走 SDK ohos.toolchain 产的 .so 自签无效（dlopen Permission denied），必须重签。
        import glob
        import os
        targets = glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so"), recursive=True)
        targets += glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so.*"), recursive=True)
        bindir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bindir):
            for name in os.listdir(bindir):
                _p = os.path.join(bindir, name)
                if os.path.isfile(_p) and not os.path.islink(_p) and self._is_elf(_p):
                    targets.append(_p)
        objcopy = os.environ.get("LLVM_OBJCOPY", "/data/service/hnp/bin/llvm-objcopy")
        signer = os.environ.get("BINARY_SIGN_TOOL", "/data/service/hnp/bin/binary-sign-tool")
        if not os.path.isfile(signer):
            self.output.warning("binary-sign-tool 不存在，跳过代码签名（请在 CI/设备环境执行）")
            return
        for f in targets:
            if os.path.islink(f):
                continue
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=f))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=f))

    def _run_upstream_tests(self, build_dir):
        import os
        test_binary = os.path.join(build_dir, "tests", "runtests")
        if not os.path.isfile(test_binary):
            raise ConanException("Missing Expat upstream test runner: {}".format(test_binary))

        objcopy = os.environ.get("LLVM_OBJCOPY", "/data/service/hnp/bin/llvm-objcopy")
        signer = os.environ.get("BINARY_SIGN_TOOL", "/data/service/hnp/bin/binary-sign-tool")
        for tool in (objcopy, signer):
            if not os.path.isfile(tool):
                raise ConanException("Required OHOS signing tool is missing: {}".format(tool))

        os.chmod(test_binary, 0o755)
        self.run(
            '{oc} --remove-section .codesign "{binary}" 2>/dev/null || true'.format(
                oc=objcopy, binary=test_binary
            )
        )
        self.run(
            '{signer} sign -inFile "{binary}" -outFile "{binary}" -selfSign 1'.format(
                signer=signer, binary=test_binary
            )
        )
        self.output.info("Running the complete Expat upstream C unit test runner")
        self.run('"{}"'.format(test_binary))

    def package_info(self):
        explicit_libs = ['expat']
        self.cpp_info.libs = explicit_libs or collect_libs(self)
        self.cpp_info.set_property("cmake_file_name", "expat")
        self.cpp_info.set_property("cmake_target_name", "expat::expat")
        pkg = "expat" or self._detect_pkg_config_name()
        if pkg:
            self.cpp_info.set_property("pkg_config_name", pkg)
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
