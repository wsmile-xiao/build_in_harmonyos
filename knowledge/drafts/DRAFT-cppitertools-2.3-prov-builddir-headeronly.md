# DRAFT-cppitertools-2.3-prov-builddir-headeronly — cppitertools 2.3 三段问题组合（provenance + 大小写不敏感 FS 构建目录 + header-only 配方）

> 对应 KV：`knowledge/drafts/DRAFT-cppitertools-2.3-prov-builddir-headeronly.kv`
> 触发事件：cppitertools 2.3 HarmonyOS PC 首轮 Bootstrap + Adapt（R01→R02，task cppitertools-2.3-r01-bootstrap-and-adapt-pc1-62）

## 问题（error_signature）

三问题组合，任一均可跨库复现：

1. **上游配方版本元数据与正式 tag 不一致（provenance）**：上游仓库自带 `conanfile.py` 声明 `version = '3.0'`，而官方 git tag 为 `v2.3`（`git ls-remote --tags` 可证）；若直接沿用上游配方版本号，归档/制品仓会出现与官方发布无关的版本。
2. **大小写不敏感文件系统下 Bazel `BUILD` 文件与 `build` 目录冲突**：仓库根目录存在 Bazel `BUILD` 文件，而 `cmake_layout(self)` 默认使用 `build/Release` 作为构建目录；在大小写不敏感 FS（本执行端）上 `mkdir build/Release` 因 `build` 已作为文件存在报 `NotADirectoryError: [Errno 20]`，`conan create` 在 generate 阶段即失败。
3. **header-only C++17 库配方**：无编译产物，`package_type = "header-library"`，消费者 include 路径与命名空间（`iter::` 而非 `itertools::`）易被写错，`test_package` 需按真实 API 校验。

## 根因（root_cause）

1. 上游版本元数据不作为发布事实来源；官方 git tag 才是。上游 conanfile 由作者维护滞后。
2. `cmake_layout` 假定 `build` 目录名可用；上游带 Bazel `BUILD` 文件的项目在大小写不敏感 FS 上与之冲突。
3. header-only 库无 ABI 残留，配方必须显式声明 `header-library`，消费者测试必须包含真实头文件 API。

## 方案（fix_approach）

1. 版本号以官方 tag 为准（`2.3`），conandata.yml 记录官方 URL + tag commit + SHA-256；不沿用上游 conanfile 的 version 字段。官方来源/标签/校验值任一无法确认 → `source_provenance_unavailable` 停止。
2. `cmake_layout(self, build_folder="build_dir")`（non-default folder name）规避与 Bazel `BUILD` 的碰撞；该参数对所有 CMake 配方均合法。
3. header-only 配方三件套：`package_type = "header-library"`、`package_info()` 只暴露 include 与 `cpp_info.set_property("cmake_target_name", ...)`；test_package 用 `find_package(cppitertools)` + `iter::range/enumerate/zip/accumulate` 真实 API 断言（C++17）。

## 验证（verification）

- `git ls-remote --tags https://github.com/ryanhaining/cppitertools` → v2.3 = `13947eb68f464cb014343de7a155016290655d1a`，tarball SHA-256 `419c8192691859650cca8ae7c7a8d633af42dfc453af87b7645338536c6e9e82`
- `conan create archives/c/cppitertools/2.3 -pr:h ohos-aarch64 -pr:b default` → EXIT 0
- test_package `test_cppitertools` 1/1 通过（8 断言：range 求和 45 / accumulate 乘积 120 / enumerate 拼接 / zip 求积 140）
- 构建日志：`.build-tmp/logs/conan-create-r01e.log`（SHA-256 `d39b97b8be9dd999295d7f9d60c58468a723db3868a11d5c8f704362bc35538b`）

## 适用边界（applicable_to）

- 上游仓库自带 conanfile.py 且声明版本与官方 tag 不一致的任何库（provenance 校验）；
- 项目根目录含 Bazel/其他 `BUILD` 文件（或任何与 `build` 同名的文件）且构建 FS 大小写不敏感的场景；
- header-only C++17（或更高标准）库的 Conan 配方与消费者测试。

## 查重差异（dedup difference）

- 查重范围：`knowledge/graph/index.tsv`、`knowledge/doc/`、`knowledge/drafts/`；关键词：`cppitertools`、`itertools`、`header-only`、`Bazel BUILD`、`case-insensitive`、`cmake_layout`、`provenance`、`version mismatch`。
- 命中条目：`E307`（header-only 消费者 compile-only 测试，无 CMake 场景）、`DRAFT-dual-case-coexist-lowercase-recipe`（大小写不敏感 FS 双 case 包目录并存）、`E035`（boost header-only install）、`E021`（conftestdir 大小写）、`E071`（autotools 版本不匹配）。
- 未覆盖差异：`DRAFT-dual-case-coexist-lowercase-recipe` 处理包目录双 case（SDL2_image/libXext），不涉及 Bazel `BUILD` 文件与 `cmake_layout` 构建目录冲突；`E307` 假设 CMake 不可用（compile-only 直编），本案例 CMake 可用且走完整 `conan create`+CTest；无既有条目覆盖"上游配方版本元数据 vs 官方 tag"provenance 校验。三问题组合为新增可跨库复用知识，非孤立 patch。

## 元信息

| 字段 | 值 |
|------|-----|
| id | `DRAFT-cppitertools-2.3-prov-builddir-headeronly` |
| trigger_tool | `conan`/`git`/`cmake` |
| phase | `bootstrap`/`configuration`/`packaging`/`testing` |
| severity | 2 |
| category | `conan`/`build`/`provenance`/`filesystem`/`packaging` |
| conan_package | cppitertools/2.3 |
| platform | OHOS 6.0 arm64（provenance 与 BUILD 冲突适用于任何大小写不敏感 FS） |