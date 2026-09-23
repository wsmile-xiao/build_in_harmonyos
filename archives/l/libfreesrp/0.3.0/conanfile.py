#!/usr/bin/env python3
"""Conan recipe — libfreesrp 0.3.0 (CMake project).

FreeSRP SDR 硬件客户端库（libfreesrp.so）+ 两个示例工具（freesrp-ctl / freesrp-io）。
Source: https://github.com/myriadrf/libfreesrp (official tag 0.3.0)
"""
import os
import subprocess
import time

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import build_jobs
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout

BUILD_RETRIES = 3


class LibfreesrpConan(ConanFile):
    name = "libfreesrp"
    version = "0.3.0"
    description = "FreeSRP SDR hardware client library (libusb-based) with freesrp-ctl/freesrp-io utilities"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/myriadrf/libfreesrp"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"
    package_type = "library"
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
        # 核心库依赖 libusb-1.0（freesrp_impl.cpp 直接调 libusb_* API）
        self.requires("libusb/1.0.27")
        # 示例工具 freesrp-ctl/freesrp-io 使用 boost::lexical_cast / boost::tokenizer
        # （仅 header-only 组件；核心库不用 boost）
        self.requires("boost/1.91.0.1.3", headers=True)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()

        tc = CMakeToolchain(self)
        # CMake 4.x compatibility: upstream declares cmake_minimum_required(2.8.4)
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # E092: CMake does not recognize HarmonyOS; force Linux so that the
        # install(TARGETS ...) rules take effect.
        tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.cache_variables["CMAKE_BUILD_TYPE"] = "Release"

        # Upstream cmake/modules/Findlibusb-1.0.cmake searches system paths only.
        # Its top-level short-circuit honours pre-set cache variables, so resolve
        # them from the libusb/1.0.27 dependency package (same approach as the
        # airspyhf 1.6.8 recipe). Note: CMakeLists also uses the singular
        # LIBUSB_1_INCLUDE_DIR in include_directories(), so set all three.
        libusb = self.dependencies["libusb"]
        usb_inc = os.path.join(libusb.package_folder, libusb.cpp_info.includedirs[0])
        if self.options.shared:
            usb_lib = os.path.join(libusb.package_folder, libusb.cpp_info.libdirs[0],
                                   "libusb-1.0.so")
        else:
            usb_lib = os.path.join(libusb.package_folder, libusb.cpp_info.libdirs[0],
                                   "libusb-1.0.a")
        tc.cache_variables["LIBUSB_1_LIBRARIES"] = usb_lib
        tc.cache_variables["LIBUSB_1_INCLUDE_DIRS"] = usb_inc
        tc.cache_variables["LIBUSB_1_INCLUDE_DIR"] = usb_inc

        # Upstream CMakeLists never calls find_package(Boost); the example tools
        # just #include <boost/...> assuming a system boost. Boost is used
        # header-only here, so inject the include path as a global cxxflag.
        boost = self.dependencies["boost"]
        boost_inc = os.path.join(boost.package_folder, boost.cpp_info.includedirs[0])
        self.conf.append("tools.build:cxxflags", "-I" + boost_inc)

        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        # 本机 OHOS 环境实测：CMake helper（self.run）驱动 make 在管道/capture
        # 下会静默失败（日志无任何 error: 行，同一命令手工执行 100% 成功）。
        # 改用 subprocess.run + 显式 env 继承，成功后不重试；出现真实编译器
        # error: 诊断时快速失败，仅对无诊断的静默失败重试（zmusic/libhpptools 同款方案）。
        jobs = max(1, min(int(build_jobs(self)), 4))
        cmd = 'cmake --build "%s" -- -j%d' % (self.build_folder, jobs)
        build_env = os.environ.copy()
        for attempt in range(1, BUILD_RETRIES + 1):
            proc = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                                  cwd=self.build_folder, env=build_env)
            if proc.returncode == 0:
                if proc.stdout:
                    self.output.info(proc.stdout[-2000:])
                break
            tail = (proc.stdout or "") + (proc.stderr or "")
            if "error:" in tail:
                raise ConanException(
                    "cmake --build 报出编译器错误（非环境性静默失败），"
                    "不重试，尾部输出:\n%s" % tail[-4000:]
                )
            self.output.warning(
                "构建第 %d/%d 次失败（rc=%d），日志无 error: 输出，"
                "属环境偶发资源竞争，输出尾部:\n%s"
                % (attempt, BUILD_RETRIES, proc.returncode, tail[-2000:])
            )
            if attempt == BUILD_RETRIES:
                raise ConanException(
                    "cmake --build 连续 %d 次失败且始终无 error: 输出，尾部输出:\n%s"
                    % (BUILD_RETRIES, tail[-4000:])
                )
            time.sleep(5)

    def package(self):
        cmake = CMake(self)
        cmake.install()
        self._sign_elf()

    def _sign_elf(self):
        """HarmonyOS requires ELF code signing before shared libraries can be
        loaded and executables can run (same as libusb / airspyhf recipes)."""
        if str(self.settings.os) != "OHOS":
            return
        signer = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if not (os.path.isfile(signer) and os.path.isfile(objcopy)):
            return
        targets = []
        libdir = os.path.join(self.package_folder, "lib")
        if os.path.isdir(libdir):
            for root, _, files in os.walk(libdir):
                for filename in files:
                    if ".so" in filename:
                        path = os.path.join(root, filename)
                        if not os.path.islink(path):
                            targets.append(path)
        bindir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bindir):
            for filename in os.listdir(bindir):
                path = os.path.join(bindir, filename)
                if os.path.isfile(path) and not os.path.islink(path):
                    targets.append(path)
        for path in targets:
            subprocess.run([objcopy, "--remove-section", ".codesign", path], check=False)
            signed = path + ".signed"
            r = subprocess.run([signer, "sign", "-inFile", path, "-outFile", signed,
                                "-selfSign", "1", "-signAlg", "SHA256withECDSA"],
                               capture_output=True, text=True)
            if r.returncode == 0 and os.path.isfile(signed):
                os.replace(signed, path)
                try:
                    os.chmod(path, 0o755)
                except OSError:
                    pass

    def package_info(self):
        self.cpp_info.libs = ["freesrp"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_find_mode", "both")
        self.cpp_info.set_property("cmake_file_name", "freesrp")
        self.cpp_info.set_property("cmake_target_name", "freesrp::freesrp")
        self.cpp_info.set_property("pkg_config_name", "libfreesrp")
        # freesrp-io 链接 pthread（上游 target_link_libraries 显式声明）
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]
