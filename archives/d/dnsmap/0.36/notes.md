# dnsmap 0.36 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-12
- 编译器: clang 15.0.4 / clang++
- 状态: published

## 编译步骤

1. 恢复源码从 .orig 目录
2. 运行 `autoreconf -i` 生成 configure 脚本
3. 修补 configure 中的 `umask 077` → `umask 002`（HMDFS平台适配）
4. 运行 `./configure --prefix=/storage/Users/currentUser/usr/local`
5. 运行 `make -j1`
6. 运行 `make install DESTDIR=/storage/Users/currentUser/tmp/test-install-dnsmap-0.36`
7. R7验证：`dnsmap` 输出 "dnsmap 0.36 - DNS Network Mapper"
8. `make check` — 无测试套件

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.status 无法创建临时目录，报 Permission denied | HMDFS 文件系统继承父目录的 owner uid（20001006）而非当前用户 uid（20020101）；`umask 077` 创建权限 700 的目录，仅 owner 有权限，当前用户无法写入 | 修补 configure 中两处 `umask 077` → `umask 002`，允许组用户写入（当前用户属于 file_manager 组 gid 1006） |
| 2 | 源码包不含 configure 脚本和 config.guess/config.sub | GitHub tarball 为 git archive 格式，不含 autotools 生成文件 | 运行 `autoreconf -i` 生成所有必要文件 |

## 源码修改

- **configure**: 修改两处 `umask 077` → `umask 002`（行 5398 和 5403）
  - 这是 HMDFS 平台适配，类似 E007 的 config.guess/config.sub 修改
  - 补丁文件: `0001-configure-hmdfs-umask.patch`

## 依赖版本

无必需依赖，无可选依赖。

## 验证结果

```bash
$ dnsmap
dnsmap 0.36 - DNS Network Mapper

$ dnsmap-bulk
usage: dnsmap-bulk <domains-file> [results-path]
```

## 交付物

| 文件 | 说明 |
|------|------|
| bin/dnsmap | DNS子域名暴力枚举器 |
| bin/dnsmap-bulk | 批量调用dnsmap的bash脚本 |
| share/man/man1/dnsmap.1 | dnsmap手册页 |
| share/man/man1/dnsmap-bulk.1 | dnsmap-bulk手册页 |

## 注意事项

- HMDFS 文件系统的 owner uid 继承特性会影响所有使用 `umask 077` 创建临时目录的 autotools 项目，此补丁模式可复用
- dnsmap 不支持 `--version` 参数，直接运行输出 banner 信息
- dnsmap 无测试套件
---

**编译结束**: 2026-06-12 17:03
**最终状态**: published
