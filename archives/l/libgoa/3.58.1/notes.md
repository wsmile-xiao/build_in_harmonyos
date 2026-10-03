# libgoa 3.58.1 — 适配笔记

## 编译环境
- 构建系统: meson（上游顶层 meson.build）
- 编译日期: 2026-09-27
- 编译器: clang / clang++ 15.0.4（OHOS 工具链）
- 目标平台: aarch64-linux-ohos（OHOS 6.0 / armv8）
- 构建方式: **原生构建**（build == host == OHOS/aarch64，非交叉编译）

## 依赖与工具链

| 角色 | 包 | 说明 |
|---|---|---|
| 运行依赖 | glib/2.88.3 | goa-1.0.pc 的 `Requires: gio-2.0, glib-2.0`；公开头文件包含 `gio/gio.h`，故 `transitive_headers=True, transitive_libs=True` |
| 构建依赖 | meson/1.11.0 | worker 未预装 meson，用制品仓已发布的 1.11.0（1.11.0.1 只在索引可见，下载报 `system acceleration policy not enabled`，按未发布处理） |

`generate()` 里 `PkgConfigDeps` + `MesonToolchain` 之后，额外向
`conan_meson_native.ini` 的 `[binaries]` 注入绝对路径：

- `ar` / `ranlib`：MesonToolchain 不写这两项，真机 hnp 工具链下 meson 报
  `Unable to detect linker`；
- `gdbus-codegen` / `glib-mkenums`：`gnome.gdbus_codegen` / `gnome.mkenums_simple`
  先查 pkg-config 变量，conan 生成的 `.pc` 没有这两个变量，meson 直接抛
  `Could not get pkg-config variable`；且 worker 自带
  `/data/service/hnp/bin/gdbus-codegen` 是指向 glib 2.38 的软链、shebang 指向
  不存在的 `/usr/bin/python3`，不可执行。故优先取本包 glib 制品自带 `bin/`。

## 上游范围裁剪

上游 3.58.1 的完整构建需要 json-glib / libsecret / libsoup-3.0 / libxml2 /
rest-1.0 / gtk4 / libadwaita-1 等（均未发布到 ohpcd），因此本配方只构建**客户端
库与数据文件**，把这些选项全部关闭：

```
-Ddefault_library=shared -Dgoabackend=false
-Dexchange=false -Dfedora=false -Dgoogle=false -Dimap_smtp=false
-Dkerberos=false -Downcloud=false -Dwebdav=false -Dms_graph=false
-Ddocumentation=false -Dintrospection=false -Dvapi=false -Dman=false
```

关闭后 libgoa-1.0 只链接 gio / gobject / glib。`dbus-1` 只服务于 goa-daemon 的
D-Bus service 安装路径（`data/meson.build` 的 goabackend 分支），补丁 0001 之后
不再进入构建图，因此 `requires` 里**不声明 dbus**：conan 2.29 会拒绝「声明了却
未出现在 cpp_info.requires 的直接依赖」。开启后端时需一并加回
dbus / json-glib / libsecret / libsoup-3.0 / libxml2 / rest-1.0。

## 补丁

**patches/0001-meson.build.patch**（由 `scripts/ohc-run.py refresh-patch --auto libgoa 3.58.1` 生成，per-file-difflib，仅命中 `meson.build` 一个文件；对 pristine 源码应用后 `meson.build` sha256 = `2f7824bbe157f043fe2e7be2b9a58877e5d4ba670f002299af10457777a0dd2f`）
- `dependency('../gio-unix-2.0')` → `required: false` + 缺失时回退 `gio_dep`：
  conan 的 glib 包不带可用的 `gio-unix-2.0.pc`（包内 `.pc` 以 `prefix=/` 安装，
  路径不可用），而 `src/goa/` 下没有任何 gio-unix 符号引用，回退不改变导出 ABI。
- `dependency('dbus-1')` 的求值挪到 `goabackend` 打开时才执行，关闭后端时该依赖
  不进入构建图。

## OHOS 适配要点：安装后必须重新签名 ELF（E077）

这是本包唯一的“平台陷阱”，也是 test_package 一度失败的原因：

