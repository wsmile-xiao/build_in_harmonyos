# lomiri-schemas 0.1.11 适配笔记

## 编译环境
- **构建系统**: cmake（纯数据包，无编译单元）
- **编译日期**: 2026-09-12
- **平台**: arm64-ohos（OpenHarmony PC）
- **状态**: built（Conan 配方验证通过）
- **补丁数量**: 1（`patches/0001-ohos-render-gschema-without-intltool.patch`）

## 上游形态

`project(lomiri-schemas LANGUAGES NONE)` + `add_subdirectory(data)`。产出：

| 类别 | 内容 |
|------|------|
| GSettings schema | 6 个 `*.gschema.xml.in`（渲染后 6 个 `.gschema.xml`，共 15 个 `<schema>` 节点） |
| D-Bus 接口 | 6 个 AccountsService XML → `share/dbus-1/interfaces/`，另在 `share/accountsservice/interfaces/` 建相对符号链接 |
| polkit | `com.lomiri.AccountsService.policy`（actions）+ `50-com.lomiri.AccountsService.rules`（rules.d） |
| pkg-config | `share/pkgconfig/lomiri-schemas.pc`（`Requires: glib-2.0`） |

上游**无测试套件**（无 tests/、无 `enable_testing()`、无 .github/workflows；
debian/Jenkinsfile 只调 ubports-build-tools 打包）。

## 编译步骤（conan create 全流程）

```bash
conan create archives/l/lomiri-schemas/0.1.11 --build=missing \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

### 1. 源码获取（source()）
`get()` 取 UBports GitLab 官方 tarball 并 strip_root（目录 lomiri-schemas-0.1.11）。

### 2. 生成（generate()）
- `CMakeDeps` + `PkgConfigDeps`：glib 的 `.pc`（gio-2.0 等）进 generators 目录，
  conan_toolchain.cmake 会把该目录注入 `PKG_CONFIG_PATH`。
- `CMakeToolchain`：`-DCMAKE_INSTALL_PREFIX=<package_folder>`（作 cache 变量下发，
  压掉上游 `/usr` 兜底分支）、`-DGSETTINGS_LOCALINSTALL=ON`。
- 往 `conan_cmakedeps_paths.cmake` 追加 `CMAKE_PREFIX_PATH`（cmake-extras 包目录）
  与 `CMAKE_PROGRAM_PATH`（gettext/glib 的 `bin/`）。
- 往生成的 `gio-2.0.pc` 补 `glib_compile_schemas=<glib>/bin/glib-compile-schemas`。

### 3. 补丁（build() 前的 apply_conandata_patches）

**0001 — 渲染 gschema 不再依赖 intltool-merge。** 上游 `data/schemas/CMakeLists.txt`
对每个 `*.gschema.xml.in` 调
`intltool_merge_translations(... ALL UTF8 STYLE "xml" NO_TRANSLATIONS)`，
展开后执行 `intltool-merge --xml-style --quiet --utf8 --no-translations <in> <out>`。
intltool-merge 是 Perl 脚本，`--xml-style` 分支的 `readXml()` 会
`require XML::Parser`，缺失即 die：

```
You must have XML::Parser installed to run .../bin/intltool-merge
```

OHOS 设备的 perl 未安装 XML::Parser（CPAN 模块，非 core），且 `--no-translations`
并不绕过该分支（intltool-merge 只是跳过 `gather_po_files`，仍要解析 XML），
所以 6 个 schema 全部构建失败。

关键事实：仓库里 6 个 `.gschema.xml.in` **不含任何 gettext 标记**——
没有 `_` 前缀元素、没有 `translatable="yes"` 属性（`grep -c "translatable|<_[a-zA-Z]" *.in`
全为 0），且上游根本没有 `po/` 目录。也就是说 `--no-translations --xml-style`
的唯一效果就是「解析后原样重新输出」，与直接拷贝逐字节等价。

故补丁把这一行换成 CMake 原生的
`configure_file("${XML_IN_FILE}" "${CMAKE_CURRENT_BINARY_DIR}/${XML_FILE}" COPYONLY)`，
并删掉同样不再需要的 `find_package(Intltool REQUIRED)`。
配方随之去掉 `tool_requires("intltool/0.51.0")`（gettext 仍保留：
`GSettingsConfig.cmake` 会 `find_package(Gettext REQUIRED)`）。

### 4. 构建（build()）
`cmake.configure()` + `cmake.build()`。实际动作只有两条：
- `configure_file(... COPYONLY)` 为每个 `.xml.in` 生成 `.xml`（补丁后）；
- `add_schema()`（cmake-extras GSettings 模块）为每个 schema 建 custom target 并
  注册 `add_test(NAME validate-<file> COMMAND <glib-compile-schemas> --dry-run
  --schema-file=<file>)`。

### 5. 打包（package()）
- `cmake.install()`：schema → `share/glib-2.0/schemas/`，D-Bus/polkit/pc 各归其位。
- 重定位 `lomiri-schemas.pc` 的 `prefix` 为 `${pcfiledir}/../..`。
- `COPYING` → `licenses/`。

## 依赖轨道

| 依赖 | 版本 | 用途 |
|------|------|------|
| glib | 2.88.3 | 运行期 GSettings（`.pc` 的 `Requires`）+ `bin/glib-compile-schemas` |
| cmake-extras | 1.9 | `find_package(GSettings)` 的 CMake 模块（构建期） |
| gettext | 0.22.5.1 | `GSettingsConfig.cmake` 的 `find_package(Gettext REQUIRED)`（msgfmt/msgmerge） |

> `intltool/0.51.0` 曾作为构建期依赖；补丁 0001 后不再需要。
> `cmake-extras` 的 `IntltoolConfig.cmake` 也因此不再被 include。

## 上游测试（rule 4）
- 上游无测试套件，如实声明 0（`ci/tools/extract_upstream_tests.sh` 口径下零命中）。
- 适配后：`test_package/test_lomiri_schemas.py` 48 项断言，在 OHOS 目标实跑，
  48/48 = 100%。其中 `glib-compile-schemas --strict --dry-run` 是对 schema 目录的
  真实合法性校验（GSettings 运行期同意这些模式），与上游 `add_schema()` 的
  `validate-*` 校验同源；补丁只替换了 schema 的渲染方式，未触碰任何校验路径。

## 已知限制
- 未做 GSettings 运行期读取验证（需 dconf/会话总线，CI 无 session bus）；
  但 schema 已通过 `glib-compile-schemas --strict` 编译级校验。
- `accountsservice/interfaces` 下是相对符号链接；断言用 `os.path.exists`（跟随链接）
  而非 `islink`，以兼容打包器对符号链接的展开行为。
- 补丁只对「无 gettext 标记」的 gschema 成立。若上游未来为 schema 加上
  `translatable="yes"`/`_` 前缀元素，本补丁会静默丢掉翻译，需重新评估
  （届时应改为在 OHOS 侧提供 XML::Parser，或把 intltool-merge 的
  `--no-translations` 渲染结果作为构建产物分发）。

---
**编译结束**: 2026-09-12
**最终状态**: built
