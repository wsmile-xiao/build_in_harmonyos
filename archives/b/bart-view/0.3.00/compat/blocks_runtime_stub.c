/* compat/blocks_runtime_stub.c — minimal BlocksRuntime for HarmonyOS
 *
 * 鸿蒙无 libBlocksRuntime。BART 头文件（misc/nested.h）用 clang blocks
 * 实现嵌套函数，编译需 -fblocks，链接需 _NSConcreteStackBlock /
 * _Block_object_assign / _Block_object_dispose 等符号。BART 的 blocks 用法
 * 为栈上块立即调用（NESTED_CALL），不跨作用域复制，故提供最小实现。
 * 与 bart/1.0.00 recipe 的 compat 文件一致。
 */
#include <stdlib.h>

/* clang blocks ABI: block layout isa 指针 */
void *_NSConcreteStackBlock = 0;
void *_NSConcreteMallocBlock = 0;
void *_NSConcreteGlobalBlock = 0;

void *_Block_copy(const void *aBlock)
{
    /* 不复制——blocks 均在栈上立即调用 */
    return (void *)aBlock;
}

void _Block_release(const void *aBlock)
{
    (void)aBlock; /* 无管理 */
}

void _Block_object_assign(void *dest, const void *object, const int flags)
{
    (void)dest; (void)object; (void)flags; /* 无对象捕获管理 */
}

void _Block_object_dispose(const void *object, const int flags)
{
    (void)object; (void)flags; /* 无对象捕获管理 */
}
