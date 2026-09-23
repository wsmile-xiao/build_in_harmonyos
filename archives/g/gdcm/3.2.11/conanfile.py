import os
import glob

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run, check_min_cppstd
from conan.tools.files import apply_conandata_patches
from conan.tools.scm import Version


class GdcmConan(ConanFile):
    name = "gdcm"
    version = "3.2.11"
    description = "Grassroots DICOM library: DICOM medical image format toolkit (parse/read/write DICOM files)"
    license = "BSD-3-Clause"
    homepage = "https://github.com/malaterre/GDCM"
    url = "https://github.com/malaterre/GDCM"
    topics = ("dicom", "medical-imaging", "healthcare", "image-format")
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "build_apps": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "build_apps": True,
    }

    exports_sources = "patches/*"

    def requirements(self):
        # W0/R36：仅声明制品仓已发布的依赖；其余第三方件（openjpeg/charls/json/uuid/ljpeg/md5/rle）
        # 走上游 Utilities/ 内嵌源码树构建，保持依赖链最短。
        self.requires("zlib/1.3.1.1")
        self.requires("expat/2.8.4")

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.name} recipe only supports Linux/OHOS (got {self.settings.os})")

    def validate(self):
        check_min_cppstd(self, 11)

    def layout(self):
        # 自发现 ohos.toolchain + 裸 cmake 路线（expat/glfw/libjpeg-turbo 同法，ML-0035：
        # CMakeToolchain 在 os=OHOS 下产出的 CMAKE_SYSTEM_NAME 不被 cmake 认识）
        from conan.tools.cmake import cmake_layout
        cmake_layout(self, src_folder="src")

    def source(self):
        from conan.tools.files import get
        get(self, **self.conan_data["sources"], strip_root=True)

    def _ohos_toolchain(self):
        # ① profile [conf] user_toolchain ② 环境 OHOS_NDK_HOME ③ glob 设备/CI 的 SDK 布局
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
        src = self.source_folder
        bdir = os.path.join(self.build_folder, "build-ohos")

        # 显式重定向 find_package 到 conan 依赖（裸 cmake 不吃 CMakeDeps 生成器，
        # gdcm 用 FindZLIB/FindEXPAT 系统模块找包，会把 sysroot 的 libz.so 抢过来）
        dep_defs = []
        for dep, varprefix in (("zlib", "ZLIB"), ("expat", "EXPAT")):
            info = self.dependencies[dep]
            agg = info.cpp_info.aggregated_components()
            inc = agg.includedirs[0]
            libdir = agg.libdirs[0]
            libnames = agg.libs or [dep]
            libfile = "lib{}.a".format(libnames[0])
            if not os.path.isfile(os.path.join(libdir, libfile)):
                # 动态库形态兜底
                for cand in ("lib{}.so".format(libnames[0]), "lib{}.so".format(dep)):
                    if os.path.isfile(os.path.join(libdir, cand)):
                        libfile = cand
                        break
            dep_defs += [
                "-D{}_INCLUDE_DIR={}".format(varprefix, inc),
                "-D{}_LIBRARY={}".format(varprefix, os.path.join(libdir, libfile)),
            ]
            self.output.info("{} -> include {}, lib {}".format(dep, inc, os.path.join(libdir, libfile)))

        defs = [
            '-DCMAKE_TOOLCHAIN_FILE="{}"'.format(toolchain),
            "-DOHOS_ARCH=arm64-v8a",
            "-DCMAKE_BUILD_TYPE={}".format(self.settings.build_type),
            "-DCMAKE_INSTALL_LIBDIR=lib",       # ohos.toolchain 64 位默认装 lib64/
            "-DCMAKE_PLATFORM_NO_VERSIONED_SONAME=ON",
            "-DCMAKE_SHARED_LIBRARY_SONAME_C_FLAG=-Wl,-soname,",
        ]
        defs += dep_defs
        defs += [
            # --- zlib/expat 走 conan 制品仓（dep_defs 已重定向 find_package 路径） ---
            "-DGDCM_USE_SYSTEM_ZLIB=ON",
            "-DGDCM_USE_SYSTEM_EXPAT=ON",
            # --- 其余第三方件用上游内嵌 Utilities 源码 ---
            "-DGDCM_USE_SYSTEM_CHARLS=OFF",
            "-DGDCM_USE_SYSTEM_JSON=OFF",
            "-DGDCM_USE_SYSTEM_UUID=OFF",
            "-DGDCM_USE_SYSTEM_OPENSSL=OFF",    # openssl 仅在 GDCM_USE_SYSTEM_* 组合下需要；内嵌 md5/uuid 替代
            "-DGDCM_USE_SYSTEM_LJPEG=OFF",
            "-DGDCM_USE_SYSTEM_PAPYRUS3=OFF",
            "-DGDCM_USE_SYSTEM_SOCKETXX=OFF",
            "-DGDCM_USE_SYSTEM_POPPLER=OFF",
            "-DGDCM_USE_SYSTEM_LIBXML2=OFF",
            "-DGDCM_USE_JPEGTURBO=OFF",
            # --- 形态 ---
            "-DGDCM_BUILD_SHARED_LIBS={}".format("ON" if self.options.shared else "OFF"),
            "-DBUILD_SHARED_LIBS={}".format("ON" if self.options.shared else "OFF"),
            "-DGDCM_BUILD_APPLICATIONS={}".format("ON" if self.options.build_apps else "OFF"),
            "-DGDCM_BUILD_EXAMPLES=OFF",
            "-DGDCM_DOCUMENTATION=OFF",
            "-DGDCM_PDF_DOCUMENTATION=OFF",
            "-DGDCM_WRAP_PYTHON=OFF",
            "-DGDCM_WRAP_PERL=OFF",
            "-DGDCM_WRAP_PHP=OFF",
            "-DGDCM_WRAP_JAVA=OFF",
            "-DGDCM_WRAP_CSHARP=OFF",
            "-DGDCM_USE_VTK=OFF",
            "-DGDCM_USE_ACTIVIZ=OFF",
            "-DGDCM_USE_COREFOUNDATION_LIBRARY=OFF",
            "-DGDCM_USE_PVRG=OFF",
            "-DGDCM_USE_KAKADU=OFF",
            # --- 上游测试铁律：编译测试二进制并注册 ctest ---
            "-DGDCM_BUILD_TESTING=ON",
            "-DBUILD_TESTING=ON",
            # GDCM_DATA_ROOT 不设置：Testing/Data 为空目录（上游数据集 gdcmData 独立分发），
            # 数据依赖型测试不注册；核心单元测试（无数据集依赖）照常注册执行。
        ]
        self.run('cmake -B "{}" -S "{}" {}'.format(bdir, src, " ".join(defs)))
        # OHOS 工具链坑：ohos.toolchain.cmake 强制 CMAKE_RANLIB=<SDK>/llvm/bin/llvm-ranlib，
        # 但本机 SDK 的 llvm/bin 只装了 llvm-ar/llvm-nm/llvm-objcopy，缺 llvm-ranlib ——
        # 静态库链接（ar qc + ranlib）在 make 阶段报 "Error running link command: no such
        # file or directory"。SDK 目录只读不能补软链，用 hnp/bin/llvm-ranlib（同版本
        # 15.0.4，实测可用）重写 build 树里所有 link.txt 的 ranlib 路径。
        self._fixup_ranlib(bdir)
        self.run('cmake --build "{}" -- -j{}'.format(bdir, 2))
        if can_run(self):
            self._run_upstream_tests(bdir)
        else:
            self.output.info("Cross-building: skip upstream ctest (target exec not runnable)")

    def _fixup_ranlib(self, build_dir):
        import re
        sdk_ranlib = "llvm/bin/llvm-ranlib"
        hnp_ranlib = "/data/service/hnp/bin/llvm-ranlib"
        if not os.path.isfile(hnp_ranlib):
            # 兜底：环境中无 hnp ranlib（如远端 CI），不动——CI 侧 SDK 若自带 ranlib 则无需修
            self.output.info("no hnp llvm-ranlib, skip link.txt fixup")
            return
        n = 0
        for root, _dirs, files in os.walk(build_dir):
            for fn in files:
                if fn == "link.txt":
                    p = os.path.join(root, fn)
                    with open(p, "r", encoding="utf-8", errors="replace") as f:
                        content = f.read()
                    if sdk_ranlib in content and hnp_ranlib not in content:
                        fixed = re.sub(r"\S*llvm/bin/llvm-ranlib", hnp_ranlib, content)
                        with open(p, "w", encoding="utf-8") as f:
                            f.write(fixed)
                        n += 1
        self.output.info(f"rewrote llvm-ranlib path in {n} link.txt files")

    def _run_upstream_tests(self, build_dir):
        # 上游测试以 ctest 驱动（create_test_sourcelist 聚合 gdcm*Tests 二进制，ctest 派发）
        # 需要签名后才能在本机执行（OHOS ELF 签名铁律 E077）
        self._sign_tree(os.path.join(build_dir, "bin"), recursive=True)
        # 运行时依赖：测试二进制 NEEDED 里有 libexpat.so（conan 共享依赖）与
        # libc++_shared.so（SDK llvm/lib）——build() 开头清掉的 LD_LIBRARY_PATH
        # 在此恢复为依赖 lib 目录 + SDK libc++ 目录
        import os as _os
        run_libs = []
        for dep in ("expat", "zlib"):
            if dep in self.dependencies:
                for d in self.dependencies[dep].cpp_info.aggregated_components().libdirs:
                    run_libs.append(d)
        for sdk_lib in (
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib",
            "/data/service/hnp/lib",
        ):
            if _os.path.isdir(sdk_lib):
                run_libs.append(sdk_lib)
        ld_path = ":".join(run_libs)
        env_args = 'GDCM_SOURCE_DIR="{}" LD_LIBRARY_PATH="{}"'.format(self.source_folder, ld_path)
        # 排除项说明（上游测试豁免，逐项证据在 notes.md）：
        #   TestEcho / TestFind / TestSCUValidation / gdcmscu-echo-dicomserver /
        #   gdcmscu-find-dicomserver —— 硬编码外网 DICOM 服务器
        #   （www.dicomserver.co.uk / 51.75.171.41:11112）的真实 C-ECHO/C-FIND
        #   网络往返测试，沙箱环境无出站 DICOM 端口，属网络环境依赖豁免。
        #   DCM(DUMP|DJPEG|DRLE) —— 依赖外部 DCMTK/dicom3tools 可执行文件（未安装）。
        self.run('ctest --test-dir "{}" --output-on-failure -E "TestEcho|TestFind|TestSCUValidation|gdcmscu-.*-dicomserver|DCM(DUMP|DJPEG|DRLE)" {}'.format(
            build_dir, env_args), env="conanbuild")

    def package(self):
        bdir = os.path.join(self.build_folder, "build-ohos")
        self.run('cmake --install "{}" --prefix "{}"'.format(bdir, self.package_folder))
        self._sign_binaries()

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_file(self, path):
        objcopy = os.environ.get("LLVM_OBJCOPY", "/data/service/hnp/bin/llvm-objcopy")
        signer = os.environ.get("BINARY_SIGN_TOOL", "/data/service/hnp/bin/binary-sign-tool")
        if not os.path.isfile(signer):
            self.output.warning("binary-sign-tool 不存在，跳过代码签名（请在 CI/设备环境执行）")
            return
        self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=path))
        self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=path))

    def _sign_tree(self, root, recursive=False):
        if not os.path.isdir(root):
            return
        pat = "**/*" if recursive else "*"
        for f in glob.glob(os.path.join(root, pat), recursive=recursive):
            if os.path.isfile(f) and not os.path.islink(f) and self._is_elf(f):
                self._sign_file(f)

    def _sign_binaries(self):
        # cmake 走 SDK ohos.toolchain 产的 .so 自签无效（dlopen Permission denied），必须重签
        targets = glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so"), recursive=True)
        targets += glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so.*"), recursive=True)
        for f in targets:
            if os.path.islink(f):
                continue
            self._sign_file(f)
        self._sign_tree(os.path.join(self.package_folder, "bin"))

    def package_info(self):
        # gdcminstall/GDCMConfig 安装的库（静态构建时为 .a 集）
        # 上游 install 布局：头文件 include/gdcm-3.2/，库 lib/*.a，CMake config lib/gdcm-3.2/GDCMConfig.cmake
        lib_names = [
            "gdcmCommon",
            "gdcmDICT",
            "gdcmDSED",
            "gdcmIOD",
            "gdcmMSFF",
            "gdcmMEXD",
            "gdcmcharls",
            "gdcmjpeg8",
            "gdcmjpeg12",
            "gdcmjpeg16",
            "gdcmmd5",
            "gdcmopenjp2",
            "gdcmrle",
            "gdcmuuid",
        ]
        self.cpp_info.libs = lib_names
        self.cpp_info.set_property("cmake_file_name", "GDCM")
        self.cpp_info.set_property("cmake_target_name", "GDCM::GDCM")
        self.cpp_info.set_property("pkg_config_name", "gdcm")
        self.cpp_info.includedirs = ["include/gdcm-3.2", "include"]
        self.cpp_info.libdirs = ["lib"]
