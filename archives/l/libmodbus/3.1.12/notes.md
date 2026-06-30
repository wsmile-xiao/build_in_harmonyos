# libmodbus 3.1.12 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-21
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. source .build-context-libmodbus-3.1.12
2. cd $BUILD_SRC_DIR
3. perl $SKILL_ROOT/scripts/patch-autotools-ohos.pl build-aux/config.guess build-aux/config.sub（已预装OHOS补丁）
4. sed -i 's/umask 000 && mktemp/umask 007 && mktemp/g; s/umask 000 && mkdir/umask 007 && mkdir/g' configure（HMDFS umask陷阱修复）
5. ./configure --prefix=$DEFAULT_PREFIX
6. make -j1 && make install DESTDIR=$TEST_PREFIX
7. make check — 失败（需要modbus网络/串口连接，构建环境中不可用）
8. python3 $SKILL_ROOT/scripts/ohc-run.py package libmodbus 3.1.12
9. make install（无DESTDIR）
10. pkg-config --modversion libmodbus 验证

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure报错"cannot compute suffix of executables: cannot compile and link" | HMDFS umask陷阱：configure脚本用umask 000创建临时目录，导致conftest.c文件在两次测试之间被删除 | sed将configure中的`umask 000`改为`umask 007` |
| 2 | make check失败 | 单元测试需要modbus TCP/串口连接，构建环境无此硬件；killall命令不可用 | 跳过，记录原因 |

## 源码修改

- configure: umask 000 → umask 007（两处）
- build-aux/config.guess, build-aux/config.sub: OHOS补丁（已预装）

## 依赖版本

无外部依赖（纯C库，仅需要标准libc头文件）

## 验证结果

```bash
pkg-config --modversion libmodbus  → 3.1.12
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libmodbus-3.1.12-ohos-aarch64.tar.gz | TBD | 预编译包 |

## 注意事项

- libmodbus测试套件依赖modbus网络连接，在无串口/TCP设备的环境下无法运行
- configure脚本的umask 000陷阱是HMDFS通用问题，需要sed修复
---

**编译结束**: 2026-05-21 22:12
**最终状态**: built
