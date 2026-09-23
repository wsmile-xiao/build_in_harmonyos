# Conan Verify Report — pangomm 2.56.2

**Verdict**: PASS
**Reference**: `pangomm/2.56.2`（本地 conan cache rrev c8838ef27810721b65155a1d83c72b62，package b2989cda3f76bb65fb237c6cb47c656a8235e0dc，2026-09-14）
**Profile**: ohos-aarch64（ci/conan/profiles/ohos-aarch64）
**Date**: 2026-09-14

命令：
```
conan create archives/p/pangomm/2.56.2 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --build='pangomm/*'
```

结果：构建成功，全文 0 ERROR；test_package 原生 OHOS 实机运行 `all 4 checks passed`。

## G1: ✅ PASS（配方静态检查）

  ✅ name 声明（pangomm）/ version 声明（2.56.2）
  ✅ settings = "os", "arch", "compiler", "build_type"；options shared/fPIC 标准四件套
  ✅ export_sources() — export_conandata_patches(self)（无补丁时仍导出 conandata.yml）
  ✅ source() — get(self, **conan_data["sources"], strip_root=True)，sha256 与官方
    pangomm-2.56.2.sha256sum 实测一致（f1e984c8...f4c0e，784648 字节）
  ✅ build() — apply_conandata_patches(self) + Meson configure/build；
    无上游 meson 测试（三重证据见 test_package/MANIFEST.yml），build() 只做 configure+compile
  ✅ package() — Meson install + COPYING 入 licenses + OHOS .so 重签
    （.codesign 段实测存在，E135）
  ✅ package_info() — includedirs（include / include/pangomm-2.48 /
    lib/pangomm-2.48/include）+ libs ["pangomm-2.48"] + pkg_config_name pangomm-2.48，
    与上游安装布局（meson 实测安装结构）一致
  ✅ requirements() 声明真实依赖：glibmm/2.68.2、cairomm/1.18.0、pango/1.56.4、
    fontconfig/2.18.1.1（override）——无宿主机头文件/库依赖；
    间接链（libsigc/3.0.6、cairo/1.18.4、glib/2.84.0.1、harfbuzz、freetype、
    fribidi、libthai、pixman 等）全部由上游配方传递声明
  ✅ conandata.yml 完整（sources.url + sha256 本地实算，patches: [] 无补丁）
  ✅ test_package/ 存在（R28），MANIFEST.yml 存在（L0e）
  ✅ 平台条件保护：.so 重签在 `if self.settings.os != "OHOS": return` 分支内，
    Linux 语义不受影响；.pc 注入属 Conan 生成器能力缺口（PkgConfigDeps 不感知
    pango 多 .pc 组件），中性逻辑不针对特定平台

## G2: ✅ PASS（.pc 依赖链可解析，非"顶层包看起来存在"）

meson configure 实测输出（conan create 日志）：
```
Run-time dependency pangocairo found: YES 1.56.4
Dependency glibmm-2.68 for host machine found: YES 2.68.2 (cached)
Dependency cairomm-1.16 for host machine found: YES 1.18.0 (cached)
Library glibmm_generate_extra_defs-2.68 found: YES
```
- pangocairo >= 1.56.0 由转发型 pangocairo.pc（Requires: pango, Version 1.56.4 取自
  pango.pc 实测值）满足，Requires 链解析到 pango/1.56.4 包；
- gmmprocdir 变量注入 glibmm-2.68.pc（上游 meson.build 需要该 pc 变量）；
- glibmm_generate_extra_defs-2.68 经 glibmm libdir 的 -L 注入（sharedlinkflags/
  exelinkflags conf）定位成功，generate_extra_defs 工具编译链接通过（[1/31]→[15/31]）。

## G3: ✅ PASS（运行时验证）

- test_probe 在原生 OHOS 上经 CONFIG_SHELL bash + 显式 LD_LIBRARY_PATH 运行成功；
- 4/4 断言 PASS（FontDescription 值对象 / SCALE 常量 / AttrList 默认构造为空
  `!get_iter().next()` / 版本宏），4 项均为真实可失败断言（评审意见 #2 已修复）；
- .so 包内产物 libpangomm-2.48.so[.1|.1.0.30] 带 .codesign 段（llvm-readelf 实测），
  可被动态加载器执行。

## 与 2.50.1 配方的行为差异

无。requirements、.pc 注入、签名逻辑全部沿用 2.50.1 实证机制；差异仅版本号、
pangocairo 下限（1.49.4→1.56.0，pango/1.56.4 满足）与注释/文档同步。
