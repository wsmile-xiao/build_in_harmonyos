// test_package 消费者测试 — 真实调用 gs 序列化 API（R34）
// r03 修复：正确性校验不依赖 assert（NDEBUG 下不再被剥离），
// 失败路径显式 return 1 并在 stderr 打印字段名/期望值/实际值。
// 结构对齐上游官方 test_package/example.cpp：先包含 gs/binary.h、
// 声明 gs::serialize 重载，再包含 gs/serializer.h（模板实例化点前可见）。
#include <gs/binary.h>

#include <cstring>
#include <fstream>
#include <iostream>
#include <string>

// 无条件校验宏：不随 NDEBUG 失效，失败时打印定位信息并记数
static int g_checks = 0;
static int g_failures = 0;

#define CHECK(cond, what, expected, actual)                                \
    do {                                                                   \
        ++g_checks;                                                        \
        if (!(cond)) {                                                     \
            ++g_failures;                                                  \
            std::cerr << "FAIL: " << what << " expected=" << expected      \
                      << " actual=" << actual << std::endl;                \
        }                                                                  \
    } while (0)

struct Vector3 {
    float x, y, z;
};

namespace gs {
template <typename Stream>
void serialize(Stream& stream, Vector3& value) {
    gs::read_or_write_bytes(stream, value);
}
}  // namespace gs

struct Record {
    int x = 0;
    float y = 0;
    char z[3];
    Vector3 vec3;
};

namespace gs {
template <typename Stream>
void serialize(Stream& stream, Record& value) {
    gs::serializer(stream, value.x, value.y, value.z, value.vec3);
}
}  // namespace gs

#include <gs/serializer.h>

int main() {
    Record src;
    src.x = 5;
    src.y = 7.5f;
    src.z[0] = 'a';
    src.z[1] = 'b';
    src.z[2] = '\0';
    src.vec3 = {1.0f, 2.0f, 3.0f};

    // 序列化到文件
    {
        std::ofstream f("gs-test.bin", std::ios::binary);
        CHECK(f.good(), "open-ofstream", "good", "bad");
        gs::serializer(f, src);
    }

    // 清零后反序列化读回
    Record dst;
    std::memset(&dst, 0, sizeof(dst));
    {
        std::ifstream f("gs-test.bin", std::ios::binary);
        CHECK(f.good(), "open-ifstream", "good", "bad");
        gs::serializer(f, dst);
    }

    // 逐字段校验往返一致（9 项无条件校验，含文件打开状态）
    CHECK(dst.x == 5, "dst.x", "5", std::to_string(dst.x));
    CHECK(dst.y == 7.5f, "dst.y", "7.5", std::to_string(dst.y));
    CHECK(dst.z[0] == 'a', "dst.z[0]", "'a'", std::string(1, dst.z[0]));
    CHECK(dst.z[1] == 'b', "dst.z[1]", "'b'", std::string(1, dst.z[1]));
    CHECK(dst.z[2] == '\0', "dst.z[2]", "'\\0'", std::string(1, dst.z[2]));
    CHECK(dst.vec3.x == 1.0f, "dst.vec3.x", "1.0", std::to_string(dst.vec3.x));
    CHECK(dst.vec3.y == 2.0f, "dst.vec3.y", "2.0", std::to_string(dst.vec3.y));
    CHECK(dst.vec3.z == 3.0f, "dst.vec3.z", "3.0", std::to_string(dst.vec3.z));

    // 字节完整性：文件大小与序列化实际写入字节一致
    // （gs 逐字段写入：int 4 + float 4 + char[3] 3 + Vector3 12 = 23，
    //   不含结构体尾部对齐填充，故期望值为 23 而非 sizeof(Record)=24）
    {
        std::ifstream f("gs-test.bin", std::ios::binary | std::ios::ate);
        const std::streamsize sz = f.tellg();
        const std::streamsize expected_size =
            sizeof(src.x) + sizeof(src.y) + sizeof(src.z) + sizeof(src.vec3);
        CHECK(sz == expected_size,
              "file-size", std::to_string(expected_size), std::to_string(sz));
    }

    std::cout << "checks=" << g_checks << " failures=" << g_failures
              << std::endl;
    if (g_failures != 0) {
        std::cerr << "generic_serialization roundtrip FAILED" << std::endl;
        return 1;
    }
    std::cout << "generic_serialization roundtrip OK" << std::endl;
    return 0;
}