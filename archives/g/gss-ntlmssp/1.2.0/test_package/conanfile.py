"""test_package — gss-ntlmssp 1.2.0 的鸿蒙特有消费者测试。

真实消费者路径：构建 dlopen 探针（不链接机制模块本体），从**安装树**加载
lib/gssntlmssp/gssntlmssp.so，完成端到端 NTLM 会话（凭据→握手→wrap/unwrap→mic）。
GSSAPI 头与 name-type OID 宿主（libgssapi_krb5）来自传递依赖 krb5。
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class GssNtlmsspTestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # 模块静态链接 libcrypto，MD4 走 legacy provider；openssl 是静态包，
        # 若不直接声明会被运行期图判 skip → package_folder=None、
        # OPENSSL_MODULES 无从注入（首轮实测）。直接声明保证其二进制在图内。
        self.requires("openssl/3.0.21")

    def layout(self):
        cmake_layout(self)

    def _krb5_dirs(self):
        for dep in self.dependencies.host.values():
            if dep.ref.name == "krb5":
                pf = dep.package_folder or ""
                incs = [d if os.path.isabs(d) else os.path.join(pf, d)
                        for d in dep.cpp_info.includedirs]
                libs = [d if os.path.isabs(d) else os.path.join(pf, d)
                        for d in dep.cpp_info.libdirs]
                return incs, libs
        raise ConanException("传递依赖 krb5 未出现在依赖图（test_package 需要 gssapi 头与 OID 符号）")

    def build(self):
        incs, libs = self._krb5_dirs()
        # 被测包自身的交付头 include/ 必须进编译面（W4 轮1 P2：gssapi_ntlmssp.h
        # 属 cpp_info.includedirs 交付面，探针 include 它以获得编译覆盖）
        self_inc = os.path.join(
            self.dependencies["gss-ntlmssp"].package_folder or "", "include")
        if os.path.isdir(self_inc) and self_inc not in incs:
            incs = incs + [self_inc]
        cmake = CMake(self)
        cmake.configure(variables={
            "GSSAPI_INCLUDE_DIRS": ";".join(incs),
            "GSSAPI_LIB_DIRS": ";".join(libs),
            "GSSAPI_LIBS": "gssapi_krb5",
        })
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.info("can_run=false，跳过消费者测试")
            return
        dep = self.dependencies["gss-ntlmssp"]
        module = os.path.join(dep.package_folder, "lib", "gssntlmssp", "gssntlmssp.so")
        cred = os.path.join(self.source_folder, "ntlm_user_file.txt")
        if not os.path.isfile(module):
            raise ConanException(f"被测模块不存在: {module}")
        if not os.path.isfile(cred):
            raise ConanException(f"凭据文件不存在: {cred}")
        # 探针可执行文件定位（cmake_layout 的二进制目录按 conan 实际取值，不猜路径）
        exe = None
        for root, _dirs, files in os.walk(self.build_folder):
            if "gssntlm_probe" in files:
                exe = os.path.join(root, "gssntlm_probe")
                break
        if exe is None:
            raise ConanException(f"gssntlm_probe 未在 {self.build_folder} 下生成")
        # 显式注入（不单靠 runenv 组合）：模块静态链接的 libcrypto 取 MD4(legacy)
        # 必须能定位 legacy.so（包内 lib/ossl-modules）。
        ssl_pf = None
        for dep in self.dependencies.host.values():
            if dep.ref.name == "openssl":
                ssl_pf = dep.package_folder
        if not ssl_pf:
            raise ConanException("openssl package_folder 不可用，无法注入 OPENSSL_MODULES")
        os.environ["OPENSSL_MODULES"] = os.path.join(ssl_pf, "lib", "ossl-modules")
        self.output.info(f"[test] OPENSSL_MODULES={os.environ['OPENSSL_MODULES']}")
        self.run(f'"{exe}" "{module}" "{cred}"', env="conanrun")
