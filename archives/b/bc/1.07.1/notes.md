# bc 1.07.1 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-08-05
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 下载源码: https://ftp.gnu.org/gnu/bc/bc-1.07.1.tar.gz
2. 修改 configure 中 umask 077 → umask 002 (HarmonyOS uid映射问题)
3. ./configure --prefix=$DEFAULT_PREFIX
4. 修改 fix-libmath_h 脚本，用 sed 替换 ed (ed 不存在于 HarmonyOS)
5. 修改 Makefile 跳过 doc 子目录 (makeinfo 不存在)
6. make -j1
7. make install DESTDIR=$TEST_PREFIX
8. make check (通过)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.status Permission denied | mktemp -d with umask 077 creates dirs owned by uid 20001006, current user is uid 20020101 | 修改 configure 中 umask 077 → umask 002 |
| 2 | fix-libmath_h: ed: command not found | ed line editor not available on HarmonyOS | 用 sed 替换 ed 命令，echo '0}' >> 追加结束标记 |
| 3 | makeinfo: command not found | texinfo not installed on HarmonyOS | 修改 Makefile 跳过 doc 子目录 |

## 源码修改

所有修改在 conanfile.py build() 方法中通过 replace_in_file 处理，无需独立补丁文件。

1. configure: umask 077 → umask 002
2. bc/fix-libmath_h: 用 sed 脚本替换 ed 脚本
3. Makefile: SUBDIRS 去除 doc

## 依赖版本

无外部依赖。bc 仅需 C 编译器、flex、bison。

## 验证结果

```bash
echo "2+3" | bc  → 5
echo "2 3 + p" | dc  → 5
bc --version  → bc 1.07.1
```

## 注意事项

- bc 构建产物为可执行文件 (bc, dc)，非库文件
- 已创建 commands.json 声明 (R38)
- test_package 使用 VirtualRunEnv 测试二进制功能
---

**编译结束**: 2026-08-05 10:18
**最终状态**: built
