# Clang

clang/LLVM 编译器前端（C/C++/Objective-C），鸿蒙 PC 真机原生编译的
`aarch64-unknown-linux-ohos` 工具链。

- 上游：https://github.com/llvm/llvm-project （release `llvmorg-20.1.8` / `llvmorg-22.1.8`）
- 许可证：Apache-2.0 WITH LLVM-exception
- 构建系统：CMake + Ninja（Release，仅 AArch64 target）

## 鸿蒙 PC 适配

**路径 A 基础适配**：鸿蒙 PC 真机原生编译（不设 `CMAKE_SYSTEM_NAME` → 不触发交叉编译 →
`llvm-tblgen` 原生编+跑），默认 triple `aarch64-unknown-linux-ohos`。

- runtimes（compiler-rt builtins / libunwind / libc++）**不源码构建**——SDK 的 libc++
  15 头与 clang 20 不兼容（musl 缺 rune table / strtoll_l），对齐手工 llvm-build 先例，
  `package()` 中从 SDK 复制（R26 合规，不输出 libc++.so 等系统同名库）。
- `config.guess` 不认 `uname -s=HarmonyOS` → build() 中覆盖为 stub 输出
  `aarch64-unknown-linux-ohos`（与 llvm/20.1.0 同族策略）。
- 产物：`bin/clang`、`bin/clang++` 及 LLVM/clang 库；test_package 用打包 clang 真实编译
  运行 test.c 校验 `__clang_major__`。

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 20.1.8 | built | 首个适配版本（conan create + test_package 通过） |
| 22.1.8 | built | 升级版本（仅 AArch64 目标，libLLVM.so + libclang-cpp.so 动态库） |
