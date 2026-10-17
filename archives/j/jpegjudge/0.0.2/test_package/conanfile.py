import base64
import os

from conan import ConanFile

# 真实 JPEG 夹具：由 IJG libjpeg 编码器生成的灰度图，
# 生成程序、参数与逐文件 sha256 见版本级 notes.md「消费者测试夹具」一节。
# 以 base64 内联是为了让 conan create / CI 不依赖任何 Python 图像绑定。

_B64_HI = (
    "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAMCAgMCAgMDAwMEAwMEBQgFBQQEBQoHBwYI"
    "DAoMDAsKCwsNDhIQDQ4RDgsLEBYQERMUFRUVDA8XGBYUGBIUFRT/wAALCAAgACABAREA"
    "/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQA"
    "AAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJico"
    "KSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKT"
    "lJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo"
    "6erx8vP09fb3+Pn6/9oACAEBAAA/AF8qGflD5Leq9Pypu+a15cZX++vIpxENzz/q3P8A"
    "Ev8AUU0ia25/1iD+Jf6ilMEcvzRN5Ten8J/woE0tqQJAQOzDkGl8qGflD5Leq9Pypu+a"
    "15cZX++vIpfsyNzA+w/3WOR+dAuJIDsmQgHjB5B/xoMEcvzRN5Ten8J/woE0tqQJAQOz"
    "DkGg238UD/8AAGP8jQLoofLmT6qw4NH2ZG5gfYf7rHI/OgXEkB2TIQDxg8g/41//2Q=="
)

_B64_LO = (
    "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDABsSFBcUERsXFhceHBsgKEIrKCUlKFE6PTBC"
    "YFVlZF9VXVtqeJmBanGQc1tdhbWGkJ6jq62rZ4C8ybqmx5moq6T/wAALCAAgACABAREA"
    "/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQA"
    "AAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJico"
    "KSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKT"
    "lJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo"
    "6erx8vP09fb3+Pn6/9oACAEBAAA/ADAPtRyKODRyKMA9OKMkdaMA+1HIox6UZx1owD04"
    "oyR1ox6UZ7GjHpRnHWv/2Q=="
)

_B64_FLAT = (
    "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAMCAgMCAgMDAwMEAwMEBQgFBQQEBQoHBwYI"
    "DAoMDAsKCwsNDhIQDQ4RDgsLEBYQERMUFRUVDA8XGBYUGBIUFRT/wAALCAAgACABAREA"
    "/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQA"
    "AAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJico"
    "KSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKT"
    "lJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo"
    "6erx8vP09fb3+Pn6/9oACAEBAAA/ACiiiiiiiiiiiiiiiv/Z"
)

_B64_TINY = (
    "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAMCAgMCAgMDAwMEAwMEBQgFBQQEBQoHBwYI"
    "DAoMDAsKCwsNDhIQDQ4RDgsLEBYQERMUFRUVDA8XGBYUGBIUFRT/wAALCAAEAAQBAREA"
    "/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQA"
    "AAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJico"
    "KSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKT"
    "lJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo"
    "6erx8vP09fb3+Pn6/9oACAEBAAA/ALMdhDtHy1//2Q=="
)

FIXTURES = {
    "hi_noise.jpg": _B64_HI,
    "lo_noise.jpg": _B64_LO,
    "flat.jpg": _B64_FLAT,
    "tiny_4x4.jpg": _B64_TINY,
}


class JpegjudgeTestConan(ConanFile):
    """test_package for jpegjudge —— 真实 JPEG 输入 + 真实执行 + 真实断言。

    被测对象是命令行工具（不导出库 API），所以消费者测试以「使用者」身份
    执行安装出来的 judge 二进制，用退出码与判定值断言行为；
    36 条断言集中在同目录的 test_jpegjudge.sh，本文件负责
    落夹具、定位二进制、真运行，并让脚本退出码决定本测试成败。

    夹具是 IJG libjpeg 编码器真实生成的 4 个灰度 JPEG（32x32 高/低质量、
    32x32 纯色、4x4 边界），生成程序与逐文件 sha256 见版本级 notes.md
    「消费者测试夹具」一节；这里内联字节是为了让 conan create / CI
    不依赖任何图像库 Python 绑定。
    """
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        for name, blob in FIXTURES.items():
            with open(os.path.join(self.source_folder, name), "wb") as handle:
                handle.write(base64.b64decode(blob))

    def test(self):
        judge = os.path.join(
            self.dependencies["jpegjudge"].cpp_info.bindirs[0], "judge")
        script = os.path.join(self.source_folder, "test_jpegjudge.sh")
        # OHOS 的 /system/bin/sh 不能直接 exec ELF，统一用 bash 包裹执行
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f'{bash} "{script}" "{judge}" "{self.source_folder}"',
                 env="conanrun")
