# libshout 2.4.6 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-08-27
- 编译器: clang/clang++ (clang 15.0.4)
- 状态: published

## 编译步骤

1. **初始化编译环境**
   ```bash
   python3 $SKILL_ROOT/scripts/ohc-run.py init-build libshout 2.4.6 \
     --url=https://downloads.xiph.org/releases/libshout/libshout-2.4.6.tar.gz
   ```

2. **configure**（禁用 theora，未发布到制品仓）
   ```bash
   cd $BUILD_SRC_DIR
   # config.guess/sub 不识别 HarmonyOS（E007），用系统 automake 版本覆盖
   cp /storage/Users/currentUser/usr/local/share/automake-1.16/config.guess ./config.guess
   cp /storage/Users/currentUser/usr/local/share/automake-1.16/config.sub ./config.sub
   # configure 内 umask 077 在 HMDFS 上导致 config.status 无法创建临时文件（E011）
   sed -i 's/umask 077/umask 022/g' configure
   # PTHREAD_LIBS 置空导致 pthread_setcancelstate 链接缺失，显式传入 -lpthread
   PTHREAD_LIBS="-lpthread" ./configure --prefix=$DEFAULT_PREFIX --disable-theora
   ```

3. **make**
   ```bash
   make -j2
   make install DESTDIR=$TEST_PREFIX
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | 上游 config.guess 版本旧（2018-02-24）| 覆盖为系统 automake-1.16 的 config.guess/sub（含 OHOS 识别）|
| 2 | config.status 报 "can't create ./confN0NdWi/subs1.awk: Permission denied" | HMDFS umask 077 临时目录权限问题（E011）| sed 将 configure 中 `umask 077` 改为 `umask 022` |
| 3 | examples 链接报 `undefined reference to pthread_setcancelstate` | OHOS 未实现 pthread_setcancelstate（E051 类同：未实现 syscall），且 ACX_PTHREAD 误判"无 flags 可用"导致 PTHREAD_LIBS 为空 | (a) 显式 `PTHREAD_LIBS=-lpthread` 传入 configure；(b) 在 thread.c 中将 `#ifndef __ANDROID__` 守卫扩展为 `__OHOS__`，跳过未实现调用 |
| 4 | clang 报 `call to undeclared function free/malloc/snprintf` | 上游 src/icy.c、src/legacy.c 缺少 `<stdlib.h>`/`<stdio.h>`（NixOS 已知问题）| 补充 include（上游 commit 600fa10 / 8ab2de3）|

## 源码修改

| 文件 | 修改 |
|------|------|
| config.guess | 覆盖为系统 automake-1.16 版（含 OHOS 识别）|
| config.sub | 同上 |
| configure | `umask 077` → `umask 022`（E011 HMDFS 临时目录权限修复）|
| src/common/thread/thread.c | `#ifndef __ANDROID__` → `#if !defined(__ANDROID__) && !defined(__OHOS__)`（跳过未实现的 pthread_setcancelstate）|
| src/icy.c | 新增 `#include <stdlib.h>` `#include <stdio.h>`（上游 commit 8ab2de3）|
| src/legacy.c | 新增 `#include <stdlib.h>`（上游 commit 600fa10）|

## 依赖版本

- libogg 1.3.6 ✅
- libvorbis 1.3.7 ✅
- openssl 3.5.6.1 ✅（configure 时未通过 pkg-config 检测到，SSL 支持被禁用，不影响核心库功能）
- speex 1.2.1 ✅（探索阶段未通过 pkg-config 检测到，被禁用，不影响核心库功能）
- libtheora ❌ 未发布 → configure 时用 --disable-theora 禁用

## 验证结果

```
make 成功：libshout.a / libshout.so.3.2.0 / examples / tools 均链接通过
make install 成功：lib/libshout.{a,so,so.3,so.3.2.0}、include/shout/shout.h、lib/pkgconfig/shout.pc、bin/shout
readelf -d libshout.so.3.2.0: SONAME=libshout.so.3, NEEDED=[libvorbis.so, libogg.so, libc.so]
```

## 交付物

| 文件 | 说明 |
|------|------|
| lib/libshout.a | 静态库 |
| lib/libshout.so.3.2.0 | 动态库（SONAME=libshout.so.3）|
| include/shout/shout.h | 公共头文件 |
| lib/pkgconfig/shout.pc | pkg-config 描述 |
| bin/shout | 命令行工具（libshout 工具）|

## 注意事项

- libshout 可能为系统同名库（R26）：Conan 配方 generate() 需配置静态构建
  （`BUILD_SHARED_LIBS=OFF`），避免 .so 污染系统路径。但本库用 autotools，
  通过 `--disable-shared --enable-static` 实现静态化。
- 依赖 libogg/libvorbis 在制品仓以 conan 包提供，探索阶段 libshout 的
  configure fallback 检测（非 pkg-config）能找到系统已安装版本；正式 Conan
  构建时需通过 conanfile.py 的 requirements + toolchain 注入。
- speex/openssl 探索阶段未启用，正式 Conan 构建需确保依赖通过 conan
  toolchain 正确注入以启用对应特性。
---

**编译结束**: 2026-08-27 12:16
**最终状态**: published
