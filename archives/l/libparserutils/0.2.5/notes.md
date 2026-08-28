# libparserutils 0.2.5 适配笔记

## 编译环境
- 构建系统: makefile（NetSurf NSSHARED → standalone Makefile 替换）
- 编译日期: 2026-08-26
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos, OHOS SDK 26.0.0.18)
- 状态: built（conan-verify G1-G4 全过，尚未走 finish/submit 发布）

## 编译步骤

1. `source .build-context-libparserutils-0.2.5 && cd $BUILD_SRC_DIR`
2. 替换顶层 Makefile 为 standalone Makefile（原 Makefile include
   `$(NSSHARED)/makefiles/Makefile.tools`，本平台无 netsurf-buildsystem）
3. `make -j2` 生成 `libparserutils.a` + `libparserutils.pc`
   （`src/charset/aliases.inc` 由 `perl build/make-aliases.pl` 自动生成）
4. `make install PREFIX=$DEFAULT_PREFIX DESTDIR=$TEST_PREFIX` 验证安装
5. `make test` 编译并驱动上游全部 test/*.c（34/34 PASS）
6. `conan-init libparserutils 0.2.5` 生成配方并手工修正
7. `conan-verify libparserutils 0.2.5` — G1/G2/G3/G4 全部 PASS

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 原始 Makefile `include $(NSSHARED)/makefiles/Makefile.tools` 找不到 | NetSurf 组件库使用自有 NSSHARED 构建系统，本平台无 netsurf-buildsystem | 替换为 standalone Makefile（libwapcaplet 0.4.3 同款方案），保留原编译标志，去除 -Werror 兼容 clang 15 |
| 2 | GNU ld(bfd) 链接的测试二进制执行 `Permission denied` (exit 126) | OHOS 沙箱拒绝未签名的 GNU ld 产物；lld 产物可执行（abuild 3.17.0.1 同款记录） | 测试链接不指定 -fuse-ld（默认 lld），链接时置 `LD_LIBRARY_PATH` 指向 SDK llvm/lib 供 lld 加载 libxml2.so.16 |
| 3 | conan build() 读 `tools.build:compiler_executables:c` 报 conf 不存在 | conan 2.29.1 对带子键的 dict conf 需整取再索引（bzip2 同款写法） | `self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)` 再 `.get("c", ...)` |
| 4 | make -j2 jobserver mkfifo `Operation not permitted` | HMDFS 禁 FIFO（E074） | make 自动退化为串行，构建仍成功；conanfile 固定 `-j1`（R9） |
| 5 | 上游 `make test` 依赖 testrunner.pl（NSTESTTOOLS） | 属于 netsurf-buildsystem | standalone Makefile 直接编译上游 test/*.c 测试程序并逐项驱动，34 项全过 |

## 源码修改

| 文件 | 原因 | 方式 | 补丁状态 |
|------|------|------|----------|
| Makefile | NetSurf 构建系统不可用 | 完全替换为独立 Makefile | patches/0001-Makefile.patch |

## 依赖版本

- 无运行时依赖（iconv 可选，未启用）
- 编译工具: clang 15.0.4, llvm-ar, llvm-ranlib, GNU make, perl 5.42.2, GNU sed
- 测试链接: lld（SDK 自带），GNU ld 产物在 OHOS 沙箱不可执行

## 验证结果

### 上游测试（make test，34/34 全过）

```bash
=== Running upstream libparserutils testcases ===
--- aliases ---                       PASS
--- filter ---                        PASS
--- inputstream ---                   PASS
--- cscodec-utf8 (2 数据文件) ---     PASS
--- cscodec-utf16 (1) ---             PASS
--- cscodec-ext8 (9) ---              PASS
--- cscodec-8859 (15) ---             PASS
--- regression: filter-segv / stream-nomem / filter-badenc-segv / buffer-discard ---  PASS
=== All upstream testcases PASSED ===
```

### conan create + test_package

```bash
$ ohc-run.py conan-verify libparserutils 0.2.5
G1: PASS  G2: PASS (conan create)  G3: PASS  G4: PASS
1/1 Test #1: test_libparserutils ..... Passed  0.03 sec
（test.c 调用 buffer/stack/vector/mibenum/utf8/inputstream API，17 断言）
```

## 交付物

| 文件 | 说明 |
|------|------|
| libparserutils.a | 静态库 (ELF64 aarch64) |
| libparserutils.pc | pkg-config 文件 (version 0.2.5) |
| include/parserutils/** | 12 个头文件 |

## 注意事项

- NetSurf 组件库（libparserutils/libwapcaplet/libcss 等）均需替换为 standalone Makefile
- 静态库无需 ELF 签名与 RPATH 处理（E018）
- 测试二进制必须用 lld 链接；GNU ld(bfd) 产物在 OHOS 沙箱 Permission denied
- 本包无下游依赖，conandata.yml URL 为官方源，sha256 与 tarball 一致（R39）
---

**编译结束**: 2026-08-26 23:48
**最终状态**: built
