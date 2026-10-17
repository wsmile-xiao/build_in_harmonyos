# mimick 0.3.0 适配笔记

## 编译环境

- 构建系统：CMake 2.8 风格项目，使用设备 clang/clang++ 与 CMake 4.1。
- 目标：HarmonyOS PC arm64；为兼容项目对平台的判断，CMake 配置使用 `CMAKE_SYSTEM_NAME=Linux`。
- 编译日期：2026-09-03。
- 源码包 SHA256：`9b984478481ae2aa0ed4cafd5726b82b53558312472341a2ac66289dd78a63a3`。

## 编译步骤

源码工作树为 `/storage/Users/currentUser/builds/mimick-0.3.0.work`，上游测试构建目录为 `/storage/Users/currentUser/tmp/w0-batch10/mimick-upstream-build`。使用 clang 配置并保留上游 CTest：

```bash
cmake -S /storage/Users/currentUser/builds/mimick-0.3.0.work   -B /storage/Users/currentUser/tmp/w0-batch10/mimick-upstream-build   -DCMAKE_SYSTEM_NAME=Linux   -DCMAKE_POLICY_VERSION_MINIMUM=3.5   -DCMAKE_C_FLAGS='-fPIC -fno-emulated-tls'
cmake --build /storage/Users/currentUser/tmp/w0-batch10/mimick-upstream-build --parallel 2
ctest --test-dir /storage/Users/currentUser/tmp/w0-batch10/mimick-upstream-build --output-on-failure
```

## 遇到的问题与解决方案

| 问题 | 根因 | 解决方案 |
|---|---|---|
| AArch64 ELF 配置阶段提示 `ElfAddr`/`ElfOff` 未声明 | 源码在 `find_dynamic()`/`get_r_debug()` 中使用了未定义的别名 | 使用现有 `ElfW(Addr)`/`ElfW(Off)` 访问器，保持 ABI 语义 |
| 初始化阶段找不到 `abort`/`vfprintf` | HarmonyOS musl loader 只提供 `DT_GNU_HASH`，源码只查 SysV `DT_HASH` | 在 ELF 动态符号查找中保留 SysV 优先，并补充 32 位 GNU hash、bloom filter 和 chain 查找；hash/bloom 均按 `uint32_t` 计算 |
| 首次 mock 写 GOT 触发段错误 | HarmonyOS 对可执行文件启用 RELRO，GOT 启动后为只读 | 只对包含目标槽位的页临时 `mprotect(PROT_READ|PROT_WRITE)`，写入后恢复 `PROT_READ`；不关闭 RELRO |
| `mmk_reset(fn)` 在 AArch64 失效 | 取函数地址和直接调用可能分别使用 `R_AARCH64_GLOB_DAT` 与 `R_AARCH64_JUMP_SLOT` 两个槽 | 在 AArch64 ELF 的动态 RELA 表中补收匹配的 GLOB_DAT 槽，并与 PLT 槽一起保存/恢复 |
| `malloc` mock 的 when 阶段递归崩溃 | 设备 clang 默认生成 emulated TLS；TLS 运行时内部会再次走已 mock 的 allocator | AArch64 clang CMake 配置加入 `-fno-emulated-tls`，改用设备原生 TLS 访问 |
| 旧 CMake 在 CMake 4.1 下拒绝 `cmake_minimum_required(VERSION 2.8)` | CMake policy 版本兼容性收紧 | 配置时使用 `CMAKE_POLICY_VERSION_MINIMUM=3.5`，不修改上游最低版本声明 |

## 源码修改

- `0001-CMakeLists.txt.patch`：仅在 AArch64 clang 构建时加入 `-fno-emulated-tls`。
- `0002-src/plt-elf.c.patch`：修正 AArch64 类型别名，补充 GNU hash 动态符号解析，处理 RELRO GOT 写入，并同步 AArch64 `GLOB_DAT`/`JUMP_SLOT` 重定位槽。

## 依赖版本

- 生产依赖：无。
- 设备工具链：clang/clang++，CMake 4.1；源码自身的旧 CMake 声明通过 policy 变量兼容。

## 验证结果

- 上游 CTest：2/2 通过（`mmk_test`、`strdup_test`）；两者均由上游顶层 CMake 的测试注册链纳入 CTest。
- `strdup_test` 覆盖对共享库 `libstrdup.so` 的 `malloc` mock、when、verify、reset 以及错误路径。
- Conan `test_package` 已调用 `mmk_mock`/`mmk_when`/`mmk_verify`/`mmk_reset` 的真实 API 并通过；不以头文件存在或打印字符串替代功能验证。

## 注意事项

- 该补丁针对 ELF/AArch64 + HarmonyOS clang 运行时差异；非 AArch64 目标仍保留原有动态重定位路径。
- 不得用伪造 `abort`/`vfprintf`、关闭 RELRO、替换 TLS 或 dummy 包绕过测试。
- `GLOB_DAT` 数值 1025 是 AArch64 ELF ABI 的重定位类型；只在生成的 `MMK_ARCH_ARM64` 分支使用。
---

**编译结束**: 2026-09-03 10:01
**最终状态**: built


## 对话记录

### 对话 #1（2026-09-03）

- 完成 AArch64 ELF/GNU hash/RELRO/GLOB_DAT/JUMP_SLOT 与 emulated-TLS 问题定位、补丁固化和 Conan/W3 验证；问题证据与路径 B 草稿同步保留。
- Conan G2、上游 CTest 2/2、test_package 1/1 和 W3 均通过。
