/* compat/blocks_runtime_stub.c — minimal BlocksRuntime for HarmonyOS
 *
 * 鸿蒙无 libBlocksRuntime。bart 用 -fblocks（NESTED 宏展开为 clang blocks），
 * 链接需要 _NSConcreteStackBlock / _Block_object_assign / _Block_object_dispose
 * 等符号。bart 的 blocks 用法为栈上块立即调用（NESTED_CALL），不跨作用域复制，
 * 因此提供最小实现：
 *   - _NSConcreteStackBlock：栈上 block 的 isa（全局符号）
 *   - _Block_copy/_Block_release：直接返回/空释放（不复制）
 *   - _Block_object_assign/_Block_object_dispose：空操作（无对象捕获管理）
 */
#include <stdlib.h>

/* clang blocks ABI: block layout isa 指针 */
void *_NSConcreteStackBlock = 0;
void *_NSConcreteMallocBlock = 0;
void *_NSConcreteGlobalBlock = 0;

void *_Block_copy(const void *aBlock)
{
    /* 不复制——bart 的 blocks 均在栈上立即调用 */
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
