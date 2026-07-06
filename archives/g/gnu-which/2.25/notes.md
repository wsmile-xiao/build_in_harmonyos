# gnu-which 2.25 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-07-03
- 编译器: clang 15.0.4 / clang++
- 状态: built

## 编译步骤

1. `init-build gnu-which 2.25 --url=https://ftpmirror.gnu.org/gnu/which/which-2.25.tar.gz`
2. 修补 config.guess/config.sub (E007): `perl patch-autotools-ohos.pl config.guess config.sub`
3. 修复 configure umask 077→022 (E011): `sed -i 's/umask 077/umask 022/g' configure`
4. 修复 configure CONFIG_SHELL 回退: 添加 `_as_shell` 变量检查路径存在性
5. `bash ./configure --prefix=$DEFAULT_PREFIX` (需用 bash 因 configure 含 `[[ =~ ]]` 语法)
6. `make -j2 && make install DESTDIR=$TEST_PREFIX`
7. `make check` (通过)
8. `conan-init` + `conan-verify` (全部门禁通过)
9. `finish gnu-which 2.25 built`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 OHOS | E007: GNU config.guess 无 HarmonyOS 分支 | patch-autotools-ohos.pl 补丁 |
| 2 | configure umask 077 权限拒绝 | E011: HMDFS UID 映射导致 0700 目录不可写 | sed 替换 umask 077→022 |
| 3 | configure `[[ =~ ]]` 语法错误 | OHOS /bin/sh 非 bash，不支持 =~ 运算符 | 用 bash 运行 configure + CONFIG_SHELL 回退补丁 |
| 4 | conan profile CONFIG_SHELL 路径不存在 | profile 指向 /data/service/hnp/bin/bash 但该路径不存在 | configure 补丁: 检查路径存在性，回退到 PATH 中的 bash |
| 5 | conan profile CC/CXX 路径不存在 | profile tools.build:compiler_executables 指向不存在路径 | conanfile.py: configure args 传递 CC/CXX 覆盖 |

## 源码修改

- `config.guess`: 添加 __OHOS__ LIBC 检测 + HarmonyOS 系统识别 (E007)
- `config.sub`: 添加 ohos-linux triplet (E007)
- `configure`: umask 077→022 (E011) + CONFIG_SHELL 路径检查回退

## 依赖版本

无依赖 (gnu-which 是独立工具)

## 验证结果

```bash
$ which --version
GNU which v2.25, Copyright (C) 1999 - 2026 Carlo Wood.

$ which bash
/storage/Users/currentUser/usr/local/bin/bash

$ make check
(通过，无错误)
```

## 注意事项

- conan profile 的 CONFIG_SHELL 和 compiler_executables 路径在本环境不存在，
  需在 conanfile.py 中通过 configure args 和 configure 补丁处理
- test_package 使用 VirtualRunEnv 而非 CMakeToolchain，避免编译器路径问题
- 3 个补丁均为平台兼容性补丁 (portability)

---

**编译结束**: 2026-07-03 15:04
**最终状态**: built
