# execline 2.9.9.2 适配笔记

## 编译环境
- 构建系统: skarnet 自有 configure+make（非标准 autotools/cmake）
- 编译日期: 2026-08-24
- 编译器: clang (OHOS aarch64 native)
- 平台: HarmonyOS PC (arm64, OHOS 6.0)
- 状态: built

## 软件概述

execline 是 skarnet.org 的非交互脚本语言，既产出 libexecline.a 静态库，
又产出命令行可执行文件（execlineb, define, exec, if, forx 等）。
它依赖 skalibs（构建时 + 运行时）。

## 编译步骤

execline 使用 skarnet 自有 configure+make 构建系统，configure 需要显式指向
skalibs 的 sysdeps/include/lib 目录：

```bash
# 通过 self.dependencies["skalibs"] 获取 skalibs 包路径
skalibs_prefix = skalibs.package_folder

./configure \
  --prefix={package_folder} \
  --disable-shared \
  --with-sysdeps={skalibs_prefix}/lib/skalibs/sysdeps \
  --with-include={skalibs_prefix}/include \
  --with-lib={skalibs_prefix}/lib/skalibs

make -j1    # R9: skarnet 构建顺序敏感，必须用 -j1
make install
```

### configure 参数说明

| 参数 | 说明 |
|------|------|
| `--prefix` | 安装前缀，指向 Conan 的 package_folder |
| `--disable-shared` | 只构建静态库（R26: 危险库静态编译） |
| `--with-sysdeps` | 指向 skalibs 的 sysdeps 目录（平台检测结果） |
| `--with-include` | 添加 skalibs 的 include 目录到头文件搜索路径 |
| `--with-lib` | 添加 skalibs 的 lib/skalibs 目录到静态库搜索路径 |

### skalibs 包结构（验证）

```
{skalibs_prefix}/
├── lib/
│   ├── libskarnet.a              # 静态库
│   └── skalibs/
│       └── sysdeps/              # 平台 sysdeps（configure 需要）
├── include/
│   └── skalibs/
│       ├── stralloc.h
│       ├── buffer.h
│       └── ...                   # 所有 skalibs 头文件
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 默认从 PREFIX/lib/skalibs/sysdeps 查找 sysdeps | execline 依赖 skalibs，但 skalibs 是独立 Conan 包，不在同一 prefix | 显式传 `--with-sysdeps`、`--with-include`、`--with-lib` 指向 skalibs 包目录 |
| 2 | `--with-lib` 指向 skalibs_prefix/lib 还是 lib/skalibs？ | libskarnet.a 在 lib/ 下，但 skarnet 的 --with-lib 期望的是包含库的目录 | 正确路径是 `lib/skalibs`（skarnet configure 内部在该目录查找 libskarnet.a） |

## 源码修改

无补丁，纯 configure+make 编译。

## 依赖版本

- skalibs/2.15.1.0@ohpcd/stable（构建时 + 运行时依赖）

## 验证结果

```bash
# Conan 配方验证
python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify execline 2.9.9.2
# → conan create 从源码构建 + test_package 测试

