# cksfv 1.3.15 适配笔记

## 编译环境
- 构建系统: autotools (configure + make)
- 编译日期: 2026-09-07
- 编译器: aarch64-unknown-linux-ohos-clang (clang 15.0.4)
- 状态: built (真机验证通过)

## 适配策略
cksfv 是纯 C CLI 工具（无库），使用 autotools 构建，无外部依赖。
主要适配点：
1. configure 脚本默认使用 `gcc`，需显式指定 `--compiler=aarch64-unknown-linux-ohos-clang`
2. `make install` 调用 POSIX `install(1)` 命令，OHOS Conan 构建环境中该命令不在 PATH
   → 覆盖 `package()` 方法，用 conan 的 `copy()` 手动复制文件和 man page
3. OHOS 部分目录下 getcwd 可能失败 → 在 build() 中显式设置 `PWD` 环境变量

## 编译步骤
1. 下载源码 cksfv-1.3.15.tar.bz2 (SHA256: a173be5b...)
2. ./configure --prefix=<pkg> --compiler=aarch64-unknown-linux-ohos-clang
3. make -j1
4. package(): copy cksfv binary to bin/, cksfv.1 to share/man/man1/, COPYING to licenses/

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 使用 gcc 默认编译器，OHOS 无 gcc | configure 脚本硬编码 CC=gcc | --compiler=aarch64-unknown-linux-ohos-clang |
| 2 | make install 失败：install 命令不存在 | OHOS Conan build 环境中无 POSIX install | 覆盖 package()，用 copy() 替代 |
| 3 | build() 中 getcwd 可能失败 | OHOS 文件系统限制 | 显式设置 PWD 环境变量 |

## 验证结果
- conan create: PASS ✅
- test_package: PASS ✅ (smoke test: create + verify SFV roundtrip)
- 上游测试 (test/test.sh): 21/21 PASS ✅
  - case 1-6: 基本校验和验证、大小写不敏感
  - case 7: 静默模式
  - case 8-10: 非法/过少/过多校验和字符报错
  - case 11-12: 部分文件验证
  - case 13-16: 递归模式（有无符号链接）
  - case 17: 反斜杠转换
  - case 18-21: -g 路径模式、null byte 文件名、-R 递归校验和文件

## 产物
- bin/cksfv (CLI binary)
- share/man/man1/cksfv.1 (manual page)
- licenses/COPYING (GPL-2.0+)

## 上游测试说明
- test/test.sh 是纯 bash 脚本，21 个用例全部自包含
- 无需 GTest、HDF5 或其他外部测试框架
- 所有 21 个用例在 OHOS aarch64 真机上实际通过
- conanfile.py build() 内调用 `make check`（即 `cd test && ./test.sh`）

---
**适配完成**: 2026-09-07
**最终状态**: 真机验证通过
