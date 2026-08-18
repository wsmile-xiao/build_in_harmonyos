# bvi 1.5.0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-08
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 初始化编译环境：`ohc-run.py init-build bvi 1.5.0`
2. 应用 HarmonyOS 平台识别补丁：`perl patch-autotools-ohos.pl config.guess config.sub`
3. 修改 configure 脚本：禁用 `umask 077`（HarmonyOS umask 行为差异导致临时目录权限异常）
4. 运行配置：`./configure --prefix=/storage/Users/currentUser/usr/local`
5. 编译：`make -j1`
6. 安装：`make install DESTDIR=$TEST_PREFIX` + `make install`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | GNU config.guess 不包含 HarmonyOS 检测分支 | 应用 patch-autotools-ohos.pl 补丁 |
| 2 | config.status 临时目录权限拒绝 | HarmonyOS umask 077 导致目录权限异常（270而非700） | 禁用 configure 中的 umask 077 |
| 3 | bm_unix.c termcap 函数未声明 | 缺少 termcap.h 头文件包含 | 添加 `#include <termcap.h>` |
| 4 | ln 硬链接失败 | HMDFS 不支持硬链接 | 修改 Makefile.in 使用软链接 |

## 源码修改

1. **Makefile.in**: 将硬链接改为软链接（`ln → rm -f && ln -s`）
2. **bm_unix.c**: 添加 `#include <termcap.h>` 头文件
3. **config.guess**: 添加 HarmonyOS/__OHOS__ 检测分支
4. **config.sub**: 添加 ohos-linux triplet 支持
5. **configure**: 禁用 umask 077（临时修复）

## 依赖版本

- ncurses: 系统预编译包

## 验证结果

```bash
# 二进制文件检查
ls -la ~/usr/local/bin/bvi ~/usr/local/bin/bmore
# bvi: 321984 bytes, executable
# bmore: 137664 bytes, executable
# bview, bvedit: 软链接到 bvi

# 帮助文件
ls -la ~/usr/local/share/bvi/bmore.help
# bmore.help: 1584 bytes
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bvi | 321984 | 二进制编辑器主程序 |
| bmore | 137664 | 二进制查看器 |
| bview → bvi | - | 软链接 |
| bvedit → bvi | - | 软链接 |

## 注意事项

- bvi/bmore 需要终端环境运行
- /tmp 在 HarmonyOS 上为只读，使用 $TMPDIR 替代
- 禁用 umask 077 是平台特有的临时修复，可能需要在知识图谱中记录
---

**编译结束**: 2026-07-13 21:17
**最终状态**: built
