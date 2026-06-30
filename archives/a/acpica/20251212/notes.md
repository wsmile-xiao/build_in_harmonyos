# acpica 20251212 适配笔记

## 编译环境
- 构建系统: makefile (自定义Makefile，无configure脚本)
- 编译日期: 2026-05-27
- 编译器: clang 15.0.4 / clang++ 15.0.4
- 状态: published

## 编译步骤

1. 源码下载：acpica-unix2-20251212.tar.gz（1.6MB），手动curl下载因SSL证书问题
2. 初始化：ohc-run.py init-build，tarball已预先放置
3. 编译：手动模式B编译
   ```bash
   cd $BUILD_SRC_DIR
   make NOWERROR=TRUE ACPI_HOST=_LINUX
   ```
4. 安装DESTDIR模式：
   ```bash
   make install NOWERROR=TRUE ACPI_HOST=_LINUX PREFIX=$DEFAULT_PREFIX DESTDIR=$TEST_PREFIX
   ```
5. 本地安装：
   ```bash
   make install NOWERROR=TRUE ACPI_HOST=_LINUX PREFIX=$DEFAULT_PREFIX
   ```
6. ELF签名：ohc-run.py sign-elf 对每个二进制签名

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | make失败：clang不支持GCC-only警告标志 -Wlogical-op, -Wmissing-parameter-type, -Wold-style-declaration | acpica Makefile.config在Linux平台默认启用GCC-only警告标志，加上-Werror使其变成致命错误 | 使用 NOWERROR=TRUE 禁用-Werror，允许clang不支持的警告选项作为warning而非error |
| 2 | SSL证书问题无法下载源码 | HarmonyOS CA证书不完整 | 手动curl下载源码tarball到~/tmp/，然后拷贝到init-build期望位置 |
| 3 | 自动模式make install DESTDIR失败 | 自动模式使用了错误的make参数组合 | 切换到模式B手动编译，显式传递PREFIX和DESTDIR |
| 4 | 二进制执行报"operation not permitted" | 鸐蒙ELF安全机制，未签名二进制不可执行 | 使用ohc-run.py sign-elf逐个签名 |
| 5 | /tmp只读文件系统(E002) | HarmonyOS HMDFS限制 | 使用$TMPDIR(~/tmp)代替/tmp |

## 源码修改

无源码修改。仅通过make参数（NOWERROR=TRUE, ACPI_HOST=_LINUX）规避GCC-only警告标志问题。

## 依赖版本

- bison/yacc: 预装
- flex: 预装
- m4: 预装
- 无外部库依赖

## 验证结果

```bash
# 版本验证（签名后）
~/usr/local/bin/iasl -v        → version 20251212
~/usr/local/bin/acpixtract -v  → version 20251212
~/usr/local/bin/acpibin -v     → version 20251212
~/usr/local/bin/acpidump -v    → version 20251212
~/usr/local/bin/acpiexec -v    → version 20251212
~/usr/local/bin/acpihelp -v    → version 20251212
~/usr/local/bin/acpisrc -v     → version 20251212
~/usr/local/bin/acpiexamples -v → version 20251212

# 功能验证：iasl编译简单ASL文件
~/usr/local/bin/iasl ~/tmp/test_acpi.asl → Compilation successful. 0 Errors, 0 Warnings

# 无make check/test目标
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| iasl | 1.1MB | ACPI ASL编译器/反汇编器 |
| acpixtract | 34KB | ACPI二进制表提取 |
| acpibin | 42KB | ACPI二进制比较 |
| acpidump | 50KB | ACPI表转储 |
| acpiexec | 554KB | AML执行/调试工具 |
| acpihelp | 218KB | ACPI帮助工具 |
| acpisrc | 100KB | ACPI源码转换工具 |
| acpiexamples | 190KB | ACPI示例工具 |

## 注意事项

- acpica使用自定义Makefile，不是标准autotools项目，没有configure脚本
- 编译必须使用 NOWERROR=TRUE 以避免clang不支持的GCC-only警告标志变成致命错误
- ACPI_HOST应设为 _LINUX（或保持默认）以正确检测平台
- 所有二进制需要ELF签名才能在鸿蒙执行
- /tmp只读，测试文件需写入$TMPDIR
---

**编译结束**: 2026-05-27 16:47
**最终状态**: published