1. **症状**：`conan create` 到 `Testing the package: Executing test` 阶段，
   消费者二进制运行时报

   ```
   Error loading shared library libgoa-1.0.so.0: (needed by ./test_goa_consumer)
   ```

   而同一份源码在构建目录里（`b/build-release/src/goa/libgoa-1.0.so.0.0.0`）
   用 `dlopen` 加载**完全正常**。

2. **根因**：鸿蒙加载器只加载 `.codesign` 段有效的 ELF（E077）。链接期由工具链
   写入的签名覆盖文件内容；而 `meson install` 会在安装期调用
   `mesonbuild/scripts/depfixer.py` 就地改写 `.dynstr`（把 build rpath 字符串清成
   `X` 并摘掉 `DT_RUNPATH`），**改写让链接期签名失效**，此后任何 `dlopen` 都返回
   `Permission denied`。签名与文件内容绑定，因此连打包产物的字节级副本也无法加载。

3. **修复**：`package()` 里 `meson.install()` 之后遍历包目录，对所有常规 ELF
   执行四步（顺序不可变，E077）：

   ```
   llvm-objcopy --remove-section .codesign <file>      # 移除旧签名
   binary-sign-tool sign -inFile <file> -outFile <out> -selfSign 1   # 重新签名
   chmod <原权限>|0755 <out>                            # 签名后权限归零，要恢复
   ```

   配方里的 `_sign_ohos_package()` 与制品仓 **glib/2.88.3** 的
   `_sign_final_ohos_package()` 同法：先 `llvm-readelf -S` 判定是否已有
   `.codesign`，签名后校验 `.codesign` 恰好一个、且签名结果与输入不同，最后
   `os.replace` 回原路径并恢复权限，并输出 `PACKAGE_CODESIGN=PASS signed_elfs=N`。
   交叉构建或缺少签名工具时输出 `PACKAGE_CODESIGN=NOT_RUN`。

## 产物与包身份面

```
include/goa-1.0/goa/                     # 公开头（goa.h / goaclient.h / ...）
lib/goa-1.0/include/goaconfig.h         # 配置期生成（Cflags 含 -I${libdir}/goa-1.0/include）
lib/libgoa-1.0.so -> .so.0 -> .so.0.0.0  # SONAME=libgoa-1.0.so.0
lib/pkgconfig/goa-1.0.pc                 # Name: Goa / Version: 3.58.1
share/applications/org.gnome.goa-daemon.desktop
share/icons/hicolor/symbolic/apps/org.gnome.goa-daemon-symbolic.svg
share/locale/*/LC_MESSAGES/gnome-online-accounts.mo   # 80 个语言
```

- `NEEDED`: `libgio-2.0.so.0`, `libgobject-2.0.so.0`, `libglib-2.0.so.0`
- `goa-1.0.pc`: `Requires: gio-2.0 >= 2.84.0, glib-2.0 >= 2.84.0`、
  `Libs: -L${libdir} -lgoa-1.0`、
  `Cflags: -I${includedir}/goa-1.0 -I${libdir}/goa-1.0/include`
- `package_info()`：`cpp_info.libs = ["goa-1.0"]`、`includedirs` 两项、
  `pkg_config_name = "goa-1.0"`、`cpp_info.requires = ["glib::glib", "glib::gio"]`
  （glib 的组件名，不是 `glib-2.0`）；共享库时把包 `lib/` 前置进
  `runenv_info` 的 `LD_LIBRARY_PATH`，消费者才能按 SONAME 找到库。

## 验证记录（2026-09-27，OHOS worker 真机）

```
conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64   -cc core.sources:download_cache=$HOME/.conan2/sources
→ RC=0；libgoa/3.58.1: PACKAGE_CODESIGN=PASS signed_elfs=1
```

`test_package`（消费者契约测试，`test_package/test_goa_consumer.c`）真实链接并
运行打包后的 `libgoa-1.0.so.0`，10 项断言全部通过：

