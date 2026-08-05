# zlib 1.3.2 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-08-03
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos)
- 目标平台: HarmonyOS PC (os=OHOS arch=armv8)
- 状态: built

## 编译步骤

`CONFIG_SHELL=<bash> CC=clang CFLAGS="-fPIC -O2" ./configure --static --prefix=/` → `make -j1` → `make check`（全部通过）

conan 配方中编译器从 `tools.build:compiler_executables` conf 获取（R33），`CONFIG_SHELL` 取环境变量（默认
`/data/service/hnp/bin/bash`），`--static -fPIC` + `make -j1`（R9）+ `make check` 内置于 build()。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 沙箱内 `https://www.zlib.net` 被代理 MITM 拦截（证书 hostname 不匹配，返回 0 字节） | 沙箱网络代理对 zlib.net 的 HTTPS 处理异常 | 改用 `http://www.zlib.net` 下载（sha256 与官方一致），conandata.yml 仍保留官方 https URL（CI 环境可用） |
| 2 | 非-PIC libz.a 链进共享库报 R_AARCH64 relocation | configure 默认不加 -fPIC | 沿用 1.3.1.1 既有经验：CFLAGS=-fPIC 编静态库（同 1.3.1.1 配方） |

## 源码修改

无补丁（源码为官方 zlib 1.3.2，仅构建旗标 CFLAGS=-fPIC）。

## 依赖版本

- 无 conan 依赖（zlib 零外部依赖）

## 验证结果

- `make check`（上游官方测试）：minigzip 往返、example、minigzip64 往返、example64 全部 OK（"zlib test OK" + "zlib 64-bit test OK"，exit 0）
- conan-verify G0-G4 + L2/L4/L5 全部 PASS
- 真机 conan create + test_package 通过（test_probe 输出 `zlib 1.3.2 ok`）
- libz.a 已确认 PIC：可直接 `clang -shared -fPIC` 链进 .so（无 TEXTREL，仅依赖 libc.so）

## 消费者（系统同名库，静态 + PIC）

下游把 zlib 静态链进共享库（cairo/libpng/qpdf 等）时须 require `zlib/1.3.2`（-fPIC 静态库，不污染系统
/lib/libz.so*），沿用 1.3.1.1 的适配结论。
---

**编译结束**: 2026-08-04 09:28
**最终状态**: built
