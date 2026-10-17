// test_oaknut.cpp — oaknut 1.2.2-git20240301.94c726c header-only 消费者测试
// 验证 <oaknut/oaknut.hpp> 可包含、CodeGenerator/VectorCodeGenerator 指令编码正确、
// PageOffset 页偏移编码正确。全部为确定性编码断言，不依赖 JIT 可执行内存与 Catch2，
// 可在任意架构编译运行。编码向量取自上游 tests/general.cpp、tests/basic.cpp 与 README。
#include <cstdint>
#include <cstdio>
#include <vector>

#include <oaknut/oaknut.hpp>

using namespace oaknut;
using namespace oaknut::util;

// 宏 CHECK 无法直接接受含逗号的模板实参，用别名规避宏参数拆分
using PageOffset212 = PageOffset<21, 12>;

static int failures = 0;

#define CHECK(cond)                                                     \
    do {                                                                \
        if (!(cond)) {                                                  \
            std::fprintf(stderr, "FAIL(%d): %s\n", __LINE__, #cond);    \
            ++failures;                                                 \
        }                                                               \
    } while (0)

int main() {
    std::uint32_t insn = 0;

    // ── 1. 单指令编码（CodeGenerator 写入单个 uint32_t，上游 general.cpp T() 向量）──
    {
        CodeGenerator code{&insn};
        code.MOV(W0, 42);  // MOVZ W0, #42 (32-bit MOVZ, sf=0)
        CHECK(insn == 0x52800540u);
    }
    {
        CodeGenerator code{&insn};
        code.RET();  // RET X30
        CHECK(insn == 0xd65f03c0u);
    }
    {
        CodeGenerator code{&insn};
        code.ADC(W3, W14, W15);
        CHECK(insn == 0x1a0f01c3u);
    }
    {
        CodeGenerator code{&insn};
        code.ADD(X8, X21, 2066);
        CHECK(insn == 0x91204aa8u);
    }
    {
        CodeGenerator code{&insn};
        code.AND(W20, W18, 0x3e000000);
        CHECK(insn == 0x12071254u);
    }

    // ── 2. PageOffset 页偏移编码（上游 tests/basic.cpp 已验证向量，无 JIT）──
    CHECK(PageOffset212::encode(0x0000000088e74000, 0xffffffffd167dece) == 0xd2202u);
    CHECK(PageOffset212::encode(0x0001000000000002, 0x0001000000000001) == 0u);
    CHECK(PageOffset212::encode(0x0001000000000001, 0x0001000000000002) == 0u);
    CHECK(PageOffset212::encode(0x0001000000001000, 0x0001000000000fff) == 0x1fffffu);
    CHECK(PageOffset212::encode(0x0001000000000fff, 0x0001000000001000) == 0x080000u);

    // ── 3. VectorCodeGenerator 多指令发射（README 示例）──
    {
        std::vector<std::uint32_t> vec;
        VectorCodeGenerator code{vec};
        code.MOV(W0, 42);
        code.RET();
        CHECK(vec.size() == 2);
        CHECK(vec[0] == 0x52800540u);
        CHECK(vec[1] == 0xd65f03c0u);
    }

    if (failures != 0) {
        std::fprintf(stderr, "FAIL: %d assertion(s) failed\n", failures);
        return 1;
    }
    std::printf("PASS: oaknut header-only 库指令编码验证通过\n");
    return 0;
}
