#!/usr/bin/env python3
"""Conan recipe — kernel-headers 6.12.77 (Linux kernel UAPI headers).

Linux 内核 UAPI（userspace API）头文件包，源自 kernel.org 官方发布
linux-6.12.77.tar.xz，以 `make ARCH=arm64 headers`（即 headers_install 的
HDRINST 阶段）导出面向用户空间的内核头文件树。

形态选型（参照 compile-time-regular 3.11.0 / boost header-only 组件包先例）：
- package_type = "header-library"，无任何编译产物（纯头文件交付）；
- package() 只拷贝 usr/include/ 下的 *.h（conan copy 替代内核 Makefile
  headers_install 末步的 rsync —— OHOS worker 无 rsync）；
- package_id 按 header-only 规约处理（settings 不参与 binary 哈希，
  implements auto_header_only_mode）。

上游测试（rule4：N=以实际构建系统注册为准）：
- Linux kernel 6.12 无独立测试套件注册于构建系统（headers_check 目标
  已于 5.x 后从 Makefile 移除，6.12 Makefile 仅有 headers_install/
  headers 目标，无 add_test/ctest 等价物）→ N=0 如实申报；
- 上游导出管线自带的完整性校验是 scripts/headers_install.sh 逐头
  sed 清洗 + Kbuild 层面 no-export-headers 排除（arm64 语义下
  linux/kvm_para.h 被 no-export 排除属预期），无失败即通过；
- 消费者验证由 test_package 承担（R34）：<linux/version.h> 版本一致性
  编译期断言（LINUX_VERSION_CODE == KERNEL_VERSION(6,12,77)）+ 交叉
  sysroot 下典型 UAPI 头联合编译 + 运行期断言。
"""
import os

from conan import ConanFile
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class KernelHeadersConan(ConanFile):
    name = "kernel-headers"
    version = "6.12.77"
    description = "Linux kernel UAPI (userspace API) headers from kernel.org linux-6.12.77, exported via make ARCH=arm64 headers_install pipeline"
    license = "GPL-2.0-only WITH Linux-syscall-note"
    homepage = "https://kernel.org"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("kernel", "uapi", "headers", "linux", "system")
    package_type = "header-library"
    implements = ["auto_header_only_mode"]

    # header-only：settings 声明但 binary 由 header-only 模式归一
    settings = "os", "compiler", "build_type", "arch"

    # 源码只读（不在源码树内构建，O= out-of-tree）
    no_copy_source = True

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        # 官方源（kernel.org CDN）优先，失败自动 fallback 镜像列表
        # （conan get() 原生支持 url 列表）
        get(self, **self.conan_data["sources"], strip_root=True)

    def package_id(self):
        # 纯头文件包：任何配置产出同一组头文件
        self.info.clear()

    def build(self):
        # 上游导出管线：make headers（HDRINST 阶段）。
        # 等价于 make headers_install，但末步 rsync 拷贝由配方 package()
        # 阶段的 conan copy 完成（OHOS worker 无 rsync，见 notes.md）。
        #
        # HOSTCC=clang：worker 无 gcc（仅 OHOS SDK clang），kbuild 宿主工具
        # （scripts/basic/fixdep、scripts/unifdef）用 clang 编译实测通过；
        # HOSTCC 仅为宿主侧辅助工具，不影响导出头文件的架构语义。
        # ARCH=arm64：目标架构 aarch64（asm/ wrapper 由
        # Makefile.asm-headers 从 asm-generic 生成，unistd_64 等架构头
        # 取 arm64 语义）。
        # O=<build_folder>：out-of-tree，生成树（arch/arm64/include/generated、
        # include/generated/uapi、usr/include）全部落在 build 目录，
        # 源码树保持干净。
        self.run(
            "make -j{jobs} ARCH=arm64 HOSTCC=clang O={oot} headers".format(
                jobs=os.cpu_count() or 2,
                oot=self.build_folder,
            ),
            cwd=self.source_folder,
        )

    def package(self):
        # licenses
        copy(self, "LICENSES/preferred/GPL-2.0", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "LICENSES/preferred/Linux-syscall-note", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # 头文件树：build 树 usr/include/ 下全部 *.h（HDRINST 产物，
        # rsync -mrl --include='*.h' 的等价拷贝）
        copy(self, "*.h",
             src=os.path.join(self.build_folder, "usr", "include"),
             dst=os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.set_property("cmake_file_name", "kernel-headers")
        self.cpp_info.set_property("cmake_target_name", "kernel-headers::kernel-headers")
        self.cpp_info.set_property("pkg_config_name", "kernel-headers")
        # 纯 UAPI 头：无 system_libs、无 defines、无 requires
