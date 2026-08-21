/* asmjit test_package — 真实功能断言
 *
 * 验证 asmjit 的核心 JIT 流程：
 *   1. JitRuntime + CodeHolder 初始化
 *   2. AArch64 Compiler 生成函数（int f() { return 42; }）
 *   3. 通过 JitRuntime 将机器码复制到可执行内存
 *   4. 通过函数指针调用生成的代码并验证返回值
 *
 * API 用法参照上游 test/asmjit_test_compiler.cpp:232：
 *   a64::Compiler cc(&code)  （构造时传入 CodeHolder*）
 *   cc.addFunc(FuncSignatureT<int>())  （返回 int 无参数）
 */
#include <asmjit/asmjit.h>
#include <asmjit/core.h>
#include <asmjit/a64.h>

#include <cstdio>
#include <cstdint>

typedef int (*Func)(void);

static int fail(const char *what, int got, int want)
{
    std::printf("FAIL %s: got %d, want %d\n", what, got, want);
    return 1;
}

int main(void)
{
    using namespace asmjit;

    /* ① 初始化 JitRuntime（可执行内存分配器） */
    JitRuntime rt;

    /* ② 初始化 CodeHolder（机器码缓冲区），关联到 JIT 环境 */
    CodeHolder code;
    code.init(rt.environment());

    /* ③ 初始化 AArch64 Compiler，构造时关联 CodeHolder */
    a64::Compiler cc(&code);

    /* ④ 声明函数签名：int f(void)，使用宿主平台调用约定 */
    cc.addFunc(FuncSignatureT<int>());

    /* ⑤ 分配虚拟寄存器，赋值 42，返回 */
    arm::Gp ret = cc.newInt32("ret");
    cc.mov(ret, 42);
    cc.ret(ret);

    cc.endFunc();
    cc.finalize();

    /* ⑥ 将 Compiler 生成的机器码复制到 JIT 可执行内存 */
    Func fn = nullptr;
    Error err = rt.add(&fn, &code);
    if (err != kErrorOk) {
        std::printf("FAIL JitRuntime::add 失败: error=%d\n", (int)err);
        return 1;
    }

    /* ⑦ 调用 JIT 生成的函数并验证返回值 */
    int result = fn();
    if (result != 42) {
        rt.release(fn);
        return fail("JIT 函数返回值", result, 42);
    }

    /* ⑧ 释放 JIT 内存 */
    rt.release(fn);

    /* ⑨ 验证版本宏存在且合理（ASMJIT_LIBRARY_VERSION = major<<16 | minor<<8 | patch） */
    int ver = ASMJIT_LIBRARY_VERSION;
    int major = (ver >> 16) & 0xFF;
    int minor = (ver >> 8) & 0xFF;
    int patch = ver & 0xFF;
    std::printf("asmjit OK: JIT 函数返回值正确 (42)，版本 %d.%d.%d\n",
                major, minor, patch);
    return 0;
}
