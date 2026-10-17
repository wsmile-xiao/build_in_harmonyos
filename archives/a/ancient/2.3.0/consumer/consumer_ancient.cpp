/*
 * 消费者验证用例：模拟业务上层组件/应用（复古游戏资源解包服务），
 * 仅通过 ancient 库第三方使用者视角使用该库 —— 只包含已安装的公开头文件
 * <ancient/ancient.hpp>、只调用公开 API（ancient::Decompressor::detect /
 * ancient::Decompressor 构造 / getRawSize / decompress / getName）、正常链接
 * -lancient，并使用运行时产物（libancient.so）。不引用库私有头文件、不调用
 * 内部符号、不复用库内部测试构建目录。
 *
 * 场景：游戏模拟器需要解包旧平台压缩资源（如 Amiga ICE 打包的关卡数据），
 * 本组件读入打包文件，用公开 API 解压后落盘，并输出解压格式名与原始大小
 * 作为可观察结果。
 */
#include <cstdio>
#include <cstdlib>
#include <cstdint>
#include <fstream>
#include <iterator>
#include <string>
#include <vector>

#include <ancient/ancient.hpp>

int main(int argc, char **argv)
{
    if (argc != 3) {
        fprintf(stderr, "usage: consumer_ancient <packed-file> <out-file>\n");
        return 2;
    }
    const char *inPath = argv[1];
    const char *outPath = argv[2];

    // 读入打包文件
    std::ifstream ifs(inPath, std::ios::binary);
    if (!ifs) {
        fprintf(stderr, "consumer: cannot open %s\n", inPath);
        return 1;
    }
    std::vector<uint8_t> packed((std::istreambuf_iterator<char>(ifs)),
                                std::istreambuf_iterator<char>());
    ifs.close();

    if (!ancient::Decompressor::detect(packed)) {
        fprintf(stderr, "consumer: %s is not a recognized compressed format\n", inPath);
        return 1;
    }

    std::vector<uint8_t> raw;
    std::string fmtName;
    try {
        ancient::Decompressor dec(packed, true, true);
        fmtName = dec.getName();
        raw = dec.decompress(true);
    } catch (const ancient::Error &e) {
        fprintf(stderr, "consumer: decompression failed: %s\n", e.what());
        return 1;
    }

    // 落盘
    std::ofstream ofs(outPath, std::ios::binary | std::ios::trunc);
    if (!ofs) {
        fprintf(stderr, "consumer: cannot write %s\n", outPath);
        return 1;
    }
    ofs.write(reinterpret_cast<const char *>(raw.data()), raw.size());
    ofs.close();

    // 可观察结果
    printf("consumer: format=%s packed=%zu raw=%zu -> %s\n",
           fmtName.c_str(), packed.size(), raw.size(), outPath);
    return 0;
}
