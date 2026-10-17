# zh-autoconvert 0.3.16 适配笔记

## 编译环境
- 构建系统: makefile（上游工程名 libhz，纯 Makefile）
- 编译日期: 2026-09-24
- 编译器: clang-15（OHOS aarch64，tools.build:compiler_executables 注入）
- 状态: published

## 编译步骤
1. `conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing`
2. 配方 `build()` 在 `hzconvert/` 目录执行上游 Makefile：
   `make CC='clang -I../include' CFLAGS='-O2 -Wall -g -fsigned-char' AR=llvm-ar RANLIB=llvm-ranlib`
3. `package()` 复制 `include/*.h` 与 `libhz.a`（静态库落在源码树 `source_folder/lib/`，非 build 目录）；
   shared 构建时复制 `libhz.so.0.0` 并实体化 SONAME/linker-name 副本（HMDFS 拒绝软链）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Makefile 链接 `-ldl` 且硬编码 `gcc`/`ar` | OHOS 无 gcc、无 libdl | 补丁 0001 改 `$(CC)`/`$(AR)`/`$(RANLIB)`，删除 `-ldl` |
| 2 | `ln -s` 建软链报 Permission denied | HMDFS 拒绝在 lib/ 下创建软链 | 删除 Makefile 软链步骤，`package()` 用 `shutil.copy2` 实体化 SONAME 副本 |
| 3 | test_package 执行报 `cannot execute binary file` (126) | test() 用 `/data/service/hnp/bin/bash` 显式解释器包装 ELF，OHOS 下该方式失败 | test() 直接执行二进制路径（`self.run(binpath, env="conanrun")`），内核可直接 exec |
| 4 | aarch64 `char` 默认无符号 | 上游按 x86 有符号 char 编写 | CFLAGS 加 `-fsigned-char` 防御（表查找已用 `(unsigned char)` 转换，本包不受影响） |

## 源码修改
- `patches/0001-use-conan-compiler-and-ar.patch`：Makefile 改用 conan 注入的 CC/AR/RANLIB，删除 `-ldl` 与两条 `ln -s`。

## 依赖版本
- 无第三方依赖（leaf 包，仅 libc/libc++）。

## 验证结果
```bash
$ conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
...
======== Testing the package: Executing test ========
RUN: ./test_hz
OK: GB<->Big5 round-trip verified for U+4E2D ('中')
```
- 构建 + 打包通过（libhz.a + hz.h/zhstatis.h 进入缓存）
- test_package CMakeDeps/CMakeToolchain 解析通过
- test 执行通过：GB2312 '中'(D6 D0) → Big5 (A4 A4) → 回环 D6 D0 精确一致

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | 配方（makefile 构建、静态/动态库打包、OHOS 签名 no-op 于静态构建） |
| conandata.yml | 源码 + 补丁声明 |
| manifest.yaml | 元数据（build_system=makefile 等） |
| patches/0001-*.patch | Makefile 可移植性补丁 |
| test_package/ | GB↔Big5 往返 C 测试 |

## 注意事项
- 默认静态构建（`shared=False`），`_sign_binaries()` 为 no-op；shared 构建时会对 `.so` 做 OHOS codesign（带 `env -u LD_LIBRARY_PATH` 规避签名工具被 SDK libc++ 带偏）。
- 本地 W3 的 junk_check 在 full 模式下会命中仓库内其他包（cloog/kics）遗留的 `.build-closed`/`.staging-verified` 标记而报错；提交本包后 JC 以 incremental 模式仅扫描本包 diff，不受影响。
