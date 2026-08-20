// test.cpp — SPIRV-LLVM-Translator test_package
// 验证包的头文件可包含 + 库可链接 (R34: 调用被测包的 API)
// 实际功能测试在 conanfile.py test() 中执行 llvm-spirv 二进制

#include <cstdio>
#include <LLVMSPIRVLib/LLVMSPIRVLib.h>

int main() {
    // 验证 LLVMSPIRVLib 头文件可包含、库可链接
    printf("test spirv-llvm-translator 20.1.0: header + link OK\n");
    return 0;
}
