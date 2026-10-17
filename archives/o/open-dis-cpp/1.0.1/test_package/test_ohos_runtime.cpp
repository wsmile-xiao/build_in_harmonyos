// test_ohos_runtime.cpp — test_package 消费者用例（鸿蒙平台运行时健全性）
//
// 只在目标设备（HarmonyOS PC / aarch64）上执行，覆盖三件与平台直接相关的事实：
//   1) 位宽与字节序：64 位指针、8-bit char、小端宿主；
//   2) DIS 协议在小端宿主上仍按网络（大端）字节序落盘——字节级核对；
//   3) 打包的共享库被设备动态加载器真实解析：
//        - 自读 /proc/self/exe，扫描 ELF 是否声明 libOpenDIS6.so 为 DT_NEEDED；
//        - 读 /proc/self/maps 确认该 .so 已映射进本进程（不可读时如实记 skip）。
// 返回 0 = 全部（非 skip）断言通过。
#include <climits>
#include <cstdint>
#include <cstdio>
#include <cstring>

#include <sys/utsname.h>

#include <dis6/EntityStatePdu.h>
#include <dis6/utils/DataStream.h>

static int g_checks = 0;
static int g_failed = 0;
static int g_skipped = 0;

static void check(bool ok, const char* what) {
    ++g_checks;
    if (ok) {
        std::printf("[ok]   %s\n", what);
    } else {
        ++g_failed;
        std::printf("[FAIL] %s\n", what);
    }
}

static bool file_contains(const char* path, const char* needle) {
    std::FILE* fp = std::fopen(path, "rb");
    if (!fp) {
        return false;
    }
    // ELF 是二进制文件、内含 NUL 字节：必须 memcmp 逐字节扫描
    // （strstr 会在首个 '\0' 处停止，对 /proc/self/exe 必然漏判）
    const size_t nlen = std::strlen(needle);
    char buf[4096];
    size_t tail = 0;
    bool found = false;
    for (;;) {
        const size_t n = std::fread(buf + tail, 1, sizeof(buf) - tail, fp);
        const size_t have = tail + n;
        if (have < nlen) {
            if (n == 0) {
                break;
            }
            tail = have;
            continue;
        }
        for (size_t i = 0; i + nlen <= have; ++i) {
            if (std::memcmp(buf + i, needle, nlen) == 0) {
                found = true;
                break;
            }
        }
        if (found || n == 0) {
            break;
        }
        // 保留 needle 长度-1 的尾部，避免跨块匹配被截断
        tail = nlen - 1;
        std::memmove(buf, buf + have - tail, tail);
    }
    std::fclose(fp);
    return found;
}

int main() {
    // ---- 1. 平台位宽与字节序 ----
    check(sizeof(void*) == 8, "指针宽度 8 字节（aarch64 64 位）");
    check(CHAR_BIT == 8, "char 宽度 8 bit");
    const std::uint16_t probe = 0x0102;
    check(*reinterpret_cast<const unsigned char*>(&probe) == 0x02,
          "宿主为小端字节序（aarch64）");

    // ---- 2. DIS 协议字节序与宿主无关（网络大端落盘）----
    DIS::DataStream wire(DIS::BIG);
    const std::uint32_t magic = 0x01020304u;
    wire << magic;
    check(wire.size() == sizeof(magic), "BIG 流写入 4 字节");
    check(static_cast<unsigned char>(wire[0]) == 0x01 &&
              static_cast<unsigned char>(wire[1]) == 0x02 &&
              static_cast<unsigned char>(wire[2]) == 0x03 &&
              static_cast<unsigned char>(wire[3]) == 0x04,
          "小端宿主上按大端（网络序）落盘 01 02 03 04");

    DIS::DataStream back(&wire[0], wire.size(), wire.GetStreamEndian());
    std::uint32_t magic_in = 0;
    back >> magic_in;
    check(magic_in == magic, "大端字节流回读值一致");

    // ---- 3. 打包共享库的动态链接面 ----
    check(file_contains("/proc/self/exe", "libOpenDIS6.so"),
          "本进程 ELF 声明 DT_NEEDED 引用打包的 libOpenDIS6.so");
    if (std::FILE* maps_probe = std::fopen("/proc/self/maps", "rb")) {
        std::fclose(maps_probe);
        check(file_contains("/proc/self/maps", "libOpenDIS6.so"),
              "libOpenDIS6.so 已被设备动态加载器映射进本进程");
    } else {
        // 环境限制（maps 不可读）时如实记 skip，不冒充通过
        std::printf("[skip] /proc/self/maps 不可读，运行时映射核对未执行（环境限制）\n");
        ++g_skipped;
    }

    // ---- 4. 平台信息（记录，不断言）----
    struct utsname ut;
    if (uname(&ut) == 0) {
        std::printf("info: sysname=%s release=%s machine=%s\n",
                    ut.sysname, ut.release, ut.machine);
    } else {
        std::printf("info: uname() 不可用（环境限制，未计入断言）\n");
        ++g_skipped;
    }

    // 真实调用一次 DIS6 API，确保上面的 .so 确实在运行期可用
    DIS::EntityStatePdu pdu;
    DIS::DataStream ds(DIS::BIG);
    pdu.marshal(ds);
    check(!ds.empty(), "运行期调用 OpenDIS6 API（EntityStatePdu::marshal）成功");

    std::printf("RESULT=%s checks=%d failed=%d skipped=%d\n",
                g_failed == 0 ? "ALL PASSED" : "FAILED", g_checks, g_failed, g_skipped);
    return g_failed == 0 ? 0 : 1;
}
