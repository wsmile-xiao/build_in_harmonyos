#!/usr/bin/env python3
"""Conan recipe for vmime 0.9.2 (CMake build) targeting aarch64-linux-ohos.

Notes:
- SASL support is disabled by default: GNU SASL (gsasl) is not published in the
  ohpcd artifact registry, and SASL is an optional vmime feature.
- TLS support uses conan-provided OpenSSL 1.1.1w: vmime 0.9.2 defines a static
  custom BIO_METHOD which is incompatible with OpenSSL 3.x opaque structs.
  The upstream CMakeLists references ${OPENSSL_INCLUDE_DIR}/${OPENSSL_LIBRARIES};
  we pre-seed those cache variables from the conan openssl dependency so the
  module-mode find_package(OpenSSL) lookup is bypassed (CMakeDeps provides
  the openssl-config.cmake package instead).
- Charset conversion uses conan-provided libiconv (OHOS sysroot has no iconv.h).
"""
from conan import ConanFile
import os

from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches

required_conan_version = ">=2.0"


class VmimeConan(ConanFile):
    name = "vmime"
    version = "0.9.2"
    description = "VMime is a powerful and extensible C++ mail library (MIME, SMTP, POP3, IMAP)"
    license = "GPL-3.0-or-later"
    homepage = "https://www.vmime.org/"
    url = "https://github.com/kisli/vmime"
    topics = ("email", "mime", "smtp", "imap", "pop3")

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_tls": [True, False],
        "with_sasl": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_tls": True,
        "with_sasl": False,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def requirements(self):
        if self.options.with_tls:
            self.requires("openssl/1.1.1w")
        # OHOS sysroot does not ship iconv.h; use conan-provided libiconv
        self.requires("libiconv/1.17.1")
        # 上游单元测试套件基于 CppUnit；仅构建期/测试期需要，不进入消费者依赖闭包
        self.test_requires("cppunit/1.15.1")

    def validate(self):
        check_min_cppstd(self, 11)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["VMIME_BUILD_STATIC_LIBRARY"] = not self.options.shared
        tc.variables["VMIME_BUILD_SHARED_LIBRARY"] = self.options.shared
        tc.variables["VMIME_BUILD_TESTS"] = True
        tc.variables["VMIME_BUILD_SAMPLES"] = False
        tc.variables["VMIME_BUILD_DOCUMENTATION"] = False
        # Optional feature switches
        tc.variables["VMIME_HAVE_SASL_SUPPORT"] = self.options.with_sasl
        tc.variables["VMIME_HAVE_TLS_SUPPORT"] = self.options.with_tls
        if self.options.with_tls:
            tc.variables["VMIME_TLS_SUPPORT_LIB"] = "openssl"
            openssl_info = self.dependencies["openssl"].cpp_info
            tc.variables["OPENSSL_INCLUDE_DIR"] = openssl_info.includedirs[0].replace("\\", "/")
            # CMakeDeps exposes the OpenSSL package as `openssl::openssl`
            tc.variables["OPENSSL_LIBRARIES"] = "openssl::openssl"
        # Charset conversion: conan libiconv (OHOS sysroot has no iconv.h)
        tc.variables["VMIME_CHARSETCONV_LIB"] = "iconv"
        iconv_info = self.dependencies["libiconv"].cpp_info
        tc.variables["ICONV_INCLUDE_DIR"] = iconv_info.includedirs[0].replace("\\", "/")
        import glob as _glob
        iconv_libdir = iconv_info.libdirs[0]
        iconv_libs = sorted(_glob.glob(os.path.join(iconv_libdir, "libiconv*.a")) +
                            _glob.glob(os.path.join(iconv_libdir, "libiconv*.so")))
        tc.variables["ICONV_LIBRARIES"] = (iconv_libs[0] if iconv_libs else os.path.join(iconv_libdir, "libiconv")).replace("\\", "/")
        # Upstream CMake requires an explicit sendmail path when the sendmail
        # transport is compiled in; it is only a compile-time constant string.
        tc.variables["VMIME_SENDMAIL_PATH"] = "/usr/sbin/sendmail"
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()

        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # 上游测试套件 (tests/testRunner, CppUnit) 在构建目录中真实执行。
        # OHOS 设备 /tmp 只读，故把 TMPDIR 指向构建目录下的可写临时目录。
        # 失败用例不静默处理：明细完整保留在 ctest 输出与 CI 日志中。
        tmpdir = os.path.join(str(self.build_folder), "vmime-test-tmp")
        os.makedirs(tmpdir, exist_ok=True)
        self.output.info("Running upstream CppUnit suite via ctest (TMPDIR=%s)" % tmpdir)
        os.environ["TMPDIR"] = tmpdir
        # 如实执行全部上游用例；失败明细保留在 CI 日志中，不做静默处理。
        # 平台限制导致的用例失败在 PR 正文与 notes.md 中逐项定位。
        # 测试失败必须使构建失败（重跑仅用于补全失败明细，随后原样上抛）：
        # 禁止测试全红仍产出可发布包。
        try:
            cmake.test()
        except Exception:
            self.output.warning("ctest 存在失败用例，重跑补全失败明细后判定构建失败")
            self.run("ctest --rerun-failed --output-on-failure", ignore_errors=True)
            raise

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "vmime")
        self.cpp_info.set_property("cmake_target_name", "vmime::vmime")
        self.cpp_info.libs = ["vmime"]
        if self.options.with_tls:
            self.cpp_info.requires = ["openssl::openssl"]
        self.cpp_info.requires.append("libiconv::libiconv")
        if not self.options.shared:
            self.cpp_info.defines.append("VMIME_STATIC")
        self.cpp_info.defines.append(
            "VMIME_HAVE_TLS_SUPPORT=1" if self.options.with_tls else "VMIME_HAVE_TLS_SUPPORT=0")
