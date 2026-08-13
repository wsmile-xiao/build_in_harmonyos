# json-glib 1.6.6 编译笔记

## 编译概述

json-glib是一个用于GLib的JSON解析库，使用Meson构建系统。

## 版本信息

- 版本：1.6.6
- 构建系统：Meson
- 编译日期：2026-05-22

## 下载源码

使用 GNOME 官方发布包：
- URL: https://download.gnome.org/sources/json-glib/1.6/json-glib-1.6.6.tar.xz
- SHA256: 96ec98be7a91f6dde33636720e3da2ff6ecbb90e76ccaa49497f31a6855a490e
- 大小：1.3MB

华为云和 USTC 镜像可作为备用下载源。

## 编译过程

### 1. Meson配置

```bash
meson setup builddir \
    --prefix=$DEFAULT_PREFIX \
    --buildtype=release \
    --default-library=static \
    -Dintrospection=disabled \
    -Dgtk_doc=disabled \
    -Dtests=false \
    -Dman=false
```

配置成功。

### 2. 编译遇到的问题

**问题1：glib-mkenums权限错误**

Meson的`gnome.mkenums`调用glib-mkenums生成enum类型文件，但subprocess.Popen调用失败：
```
PermissionError: [Errno 13] Permission denied: '/storage/Users/currentUser/usr/local/bin/glib-mkenums'
```

**解决方案**：
手动生成enum文件并修改meson.build：
```bash
glib-mkenums --template json-enum-types.h.in ... > json-enum-types.h
glib-mkenums --template json-enum-types.c.in ... > json-enum-types.c
```

修改`json-glib/meson.build`第19-26行，使用预生成的文件而非动态生成。

**问题2：/bin/sh无法调用rm命令**

静态库链接时ninja执行`rm -f`失败：
```
/bin/sh: rm: inaccessible or not found
```

原因：OpenHarmony上/bin/sh是musl动态链接的程序，无法调用toybox的rm命令。

**解决方案**：
修改build.ninja，将`rm -f`改为`/usr/bin/rm -f`。

**问题3：工具程序链接失败**

json-glib-validate和json-glib-format链接失败，缺少多个依赖：
- libintl (g_libintl_bindtextdomain)
- libffi (ffi_type_void)
- libz (inflateEnd)
- gmodule (g_module_supported)

**状态**：
工具程序暂不编译，仅编译静态库和头文件。

### 3. 最终产物

成功编译并安装：
- 静态库：libjson-glib-1.0.a (368KB)
- 头文件：json-glib-1.0/json-glib/*.h (18个文件)
- pkg-config文件：json-glib-1.0.pc

## 质量验证结果

- G1（二进制完整性）：✅ 通过
- G2（功能可用性）：✅ 本地消费者验证通过
- G3（可移植性）：✅ 通过（静态库）
- G4（档案完整性）：等待修复提交的远端 OHOS CI/评审确认

## 本地复验（2026-08-01）

- 官方 `json-glib-1.6.6.tar.xz` 的 SHA256 为
  `96ec98be7a91f6dde33636720e3da2ff6ecbb90e76ccaa49497f31a6855a490e`，与 `conandata.yml` 一致。
- 在 Ubuntu x86_64 上以 `-Dtests=true -Dintrospection=disabled -Dgtk_doc=disabled -Dman=false` 配置官方源码，Meson 上游测试通过 **14/14**。
- 将本配方补丁应用到干净源码、使用预生成枚举源并以静态库配置重新构建后，同一 Meson 上游测试通过 **14/14**。
- 对 staged 安装树的 `libjson-glib-1.0.a` 和安装头文件编译、链接并运行 `test_package/test_json_glib.c`，消费者验证通过 **1/1**；该程序覆盖 JSON 解析、对象成员读取和数组元素计数。
- 上述结果是原生 Linux 验证，不替代本提交推送后的 OHOS 交叉编译 CI。

## 补丁说明

### 0001-meson-enum-types.patch

修改`json-glib/meson.build`，使用预生成的enum文件：
```diff
- json_glib_enums = gnome.mkenums(
-   'json-enum-types',
-   sources: source_h,
-   h_template: 'json-enum-types.h.in',
-   c_template: 'json-enum-types.c.in',
-   install_header: true,
-   install_dir: install_header_dir,
- )
- # Keep a reference to the generated header, for internal dependencies
- json_enum_types_h = json_glib_enums.get(1)
+ # Use pre-generated enum files instead of gnome.mkenums (to avoid subprocess permission issues)
+ json_enum_types_h = configure_file(
+   input: 'json-enum-types.h',
+   output: 'json-enum-types.h',
+   copy: true,
+   install: true,
+   install_dir: install_header_dir,
+ )
+ json_glib_enums = [
+   'json-enum-types.c',
+   json_enum_types_h,
+ ]
+ # Keep a reference to the generated header, for internal dependencies
+ json_glib_dep = declare_dependency(
+   link_with: json_lib,
+   include_directories: [ root_dir, include_directories('.') ],
+   dependencies: [gio_dep],
+   sources: [ json_enum_types_h, json_glib_gir ],
+ )
```

## 后续改进建议

1. 工具程序需要完整的依赖链（libintl, libffi, zlib, gmodule）
2. 需要将enum文件生成规则固化为补丁
3. 建议在知识图谱中添加"meson构建系统在OpenHarmony上的权限问题"

## 2026-08-08 真机测试入口

- `with_upstream_tests=False` 保持默认包构建不执行 Meson 上游测试。
- 真机原生执行可显式设置 `with_upstream_tests=True`，配方随后调用
  `meson.test()` 执行上游测试集；该选项不应被用于交叉构建或 CI 结果冒充
  真机证据。
- 消费者 `test_package` 现在以 Conan `can_run()` 决定是否运行。它不再仅因
  `os=OHOS` 跳过，因此同一 OHOS 真机上的原生 Conan 事务会真正执行
  `test_json_glib`。

---
**编译结束**
**最终状态**: built（静态库与原生消费者验证通过；工具程序待后续依赖链完善；修复提交的远端 OHOS CI 待确认）