# test_package 调用 execline API:
# - el_semicolon (block parsing)
# - el_getstrict (strictness level)
# - el_vardupl (variable duplicate detection)
# - ELTRANSFORMINFO_ZERO (struct initialization)
# - el_parse_from_string (core parsing)
```

## 产物

| 文件 | 说明 |
|------|------|
| lib/libexecline.a | 静态库 |
| include/execline/execline.h | 头文件 |
| bin/execlineb | execline 脚本解释器 |
| bin/define, exec, if, forx, ... | execline 命令行工具 |

## 注意事项

- execline 的 `--with-lib` 参数指向 `lib/skalibs`（不是 `lib/`），因为
  skarnet configure 在该目录下查找 `libskarnet.a`。
- make 必须用 `-j1`（R9），skarnet 构建系统有内部顺序依赖。
- execline 是纯 C 库，test_package 也用 C（不要用 C++）。
- 产物既包含库（libexecline.a）又包含可执行文件（bin/*），package_type
  设为 "library"（主要是库，可执行文件是配套工具）。
## 上游测试用例验证（2026-08-24）

### 上游测试套件分析

| 软件 | 测试套件 | 说明 |
|------|---------|------|
| skalibs 2.15.1.0 | ❌ 无 | 无 `check`/`test` make target，无独立测试目录 |
| execline 2.9.9.2 | ⚠️ 无自运行单元测试 | Makefile 有 `check` target 和 `tools/run-test.sh`，但 `TEST_BINS :=` 为空，`src/tests/` 目录不存在 |

### eltest 运行时验证

execline 源码含 `src/execline/eltest.c`（508 行），这是 execline 版的 `test` 命令（生产工具，非单元测试）。
它实现了完整的 POSIX test 表达式求值器（lexer + LALR parser + runner），覆盖 46 种操作符。
我在 OHOS 设备上对 eltest 二进制进行了运行时功能验证（28 项断言）：

| # | 测试 | 操作符 | 输入 | 预期exit | 实际exit | 结果 |
|---|------|--------|------|---------|---------|------|
| T1 | 非空字符串 | `-n` | hello | 0 | 0 | ✅ |
| T2 | 空字符串 | `-z` | "" | 0 | 0 | ✅ |
| T3 | 目录存在 | `-d` | /tmp | 0 | 0 | ✅ |
| T4 | 常规文件 | `-f` | /etc/hosts | 0 | 0 | ✅ |
| T5 | 路径存在 | `-e` | /bin/sh | 0 | 0 | ✅ |
| T6 | 可读 | `-r` | /etc/hosts | 0 | 0 | ✅ |
| T7 | 可写 | `-w` | $TMPDIR | 0 | 0 | ✅ |
| T8 | 可执行 | `-x` | /bin/sh | 0 | 0 | ✅ |
| T9 | 字符串相等 | `=` | abc=abc | 0 | 0 | ✅ |
| T10 | 字符串不等 | `!=` | abc!=def | 0 | 0 | ✅ |
| T11 | 数值相等 | `-eq` | 42=42 | 0 | 0 | ✅ |
| T12 | 数值大于 | `-gt` | 5>3 | 0 | 0 | ✅ |
| T13 | 数值小于 | `-lt` | 3<5 | 0 | 0 | ✅ |
| T14 | 逻辑与 | `-a` | -n hi -a -n bye | 0 | 0 | ✅ |
| T15 | 逻辑或 | `-o` | -z "" -o -n hi | 0 | 0 | ✅ |
| T16 | 逻辑非 | `!` | ! -z hi | 0 | 0 | ✅ |
| T17 | 正则匹配 | `=~` | "hello" =~ "hel.*" | 0 | 0 | ✅ |
| T17b | 正则不匹配 | `=~` | "world" =~ "hel.*" | 1 | 1 | ✅ |
| T18 | 嵌套括号 | `()` | (-n hi -o -n bye) -a -n ok | 0 | 0 | ✅ |
| T19 | 空文件 | `-s` | empty.txt | 1 | 1 | ✅ |
| T20 | 非空文件 | `-s` | nonempty.txt | 0 | 0 | ✅ |
| T21 | 同设备/inode | `-ef` | file -ef file | 0 | 0 | ✅ |
| T22 | 更新 | `-nt` | newer -nt older | 0 | 0 | ✅ |
| T23 | 更旧 | `-ot` | older -ot newer | 0 | 0 | ✅ |
| T24 | 非socket | `-S` | /dev/null | 1 | 1 | ✅ |
| T25 | 环境变量已设 | `-v` | FOO=bar -v FOO | 0 | 0 | ✅ |
| T26 | 环境变量未设 | `-v` | -v NONEXISTENT | 1 | 1 | ✅ |
| T27 | 复合表达式 | `()` `-a` | (-d /tmp -a -w $TMPDIR) -a -n ok | 0 | 0 | ✅ |
| T28 | 数值不等 | `-eq` | 5 -eq 3 | 1 | 1 | ✅ |

**结论**: 28/28 全部通过。eltest 的 lexer/parser/runner 全链路在 OHOS aarch64 上功能正常，
涵盖字符串比较、数值比较、文件类型检测、文件权限检测、逻辑运算（AND/OR/NOT）、
正则匹配（POSIX regex）、嵌套括号表达式、环境变量检测等全部操作符类别。

**注意**: T17 初次因 shell 对 `=~` 的 tilde 展开导致 parse error（exit 100），
正确引号 `"hello" "=~" "hel.*"` 后通过——这是 shell 引用问题，非 eltest 缺陷。

---

**编译结束**: 2026-08-24 10:16
**最终状态**: built
