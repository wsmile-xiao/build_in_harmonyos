# coreutils-sha512sum 9.11 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-09-08
- 编译器: Clang 15.0.4 (HarmonyOS NDK, /data/service/hnp/bin/clang)
- C 库: musl libc
- 目标平台: aarch64-unknown-linux-ohos
- 状态: built (conan create + W3 本地 CI 通过)

## 编译步骤
1. 下载 coreutils-9.11.tar.xz (官方 ftp.gnu.org, sha256=394024eda0a5955217ceda9cd1201e65dc8fa3aa29c2951135a49521d57c3cc3, 与清华镜像逐字节一致)
2. 应用 2 个补丁: 0001 config.guess OHOS 识别 + 0002 freadahead musl 适配
3. conan create -pr:h=ci/conan/profiles/ohos-aarch64 (configure ~13min + make + test_package)
4. 构建默认 `all` 目标 (不能直接 make src/sha512sum, 会跳过 BUILT_SOURCES 缺 gnulib 头)
5. 打包仅 bin/sha512sum (package_type=application, commands.json binary: true)

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | make src/sha512sum 缺 stdckdint.h/stdcountof.h/locale.h | 直接目标跳过 BUILT_SOURCES (gnulib 生成头) | 配方改为构建默认 all 目标 |
| 2 | 9.10 补丁 0003/0004 (freadptr/freadseek) 无法应用 | 9.11 已移除 gnulib freadptr/freadseek 模块 | 不携带该补丁 (源文件不存在) |
| 3 | 9.10 补丁 0005-0012 (cat/dd/head/tail/wc EACCES) | 针对其他命令; sha512sum 只用 isatty() 不 fstat/lseek | 本包不需要 |
| 4 | W3 L1e 判 test_package "假测试" | test.sh 用裸 sha512sum 走 PATH, 系统自带 coreutils 二进制 | test 显式传包内二进制绝对路径 |
| 5 | 兄弟工具 sh 测试 (b2sum/cksum-a/cksum-raw/cksum-sha3) set-up 失败 | OHOS 管道 fstat EACCES (E076) + 上游脚本 SIGPIPE | 不属本包, 台账列明原因; 如需运行需为 cksum.c 加 EACCES 降级补丁 |

## 源码修改
| 文件 | 修改内容 | 是否已生成补丁 |
|------|----------|----------------|
| build-aux/config.guess | HarmonyOS 系统检测 | ✅ 0001 |
| lib/freadahead.c | musl libc FILE 结构适配 | ✅ 0002 |

## 测试结果
- 上游 sha512sum.pl: 5/5 PASS (s1-s4, s8)
- 摘要家族 (tests/cksum/ 21 脚本): 17 PASS + 4 ERROR (兄弟工具 E076, 非本包)
- 共享脚本: usage_vs_refs.sh PASS; tty-eof.pl SKIP (无 Perl Expect)
- test_package: test.sh 4/4 + test_ohos.sh 4/4 PASS; W3 L1e 负向测试确认依赖包
- 双口径: 5/5 (100%); 家族补齐 17/21

## 知识沉淀 (路径 B)
- coreutils 9.11 cksum 框架摘要工具变更 (src/sha512sum 由 coreutils-sha512sum.c + cksum.c 组成)
- 9.11 gnulib 模块变更 (freadptr/freadseek 移除) 与 BUILT_SOURCES 头文件前提
- 详见知识草稿归档 (knowledge/drafts)