```
ok - goaconfig.h: GOA_MAJOR/MINOR/MICRO_VERSION == 3.58.1
ok - goaversion.h: GOA_CHECK_VERSION(3,58,1)
ok - libgoa-1.0: goa_major/minor/micro_version == 3.58.1
ok - libgoa-1.0: goa_check_version(3,58,1) == NULL
ok - libgoa-1.0: goa_check_version(3,99,0) 返回错误说明
ok - libgoa-1.0: goa_error_quark() != 0
ok - GOA_TYPE_CLIENT -> "GoaClient"
ok - GoaClient 继承自 GObject
ok - goa-generated.h: GoaObject/GoaAccount/GoaManager 类型已注册
ok - goa_client_new_sync() 返回 GoaClient 或 GError
libgoa 3.58.1 consumer contract: all checks passed
```

同一 `test()` 里还用 `PkgConfig` 校验包身份面：`goa-1.0.pc` 的 modversion
（3.58.1）、includedirs（含本包 `goa-1.0`）、libs（含 `-lgoa-1.0`）必须来自本包。

补充真机证据：

- 打包产物 `p/lib/libgoa-1.0.so.0.0.0` 与 SONAME 软链 `libgoa-1.0.so.0`
  `dlopen` 均 **OK**；`.codesign` 段恰好 1 个。
- 上游**没有测试套件**：3.58.1 的官方 tarball 内没有任何 `meson test` 目标
  （全量 `meson.build` 检索 `test(` 无命中），故 `test_package/MANIFEST.yml`
  如实声明 `upstream_test_in_build: false`、`upstream_tests: []`，不假声明。

### 装包树复核（2026-09-28，真机 conan cache）

对 **已打包** 的包目录（不是构建目录）直接核验，全部为真机实测输出：

```
包内 94 个文件 + 2 个软链：
  include/goa-1.0/goa/        7 个头（goa.h goaclient.h goa-generated.h goaenums.h
                              goaenumtypes.h goaerror.h goaversion.h）
  lib/goa-1.0/include/goaconfig.h      197 B（配置期生成；Cflags 已含 -I${libdir}/goa-1.0/include）
  lib/libgoa-1.0.so{,.0,.0.0.0}        md5 5c323a0a7a1aeaa0f5460b261975e05a
  lib/pkgconfig/goa-1.0.pc             852ab02060534931d0189d0ac5c61069
  share/locale/*/LC_MESSAGES/gnome-online-accounts.mo   80 个
  share/applications/org.gnome.goa-daemon.desktop, share/icons/.../…-symbolic.svg
  conaninfo.txt: os=OHOS / os.version=6.0 / arch=armv8 / clang 15 / Release / shared=True
                 requires: glib/2.88.Z

readelf -dW 包内 .so：SONAME [libgoa-1.0.so.0]；NEEDED = libgio-2.0.so.0 / libgobject-2.0.so.0 / libglib-2.0.so.0
readelf -SW 包内 .so：.codesign 段恰好 1 个（[37] .codesign PROGBITS … 001000）
裁剪面核验（包内计数）：*goa-backend* = 0；目录 goabackend/ = 0
交付面审计：以上游变量声明的交付面全集（goa_api_name / goa_backend_api_name）与真机安装树逐项 diff；差集 = goa-backend-1.0 + goa-daemon（其依赖 json-glib / libsecret / libsoup-3.0 / libxml2 / rest-1.0 未发布到 ohpcd），已在本文与 manifest 显式申报；公开面（goa-1.0.pc / libgoa-1.0.so.0 / include/goa-1.0/goa）完整不受影响。（全集机械化枚举手段：`meson introspect --installed <builddir>`，本次未在真机实跑，以上游 install 声明 + 安装树清单完成等价 diff）
可复现性：两次独立 conan create（2026-09-27 23:37 与 2026-09-28 16:22）的 .so 与 .pc md5 完全一致
```

## 已知限制

- goa-daemon 不在 OHOS 上运行，`goa_client_new_sync()` 现场拿不到会话总线
  （`Cannot spawn a message bus without a machine-id`）。消费者测试对此**如实容忍**
  （断言返回 `GoaClient` 或 `GError`），不伪造运行通过。
- 真机 `pkg-config --cflags/--libs goa-1.0` 需要 `proxy-libintl.pc`（glib 自身的
  `Requires` 之一，由 conan `PkgConfigDeps` 在消费者生成目录提供），直接指向包内
  `.pc` 时只有 `--modversion` 可用；`test_package` 走 conan 生成目录，不受影响。
