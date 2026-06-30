# crunch 3.6 适配笔记

## 编译环境
- 构建系统: makefile（纯 Makefile 项目，无 configure 脚本）
- 编译日期: 2026-06-01
- 编译器: clang 15.0.4 / clang++ 15.0.4
- 状态: published

## 编译步骤

1. **下载源码**: `curl -kL -o ~/tmp/crunch-3.6.tar.gz https://sourceforge.net/projects/crunch-wordlist/files/crunch-3.6.tgz/download`
2. **初始化**: `python3 $SKILL_ROOT/scripts/ohc-run.py init-build crunch 3.6 --url=... --no-download`
3. **修正 manifest.yaml**: build_system 从 autotools 改为 makefile（crunch 没有 configure 脚本）
4. **编译**:
   ```bash
   cd ~/tmp/builds/crunch-3.6.work
   make CC=clang PREFIX=$DEFAULT_PREFIX CFLAGS="-fPIC -O2" LFS="" INSTALL="install" INSTALL_OPTIONS=""
   ```
5. **Staging 安装** (DESTDIR 模式, R20):
   ```bash
   make install DESTDIR=$TEST_PREFIX PREFIX=$DEFAULT_PREFIX INSTALL="install" INSTALL_OPTIONS=""
   ```
6. **安全弹窗验证(R7)**: `$TEST_PREFIX/$DEFAULT_PREFIX/bin/crunch --version` → "crunch version 3.6"
7. **功能测试**: `crunch 1 2 0123456789 -o test.txt` → 110 行密码列表生成成功
8. **预编译包制作**: `python3 $SKILL_ROOT/scripts/ohc-run.py package crunch 3.6`
9. **本地安装**: `make install PREFIX=$DEFAULT_PREFIX INSTALL="install" INSTALL_OPTIONS=""`
10. **用户验证**: `~/usr/local/bin/crunch --version` → "crunch version 3.6"

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 检测构建系统为 autotools | crunch 只有 Makefile，无 configure，但 init-build 默认检测为 autotools | 修正 manifest.yaml: build_system 改为 makefile |
| 2 | Makefile 默认 INSTALL=sudo install | 鸿蒙环境无 sudo，且需用普通 install | 覆盖 INSTALL="install" INSTALL_OPTIONS="" |
| 3 | Makefile 默认 CC=gcc | 鸿蒙平台使用 clang | 覆盖 CC=clang |
| 4 | Makefile 默认 LFS=getconf POSIX_V6_ILP32_OFFBIG_CFLAGS | 鸿蒙 getconf 可能返回不兼容选项 | 覆盖 LFS="" |
| 5 | 编译有2个 strict-prototypes 警告 | crunch.c 的 ex_program() 和 usage() 函数声明缺少 void 参数 | 非关键警告，不阻塞编译 |

## 源码修改

无需源码修改（无补丁）。仅通过 Make 变量覆盖解决所有问题：
- CC=clang, CFLAGS="-fPIC -O2", LFS=""
- INSTALL="install", INSTALL_OPTIONS=""（去掉 sudo 和 root 权限选项）

## 依赖版本

- 无外部依赖（仅 libc 数学库 -lm）

## 验证结果

```bash
$ ~/usr/local/bin/crunch --version
crunch version 3.6

$ crunch 1 2 0123456789 -o test.txt
Crunch will now generate the following number of lines: 110
crunch: 100% completed generating output
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| crunch-3.6-ohos-aarch64.tar.gz | 133163 bytes (130KB) | 预编译包（含 bin/crunch、share/crunch/charset.lst、share/man/man1/crunch.1、share/doc/crunch/COPYING） |
| crunch-3.6-ohos-aarch64-debug.tar.gz | 30743 bytes (30KB) | 调试符号包 |

## 注意事项

- crunch 是纯 Makefile 项目，不支持 configure，必须通过 Make 变量覆盖控制编译参数
- INSTALL 变量必须覆盖为普通 "install"，否则默认用 "sudo install" 导致权限问题
- INSTALL_OPTIONS 必须设为空，否则默认 "-g root -o root" 在鸿蒙上不适用
- DESTDIR 模式已在 Makefile 的 install 目标中原生支持（无需修改）
---

**编译结束**: 2026-06-01 18:50
**最终状态**: published
