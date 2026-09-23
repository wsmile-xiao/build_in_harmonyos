# pktanon 1.4.0 适配笔记

## 版本背景（重要）

- 上游（KIT Telematics，www.tm.kit.edu/software/pktanon）**从未发布正式的（非 dev）1.4.0 发行版**。
- 唯一官方 1.4.0 系发行物 = 官网 tarball `pktanon-1.4.0-dev.tar.gz`，解包后 `configure.ac` 内
  `AC_INIT([pktanon], [1.4.0-dev])`（自报 1.4.0-dev）。
- GitHub 镜像 KIT-Telematics/pktanon 默认分支 master 已是 2.0-beta（AC_INIT 2.0-beta），**无 git tag、
  无 release** —— 不可作为 1.4.0 源。
- 决策：归档版本号 = `1.4.0`（用户指定）；`conandata.yml` url 指向官方 1.4.0-dev tarball（官方源，R39）；
  sha256 = `db3f437bcb8ddb40323ddef7a9de25a465c5f6b4cce078202060f661d4b97ba3`。Conan 版本解析对归档版本
  无硬约束，故 version=1.4.0、source 指向 -dev tarball（运行时横幅输出 v1.4.0-dev，属上游自报，不影响归档）。

## 编译环境
- 构建系统: autotools（tarball 自带 configure / Makefile.in，无需 automake 再生成）
- 编译日期: 2026-09-04
- 编译器: clang/clang++（OHOS aarch64 原生，profile ohos-aarch64）
- 状态: built/published（见 manifest.yaml）

## 编译步骤

```bash
# 探索编译（依赖取自制品仓已发布二进制）
conan install --requires=xerces-c/3.2.5 --requires=boost/1.84.0 -r=ohpcd -pr=... --build=never
CPPFLAGS="-I<boost>/include -I<xerces>/include" LDFLAGS="-L<xerces>/lib" \
  ./configure --prefix=$DEFAULT_PREFIX
make -j2            # 产物 bin/pktanon
make check          # 上游无 TESTS，空操作
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `config.status: can't create ./conf*/subs1.awk: Permission denied` / `could not setup config files machinery` | HMDFS 强制 setgid + configure 临时目录 `umask 077` → 生成 drwx--S--- 目录，属主亦不可写（E129） | 构建前将 configure 中 `umask 077` 改为 `umask 022`（conanfile `_patch_configure_umask()`，探索期 sed 验证通过） |
| 2 | `src/Timer.cpp:82: use of undeclared identifier 'sleep'` | Timer.h 的 `#elif defined LINUX` 分支调用 sleep() 却未 `#include <unistd.h>`；glibc 下被传递引入掩盖，musl(OHOS) 下暴露 | Timer.h LINUX 分支补 `#include <unistd.h>`（conanfile `_patch_timer_unistd()`，通用可移植性修复，无平台宏） |

## 源码修改

上游两个 bug 均以 **conanfile.py build() 内联修复**实现（参考 archives/a/abnfgen/0.21 处理同类 configure
临时目录问题的先例），未采用静态 patches/*.patch 文件（`patches/` 目录不存在，conandata `patches: {}`）。
理由：修改量小、幂等、自包含，且 0002(Timer.h) 的自动补丁 dry-run 不干净。

## 依赖版本

| 依赖 | 版本 | 引入方式 | 说明 |
|------|------|----------|------|
| xerces-c | 3.2.5 | `self.requires("xerces-c/3.2.5")` | 制品仓已发布；静态库（recipe 默认 shared=False，transcoder=gnuiconv/message-loader=inmemory/network=socket，零外部依赖），pktanon 链接后运行时无 NEEDED xerces |
| boost | 1.84.0 | `self.requires("boost/1.84.0")` | 仅头文件使用（configure 检查 boost/pool/object_pool.hpp，代码 include boost/cstdint.hpp）；boost 自身依赖 zlib/1.3.1 已发布 |

> 链接命令仅需 `-lxerces-c -lpthread`（xerces 静态库不需 -lz，已实测去掉 -lz 可链接可运行）。
> pcap 解析为 pktanon 自实现（PcapFile.cpp 直接读写 pcap 文件格式），**不依赖 libpcap**。

## 验证结果

```bash
# 端到端功能验证（test_package 同款）：1 包以太网/IPv4/TCP pcap + identity profile
./pktanon profile.xml   # → "anonymization done"，生成 out.pcap（含 pcap 魔数）
make check              # 上游无测试套件，无操作
```

## 注意事项

- pktanon 为命令行工具（bin/pktanon），软件类型 tool（R38），已在软件级目录提交 `commands.json`。
- 运行时动态依赖仅 `libc++_shared.so` / `libc.so`（system），无未发布依赖。
- 上游 `make check` 空操作；真实功能验证在 test_package（解析 XML→读 pcap→匿名化→写 pcap 全链路）。
