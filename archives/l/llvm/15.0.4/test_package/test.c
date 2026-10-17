/* llvm/15.0.4 static package minimal consumer probe (R8 scaffold, NOT executed).
 * 后续获批构建后用于核验 LLVMConfig 导出与静态链接；本轮仅作为最小测试源占位。
 */
#include <llvm/Config/llvm-config.h>

#ifndef LLVM_VERSION_MAJOR
#error "LLVM_VERSION_MAJOR not defined"
#endif

#if LLVM_VERSION_MAJOR != 15
#error "unexpected LLVM major version"
#endif

int main(void) {
    return 0;
}
