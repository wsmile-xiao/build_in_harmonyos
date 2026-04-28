# fcrackzip 1.0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-04-24
- 编译器: clang
- 状态: partial（编译成功但未完整验证）

## 编译步骤
1. 下载源码并解压
2. 应用 3 个补丁（crack.h, getopt.c, getopt1.c）
3. `./configure --prefix=$DEFAULT_PREFIX`
4. `make -j$(nproc)`
5. `make install` 到 staging 目录

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 编译错误 | crack.h/getopt.c/getopt1.c 不兼容 OHOS | 修补相关文件 |

## 源码修改
| 文件 | 修改内容 | 是否已生成补丁 |
|------|----------|---------------|
| crack.h | 平台适配 | ✅ 0001-crack.h.patch |
| getopt.c | 平台适配 | ✅ 0002-getopt.c.patch |
| getopt1.c | 平台适配 | ✅ 0003-getopt1.c.patch |

## 依赖版本
无外部依赖

## 注意事项
- 原始源码 URL 为本地文件，已替换为 GitHub 公开 URL
