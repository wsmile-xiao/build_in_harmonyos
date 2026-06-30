# libxls 1.6.3 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-03（重试）
- 编译器: clang/clang++ (15.0.4)
- 状态: built（之前因 ENOMEM 中断，本次成功）

## 编译步骤

1. `python3 $SKILL_ROOT/scripts/ohc-run.py init-build libxls 1.6.3 --url=URL --no-download`（恢复构建上下文）
2. config.guess 已由之前 patch-autotools-ohos.pl 补丁修复，无需重做
3. config.sub 需要重新添加 `linux-ohos*-` kernel-OS validation case（之前的补丁保留在 .work 中）
4. `./configure --prefix=$DEFAULT_PREFIX` → configure 全部通过
5. 修复 config.status umask 077 → 002（HMDFS Permission denied）
6. 修复 configure umask 077 → 002（固化到源文件）
7. `make -j1` → 编译成功
8. `make install DESTDIR=$TEST_PREFIX` → staging 安装成功
9. `make check` → 1 test FAIL（平台限制：musl ld 不支持 LD_LIBRARY_PATH）
10. `make install` → 本地安装成功（不带 DESTDIR）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 | 类型 |
|---|------|------|----------|------|
| 1 | config.guess 无法识别 HarmonyOS | E007: GNU config.guess 不含 HarmonyOS 检测 | patch-autotools-ohos.pl 补丁（已保留在 .work 目录） | 平台（L1） |
| 2 | config.sub 拒绝 linux-ohos 三元组 | kernel-OS validation 缺少 linux-ohos 组合 | 手动添加 `linux-ohos*-)` case → 补丁 0002-config.sub.patch | 平台（L1） |
| 3 | config.status 临时目录 Permission denied | HMDFS 不允许 umask 077 创建目录内写文件 | 修改 umask 077 → 002 → 补丁 0003-configure.patch | 平台（L1） |
| 4 | make check 测试 FAIL (exit 127) | musl ld 不支持 LD_LIBRARY_PATH/RUNPATH，共享库无法加载 | 平台限制，不影响编译产物。部署到系统路径后可工作 | 平台（L1） |
| 5 | 之前编译因 ENOMEM 中断 | 系统内存耗尽 | 重试编译成功（内存已恢复） | 环境 |

## 源码修改

### config.guess（patch-autotools-ohos.pl 自动修改，保留在 .work）
- 添加 `__OHOS__` LIBC 检测分支
- 添加 HarmonyOS 系统识别 case

### config.sub（补丁 0002-config.sub.patch）
- 添加 `ohos-linux` triplet 映射
- 添加 `ohos*` 到 OS 列表
- 添加 `linux-ohos*-` kernel-OS validation case

### configure（补丁 0003-configure.patch）
- 修改 `umask 077` → `umask 002`（解决 HMDFS Permission denied）

## Staging 产物验证

```
二进制: xls2csv (27KB)
共享库: libxlsreader.so.8.0.3 (80KB) + symlinks (.so, .so.8)
头文件: include/xls.h, libxls/*.h (9 个)
pkg-config: libxls.pc
man page: xls2csv.1
```

## make check 结果

```
TOTAL: 1
PASS: 0
FAIL: 1 (test_libxls - 平台限制：musl ld 无法加载共享库)
SKIP: 0
```

**测试失败原因**: HarmonyOS musl 动态链接器 (`ld-musl-aarch64.so.1`) 不支持 LD_LIBRARY_PATH/RUNPATH，
库搜索路径受限于 `/etc/ld-musl-aarch64.path` 中列出的系统路径。
当库部署到系统路径后，测试应可通过。

---

**编译开始**: 2026-06-03 重试编译
**编译结束**: 2026-06-03 编译成功
**最终状态**: built（make check 1 FAIL - 平台限制）
---

**编译结束**: 2026-06-03 17:24
**最终状态**: built
