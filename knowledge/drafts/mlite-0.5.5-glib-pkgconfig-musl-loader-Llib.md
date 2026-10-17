# glib 的 pkg-config 元数据含 “-L/lib -l:ld-musl-aarch64.so.1”，而 pkg-config 默认过滤系统路径 -L/lib，链接期直接失败

> Draft: `DRAFT-MLITE-055-GLIB-PKGCONFIG-MUSL-LOADER-NEEDS-L-LIB`
> Stem: `mlite-0.5.5-glib-pkgconfig-musl-loader-Llib` — pairs with the same-stem `.kv`

## 基本信息

- **ID**: DRAFT-MLITE-055-GLIB-PKGCONFIG-MUSL-LOADER-NEEDS-L-LIB
- **严重度**: 2（3=🔴blocking / 2=🟡medium / 1=🟢minor）
- **类别**: linking|pkg-config|ohos-platform
- **触发工具**: ld
- **阶段**: linking

## 错误特征

```
unable to find library -l:ld-musl-aarch64\.so\.1|-l:ld-musl-aarch64\.so\.1
```

匹配关键词：`ld.lld, unable to find library, -l:ld-musl-aarch64.so.1, ld-musl, pkg-config, glib, link_pkgconfig, qmake`

## 根因

glib 包的 cpp_info.system_libs 把 musl 动态加载器写成 “-l:ld-musl-aarch64.so.1”（配合 -L/lib）；pkg-config/pkgconf 在输出 --libs 时会剔除系统库目录（-L/lib、-L/usr/lib），于是只剩找不到搜索路径的 “-l:ld-musl-aarch64.so.1”，ld.lld 报错。qmake 的 CONFIG += link_pkgconfig 会把 pkg-config 的 flags 原样放进链接行，因此任何 link_pkgconfig + glib-2.0 的项目都会撞上。

## 影响范围

以 pkg-config 取 glib-2.0（或任何把 musl 加载器写进 Libs 的包）作为链接输入的构建；OHOS/musl 平台。

## 验证命令

```bash
pkg-config --libs glib-2.0 | tr ' ' '\n' | grep -c '^-L/lib$'   # 期望 0（被过滤）；对照 glib.pc Libs 原文含 -L/lib
```

## 处置建议

- **优先级**: 2
- **方案**: `add-L-lib-back-via-mkspec-or-extra-libs`
- **说明**: (1) 在自定义 mkspec（或链接参数）里显式补回 QMAKE_LFLAGS += -L/lib，使 -l:ld-musl-aarch64.so.1 可解析；(2) 不要把该路径写进 conandata/patch；它是构建参数，不是源码改动；(3) 同一 mkspec 机制可复用为其他 Qt5 项目的 OHOS 适配入口（制品仓无 ohos mkspec，统一用 linux-clang + 覆盖）。
- **参考命令**: `echo 'include(<qtbase>/mkspecs/linux-clang/qmake.conf)' > qmake.conf && echo 'QMAKE_LFLAGS += -L/lib' >> qmake.conf && qmake -spec <dir>`
- **可自动修复**: false

## 可复用知识总结（同类问题通用）

- **问题类**：pkg-config 元数据里把 **musl 动态加载器**当普通库声明（`-l:ld-musl-aarch64.so.1`），而配套的 `-L/lib` 被 pkg-config 当系统路径过滤 → 链接期解析失败。
- **识别信号**：`ld.lld: error: unable to find library -l:ld-musl-aarch64.so.1`；`pkg-config --libs glib-2.0 | grep -c '^-L/lib$'` 为 0（但 `.pc` 原文含 `-L/lib`）。
- **通用处置**：在构建参数层补回系统库搜索路径（如自定义 mkspec `QMAKE_LFLAGS += -L/lib`，或 `LIBS+=`/`LDFLAGS`），**不要**改依赖包或打源码补丁。
- **适用范围**：OHOS/musl 平台上任何用 `pkg-config`（qmake `link_pkgconfig`、autotools `PKG_CHECK_MODULES` 等）取 glib 系库的构建。
- **关联**：本仓 OHOS 无 ohos mkspec → 统一以 `linux-clang` 继承 + 覆盖的方式落适配参数。
