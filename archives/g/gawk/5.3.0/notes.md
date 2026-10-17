# gawk 5.3.0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-04-09
- 编译器: clang 15.0.4
- 状态: success

## 编译步骤
1. 下载源码 `gawk-5.3.0.tar.xz` 并解压
2. 应用 11 个补丁 (0001-0011，通过 conan apply_conandata_patches)
3. `./configure --prefix=$HOME/usr/local` (Conan: AutotoolsToolchain 管理 prefix)
4. `make -j1` (全部扩展模块成功编译)
5. `make install DESTDIR=$TEST_PREFIX`

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 不识别 HarmonyOS | 缺少 HarmonyOS 检测 | 添加 `*:HarmonyOS:*:*` case |
| 2 | config.sub 不识别 ohos | 缺少 ohos 操作系统 | 添加 `linux-ohos*` 三处 |
| 3 | fstat 对管道/终端返回 EACCES | HM 安全限制 | `__OHOS__` 条件编译，EACCES/EPERM 时用默认值 |
| 4 | 扩展模块 dirent.h 未正确包含 | `_BSD_SOURCE` 不够 | 改为 `_GNU_SOURCE`，无条件包含 dirent.h |
| 5 | pma.h 找不到 | 包含路径错误 | `#include "pma.h"` → `#include "support/pma.h"` |

## 源码修改
| 文件 | 修改内容 | 是否已生成补丁 |
|------|----------|----------------|
| build-aux/config.guess | 添加 HarmonyOS 检测 | ✅ |
| build-aux/config.sub | 添加 linux-ohos 支持 | ✅ |
| io.c | fstat EACCES 处理 | ✅ |
| main.c | init_fds fstat 处理 | ✅ |
| posix/gawkmisc.c | optimal_bufsize fstat 处理 | ✅ |
| custom.h | pma.h 路径修正 | ✅ |
| extension/*.c | _BSD_SOURCE → _GNU_SOURCE | ✅ |

## 依赖版本
- 无必须依赖
- 可选：mpfr, gmp

## 验证结果
```bash
gawk --version  # GNU Awk 5.3.0, API 4.0 ✅
echo "hello world" | gawk '{print $1}'  # hello ✅
gawk -l time 'BEGIN { print strftime("%Y-%m-%d") }'  # 正常 ✅
gawk -l fork 'BEGIN { if (fork() == 0) print "Child"; else print "Parent" }'  # 正常 ✅
```

## 注意事项
- 13 个扩展模块中 readdir 部分受 fstat 限制，其余全部正常
- 编译后务必进行管道输入测试，确保 fstat 兼容性修复有效
---

**编译结束**: 2026-08-27 12:36
**最终状态**: published
