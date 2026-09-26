#!/usr/bin/env python3
"""test_package for aghermann 1.1.2 — R34: 实质调用被测包二进制。

aghermann 是 application（GUI + CLI 工具），产物含 bin/edfcat、bin/edfhed、
bin/agh-profile-gen 等。本测试实际执行 edfhed 处理一个按 EDF 规范构造的
最小 EDF 文件（2 通道、各 8 样本），并断言其解析出 2 通道，
验证包内二进制 + 依赖共享库（libsigfile 等）可加载运行。
"""
import os

from conan import ConanFile
from conan.tools.env import VirtualRunEnv
from conan.tools.files import copy


class AghermannTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        # 测试源文件（.sh）必须随 test_package 一起导出：CI L0c 门禁要求
        # test_package/ 下存在 .c/.cpp/.cc/.cxx/.sh/.py 测试源（E308/E255）。
        copy(self, "test_edf.sh", src=self.recipe_folder, dst=self.export_sources_folder)
        copy(self, "test_ohos.sh", src=self.recipe_folder, dst=self.export_sources_folder)

    def requirements(self):
        # 声明对被测包的依赖（conan create 时注入 tested_reference_str）
        self.requires(self.tested_reference_str)

    def generate(self):
        VirtualRunEnv(self).generate()

    def build(self):
        pass

    def test(self):
        # R34: 必须实质执行被测包二进制（禁止空壳 print）。
        # 按 EDF 规范构造最小文件（2 通道、各 8 样本/记录、1 个数据记录）：
        # 头布局与 libsigfile edf.hh SEDFHeader 一致——version@0[8],
        # patient@8[80], recording@88[80], date@168[8], time@176[8],
        # header_length@184[8], reserved@192[44], n_data_records@236[8],
        # data_record_size@244[8], n_channels@252[4], 通道@256 起每通道 256B
        # (label[16] transducer[80] physical_dim[8] physical_min[8]
        #  physical_max[8] digital_min[8] digital_max[8] filtering[80]
        #  samples_per_record[8] reserved[32]).
        n_ch = 2
        header_length = 256 + n_ch * 256
        header = bytearray(header_length)
        header[0:8] = b"0       "                       # version
        header[8:88] = b"Test Patient ID X X X X".ljust(80, b" ")
        header[88:168] = b"Test Recording".ljust(80, b" ")
        header[168:176] = b"01.01.20"                   # recording date
        header[176:184] = b"01.01.20"                   # recording time
        header[184:192] = str(header_length).encode().ljust(8, b" ")
        header[236:244] = b"1".ljust(8, b" ")           # n_data_records
        header[244:252] = b"1".ljust(8, b" ")           # data_record_size (s)
        header[252:256] = str(n_ch).encode().ljust(4, b" ")
        for ch in range(n_ch):
            base = 256 + ch * 256
            header[base:base + 16] = ("EEG-C%d" % (ch + 1)).encode().ljust(16, b" ")
            header[base + 16:base + 96] = b"uV".ljust(80, b" ")   # transducer
            header[base + 96:base + 104] = b"uV".ljust(8, b" ")   # physical_dim
            header[base + 104:base + 112] = b"0".ljust(8, b" ")   # physical_min
            header[base + 112:base + 120] = b"1".ljust(8, b" ")   # physical_max
            header[base + 120:base + 128] = b"-2048".ljust(8, b" ")  # digital_min
            header[base + 128:base + 136] = b"2047".ljust(8, b" ")   # digital_max
            header[base + 136:base + 216] = b"".ljust(80, b" ")      # filtering
            header[base + 216:base + 224] = b"8".ljust(8, b" ")      # samples_per_record
        data = bytearray()
        for ch in range(n_ch):
            # 8 samples/record, int16: 0,16,32,48,64,80,96,112
            data += bytes([0, 0, 16, 0, 32, 0, 48, 0, 64, 0, 80, 0, 96, 0, 112, 0])
        # EDF 是二进制，用标准 open(...,"wb") 写（conan save() 只写 str）。
        with open(os.path.join(self.build_folder, "minimal.edf"), "wb") as fh:
            fh.write(bytes(header) + bytes(data))

        bin_dir = os.path.join(self.dependencies["aghermann"].package_folder, "bin")
        # R34/L0d: self.run() 调用测试源脚本 test_edf.sh（L0c 测试源文件，
        # 否则 CI 报 'no_test_sources' 门禁失败，见 E255/E308），脚本内部
        # 实际执行 bin/edfhed 解析 2 通道 EDF 并断言输出（非空壳）。
        edf_file = os.path.join(self.build_folder, "minimal.edf")
        script = os.path.join(self.source_folder, "test_edf.sh")
        shell = os.environ.get("CONFIG_SHELL") or "/bin/sh"
        self.run('"{}" "{}" "{}" "{}"'.format(shell, script, bin_dir, edf_file), env="conanrun")
        self.output.info("edfhed parsed minimal EDF OK (R34 substantive test passed)")

        # rule12 鸿蒙特有测试：在 OpenHarmony 目标上追加平台断言
        # （平台三元组 / ELF64 指针宽度 / 动态依赖闭合），由 test_ohos.sh 执行。
        ohos_script = os.path.join(self.source_folder, "test_ohos.sh")
        if os.path.isfile(ohos_script):
            self.run('"{}" "{}" "{}" "{}"'.format(shell, ohos_script, bin_dir, edf_file), env="conanrun")
            self.output.info("HarmonyOS-specific test OK (rule12: triplet/pointer-width/dep-closure)")
