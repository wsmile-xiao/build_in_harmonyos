# DRAFT: codecrypt 1.8 (ccr) OHOS 适配六连环坑

## 适用场景
C/C++ CLI 工具（application 类型）从 Linux 适配 OHOS，且上游是
C++11 autotools 项目（tarball 无 configure）+ C++ 库依赖。

## 六个坑与修复

| # | 症状 | 根因 | 修复 |
|---|------|------|------|
| 1 | `use of undeclared identifier 'getpass'` | musl 无 getpass/readpassphrase | `#elif !defined(HAVE_GETPASS)` 特性宏内联 termios 实现 |
| 2 | `reference to 'byte' is ambiguous` | cppstd=17 的 std::byte 与上游全局 typedef byte 冲突 | `rm_safe("compiler.cppstd")` 回退上游 C++11 |
| 3 | `cannot run C compiled programs` + `Error relocating libgmpxx.so.4` | AutotoolsDeps LIBS 含 -lgmpxx（需 libc++） | `Environment().define("LIBS", ...)` 覆盖 + LD_LIBRARY_PATH 前置 |
| 4 | `could not setup config files machinery` | E114 umask 077 × HMDFS setgid | replace_in_file 去掉生成 configure 的 umask 077 |
| 5 | `Package libcrypto++ not found` | conan pc 名 cryptopp.pc ≠ 上游期望 libcrypto++ | CRYPTOPP_CFLAGS/LIBS 环境变量直接喂 |
| 6 | test_package `Error loading shared library libc++_shared.so` | SDK 运行时不在 conan 依赖 | `clang++ -print-file-name=libc++_shared.so` 定位拼 LD_LIBRARY_PATH |

## 通用性
坑 2/3/6 对所有 C++ 代码库普遍适用；坑 1 是 E093 的 readpassphrase 形态；
坑 4/5 见 E114/既有经验。组合出现在单二进制 C++ autotools 工具上是首次记录。
