# whois 5.6.6 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-05-28
- 编译器: clang/clang++
- 状态: built

## 编译步骤

whois 使用简单的 Makefile 构建，不需要 configure 步骤：

1. 下载源码（使用 ghproxy.net 镜像加速 GitHub 下载）
2. 安装依赖 libidn2 2.3.8（从 cmd-pkgs 预编译包）
3. 生成 version.h：`perl make_version_h.pl debian/changelog > version.h`
4. 编译：`make whois prefix=$DEFAULT_PREFIX`
5. Staging 安装：`make install-whois prefix=$DEFAULT_PREFIX DESTDIR=$TEST_PREFIX`
6. 本地安装：`make install-whois prefix=$DEFAULT_PREFIX`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 下载超时 | 国内网络访问 GitHub 困难 | 使用 ghproxy.net 镜像加速 |
| 2 | IDSTRING 未定义 | 缺少 version.h 文件 | 运行 `perl make_version_h.pl debian/changelog > version.h` |
| 3 | libidn2 未安装 | 依赖缺失 | 从 cmd-pkgs 安装预编译包 libidn2 2.3.8 |
| 4 | curl 命令损坏 | curl 依赖库问题 | 使用 Python urllib 替代 |

## 源码修改

无补丁。需要生成 version.h 文件（由 make_version_h.pl 脚本生成）。

## 依赖版本

- libidn2 2.3.8（从 cmd-pkgs 预编译包安装）

## 验证结果

```bash
$ whois example.com
   Domain Name: EXAMPLE.COM
   Registry Domain ID: 2336799_DOMAIN_COM-VRSN
   ...
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| whois-5.6.6-ohos-aarch64.tar.gz | ~220KB | 预编译包（待生成） |

## 注意事项

1. whois 使用 Makefile 构建，不是 autotools，无需 configure 步骤
2. 需要运行 `make_version_h.pl` 生成 version.h，否则编译失败
3. libidn2 是可选依赖，但建议安装以支持国际化域名
4. mkpasswd 编译失败（缺少 getpass 函数），但 whois 本体编译成功
---

**编译结束**: 2026-05-28 10:31
**最终状态**: built
