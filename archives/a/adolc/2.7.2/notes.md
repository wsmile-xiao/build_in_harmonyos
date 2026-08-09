# adolc 2.7.2 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-08-05
- 编译器: /data/service/hnp/bin/clang, clang++ (aarch64-unknown-linux-ohos)
- 状态: built（本地验证通过，未 upload/PR）

## 编译步骤

```bash
cd $BUILD_SRC_DIR  # /storage/Users/currentUser/builds/adolc-2.7.2.work

# 1. config.guess/config.sub 补 HarmonyOS 三元组（patch-autotools-ohos.pl + 手工修）
#    config.guess: 加 *:HarmonyOS:*:*) 分支（直接 echo aarch64-unknown-linux-ohos; exit）
#    config.sub:   maybe_os 加 linux-ohos*/ohos*，新增 ohos-linux case，OS 白名单加 -linux-ohos*/-ohos*

# 2. configure 前修 umask（E129，HMDFS 临时目录权限）
perl -pi -e 's/umask 077/umask 022/g' configure config.status

# 3. configure（LDFLAGS 追加 compiler-rt builtins，让 .so 自包含 quad-float 符号）
export TMPDIR=/storage/Users/currentUser CONFIG_SHELL=/data/service/hnp/bin/bash
export CC=/data/service/hnp/bin/clang CXX=/data/service/hnp/bin/clang++
./configure --prefix=/storage/Users/currentUser/usr/local --enable-sparse=no --without-boost \
  LDFLAGS="/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/clang/15.0.4/lib/aarch64-linux-ohos/libclang_rt.builtins.a"

# 4. 编译 + 安装（staging 隔离）
make -j1 && make install DESTDIR=/storage/Users/currentUser/test-install-adolc-2.7.2

# 5. 上游测试（run_tests 无 shebang，用 bash 执行）
cd ADOL-C/test && LD_LIBRARY_PATH=$PWD/../.libs /data/service/hnp/bin/bash run_tests
# powexam: Test passed! / speelpenning: Test passed!
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 不识别 HarmonyOS 平台 | config.guess/config.sub 无 ohos 三元组 | patch-autotools-ohos.pl + 手工修（config.guess 2016 版无 GUESS 回显，改直接 echo+exit） |
| 2 | config.status: subs1.awk Permission denied | HMDFS umask 077 建 700 临时目录 (E129) | configure/config.status 中 umask 077 → 022 |
| 3 | 测试运行报 `Error relocating libadolc.so.2: __addtf3 symbol not found` | taylor.o (Taylor ODE 驱动) 用 long double；libtool 以 clang++ -nostdlib 链接 .so 不带 compiler-rt builtins | LDFLAGS 追加 libclang_rt.builtins.a（同 graphviz E098 模式） |
| 4 | 手动构建安装目录为 lib64 非 lib；conan 构建为 lib | ADOL-C 64 位默认 lib64；conan AutotoolsToolchain 强制 --libdir=${prefix}/lib | 手动构建记录即可；conan 包内用默认 libdirs=lib |
| 5 | CI #13458 source() FileNotFoundError | `releases/download/.../ADOL-C-2.7.2.tar.gz` 404 后回落到本机 `file://.../.tmp-adolc/...`（Worker 无此文件） | 改为官方 tag archive 单值 URL（R39；CI 自动加镜像）；删 file://；软件级 manifest `source_url` 同步 |

## 源码修改

无补丁文件（探索阶段直接改源，R1）。构建时由 conanfile.py 注入：
1. config.guess/config.sub 平台补丁（已手工应用到 autoconf/ 下的副本）
2. configure/config.status umask 077→022
3. LDFLAGS 追加 builtins.a

## 依赖版本

- 无编译必需依赖（colpack/boost/OpenMP 全部保持禁用，ohpcd 未发布 colpack）
- 运行时自包含：libclang_rt.builtins.a（clang 15.0.4 / ohos-sdk 26.0.0.18）

## 验证结果

```bash
# configure 识别平台
checking build system type... aarch64-unknown-linux-ohos
checking host system type... aarch64-unknown-linux-ohos

# 上游测试
./run_tests -> powexam: Test passed! / speelpenning: Test passed! (exit 0)

# 自包含验证
llvm-nm -D ADOL-C/.libs/libadolc.so.2 | grep __addtf3  # 无 undefined（已内链 builtins）
```

## 交付物

| 文件 | 说明 |
|------|------|
| archives/a/adolc/2.7.2/conanfile.py | Conan 配方（autotools） |
| archives/a/adolc/2.7.2/conandata.yml | 源码声明 + sha256 |
| archives/a/adolc/2.7.2/test_package/ | test.cpp（真实 ADOL-C API 测试）+ CMake + MANIFEST |
| libadolc.so.2.2.0 | 共享库（含 include/adolc 头 + lib64/pkgconfig/adolc.pc） |

## 注意事项

- 源码 URL 使用官方 GitHub tag archive 单值地址（`archive/refs/tags/releases/2.7.2.tar.gz`），
  由 CI 自动加 GitHub 镜像 fallback。勿用 `releases/download/.../ADOL-C-2.7.2.tar.gz`（404，无该 asset），
  亦勿写 file:// 本地路径（CI Worker 上不存在）。
- 禁止启用 --enable-sparse（colpack 未发布到 ohpcd）；OpenMP 未发布，保持默认关闭。
- config.guess/config.sub / umask / adolc_settings 已固化为 patches/0001-0004，由 apply_conandata_patches 应用。
- `_builtins_path()` 仅在 builtins.a 真实存在时追加 LDFLAGS；找不到则 warning 并跳过（避免硬编码幽灵路径）。
---

**编译结束**: 2026-08-05 16:44
**最终状态**: built
