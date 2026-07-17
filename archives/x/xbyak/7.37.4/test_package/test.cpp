#include <stdio.h>
#include <xbyak/xbyak.h>

/* R34 反空壳：验证头文件真实可被预处理且定义了 Xbyak API 符号 */

class TestGen : public Xbyak::CodeGenerator {
public:
    TestGen() : Xbyak::CodeGenerator(Xbyak::DEFAULT_MAX_CODE_SIZE, Xbyak::DontSetProtectRWE) {}
};

int main(void) {
    /* 验证 CodeGenerator 可实例化（不涉及 JIT 执行） */
    TestGen gen;
    /* 验证版本号宏：VERSION = 0x7374 对应 7.37.4 */
    if (gen.getVersion() != Xbyak::VERSION) {
        fprintf(stderr, "version mismatch: %d != %d\n", gen.getVersion(), Xbyak::VERSION);
        return 1;
    }
    /* 验证 getSize() 初始为 0（未生成任何指令） */
    if (gen.getSize() != 0) {
        fprintf(stderr, "size should be 0, got %zu\n", gen.getSize());
        return 1;
    }
    printf("xbyak: version=0x%08X, getSize=%zu, CodeGenerator instantiation ok\n",
           gen.getVersion(), gen.getSize());
    printf("xbyak.h standalone test PASSED.\n");
    return 0;
}
