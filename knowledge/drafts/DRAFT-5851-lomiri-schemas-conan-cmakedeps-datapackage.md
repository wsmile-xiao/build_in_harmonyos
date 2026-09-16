# OHOS 数据包 / GSchema：intltool-merge 的 Perl XML::Parser，外加 Conan CMakeDeps 的三个 generate() 补丁点

> 知识草稿（与 lomiri-schemas 0.1.11 归档同 PR 交付）。
> 来源：lomiri-schemas 0.1.11 适配，G2（conan create, ohos-aarch64, clang 15）通过，
> test_package 48/48 断言在 OHOS 目标实跑通过。
> 载体：GSettings schema + AccountsService D-Bus 接口 XML + polkit 的纯 CMake 数据包
> （上游 `project(lomiri-schemas LANGUAGES NONE)`，零编译单元，1 个移植性补丁）。

## 问题 1：`intltool-merge --xml-style` 硬依赖 Perl 的 `XML::Parser`

- **现象**：`conan create` 在 build 阶段中止，每个 schema 都报

  ```
  You must have XML::Parser installed to run .../bin/intltool-merge
  make[2]: *** [data/schemas/CMakeFiles/com.lomiri.Shell.gschema.xml.dir/build.make:73: …gschema.xml] Error 2
  ```

- **根因**：上游 `data/schemas/CMakeLists.txt` 对每个 `*.gschema.xml.in` 调
  `intltool_merge_translations(... ALL UTF8 STYLE "xml" NO_TRANSLATIONS)`，
  展开后执行 `intltool-merge --xml-style --quiet --utf8 --no-translations <in> <out>`。
  intltool-merge 是 Perl 脚本，`--xml-style` 分支的 `readXml()` 里
  `eval 'require XML::Parser'`，缺失即 die。`XML::Parser` 是 CPAN 模块（依赖 expat），
  **不是 perl core**，OHOS 设备的 perl 没有装它。
  关键陷阱：`--no-translations` **并不能绕过**这条分支——它只让 `preparation()`
  跳过 `gather_po_files` / `get_translation_database`，随后照样调用 `readXml()`
  解析输入。所以「我不用翻译，应该没事」是错的。
- **修复**：先判定能否直接拷贝。本仓库 6 个 `.gschema.xml.in`
  **不含任何 gettext 标记**（`grep -c "translatable\|<_[a-zA-Z]" *.in` 全为 0），
  且上游根本没有 `po/` 目录。此时 `--xml-style --no-translations` 的唯一效果就是
  「解析后原样重新输出」，与直接拷贝逐字节等价。于是补丁把该行换成 CMake 原生：

  ```cmake
  configure_file("${XML_IN_FILE}" "${CMAKE_CURRENT_BINARY_DIR}/${XML_FILE}" COPYONLY)
  ```

  并删掉随之无用的 `find_package(Intltool REQUIRED)`，配方里的
  `tool_requires("intltool/0.51.0")` 也一并去掉（`gettext` 保留：GSettingsConfig
  会 `find_package(Gettext REQUIRED)`）。
- **适用边界（重要）**：拷贝替代只对「无 gettext 标记 + 无 `po/`」的文件成立。
  若源文件确有 `translatable="yes"` / `_` 前缀元素或上游带 `po/`，拷贝会**静默丢失
  翻译**，此时应改为在 OHOS 侧提供 `XML::Parser`，或把渲染结果作为构建产物分发。
- **验证**：`conan create` G2 通过；`glib-compile-schemas --strict --dry-run <schema 目录>`
  退出码 0（`--strict` 把 schema 告警当错误）。

## 问题 2：`conan_cmakedeps_paths.cmake` 永远不含 `CMAKE_PREFIX_PATH`

- **现象**：`find_package(GSettings)` 报
  `Could NOT find GSettings (missing: GSettings_DIR)`，尽管 cmake-extras/1.9 已是
  构建期依赖、`GSettingsConfig.cmake` 确实在包内
  `share/cmake/GSettings/GSettingsConfig.cmake`。
- **根因**：Conan 2.x 的 `CMakeConfigDeps`（`CMakeDeps` 的实现）生成的
  `<generators>/conan_cmakedeps_paths.cmake` 只写每个依赖的 `<pkg>_DIR`、
  `CMAKE_PROGRAM_PATH`（直接依赖 bindirs）与 `CMAKE_MODULE_PATH`（所有依赖 builddirs），
  **从不写 `CMAKE_PREFIX_PATH`**。而 `CMakeToolchain` 的 FindFiles 块是**互斥二选一**：
  ```cmake
  if(EXISTS "${CMAKE_CURRENT_LIST_DIR}/conan_cmakedeps_paths.cmake")
      include(...)                # 走这里 → 没有 CMAKE_PREFIX_PATH
  else()
      set(CMAKE_PREFIX_PATH ...)  # 自带兜底 → 被跳过
  endif()
  ```
  于是「路径文件存在」反倒意味着「toolchain 不补 `CMAKE_PREFIX_PATH`」；而
  `<pkg>_DIR` 指向包根，`share/cmake/<Module>/` 这种布局不在任何搜索路径内。
