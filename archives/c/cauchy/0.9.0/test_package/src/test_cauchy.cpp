// test_cauchy: 消费者测试 — 链接 libCauchy 并调用版本 API，验证 ABI 与头文件
// 正确暴露（OHOS aarch64 真机运行）。避免触发 cauchymc 代码生成路径
// （该上游后端在本环境有 SIGSEGV，见 notes.md 已知限制）。
#include <Cauchy/Version.h>
#include <iostream>

int main() {
    std::cout << "cauchy " << Cauchy::LibraryVersionString()
              << " (" << Cauchy::LibraryShortName() << ")" << std::endl;
    int major = Cauchy::LibraryVersionMajor();
    int minor = Cauchy::LibraryVersionMinor();
    int rev = Cauchy::LibraryVersionRevision();
    if (major == 0 && minor == 9 && rev == 0) {
        std::cout << "cauchy version check: OK" << std::endl;
        return 0;
    }
    std::cout << "cauchy version check: FAILED ("
              << major << "." << minor << "." << rev << ")" << std::endl;
    return 1;
}
