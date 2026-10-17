# Source-only C++ archives on HarmonyOS need profile tools and wrapper-warning isolation

- 路径：B（知识库扩展）
- 来源：tiny-aes-c 0.4.2，真实 HarmonyOS aarch64 设备
- 适用范围：无上游构建系统、由单个 C++ 实现文件生成静态库的 Conan 配方

## 规则

从 `tools.build:compiler_executables` 读取 C++ 编译器和 archiver，直接构建
静态归档，并用独立安装后消费者覆盖公开 API。OHOS clang wrapper 会把链接器
参数注入编译命令；只对 `unused-command-line-argument` 降级，不能取消其余
`-Werror` 源码诊断。

## 证据

CryptoManiac/tiny-aes-cpp commit `b2761c223710` 在真机上成功构建并安装；上游
测试数量为 0，Conan consumer 的 NIST AES-256-CTR、双向 round trip、计数器进位/
回绕、空输入共 12/12 断言通过。

## 禁止

- 不要把无测试的上游快照报告为“上游测试通过”。
- 不要为适应 wrapper 警告而移除全部 `-Werror`。