- **修复**：`generate()` 里 `CMakeToolchain(self).generate()` 之后，往
  `conan_cmakedeps_paths.cmake` 追加
  `list(PREPEND CMAKE_PREFIX_PATH "<cmake-extras 包目录>")`。
  用 `list(PREPEND)` 而非 `set(...)`，不破坏文件里已有的同名变量；文件此时已存在，
  直接 `open(..., "a")` 追加。

## 问题 3：`PkgConfigDeps` 丢失上游自定义 pkg-config 变量

- **现象**：configure 能过，但 `GSettingsConfig.cmake` 用
  `pkg-config gio-2.0 --variable glib_compile_schemas` 取到的路径是**空串**，
  `add_test(NAME validate-<schema> COMMAND <empty> --dry-run ...)` 的首 token
  变成 `--dry-run`（被当成程序名），校验命令形同虚设。
- **根因**：`PkgConfigDeps` 生成的 `.pc` 从 `cpp_info` **反推**，只含 libs /
  includedirs / requires 等可推导字段；上游 `.pc.in` 的自定义变量（glib 系的
  `glib_compile_schemas`、`glib_genmarshal` 等）不在 `cpp_info` 里，全部丢失。
- **修复**：`PkgConfigDeps(self).generate()` 之后，检测
  `<generators>/gio-2.0.pc` 是否含 `glib_compile_schemas`，缺失则追加
  `glib_compile_schemas=<glib 包>/bin/glib-compile-schemas`（带幂等判定）。

## 问题 4：纯数据包的安装前缀 —— `/usr` 兜底 vs 只读依赖 prefix

- **现象 A**：上游 `CMakeLists.txt` 有
  `if(CMAKE_INSTALL_PREFIX_INITIALIZED_TO_DEFAULT) SET(CMAKE_INSTALL_PREFIX "/usr" ... FORCE)`，
  install 会直写宿主 `/usr`。`CMakeToolchain` 的 `OutputDirsBlock` 虽然设了
  `CMAKE_INSTALL_PREFIX=package_folder`，但那是在 toolchain 文件里 `set()` 的，
  会被上游 cache 变量 `FORCE` 覆盖。
  **修复 A**：`tc.cache_variables["CMAKE_INSTALL_PREFIX"] = self.package_folder`
  （cache 变量等价于命令行 `-D`，优先级在源码 `FORCE` 之上）。
- **现象 B**：GSettings 模块默认把 schema 装进 `_glib_prefix`（只读的 glib 依赖
  prefix），install 失败。**修复 B**：`tc.variables["GSETTINGS_LOCALINSTALL"] = "ON"`。
- **附带的构建期工具问题**：OHOS SDK 的 `/data/service/hnp/bin` 里有 shebang 指向
  不存在解释器的坏条目，`find_program` 可能命中它们。用
  `list(PREPEND CMAKE_PROGRAM_PATH "<conan 侧>/bin")` 把 gettext/glib 的 bin 前置
  （与问题 2 的补丁点合并完成）。

## 适用范围与边界

- **问题 1**：所有在 OHOS 上经 intltool-merge 渲染 `.in` 的项目（GSettings schema、
  `.desktop`、gettext 生态工程）。**拷贝替代前必须先确认无 gettext 标记且无 `po/`**。
- **问题 2**：所有构建期依赖提供 CMake config 且装在 `share/cmake/<Module>/` 的配方
  （cmake-extras 家族 GSettings / Intltool / ECM）。这是通用结构问题。
- **问题 3**：所有依赖上游 `.pc.in` 自定义变量的配方（glib 系）。
- **问题 4**：纯数据类 CMake 包。**特别注意**：数据包的 `test_package` 必须包含
  「用真实工具消费产物」的一条断言（这里是
  `glib-compile-schemas --strict --dry-run`），否则空命令哑火不会被发现。

## 查重差异

- **intltool-merge / XML::Parser**：图谱未见 intltool 相关条目（`knowledge/graph/index.tsv`
  中 `intltool` 零命中），未命中，新增。这是本条目最强的独立价值：它解释了
  「`--no-translations` 并不绕过 XML 解析」这一反直觉陷阱。
- **`conan_cmakedeps_paths.cmake` 追加 `CMAKE_PREFIX_PATH`**：E487
  （qt6linguisttools-tool-require-plus-pin-DIR）方向一致但场景不同——E487 针对 Qt6Config
  组件解析锚定 `Qt6_DIR` 相对路径的 Qt 特有问题，方案核心是 `tool_requires` +
  显式 `Qt6LinguistTools_DIR`；本条目给的是**通用机制解释**（CMakeToolchain FindFiles
  两分支互斥）与 `list(PREPEND)` 幂等追加手法。属部分覆盖 + 机制新增。
- **`PkgConfigDeps` 丢自定义变量**：E348（pkg_config_name / forwarding pc）与
  E468（`PKG_CONFIG_PATH` 指 generators 目录）都在 pkg-config 主题下，但前者解决
  「包名/别名解析」、后者解决「找得到 `.pc`」，均未涉及「`.pc` 里少了上游自定义变量」
  这一反向丢失。未命中，新增。
- **`GSETTINGS_LOCALINSTALL` / 数据包安装前缀**：图谱无 GSettings 数据包相关条目
  （E393 是 libsndfile 的 `CMAKE_MODULE_PATH` 列表语义、E527 是 gtk broadway 后端），
  未命中，新增。
