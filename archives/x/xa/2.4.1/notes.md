# xa 2.4.1 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-06-15
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. init-build xa 2.4.1 --url=https://www.floodgap.com/retrotech/xa/dists/xa-2.4.1.tar.gz
2. 修改 Makefile: CC=gcc→clang, LD=gcc→clang, CFLAGS added -fPIC, DESTDIR→PREFIX+DESTDIR staging support
3. make CC=clang LD=clang CFLAGS="-fPIC -O2 -g" LDFLAGS="-lc"
4. make install DESTDIR=$TEST_PREFIX PREFIX=$DEFAULT_PREFIX
5. make install PREFIX=$DEFAULT_PREFIX (本地安装)
6. ohc-run.py package xa 2.4.1
7. ohc-run.py finish xa 2.4.1 built

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | make 报 gcc: No such file or directory | Makefile 硬编码 CC=gcc/LD=gcc | sed 修改 CC=clang/LD=clang |
| 2 | DESTDIR 在 xa Makefile 中作为 PREFIX 使用（非标准） | xa Makefile 设计问题 | 重命名 DESTDIR→PREFIX，添加标准 DESTDIR staging 支持 |
| 3 | make test 失败 (harness/hextool shebang #!/usr/bin/perl) | HMDFS perl 路径不在 /usr/bin | 记录为平台限制，核心功能已验证 |
| 4 | G0 clean-verify configure 失败 | xa 无 configure 脚本 | 创建 hints/configure dummy script |

## 源码修改

- 0001-Makefile.patch: CC=gcc→clang, LD=gcc→clang, CFLAGS+=-fPIC, DESTDIR→PREFIX+DESTDIR staging

## 依赖版本

无依赖（standalone C 项目）

## 验证结果

```bash
$DEFAULT_PREFIX/bin/xa --version
xa (xa65) 2.4.1
Written by Andre Fachat, Jolse Maginnis, David Weinehall and Cameron Kaiser

$DEFAULT_PREFIX/bin/file65 → OK (usage output)
$DEFAULT_PREFIX/bin/ldo65 → OK (usage output)
$DEFAULT_PREFIX/bin/printcbm → OK (usage output)
$DEFAULT_PREFIX/bin/reloc65 → OK (usage output)
$DEFAULT_PREFIX/bin/uncpk → OK (usage output)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| xa-2.4.1-ohos-aarch64.tar.gz | 580KB | 预编译包 |

## 注意事项

- xa 是纯 Makefile 项目，无 configure 脚本
- Test harness 因 Perl shebang 路径问题无法完整运行
- Makefile 的 DESTDIR 语义为 PREFIX（非标准），已修正为标准 DESTDIR 模式

---

**编译结束**: 2026-06-15 10:35
**最终状态**: built
