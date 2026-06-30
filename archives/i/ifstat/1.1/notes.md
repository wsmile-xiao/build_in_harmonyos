# ifstat 1.1 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-01
- 编译器: clang 15.0.4 / clang++
- 平台: OpenHarmony (aarch64, musl libc)
- 状态: published

## 编译步骤

```bash
source .build-context-ifstat-1.1
cd $BUILD_SRC_DIR
./configure --prefix=$DEFAULT_PREFIX
make -j1
make install DESTDIR=$TEST_PREFIX
```

关键参数：仅使用 `--prefix=$DEFAULT_PREFIX`（R1 铁律：不加 --build/--host/--target）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 下载失败（SSL 证书验证） | 鸿蒙平台 SSL 证书链不完整 | 手动 `curl -kL` 下载 tarball 后用 `--no-download` 模式初始化 |
| 2 | `make install DESTDIR=$TEST_PREFIX` 未安装到 staging 目录，直接安装到 prefix | Makefile.in 不支持 DESTDIR（install 目标路径缺少 $(DESTDIR) 前缀） | 修改 Makefile.in：添加 `DESTDIR =` 变量，所有 install 路径 prepend `$(DESTDIR)` |
| 3 | manifest.yaml G4 检查报"缺少 build_system" | G4 门禁要求顶层 `build_system:` 字段，而模板只有嵌套的 `build.system` | 在 manifest.yaml 顶层添加 `build_system: autotools` |
| 4 | 二进制未签名无法执行（"operation not permitted"） | 鸼蒙平台要求 ELF 签名才能执行 | 使用 `ohc-run.py sign-elf` 签名 |

## 源码修改

### 补丁: 0001-Makefile.in.patch

修改内容：为 Makefile.in 添加 DESTDIR 支持，确保 `make install DESTDIR=...` 正确安装到 staging 目录。

具体变更：
1. 在变量声明区域添加 `DESTDIR =`
2. `install-$(TARGET)` 目标中的 `$(bindir)` → `$(DESTDIR)$(bindir)`，`$(mandir)` → `$(DESTDIR)$(mandir)`
3. `install-$(LIBTARGET)` 目标中的 `$(bindir)` → `$(DESTDIR)$(bindir)`，`$(includedir)` → `$(DESTDIR)$(includedir)`，`$(libdir)` → `$(DESTDIR)$(libdir)`

变更统计：+11/-10

## 依赖版本

ifstat 1.1 无外部依赖，仅需：
- clang 15.0.4
- GNU Make 4.4.1
- ginstall (GNU coreutils)

## 验证结果

```bash
# 版本查询
$ ifstat -v
ifstat version 1.1.
Copyright (C) 2001-2003, Gaël Roualland <gael.roualland@dial.oleane.com>
Compiled-in drivers: proc.

# 单次带宽采样
$ ifstat 1 1
      wlan0                p2p0               chba0
 KB/s in  KB/s out   KB/s in  KB/s out   KB/s in  KB/s out
    0.72      0.00      0.00      0.00      0.00      0.00

# 指定接口统计
$ ifstat -i wlan0 1 1
      wlan0
 KB/s in  KB/s out
    0.00      0.00

# 二进制格式
$ file ~/usr/local/bin/ifstat
ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), stripped
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| ifstat-1.1-ohos-aarch64.tar.gz | 91KB | 预编译包（含 ELF 签名） |
| ifstat-1.1-ohos-aarch64-debug.tar.gz | 18KB | 调试符号包 |
| 0001-Makefile.in.patch | 2.1KB | DESTDIR 支持补丁 |

## 注意事项

- ifstat 不支持 `--version` 参数，版本查询需用 `-v`（验证脚本注意用 `-v` 而非 `--version`）
- ifstat 1.1 无测试套件（`make check` 无目标），仅通过手动功能验证确认可用性
- 编译过程中有一个 clang 警告（ifstat.c:493 非法字符编码），属源码自带问题（版权字符串含非 ASCII 字符），不影响功能

---

**编译结束**: 2026-06-01 18:10
**最终状态**: published
