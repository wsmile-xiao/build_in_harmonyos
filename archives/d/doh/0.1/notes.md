# doh 0.1 适配笔记

## 软件信息
- 名称: doh
- 版本: 0.1
- 描述: Stand-alone DNS-over-HTTPS resolver using libcurl
- 主页: https://github.com/curl/doh
- 许可证: MIT
- 语言: C

## 构建系统适配

### 原始构建系统
doh 0.1 使用手写的简单 Makefile（非 autotools），仅有 `make` 和 `make clean` 目标。
Makefile 依赖 `curl-config` 获取 libcurl 的编译和链接选项。

### 适配修改
1. **创建 build.sh**: 添加了 `build.sh` 包装脚本，支持 `all`/`install`/`clean` 子命令，
   以兼容 clean-verify 的 custom 构建系统流程。
2. **Manifest 构建系统**: 设为 `custom`（因为非标准 autotools，无 configure 脚本）。

### 编译选项
- 编译器: clang 15.0.4
- CFLAGS: -W -Wall -pedantic -g（来自 Makefile）+ curl-config --cflags
- LDLIBS: curl-config --libs
- 编译参数: 无特殊参数，直接 `make`

### 依赖
- libcurl（通过 curl-config，已预安装在 ~/usr/local）
- 无其他外部依赖

## make check
- 无 `check` 目标（简单项目，不包含测试套件）
- 执行了 14 项手动功能测试，详见 reports/test-report.md

## 手动测试结果摘要
- 基础功能: 5/5 通过（版本、帮助、参数验证）
- 错误处理: 3/3 通过（无参数、无效选项、多选项组合）
- 网络功能: 0/4 通过（4 项因环境网络限制未通过，非二进制问题）
- 二进制完整性: 2/2 通过（ELF64 arm64 PIE, 依赖 libcurl.so.4 + libc.so）
- **结论**: 二进制编译正确，程序逻辑正确（verbose 日志显示完整的 DNS→TLS→HTTP 流程）

## 编译过程
1. `make -j1` → 编译 doh.o，链接生成 doh 二进制 ✅
2. 手动安装到 staging 目录（Makefile 无 install 目标）✅
3. Staging 验证: `doh -h` 输出正确 ✅
4. 本地安装: `doh -V` 输出 "doh version 0.1" ✅
5. ELF 验证: ELF64 arm64 PIE, 依赖 libcurl.so.4 + libc.so ✅

---

**编译开始**: 2026-06-24
**最终状态**: built

---

**编译结束**: 2026-06-24
**最终状态**: built
