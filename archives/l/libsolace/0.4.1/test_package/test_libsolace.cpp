// 消费者测试（鸿蒙特有测试行，不进上游分母）。
// 只通过**已安装包头** <solace/…> 与导入目标 libsolace::libsolace 使用上游 API：
// 不 include 上游源码树、不依赖 assert/NDEBUG——全部为显式计数检查，
// 任一失败进程非零退出（R34 反空壳）。
//
// 覆盖面：链接面（getBuildVersion 是 .a 里的符号）/ Version 比较与 parse 正负两条 /
// String 构造与相等 / makeStringJoin 变参格式化 / Base64·Base16 RFC 4648 已知向量 /
// Path 组件语义 / Array 系统堆分配 / UUID 约束常量 / Optional 有无 /
// MemoryView 视图 / 进程环境 set-get-unset 往返。
#include <solace/array.hpp>
#include <solace/base16.hpp>
#include <solace/base64.hpp>
#include <solace/byteWriter.hpp>
#include <solace/env.hpp>
#include <solace/memoryView.hpp>
#include <solace/optional.hpp>
#include <solace/path.hpp>
#include <solace/string.hpp>
#include <solace/uuid.hpp>
#include <solace/version.hpp>

#include <cstdio>

using namespace Solace;

static int g_run = 0;
static int g_failed = 0;

#define CHECK(cond)                                                            \
    do {                                                                       \
        ++g_run;                                                               \
        if (!(cond)) {                                                         \
            ++g_failed;                                                        \
            std::printf("FAIL %s:%d  %s\n", __FILE__, __LINE__, #cond);        \
        }                                                                      \
    } while (false)

int main() {
    // 1. 链接面：getBuildVersion 由 libs solace 定义，能跑通即证已链到已安装包
    const Version buildVer = getBuildVersion();
    CHECK(buildVer.build.empty());
    CHECK(buildVer.majorNumber == 0);

    // 2. Version 比较
    const Version v1(1, 2, 3);
    const Version v1b(1, 2, 3);
    const Version v2(2, 0, 0);
    CHECK(v1.equals(v1b));
    CHECK(v1 != v2);
    CHECK(v1 < v2);
    CHECK(v2 > v1);

    // 3. Version::parse — 成功与失败两条路径
    const auto goodParse = Version::parse("2.0.5-alpha1");
    CHECK(goodParse.isOk());
    CHECK(goodParse.unwrap().majorNumber == 2);
    CHECK(goodParse.unwrap().minorNumber == 0);
    CHECK(goodParse.unwrap().patchNumber == 5);
    CHECK(Version::parse("x3+Bingo").isError());

    // 4. String 构造与相等
    const auto hello = makeString("hello");
    CHECK(hello.isOk());
    CHECK(hello.unwrap().size() == 5);
    CHECK(hello.unwrap().equals(StringView("hello")));

    // 5. makeStringJoin（变参格式化）
    const auto joined = makeStringJoin(',', "1", "2", "Bingo!");
    CHECK(joined.isOk());
    CHECK(joined.unwrap() == StringLiteral{"1,2,Bingo!"});

    // 6. Base64 编码（RFC 4648 已知向量 foobar → Zm9vYmFy）
    CHECK(Base64Encoder::encodedSize(6) == 8);
    byte b64buf[64];
    ByteWriter b64dest(wrapMemory(b64buf));
    Base64Encoder b64enc(b64dest);
    const char* foobar = "foobar";
    CHECK(b64enc.encode(wrapMemory(foobar, 6)).isOk());
    CHECK(b64dest.viewWritten() == wrapMemory("Zm9vYmFy", 8));

    // 7. Base16 编码（RFC 4648 已知向量 foo → 666f6f，小写）
    CHECK(Base16Encoder::encodedSize(3) == 6);
    byte b16buf[64];
    ByteWriter b16dest(wrapMemory(b16buf));
    Base16Encoder b16enc(b16dest);
    CHECK(b16enc.encode(wrapMemory("foo", 3)).isOk());
    CHECK(b16dest.viewWritten() == wrapMemory("666f6f", 6));

    // 8. Path 组件语义
    CHECK(Path::Root.getComponentsCount() == 1);
    CHECK(Path{}.getComponentsCount() == 0);
    const auto p = makePath("1", "2", "3");
    CHECK(p.isOk());
    CHECK(p.unwrap().getComponentsCount() == 3);

    // 9. Array（走系统堆 MemoryManager，实测 OHOS 分配路径）
    const auto arr = makeArray<unsigned int>(4);
    CHECK(arr.isOk());
    CHECK(arr.unwrap().size() == 4);

    // 10. UUID 约束常量
    CHECK(UUID::StaticSize == 16);
    CHECK(UUID::StringSize == 36);

    // 11. Optional 有/无
    const Optional<int> someValue = 42;
    const Optional<int> noneValue;
    CHECK(someValue.isSome());
    CHECK(*someValue == 42);
    CHECK(noneValue.isNone());

    // 12. MemoryView 视图
    CHECK(wrapMemory("abc", 3).size() == 3);
    CHECK(wrapMemory("", 0).empty());

    // 13. 进程环境 set → get → unset 真实往返（OHOS libc setenv/getenv/unsetenv）
    Env env;
    CHECK(env.set(StringView("LIBSOLACE_TEST_PACKAGE"), StringView("harmonyos")).isOk());
    const auto got = env.get(StringView("LIBSOLACE_TEST_PACKAGE"));
    CHECK(got.isSome());
    CHECK(*got == StringView("harmonyos"));
    CHECK(env.unset(StringView("LIBSOLACE_TEST_PACKAGE")).isOk());
    CHECK(env.get(StringView("LIBSOLACE_TEST_PACKAGE")).isNone());

    std::printf("libsolace consumer checks: %d run, %d failed\n", g_run, g_failed);
    return g_failed == 0 ? 0 : 1;
}
