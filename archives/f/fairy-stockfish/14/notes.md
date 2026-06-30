# fairy-stockfish v14 编译笔记

## 源码
- 来源: https://github.com/fairy-stockfish/Fairy-Stockfish/archive/refs/tags/fairy_sf_14.tar.gz
- 下载镜像: ghfast.top (GitHub 直连超时, E017)
- 源码SHA256: db5e96cf47faf4bfd4a500f58ae86e46fee92c2f5544e78750fc01ad098cbad2
- 源码结构: GitHub 归档为 Fairy-Stockfish-fairy_sf_14/src/，源码在 src/ 子目录

## 构建系统
- 自定义 Makefile（非 autotools/cmake）
- 构建目标: `make build ARCH=armv8 COMP=clang`
- 无 configure 步骤，直接 make
- 安装: `make install PREFIX=<dir>` (不支持 DESTDIR)

## 编译参数
```
make -j2 build ARCH=armv8 COMP=clang
```
- ARCH=armv8: ARMv8 64-bit with popcnt and neon
- COMP=clang: 使用 clang++ 编译器（系统无 g++）

## 修改记录

### 1. 移除 -latomic (patches/0001-Makefile.patch)
- 问题: `ld.lld: error: unable to find library -latomic`
- 原因: HarmonyOS/musl/aarch64 系统没有 libatomic 库
- 修复: 在 Makefile clang 配置部分注释掉 `LDFLAGS += -latomic`
- 理由: ARMv8 的原子操作是内建的，不需要 libatomic

### 2. 添加 -static-libstdc++ (patches/0001-Makefile.patch)
- 问题: 默认链接动态 C++ 运行时，违反 R26 静态链接铁律
- 修复: 在 Makefile clang 配置部分添加 `LDFLAGS += -static-libstdc++`
- 结果: 二进制仅依赖 libc.so (系统库)，C++ 运行时静态链接

## Conan 配方适配
- conan-init 生成的模板基于 Autotools，手动重写为 Makefile 构建
- build() 中使用 self.source_folder + "src/" 定位源码
- apply_conandata_patches + sed fallback 确保补丁应用
- test_package 简化为文件存在性检查（鸿蒙 SELinux 限制无法执行二进制）

## 测试
- make check: 无此目标（fairy-stockfish Makefile 不提供）
- ./stockfish bench: 无法执行（鸿蒙 SELinux 限制 E046, exit 126）
- conan-verify L2 smoke test: 通过（conan 环境下可执行）

## 产物
- bin/stockfish (ELF 64-bit AArch64, 静态链接C++运行时)
- 无 lib/ 和 include/ 产物（纯可执行程序）
- 动态依赖: 仅 libc.so (系统库)

---

**编译日期**: 2026-06-29
**最终状态**: published
**conan-verify**: 8道门禁全部通过
