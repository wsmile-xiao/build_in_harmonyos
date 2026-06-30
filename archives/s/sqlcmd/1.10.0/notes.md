# sqlcmd 1.10.0 适配笔记

## 编译环境
- 构建系统: prebuilt/go (Go 项目预编译二进制适配)
- 编译日期: 2026-06-09
- 编译器: clang/clang++
- 状态: built

## 编译步骤
  1. 初始化: `ohc-run.py init-build sqlcmd 1.10.0 --url=https://github.com/microsoft/go-sqlcmd/archive/refs/tags/v1.10.0.tar.gz`
  2. 下载官方预编译二进制: `https://github.com/microsoft/go-sqlcmd/releases/download/v1.10.0/sqlcmd-linux-arm64.tar.bz2`
  3. 解压并提取 sqlcmd 二进制
  4. ELF 签名: `ohc-run.py sign-elf` 5. 安装到 DESTDIR ( `~/usr/local/bin/sqlcmd`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Go linker mmap 失败 | HarmonyOS hmdfs 不支持 fallocate ( posix_fallocate 在 hmdfs/tmpfs 上返回 errno=13 (EACCES)， Go linker 在 fallocate     仍然尝试 mmap， 文件大小为 0 | mmap(size) 在 0 bytes文件上 失败 | | 下载官方预编译二进制并 ELF 签名 适配 | CGO_ENABLED=0, Go 静态编译 |

## 源码修改
 无源码修改（无补丁) - 它 使用官方预编译二进制， Go linker mmap 问题不需要源码修改，只需 ELF 签名 适配 |

## 依赖版本
- Go 1.25.7 (via goenv)
goenv 3.1.1)
## 验证结果
```bash
# ELF 签名前 ohc-run.py sign-elf`  => 可手动确认弹窗
 sqlcmd --version

```
## 交付物
| 文件 | 大小 | 说明 |
|------|------|------|
| sqlcmd-1.10.0-ohos-aarch64.tar.gz | ~7MB | 预编译包 (aarch64) |
| sqlcmd-1.10.0-ohos-aarch64-debug.tar.gz | ~7MB | 调试版 (debug) |
## 注意事项
- HarmonyOS 上 Go linker 因 fallocate/mmap 限制无法编译 Go 项目
 霄要下载官方预编译二进制
---

**编译结束**: 2026-06-09 22:36
**最终状态**: built
