# arpalert 2.0.12 适配笔记

## 软件信息
- **名称**: arpalert
- **版本**: 2.0.12
- **构建系统**: autotools (configure + Makefile.in, non-standard automake)
- **类型**: 命令行工具 (ARP 网络监控)
- **许可证**: GPL-2.0-or-later
- **上游**: https://github.com/thierry-f-78/arpalert

## 依赖
- **libpcap/1.10.6** — 通过 Conan 制品仓获取，用于 ARP 抓包

## 编译修改

### 1. configure — umask 077 → 022
- **原因**: HMDFS 文件系统下 umask 077 导致临时目录不可写，configure 失败
- **修改**: `sed -i 's/umask 077/umask 022/g' configure`
- **行号**: 11300, 11305

### 2. Makefile.in — 添加 @LDFLAGS@
- **原因**: Makefile.in 硬编码 `LDFLAGS = -Wl,--export-dynamic`，不包含 `@LDFLAGS@`
- **修改**: `LDFLAGS = @LDFLAGS@ -Wl,--export-dynamic`
- **影响**: Conan Toolchain 的 LDFLAGS 可以正确传递给链接器

### 3. module_example/Makefile — CC 和 CFLAGS 修复
- **原因**: 
  - `CC = gcc` 硬编码，不支持交叉编译
  - `CFLAGS = -Wall -g` 缺少 -fPIC，aarch64 上编译 .so 失败
  - 缺少 -fcommon，clang 对重复全局定义报错
- **修改**: 
  - `CC = gcc` → `CC ?= gcc` (允许环境变量覆盖)
  - `CFLAGS = -Wall -g` → `CFLAGS = -Wall -g -fPIC -fcommon`

## 编译步骤
```bash
CFLAGS="-fPIC -O2 -fcommon -I${PCAP_DIR}/include" \
LDFLAGS="-L${PCAP_DIR}/lib" \
LIBS="-lpcap" \
bash ./configure --prefix=$DEFAULT_PREFIX --with-syslog
make -j1
make install DESTDIR=$TEST_PREFIX
```

## 测试
- **上游测试**: 无（Makefile 无 check 目标）
- **二进制验证**: `arpalert -h` 正常输出帮助信息
- **安装验证**: install.sh 支持 DESTDIR，文件正确安装到 sbin/, etc/arpalert/, include/, man/man8/

## 补丁列表
1. `0001-Makefile.in.patch` — 添加 @LDFLAGS@
2. `0002-configure.patch` — umask 077 → 022
3. `0003-module_example-Makefile.patch` — CC ?= gcc + CFLAGS -fPIC -fcommon
---

**编译结束**: 2026-08-14 12:43
**最终状态**: built
