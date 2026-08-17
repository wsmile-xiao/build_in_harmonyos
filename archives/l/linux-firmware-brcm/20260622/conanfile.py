from conan import ConanFile
from conan.tools.files import copy, get, download, unzip, export_conandata_patches, apply_conandata_patches
from conan.tools.build import check_min_cppstd
import os

required_conan_version = ">=2.0"

class LinuxFirmwareBrcmConan(ConanFile):
    name = "linux-firmware-brcm"
    version = "20260622"
    package_type = "unknown"

    # 纯资源包，无平台/编译器/构建配置依赖
    # CI L0 要求显式声明 Conan settings（os/compiler/build_type/arch）
    settings = "os", "compiler", "build_type", "arch"
    options = None
    default_options = None

    # 无 Conan 第三方依赖
    def requirements(self):
        pass

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        # 下载完整 linux-firmware tarball（.tar.xz, 639MB）
        get(self, **self.conan_data["sources"][self.version],
            destination=self.source_folder, strip_root=True)

    def build(self):
        # 纯固件资源包，无编译步骤，仅应用补丁（当前无补丁）
        apply_conandata_patches(self)

    def package(self):
        # 仅打包 brcm 子目录中的固件文件到资源目录
        # 固件部署路径: lib/firmware/brcm/ （Linux 标准固件路径）
        brcm_src = os.path.join(self.source_folder, "brcm")
        if os.path.exists(brcm_src):
            copy(self, "*", src=brcm_src, dst=os.path.join(self.package_folder, "res", "brcm"))
        else:
            self.output.warning("brcm/ directory not found in source tree")
        # 将上游 Broadcom 许可证复制到 Conan 标准 licenses/ 目录
        lic_src = os.path.join(self.source_folder, "LICENSES", "LICENCE.broadcom_bcm43xx")
        if os.path.exists(lic_src):
            copy(self, "LICENCE.broadcom_bcm43xx", src=os.path.dirname(lic_src),
                 dst=os.path.join(self.package_folder, "licenses"))
        else:
            self.output.warning("LICENSES/LICENCE.broadcom_bcm43xx not found in source tree")

    def package_info(self):
        # 固件资源包：不声明库或二进制目录，仅声明 res 目录
        self.cpp_info.resdirs = ["res"]
        # 明确不声明如下字段（固件资源无库/二进制文件）：
        # self.cpp_info.libs = []
        # 二进制目录不声明（固件资源无库/可执行文件）
