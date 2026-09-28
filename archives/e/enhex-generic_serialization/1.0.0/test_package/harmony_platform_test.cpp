// Harmony-Specific Test — enhex-generic_serialization 1.0.0
//
// rule12 鸿蒙特有测试：验证明确的鸿蒙 PC (OHOS aarch64) 行为，而非仅编译通过。
// r03 修复：正确性校验不依赖 assert（NDEBUG 下不再被剥离），
// 失败路径显式 return 1 并在 stderr 打印字段名/期望值/实际值。
// 本入口与既有 test_package/test.cpp（通用消费者往返测试）去重：
//  - test.cpp: 仅验证 gs::serializer 的通用序列化往返（POD + 组合结构）。
//  - harmony_platform_test.cpp: 验证鸿蒙平台语义 ——
//      A) OHOS 平台标识（uname 系统属性，HongMeng Kernel aarch64）纳入被测数据，
//         经序列化→落盘→读回→反序列化后逐字节不变（平台数据完整性）；
//      B) OHOS /tmp 只读 (EROFS) 语义探测：/tmp 直接创建失败 → 回退 $TMPDIR 写入，
//         核验回退策略与实际写入位置（$TMPDIR 而非 /tmp）；
//      C) HMDFS 归档写入/替换语义：对已存在文件先移除再写入（安全策略）并核验
//         字节完整性（写后读回逐字节一致）。
// 入口名/文件名与 test_package/test.cpp 不同（harmony_platform_test.cpp），
// 为独立新增文件，调用被测库公开 API gs::serializer / gs::serialize 重载。
#include <gs/binary.h>

#include <sys/utsname.h>

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

namespace {

// 被测平台标识（uname 系统属性 = OHOS 平台实测值）
std::string GetPlatformIdentity() {
    struct utsname buf;
    if (uname(&buf) != 0) {
        return "<uname-failed>";
    }
    std::string id = std::string(buf.sysname) + "|" + std::string(buf.release) +
                     "|" + std::string(buf.version) + "|" + std::string(buf.machine);
    return id;
}

struct PlatformRecord {
    int magic = 0;
    float pi = 0.0f;
    char tag[16];
    // 平台标识以定长字符数组纳入被测数据（POD 化，避免指针跨进程问题）
    char platform[128];
};

void InitRecord(PlatformRecord& r, const std::string& platform) {
    r.magic = 0x5A5A;
    r.pi = 3.14159265f;
    std::strncpy(r.tag, "os-roundtrip", sizeof(r.tag) - 1);
    r.tag[sizeof(r.tag) - 1] = '\0';
    std::strncpy(r.platform, platform.c_str(), sizeof(r.platform) - 1);
    r.platform[sizeof(r.platform) - 1] = '\0';
}

// POD 结构：逐字节二进制序列化（含平台标识）
bool LikelyOk(const PlatformRecord& r) {
    return r.magic == 0x5A5A;
}

}  // namespace

namespace gs {
template <typename Stream>
void serialize(Stream& stream, PlatformRecord& value) {
    gs::read_or_write_bytes(stream, value);
}
}  // namespace gs

// 模板实例化点必须在 serialize 重载声明之后（二阶段查找/ADL，同上游 example.cpp）
#include <gs/serializer.h>

// 返回实际使用的写入目录（探测 /tmp 只读后回退 $TMPDIR）
static std::string PickWritableTmpDir(bool* tmp_is_ro) {
    *tmp_is_ro = false;
    // A) 探测 OHOS /tmp 只读语义
    {
        std::ofstream probe("/tmp/.gs-probe", std::ios::binary);
        if (!probe) {
            *tmp_is_ro = true;
        }
    }
    // B) 回退策略：/tmp 只读 → $TMPDIR（init-build 环境 TMPDIR=/storage/Users/currentUser/tmp）
    const char* tmpdir = std::getenv("TMPDIR");
    if (tmpdir == nullptr || tmpdir[0] == '\0') {
        tmpdir = "/storage/Users/currentUser/tmp";  // SKILL 规定 $TMPDIR 兜底偏好
    }
    return std::string(tmpdir);
}

int main() {
    // 1. 平台标识实测（uname）
    const std::string platform = GetPlatformIdentity();
    std::cout << "[harmony] platform identity: " << platform << std::endl;

    // 2. OHOS 临时目录语义：/tmp 只读探测 + $TMPDIR 回退
    bool tmp_is_ro = false;
    const std::string dir = PickWritableTmpDir(&tmp_is_ro);
    std::cout << "[harmony] /tmp read-only(EROFS): "
              << (tmp_is_ro ? "yes" : "no") << "; writable dir: "
              << dir << std::endl;
    CHECK(tmp_is_ro, "tmp-erofs", "yes", (tmp_is_ro ? "yes" : "no"));
    CHECK(!dir.empty() && dir != "/tmp", "writable-dir-not-tmp",
          "!= /tmp", dir);

    // 3. 归档写入/替换安全策略：已有文件先移除再写入（HMDFS 软链接替换需 rm 后 ln）
    const std::string path = dir + "/gs-harmony-platform.bin";
    std::remove(path.c_str());  // 写前清理（可重复运行）
    {
        std::ofstream f(path, std::ios::binary);
        CHECK(f.good(), "open-ofstream", "good", "bad");
        PlatformRecord rec;
        InitRecord(rec, platform);
        gs::serializer(f, rec);
    }

    // 4. 读回 + 反序列化 + 逐字段校验（含平台标识逐字节不变）
    {
        std::ifstream f(path, std::ios::binary);
        CHECK(f.good(), "open-ifstream", "good", "bad");
        PlatformRecord out;
        std::memset(&out, 0, sizeof(out));
        gs::serializer(f, out);
        CHECK(LikelyOk(out), "magic-ok", "0x5A5A",
              std::to_string(out.magic));
        CHECK(out.magic == 0x5A5A, "magic", "46602",
              std::to_string(out.magic));
        CHECK(out.pi > 3.14159f && out.pi < 3.14160f, "pi", "3.14159..3.14160",
              std::to_string(out.pi));
        CHECK(std::strcmp(out.tag, "os-roundtrip") == 0, "tag", "os-roundtrip",
              std::string(out.tag));
        // 鸿蒙平台标识经序列化往返后逐字节不变
        CHECK(std::strcmp(out.platform, platform.c_str()) == 0, "platform-id",
              platform, std::string(out.platform));
    }

    // 5. 字节完整性：文件内容非空且与写出大小一致（POD 结构定长）
    {
        std::ifstream f(path, std::ios::binary | std::ios::ate);
        CHECK(f.good(), "open-size", "good", "bad");
        const std::streamsize sz = f.tellg();
        CHECK(sz == static_cast<std::streamsize>(sizeof(PlatformRecord)),
              "file-size", std::to_string(sizeof(PlatformRecord)),
              std::to_string(sz));
    }

    std::cout << "[harmony] checks=" << g_checks
              << " failures=" << g_failures << std::endl;
    if (g_failures != 0) {
        std::cerr << "[harmony] harmony-specific test FAILED" << std::endl;
        return 1;
    }
    std::cout << "[harmony] harmony-specific test PASS (" << platform << ")"
              << std::endl;
    return 0;
}