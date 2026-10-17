# dylib 3.0.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-03
- 编译器: clang 15.0.4 / clang++（OHOS SDK 26.0.0.18, aarch64-linux-ohos）
- 状态: built
- Conan: 2.32.0（OHOS 适配版），profile: ci/conan/profiles/ohos-aarch64

## 编译步骤

1. 官方源码：https://github.com/martin-olivier/dylib tag v3.0.1（tar.gz，SHA-256
   dfef3f0aeccf4ad847a5cd02f0b0bff086b4fac6e764e33abd82d3c85cfb578c）
2. 上游测试：`cmake -DDYLIB_BUILD_TESTS=ON` + googletest 1.15.2 → `./unit_tests`
   - C++17（含 std_filesystem）: 17/17 PASS（R02 实测，EXIT=0）
3. Conan 配方：CMake 驱动，静态库 libdylib.a；`conan create -pr:h/-pr:b ohos-aarch64`
4. W3 本地 CI：`ci/conan/build_and_test.sh archives/d/dylib/3.0.1` → JC pass, L0 pass

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | src/symbols.cpp: use of undeclared identifier 'dlinfo' | OHOS musl libc 不提供 glibc 独有的 dlinfo(RTLD_DI_LINKMAP) | patches/0002-src-symbols.cpp.patch：`#if defined(__GLIBC__)` 保留原路径，`#else` 用 dl_iterate_phdr 遍历 PT_DYNAMIC 解析 DT_SYMTAB/STRTAB，dlsym(handle) 过滤归属 |
| 1b | R02 审查 P2-1：非 glibc 符号遍历用 DT_STRSZ/DT_SYMENT 推导 .dynsym 条目数（无 ELF 语义，可能漏枚举或越界读） | 字符串表字节数 ÷ 符号项字节数 ≠ 符号条目数 | 改为可验证边界：优先 DT_HASH 的 nchain（ELF ABI 定义）；仅 GNU hash 时遍历 bucket 链求最大符号索引（bloom 为 ElfW(Xword) 宽，64 位 8 字节）；两者皆无则跳过该对象不猜测。实测修复前 SIGSEGV（Signal 11），修复后上游 17/17、专项测试 5/5 |
| 2 | 上游 gtest cpp_symbols.functions / functions_overload_namespace 失败（Symbol not found） | OHOS libc++ 内联命名空间 std::__n1:: 使 demangle 签名与规范 std:: 失配 | patches/0001-src-format.cpp.patch：format_symbol 增加 `std::__n1::` → `std::` 归一化（与既有 __1/__cxx11 同族） |
| 3 | R02 审查 P2-2：test_package 对 HiLogPrint 用固定 4 参原型（int,int,const char*,const char*） | HiLogPrint 是变参函数 int HiLogPrint(LogType,LogLevel,unsigned int,const char*,const char*,...)，固定原型属未定义行为 | test_package/test.cpp 改用带省略号的变参函数指针原型，按 OHOS 契约（返回 >=0 为成功）用 LOG_WARN 断言 rc>=0；实测 rc=72 PASS |

## 源码修改

- patches/0001-src-format.cpp.patch（demangle 命名空间归一化，平台相关）
- patches/0002-src-symbols.cpp.patch（dl_iterate_phdr 符号枚举替代 dlinfo + DT_HASH/GNU hash 可验证条目数边界，平台相关）
- test_package/test.cpp（HiLogPrint 变参函数指针原型与实际 API 一致，R02 修复）

## 依赖版本

- 无 Conan 外部依赖（仅系统 dl）
- 测试依赖：googletest 1.15.2（仅测试构建）

## 验证结果

```bash
# 上游测试（C++17 全量，R02 实测）
./unit_tests → 17/17 PASS（EXIT=0，日志 upstream_test_r02.log）

# HarmonyOS 专项测试（本适配新增，真实加载系统库，R02 实测）
./ohos_test → dlopen libhilog OK, symbols() 3962 个, HiLogPrint rc=72（OHOS 契约成功）,
             无 std::__n1:: 残留 → ALL OHOS TESTS PASSED（EXIT=0，日志 ohos_test_r02.log）

# 消费者验证（test_package，R02 实测）
conan create → test_dylib 加载 libhilog 并变参调用 HiLogPrint → PASS（1/1，日志 conan_create_r02.log）
```

## 注意事项

- OHOS 上 dlopen 句柄不可按 glibc link_map 强转（SIGSEGV）；dlinfo 路径仅限 __GLIBC__
- .dynsym 条目数必须用可验证 ELF 边界（DT_HASH nchain 优先），禁止 DT_STRSZ/DT_SYMENT 推导
- 上游 17 个独立 TEST_CASE（library 6 / symbols 3 / cpp_symbols 8）全量枚举并运行，
  C++17 全量通过率 17/17 = 100%
- 知识草稿（.md/.kv 同 stem 配对，仅位于 knowledge/drafts/）：
  knowledge/drafts/dylib-3.0.1-dlinfo-ohos.md/.kv 与
  knowledge/drafts/dylib-3.0.1-ohos-demangle-n1.md/.kv（路径 B，已按 R02/R03 修复内容同步）

---

**编译结束**: 2026-09-03（R02 返工）
**最终状态**: built
