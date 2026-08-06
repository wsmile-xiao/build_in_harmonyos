# fcrackzip 1.0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-08-06
- 编译器: clang 15.0.4
- 状态: built (conan 适配完成，待 CI 发布)

## 编译步骤
1. 下载源码并解压（来自 Kali 镜像源 fcrackzip_1.0.orig.tar.gz）
2. 通过 replace_in_file() 修补 4 个文件（crack.h, getopt.c, getopt1.c, configure umask fix）
3. `./configure --prefix=$DEFAULT_PREFIX`
4. `make -j1`（OHOS 不支持 jobserver mkfifo）
5. `make install` 到 staging 目录

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 编译错误 | crack.h/getopt.c/getopt1.c 使用 `#include <config.h>` 系统包含路径 | 改为 `#include "config.h"` 本地包含 |
| 2 | config.status 创建临时文件失败 | configure 脚本使用 `umask 077` 创建临时目录，OHOS 文件系统保留 setgid 位但无 group execute，导致 `drwx--S---` 模式无法在目录内创建文件 | 修补 configure 脚本将 `umask 077` 改为 `umask 022` |
| 3 | make -j2 失败 | OHOS 不支持 jobserver mkfifo (Operation not permitted) | 使用 `make -j1` |

## 源码修改
| 文件 | 修改内容 | 补丁文件 |
|------|----------|----------|
| crack.h | 添加 `#include "config.h"` 包含守卫 | 0001-crack.h.patch |
| getopt.c | `<config.h>` → `"config.h"` | 0002-getopt.c.patch |
| getopt1.c | `<config.h>` → `"config.h"` | 0003-getopt1.c.patch |
| configure | `umask 077` → `umask 022` (临时目录权限修复) | conanfile.py build() replace_in_file |

## 依赖版本
无外部依赖

## 注意事项
- GitHub 仓库 https://github.com/hyc/fcrackzip 无 release tags，源码使用 Kali 镜像源 orig.tar.gz
- 系统已提供 getopt_long，因此 getopt.c/getopt1.c 不会被编译，补丁仅为完整性
- fcrackzip 构建产物为可执行文件（fcrackzip, zipinfo），非库文件
---

**编译结束**: 2026-08-06 10:51
**最终状态**: built
