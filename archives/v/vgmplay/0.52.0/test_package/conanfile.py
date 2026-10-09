import os
import struct

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


def make_min_vgm(path):
    """构造最小合法 VGM 1.72 文件（136 字节）：wait 静音 120 帧 + EOF。

    运行时生成而非仓库内提交二进制夹具：GitCode PR diff 对二进制文件
    生成 base85 patch，CI checkout 应用 patch 时丢失二进制数据导致
    "missing binary patch data"。改为脚本生成，diff 保持纯文本。
    """
    header = bytearray(0x84)
    header[0:4] = b"Vgm "
    struct.pack_into("<I", header, 0x04, 0x84)  # EOF offset（0x66 之后）
    struct.pack_into("<I", header, 0x08, 0x00000172)  # version 1.72
    struct.pack_into("<I", header, 0x80, 0x84)  # data offset
    data = bytes([0x61, 0x78, 0x00, 0x66])  # wait 120 frames + EOF
    with open(path, "wb") as f:
        f.write(bytes(header) + data)


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            cmake = CMake(self)
            cmake.test()
            # 非交互自检入口：--version / --lib-info / --help 不打开音频设备、
            # 不读 stdin。每条 self.run 以 grep -q 结尾，无匹配则退出码非 0。
            # 1) 版本串
            self.run("vgmplay --version | grep -q 'VGMPlay 0.52.0'", env="conanrun")
            # 2) 支持的 VGM 规范版本
            self.run("vgmplay --version | grep -q 'supports VGM 1.72'", env="conanrun")
            # 3) lib-info 横幅
            self.run("vgmplay --lib-info | grep -q 'Supported formats'", env="conanrun")
            # 4) VGM 格式引擎已注册
            self.run("vgmplay --lib-info | grep -q -- '- VGM'", env="conanrun")
            # 5) YM2612 FM 核心已链接
            self.run("vgmplay --lib-info | grep -q 'YM2612'", env="conanrun")
            # 6) 消费者用例：--help 打印用法
            self.run("vgmplay --help | grep -qi 'usage'", env="conanrun")
            # 7) 端到端解码用例：-w/--dump-wav 把最小 VGM 解码导出为 WAV
            #    （AUDDRV_WAVEWRITE 驱动，无需音频设备；断言 WAV 存在且 > 1 KiB）
            vgm = os.path.join(self.build_folder, "test.vgm")
            make_min_vgm(vgm)
            dump_dir = os.path.join(self.build_folder, "wavdump")
            os.makedirs(dump_dir, exist_ok=True)
            self.run(
                f'vgmplay -w -W "{dump_dir}" "{vgm}" 2>&1 | grep -q "Bye."',
                env="conanrun",
            )
            wav = os.path.join(dump_dir, "test.wav")
            if not os.path.exists(wav):
                raise Exception(f"WAV export failed: {wav} not found")
            if os.path.getsize(wav) < 1024:
                raise Exception(f"WAV export suspiciously small: {os.path.getsize(wav)} bytes")
