# clang 20.1.8 — 鸿蒙 PC 适配说明

clang/LLVM 20.1.8 编译器前端工具链，鸿蒙 PC 真机原生编译的
`aarch64-unknown-linux-ohos` 版本。

## 构建方式

- 鸿蒙 PC 真机原生编译（不设 `CMAKE_SYSTEM_NAME` → 不触发交叉编译 → `llvm-tblgen`
  原生编+跑），CMake + Ninja（Release，仅 AArch64 target）。
- `config.guess` 不认 `uname -s=HarmonyOS` → build() 覆盖为 stub 输出
  `aarch64-unknown-linux-ohos`。
- runtimes（compiler-rt builtins / libunwind / libc++）不源码构建：SDK libc++ 15 头与
  clang 20 不兼容，对齐手工 llvm-build 先例，`package()` 中从 SDK 复制
  （R26 合规，不输出 libc++.so 等系统同名库）。

## 产物与消费

- `bin/clang`、`bin/clang++`（默认 triple `aarch64-unknown-linux-ohos`）
- LLVM/clang 库、头文件（含 SDK 复制的 libc++ 头）
- 测试：`test_package` 用打包 clang 真实编译运行 test.c，校验 `__clang_major__==20`
- 上游 46,276 个 lit 用例：通过 43,043（按适用口径 99.85%）
