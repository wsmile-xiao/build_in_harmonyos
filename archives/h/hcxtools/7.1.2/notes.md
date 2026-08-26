# hcxtools 7.1.2 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-08-06
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. 下载源码: `https://github.com/ZerBea/hcxtools/archive/refs/tags/7.1.2.tar.gz` (via ghfast.top mirror)
2. 安装依赖: `conan install` with PkgConfigDeps generator
3. 编译: `PKG_CONFIG_PATH=<generators_folder> make CC=clang -j1`
4. 安装: `make install PREFIX=/usr DESTDIR=<staging>`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 不可达 | HarmonyOS 网络限制 | 使用 ghfast.top 镜像下载源码 |
| 2 | curl/8.19.0 不存在 | 制品仓中无此版本 | 使用 curl/8.15.0 |
| 3 | openssl 版本冲突 | curl/8.15.0 要求 openssl/3.5.6.1 | 使用 openssl/3.5.6.1 |
| 4 | zlib 版本冲突 | curl/8.15.0 要求 zlib/1.3.1.1 | 使用 zlib/1.3.1.1 |
| 5 | Makefile 找不到 | self.run() 在 build_folder 执行 | 使用 cwd=self.source_folder |
| 6 | pkg-config 找不到依赖 | PKG_CONFIG_PATH 未设置 | 设置 PKG_CONFIG_PATH=generators_folder |
| 7 | tools.build:compiler_executables:c 不存在 | conf key 格式错误 | 使用 dict 方式获取编译器路径 |

## 依赖版本

- openssl/3.5.6.1
- zlib/1.3.1.1
- curl/8.15.0

## 验证结果

```bash
hcxpcapngtool --version → hcxpcapngtool 7.1.2 (C) 2026 ZeroBeat
hcxhashtool --version → hcxhashtool 7.1.2 (C) 2026 ZeroBeat
hcxpsktool --version → hcxpsktool 7.1.2 (C) 2026 ZeroBeat
hcxpmktool --version → hcxpmktool 7.1.2 (C) 2026 ZeroBeat
hcxpottool --version → hcxpottool 7.1.2 (C) 2026 ZeroBeat
hcxeiutool --version → hcxeiutool 7.1.2 (C) 2026 ZeroBeat
hcxwltool --version → hcxwltool 7.1.2 (C) 2026 ZeroBeat
hcxhash2cap --version → hcxhash2cap 7.1.2 (C) 2026 ZeroBeat
```

## 交付物

10 个命令行工具:
- hcxpcapngtool (OpenSSL + zlib)
- hcxhashtool (OpenSSL + curl)
- hcxpsktool (OpenSSL)
- hcxpmktool (OpenSSL)
- hcxpottool (OpenSSL + pthread)
- hcxeiutool (no deps)
- hcxwltool (no deps)
- hcxhash2cap (no deps)
- wlancap2wpasec (OpenSSL + curl)
- whoismac (OpenSSL + curl)
---

**编译结束**: 2026-08-06 16:54
**最终状态**: built
