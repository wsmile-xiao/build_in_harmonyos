# DRAFT-appstream-1.2.0-ohos-pkgconfig-component-requires-pc — PkgConfigDeps 完整 Requires 的组件式 package_info

> **Contributor**: pc2-19 | **Status**: DRAFT | **Updated**: 2026-09-20
> **Severity**: medium (2) | **Category**: conan / pkg-config / packaging / static-linking / cmake
> **Audience**: 所有 Conan 2 meson/静态库配方：头文件在 include/<name>/ 子目录、库+CLI 双产物、消费者走 .pc 或 CMakeDeps

## 触发（trigger）

- appstream 1.2.0 OHOS 适配：test_package（PkgConfigDeps 流）链接 `libappstream.a`
  报 `undefined symbol: fy_*（libfyaml）/ sb_*（libstemmer）`；
  CMakeDeps 流报 `fatal error: 'appstream.h' file not found`。

## 症状（symptom）

```
ld.lld: error: undefined symbol: fy_node_get_type
>>> as-yaml.c.o in archive .../libappstream.a
ld.lld: error: undefined symbol: sb_stemmer_new
>>> as-stemmer.c.o in archive .../libappstream.a
```

修复前生成的 `appstream.pc`：`Requires: glib-2.0 gobject-2.0 gio-2.0 gmodule-2.0
libcurl libxml-2.0 xmlb libzstd`——缺 libfyaml/libstemmer，静默无告警。

## 机制（root cause）

1. **根级 cpp_info.requires 的 .pc Requires 解析静默缺项**：PkgConfigDeps 对
   `self.cpp_info.requires`（根级列表）的组件引用解析不稳定，静态库消费者按
   appstream.pc 链接时缺 libfyaml/libstemmer 等传递符号；
   组件式声明（`components["x"].requires` 全量列出）生成的 Requires 才完整
   （libxmlb 同款已被 meson 消费验证）。
2. **package_type='application' 破坏 CMakeDeps 消费者**：含 CLI 的库配方若声明
   application 包类型，CMakeDeps 按可执行应用处理 → 消费者目标空 include/libs
   （appstream.h 找不到）；库 + CLI 双产物应 package_type='library'，CLI 由
   软件级 commands.json 声明（R38/L0k）。

## 修复（rec）

```python
# conanfile.py package_info()
self.cpp_info.set_property("cmake_file_name", "appstream")
self.cpp_info.set_property("cmake_target_name", "appstream::appstream")
self.cpp_info.set_property("pkg_config_name", "appstream")
lib = self.cpp_info.components["appstream"]
lib.includedirs = ["include/appstream"]          # R38 头文件子目录布局
lib.libs = ["appstream"]
lib.requires = [
    "glib::glib", "glib::gobject", "glib::gio", "glib::gmodule",
    "libcurl::libcurl", "libxml2::libxml2", "libxmlb::libxmlb",
    "libfyaml::libfyaml", "libstemmer::libstemmer", "zstd::zstd",
]
lib.system_libs = ["m", "pthread"]
# 类级：package_type = "library" + options {shared,fPIC}（CLI 在 commands.json 声明）
```

生成的 `appstream.pc` Requires 完整：
`glib-2.0 gobject-2.0 gio-2.0 gmodule-2.0 libcurl libxml-2.0 xmlb libfyaml libstemmer libzstd`。

## 验证（verification）

`conan create`：test_package 真实 API 消费者（`as_metadata_parse_data`）编译链接运行
1/1 通过；`appstream.pc` Requires 链完整；W3 L0 门禁通过（commands.json R38）。

## 适用边界 / 反例

- 适用：静态库交付 + pkg-config/CMakeDeps 消费者；include/<name>/ 头文件布局；
- 反例：仅动态库交付且链接器解析运行期依赖的项目可简化；
- 反例：包无 CLI、无子目录头文件布局时不需要同时处理两件事（可只取组件 requires 点）。

## 关系

- `similar_to`: DRAFT-conan-shared-pkgconfig-requires-drop（.pc Requires 链不完整，
  但触发机制不同：该草稿是 shared-library 静态依赖 transform_downstream skip，
  本候选是根级 vs 组件式声明差异）、E348（PkgConfigDeps 多 .pc 转发）、
  E216/E447（CMakeDeps INTERFACE_INCLUDE_DIRECTORIES 传播）
- 差异：本候选给出**组件式 package_info 全量 requires** 与 **package_type 语义**两
  个可复用手法，且 test_package 真实 API 消费者证据。

## 证据

- 配方：`archives/a/appstream/1.2.0/conanfile.py`
- 测试：`archives/a/appstream/1.2.0/test_package/test.c`（真实 API 调用）
- 生成的 .pc：`test_package/build/<profile>/generators/appstream.pc`
- 台账：`archives/a/appstream/1.2.0/reports/knowledge-candidate-ledger.md` 候选 5+6