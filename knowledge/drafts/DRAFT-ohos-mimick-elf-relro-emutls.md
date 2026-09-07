# DRAFT-ohos-mimick-elf-relro-emutls：OHOS AArch64 ELF 动态拦截器适配

## 现象

在 OHOS PC arm64 上构建 Mimick 0.3.0 时，问题不是单一编译错误：旧代码的 AArch64 ELF 类型别名未定义；musl loader 只提供 GNU hash 时，初始化找不到 `abort`/`vfprintf`；首次写入函数 GOT 槽位会因 RELRO 段只读而崩溃；只处理 PLT 的 `JUMP_SLOT` 又会使通过函数地址取得的 `GLOB_DAT` 槽无法 reset。补齐这些路径后，`malloc` mock 在 when 阶段仍可能因默认 emulated TLS 重新进入被 mock 的分配器而递归崩溃。

## 可复用处理

1. 先用目标 clang 编译最小 AArch64 ELF 探针，并分别检查 `DT_HASH`、`DT_GNU_HASH`、`DT_JMPREL`/`DT_RELA` 和重定位类型；不要把“能生成 ELF”当作动态符号拦截已可用。
2. 动态符号查找保留 SysV hash，并补充 32 位 GNU hash 的 bloom filter 与 chain 查找；bloom 位运算和 hash 值使用 `uint32_t`，避免在 64 位平台扩大类型后误判未命中。
3. 修改 RELRO GOT 前只临时将包含目标槽的页设为 `PROT_READ|PROT_WRITE`，写入后恢复 `PROT_READ`；不要关闭 RELRO 或伪造符号。
4. AArch64 动态 RELA 扫描同时覆盖匹配的 `JUMP_SLOT` 和 `GLOB_DAT`，否则直接调用与函数指针调用可能走不同槽位，`reset` 证据不完整。
5. 如果 mock 框架的线程本地状态会经过 allocator，使用目标 clang 的 `-fno-emulated-tls` 重新构建并验证 malloc/when/verify/reset 全链路；这属于运行时 TLS 递归边界，不是语言预检不匹配。
6. 旧 CMake 工程在 CMake 4.x 配置时使用 `CMAKE_POLICY_VERSION_MINIMUM=3.5`，把兼容变量作为构建参数保留，不降低真实测试覆盖。

## 证据

- 原始 OHOS AArch64 构建报告 `ElfAddr`/`ElfOff` 未声明；改用 `ElfW(Addr)`/`ElfW(Off)` 后进入运行时验证。
- 原始初始化日志为 `could not find definitions for vital function(s): 'abort' 'vfprintf'`；GNU hash 查找补齐后通过。
- 直接写 RELRO GOT 会触发段错误；页级临时 `mprotect` 并恢复只读后，mock 写入通过。
- `mmk_reset(fn)` 只有同时收集 `GLOB_DAT` 与 `JUMP_SLOT` 后才恢复正确。
- 默认 emulated TLS 下 `strdup_test` 在 `mmk_when(malloc(...))` 阶段递归崩溃；加入 `-fno-emulated-tls` 后上游 CTest `mmk_test`、`strdup_test` 共 2/2 通过；两者均在上游顶层 CMake 的 `add_test` 注册链中。

## 边界

本知识适用于 ELF/AArch64 动态拦截器在 OHOS clang/musl 运行时的构建和运行适配。补丁必须由架构、编译器和 ELF 格式条件守卫；不能把测试关闭、dummy 符号、伪造头文件或禁用 RELRO 当作适配。若公共 API 本身依赖缺失的系统能力，应转为有证据的部分/无法适配分析。
