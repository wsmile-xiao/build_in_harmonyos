# OHOS SDK LLVM 内嵌 `__h` ABI libc++，消费方 C++ 代码须以 `__h` 头编译并补 iostream shim

- 形态：knowledge/drafts 条目草稿（最终编号 Exxx 由知识库主编确认）
- 配套 kv：`knowledge/drafts/DRAFT-ohos-sdk-llvm-h-abi-iostream-shim.kv`
- 申报路径：B【知识库扩展】（L1 平台/工具链语义层，单库发现即可申报）
- 来源 run：bcc/0.37.0（pc2-15，2026-09-16 首轮；本地 Step 2 ± conan-verify 8 门禁 PASS）

## 1. 一句规则

OHOS SDK 预编译的 clang/LLVM 共享库（libclang-cpp.so、libLLVM.so）把自身
构建时使用的 libc++ 静态内嵌其中，且该 libc++ 的 ABI 内联命名空间是
`std::__h`（NEEDED 仅 libc.so）；而设备对外发布的 libc++ 头（libcxx-ohos）
与运行库（libc++_shared.so）是 `std::__n1` ABI。任何要链接 clang C++ API 的
第三方库必须以 `__h` ABI 头编译（否则 clang 符号全部 ABI 不匹配），且 SDK
库不导出 iostream 全局对象（`std::__h::cout/cerr`），需自建 shim 或改用 stdio。

## 2. 机理链（每环有独立可复现证据）

1. **双 ABI 并存**：`/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/include/libcxx-ohos/include/c++/v1/__config_site`
   定义 `_LIBCPP_ABI_NAMESPACE __n1`；而 `nm -D libclang-cpp.so` 导出符号均为
   `_ZNSt3__h...`（`std::__h`），其 NEEDED 仅 libc.so → 该库静态内嵌 `__h` 版 libc++。
2. **bcc 默认编译不匹配**：用设备默认头（`__n1`）编译 bcc 的 clang 前端时，
   链接报 `undefined reference … clang::MultiplexConsumer(……std::__n1::vector…)`，
   因 libclang-cpp.so 只导出 `__h` 版本。
3. **`__h` 头可行**：复制 libcxx-ohos 头并改 `__config_site` 为 `__h`，以
   `-nostdinc++ -isystem <头>` 编译，clang 符号全部匹配（sample 链接运行 OK）。
4. **iostream 全局缺失**：`std::__h::cout/cerr/clog` 无任何 SDK 库导出；需自建
   shim 静态库（基于 libclang-cpp.so 导出的 basic_ostream/streambuf 构造符号
   定义 cout/cerr/clog + ios_base::Init），且库内 `<iostream>` 输出改 `fprintf`。

## 3. 修复步骤（bcc 0.37.0 实测）

1. 复制 `include/libcxx-ohos/include/c++/v1` → `libcxx-h/v1`，`__config_site`
   中 `__n1` → `__h`。
2. `CMAKE_CXX_FLAGS="-nostdinc++ -isystem <libcxx-h>/v1"`。
3. 编译 `ohos_iostream_shim.cc`（`basic_ostream<char> cout(&cout_buf)` 等，
   FdStreambuf write(fd)），`llvm-ar` 打成 `libohos_iostream_shim.a` 加入 EXE 链接。
4. 库源码中 `std::cerr/std::cout` 输出改为 `fprintf(stderr/stdout,…)`（5 处）。

## 4. 适用边界与反例

- 适用：消费 OHOS SDK clang/LLVM **C++ API** 的库（链接 libclang-cpp.so）。
- 不适用：仅链接 SDK 库的 C ABI（libclang.so）或纯运行时不链接的包。
- 反例：发布包 llvm/xx（conan）若按 `__n1` 构建，则无此问题但缺平台 target
  （本 run 中发布 llvm/15.0.4 缺 BPF target，见 C2 佐证）。

## 5. 验证

- bcc 全目标 make 通过；libbcc.so 4.5MB；消费者用例 + 鸿蒙专项测试 PASS；
  conan-verify G0-G4/L2/L4/L5 全 PASS；W3 finish PASS。