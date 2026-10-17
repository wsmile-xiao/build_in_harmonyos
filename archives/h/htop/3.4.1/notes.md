# htop 3.4.1 适配笔记

## 编译环境
- 构建系统: autotools (configure)
- 编译日期: 2026-04-14
- 编译器: clang 15.0.4 (LLVM)
- 状态: partial（编译成功，运行受平台权限限制）

## 编译步骤
1. 下载并解压源码（htop-3.4.1.tar.xz, 418K）
2. 应用 3 个补丁：config.guess + config.sub + IOPriorityPanel.h
3. 配置：`./configure --prefix=$HOME/usr/local NCURSES_CFLAGS=-I$HOME/usr/local/include NCURSES_LIBS="-L$HOME/usr/local/lib -lncursesw" LDFLAGS=-L$HOME/usr/local/lib`
4. 编译：`make`
5. 安装：`make install`

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | /proc 文件系统权限限制 | 鸿蒙 SELinux 策略限制 | 使用 `sudo $HOME/usr/local/bin/htop` |
| 2 | 系统 libncursesw.so.6 无法加载 | SELinux 限制共享库加载 | 静态链接 ncursesw（LDFLAGS=-static） |
| 3 | sudo 后功能键不工作 | TERM/TERMINFO 环境变量丢失 | `sudo -E TERM=xterm-256color TERMINFO=$HOME/usr/local/share/terminfo htop` |
| 4 | config.guess 不在根目录 | htop 的 config 文件在 build-aux/ 子目录 | 补丁路径使用 build-aux/ 前缀 |
| 5 | IOPriorityPanel.h include 路径错误 | htop 3.4.1 自身 bug | 修改为 `#include "../Panel.h"` |

## 源码修改
| 文件 | 修改内容 | 是否已生成补丁 |
|------|----------|----------------|
| build-aux/config.guess | 添加 HarmonyOS 系统检测 | ✅ 0001-build-aux-config.guess.patch |
| build-aux/config.sub | 添加 ohos 操作系统支持 + linux-ohos* 白名单 | ✅ 0002-build-aux-config.sub.patch |
| linux/IOPriorityPanel.h | `#include "Panel.h"` → `#include "../Panel.h"` | ✅ 0003-linux-IOPriorityPanel.h.patch |

## 依赖版本
- ncursesw（静态链接，编译的 .a 版本）
- clang, make

## 验证结果
- htop --version 通过 ✅
- 二进制签名通过 ✅
- ncursesw 静态链接通过（NEEDED 仅 libc.so）✅
- /proc/stat 需 sudo（平台限制）

## 交付物
| 文件 | 大小 | 说明 |
|------|------|------|
| htop-3.4.1-ohos-aarch64.tar.gz | 539KB | 主包 |
| htop-3.4.1-ohos-aarch64-debug.tar.gz | 117KB | debug 包 |

## 注意事项
- 必须使用 sudo 运行：`sudo -E TERM=xterm-256color TERMINFO=$HOME/usr/local/share/terminfo $HOME/usr/local/bin/htop`
- ncursesw 已静态嵌入，无需运行时 ncurses 库
- htop 没有官方测试套件
- patch-autotools-ohos.pl 漏加 kernel-os 白名单 linux-ohos*，需手动补充
---

**编译结束**: 2026-08-10 02:01
**最终状态**: built
