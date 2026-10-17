import os
import sys

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("libpcap/1.10.6")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        fixtures = os.path.join(self.source_folder, "fixtures")
        bin_ = os.path.join(self.build_folder, "test_package")
        shared = self.dependencies[self.tested_reference_str].options.shared
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries; wrap with
        # bash. CONFIG_SHELL comes from the build environment; fall back to
        # the first bash found on PATH (repo convention, see libpcap 1.10.6).
        bash = os.environ.get("CONFIG_SHELL", "bash")
        # 0. 运行时生成 pcap fixture 到构建临时目录（不回写源码目录）：
        #    裸二进制 .pcap 无法随 GitCode PR diff 传输（packetq 1.7.3 先例），
        #    仓库只保留确定性生成脚本（输出字节级可复现）。
        single_pcap = os.path.join(self.build_folder, "one_tcp_flow.pcap")
        multi_pcap = os.path.join(self.build_folder, "flows.pcap")
        self.run(f'"{sys.executable}" "{fixtures}/gen_one_tcp_flow.py" "{single_pcap}"')
        self.run(f'"{sys.executable}" "{fixtures}/gen_flows.py" "{multi_pcap}"')
        # 1. 真实消费者验证（离线 pcap，无 root/网卡）：
        #    a) 单流状态机: JUST_EST -> 双向 DATA -> CLOSE，payload 精确比对
        #    b) 多流 + 坏校验和静默丢弃 + 有效重传重组 + 选择性关闭
        self.run(f'"{bash}" -c \'{bin_} single "{single_pcap}"\'', env="conanrun")
        self.run(f'"{bash}" -c \'{bin_} multi "{multi_pcap}"\'', env="conanrun")
        # 2. HarmonyOS 专项 ELF 检查（真实工具）：ELF64/AArch64/PIE(DYN)，
        #    shared 变体须 NEEDED libnids 且无宿主 RPATH/RUNPATH；
        #    static 变体须无 NEEDED libnids（符号已静态链入）。
        readelf = "readelf"
        self.run(f'{readelf} -h "{bin_}" | grep -q "Class:.*ELF64"', env="conanrun")
        self.run(f'{readelf} -h "{bin_}" | grep -q "Machine:.*AArch64"', env="conanrun")
        self.run(f'{readelf} -h "{bin_}" | grep -q "Type:.*DYN"', env="conanrun")
        if shared:
            self.run(f'{readelf} -d "{bin_}" | grep -q "NEEDED.*libnids"', env="conanrun")
        else:
            self.run(f'{readelf} -d "{bin_}" | grep -q "NEEDED.*libnids" && exit 1 || exit 0', env="conanrun")
        self.run(f'{readelf} -d "{bin_}" | grep "RPATH\\|RUNPATH" && exit 1 || exit 0', env="conanrun")
