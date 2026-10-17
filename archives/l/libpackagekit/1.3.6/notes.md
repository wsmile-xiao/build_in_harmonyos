# libpackagekit 1.3.6 — HarmonyOS PC (aarch64/OHOS) 适配笔记

## 概述

- 软件：PackageKit 的库组件 libpackagekit（libpackagekit-glib2）
- 版本：1.3.6（上游 PackageKit monorepo，库组件位于 lib/packagekit-glib2）
- 构建系统：Meson（`project('PackageKit', 'c', version: '1.3.6')`）
- 产物：`libpackagekit-glib2.so.18.1.3`（共享库）+ 37 个头文件 + `packagekit-glib2.pc`
- 状态：published（conan-verify 8 道门禁通过；W3 本地 conan create 真实执行成功）

## 依赖（W0 预检全部已发布）

| 依赖 | 版本 | 用途 | 制品仓 |
|------|------|------|--------|
| glib | 2.84.0 | glib/gobject/gio/gio-unix/gmodule | ✅ 已发布 |
| sqlite3 | 3.53.4 | daemon（构建期，库不链接） | ✅ 已发布 |
| polkit | 127 | daemon 授权（构建期） | ✅ 已发布 |
| jansson | 2.15.1.1 | pkgcli（构建期） | ✅ 已发布 |

> 版本选择说明：polkit/127 依赖 glib/2.84.0，且满足 PackageKit 的 glib>=2.76 要求，
> 故采用 glib/2.84.0（避免版本冲突）。
> sqlite3/polkit/jansson 以 `visible=False` 声明——仅供构建 daemon/CLI 目标使用，
> 最终库包只链接 glib，不向下游泄漏（避免 conan package_info 报未使用依赖）。

## 关键适配点（OHOS）

### 1. meson 选项裁剪
只构建库组件语义，关闭非必要目标：
`-Dsystemd=false -Dgobject_introspection=false -Dman_pages=false -Dgtk_doc=false
 -Dlegacy_tools=false -Dpackaging_backend=dummy -Ddaemon_tests=false -Dcron=false
 -Dpython_backend=false -Dgtk_module=false -Dgstreamer_plugin=false
 -Dbash_completion=false -Dbash_command_not_found=false -Doffline_update=false
 --wrap-mode=nodownload`

### 2. gettext 宏（musl libintl stub）
OHOS musl 的 libintl.h 是空 stub，`gettext()`/`dgettext()`/`bindtextdomain()`/
`bind_textdomain_codeset()`/`textdomain()` 均未声明（编译器报 implicit function
declaration / int 到指针转换错误）。方案（polkit 已验证同款）：
```
-Dgettext(x)=(x) -Ddgettext(d,x)=(x) -Dbindtextdomain(d,l)=(d)
-Dbind_textdomain_codeset(d,c)=(d) -Dtextdomain(d)=(d)
```
注意：必须逐条作为独立 c_args 传入（MesonToolchain），不能合并为一个带空格的
字符串参数（否则 clang 把整串当宏名，报 `Ddgettext` 之类畸形符号）。

### 3. policy XML 翻译跳过（补丁 0001）
`policy/org.freedesktop.packagekit.policy` 的 i18n.merge_file 依赖 msgfmt 的
ITS 规则（`cannot locate ITS rules`），OHOS msgfmt 不支持。改用 install_data
直接安装未翻译的 .policy.in 原文件（功能等价），记录于 patches/0001-policy-meson.build.patch。

### 4. glib 子 .pc 补齐（PkgConfigDeps 不生成）
meson 编译需要 gio-2.0.pc/gio-unix-2.0.pc/gobject-2.0.pc/gmodule-2.0.pc 等，
且 gnome.mkenums 需要从 glib-2.0.pc 读 `glib_mkenums` 工具变量。Conan
PkgConfigDeps 只生成 glib-2.0.pc。方案（polkit 同款）：
- 从 glib 包 `lib/pkgconfig/` 复制全部子 .pc 到 generators_folder
- 修正 prefix 指向 glib 包实际路径
- 合并 glib 原始 .pc 的 mkenums 工具变量行进 Conan 生成的 glib-2.0.pc 等

### 5. OHOS ELF 签名（关键！）
**症状**：conan create 成功、test 二进制也链接成功，但运行报：
```
Error loading shared library libpackagekit-glib2.so.18
Error relocating ...: pk_control_new: symbol not found  (g_assertion_* 等也报)
```
**根因**：OHOS 加载器要求 ELF 带 codesign 签名，未签名的 .so 拒绝加载。
**解决**（jansson 已验证同款）：package() 中对真实 .so 执行
`llvm-objcopy --remove-section .codesign` + `binary-sign-tool sign -selfSign 1`。

### 6. HMDFS 符号链接（E050）
musl loader 在 HMDFS 上无法追踪符号链接，.so 的版本化软链接
（libpackagekit-glib2.so.18 → .so.18.1.3）在 dlopen 时失效。package() 中把
符号链接替换为真实文件副本（先签名再复制，保持签名一致）。
注意：HMDFS 上 `os.path.islink()` 不可靠，需用 `os.path.lexists()` + 无条件
remove 后 copy。

### 7. LD_LIBRARY_PATH 与 -L/lib
- test_package 链接时 pkg-config 过滤掉了 `-L/lib`（系统目录），而 glib 需要
  musl loader（`-l:ld-musl-aarch64.so.1`，位于 /lib），需显式补 `-L/lib`。
- test() 运行时需 VirtualRunEnv 并确保被测包 lib 目录在 LD_LIBRARY_PATH。

## 上游测试（R51 三步法实测）

tests/meson.build 注册 3 项测试：
1. `pk-test-library`（库单元测试，10 个子用例）— **实测运行**
   - **7/10 通过**：common / enum / bitfield / package-id / package-ids / results / package
   - **offline 失败**：`g_mkdir_with_parents("/tmp/PackageKit-self-test")`，
     OHOS /tmp 只读（E002 平台限制，非代码缺陷）
   - 剩余 test 因 bail out 未执行
2. `pk-test-daemon-internal`（daemon 内部）— 未运行（daemon_tests=false，库组件不构建）
3. `pk-test-e2e`（端到端，需运行 daemon+DBus）— 未运行（api 环境不满足，如实声明）

conanfile.py build() 已集成 `meson test --print-errorlogs`（ignore_errors=True，
平台限制不阻塞发布）。

## 产物

```
include/PackageKit/packagekit-glib2/*.h   (37 个头文件)
lib/libpackagekit-glib2.so.18.1.3         (已签名)
lib/libpackagekit-glib2.so.18 → 副本       (HMDFS 兼容)
lib/libpackagekit-glib2.so   → 副本
lib/pkgconfig/packagekit-glib2.pc
licenses/COPYING
```

## 踩坑清单（供后续包参考）

1. MesonToolchain c_args 多宏必须分条 append，不能合并字符串
2. OHOS .so 必须 codesign，否则 dlopen 报 symbol not found（欺骗性症状）
3. HMDFS islink 检测不可靠，符号链接处理用 lexists + remove + copy
4. PkgConfigDeps 不生成 glib 子 .pc，需从包复制 + 合并工具变量
5. musl gettext stub 需 -D 宏规格化（gettext/dgettext/bindtextdomain 全套）
6. pkg-config 过滤 -L/lib，交叉链接 musl loader 需显式补
---

**编译结束**: 2026-09-20 23:23
**最终状态**: published
