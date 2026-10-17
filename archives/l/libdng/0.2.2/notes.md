# libdng 0.2.2 适配笔记

## 编译环境

- 构建系统: meson
- 编译日期: 2026-09-17
- 编译器: clang/clang++ (HarmonyOS PC aarch64, conan profile ohos-aarch64)
- 状态: built（待真机预检回填 evidence 后确认）

## 编译步骤

上游主构建为 Meson（`meson.build` 版本 0.2.2；`CMakeLists.txt` 仍为 0.1 旧版，不采用）：

```bash
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

配方关键动作（`archives/l/libdng/0.2.2/conanfile.py`）：

1. `PkgConfigDeps` 生成 `libtiff-4.pc`，供给上游 `dependency('libtiff-4')`
2. `MesonToolchain` 设置 `default_library=shared`、`man-pages=disabled`（OHOS/CI 无 scdoc）、`wrap_mode=nodownload`
3. 构建期把 `meson.build` 中 `shared_library('dng', ...)` 替换为 `library('dng', ...)`，仅为让 `default_library` 控制静态/动态，不改源码逻辑
4. `meson.configure()` → `meson.build()` → `meson.test()`（4 个 greatest 测试全量运行），成功后输出 `HMBS_UPSTREAM_TEST_RESULT`（meson, 4/4）
5. `meson.install()` 后对 `lib/*.so*` 与 `bin/makedng`、`bin/dumpdng` 自签（`llvm-objcopy` 去旧 `.codesign` + `binary-sign-tool -selfSign 1`；工具缺失时告警跳过）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 `CMakeLists.txt` 版本号停留在 0.1 | CMake 文件是旧版遗留，主构建已迁移到 Meson | 选用 Meson 路线，不使用 CMake |
| 2 | `dependency('scdoc')` 在 OHOS 失败 | OHOS/CI 无 scdoc，man 页无法生成 | `man-pages=disabled` 固定关闭 |
| 3 | `shared_library()` 无视 `default_library` | Meson 语义：`shared_library()` 恒为动态 | 构建期一行替换为 `library()`，静态/动态由选项控制 |
| 4 | `dependency('libtiff-4')` 找不到 | 需 conan 包提供 pkg-config 文件 | `requirements libtiff/4.7.2` + `PkgConfigDeps` |

## 源码修改

无补丁。仅构建期一行构建定义替换（见上），未改源码逻辑，未引入 `__OHOS__` 平台宏。

## 依赖版本

- libtiff/4.7.2（本仓同版本配方；下游均以此版本为基准）

## 上游测试清点（申报表）

- 来源目录：`tests/`（`meson.build` 注册 4 个 `test()`）
- `check_mode`：3 个 TEST（mode_from_name_8bit / 10bit / 10bit_packed）
- `check_dng`：2 个 TEST（generate_simple_dng / read_dng）
- `check_dcp`：1 个 TEST（load_pinephone_dcp，需 `tests/fixture/pinephone.dcp`，上游 `fs.copyfile` 已处理 workdir）
- `check_repack`：2 个 TEST（repack_10bit / repack_10bit_pad1）
- 合计：4 个 meson 测试，8 个 greatest TEST；可选 `dng_validate`（Adobe 外部程序）缺失时上游自动跳过
- 接入：`build()` 调用 `meson.test()`（`meson test --print-errorlogs`），失败即抛错阻断打包；`test_package` 复发 `HMBS_UPSTREAM_TEST_RESULT` 以便缓存命中轮次仍可见证据
- 证伪要点：`check_dng` 写出 `test.dng` 后用 libtiff 直接回读并断言 TIFFTAG 字段；输出参照为真实写出的文件，非空文件比对；`check_dcp` 断言色矩阵/正向矩阵/tone curve/HueSatMap 数值范围，非静默跳过

## 验证结果

```bash
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

待 HMBS 真机预检回填：`HMBS_TEST_PACKAGE_RESULT`（test_package 4 个 CHECK-OK）与 `HMBS_UPSTREAM_TEST_RESULT`（meson 4/4）的实测行。

## 交付物

| 文件 | 说明 |
|------|------|
| lib/libdng.so.1.2.0（含 libdng.so.1/libdng.so 链接） | 主库 |
| include/libdng.h | 公开头文件 |
| lib/pkgconfig/libdng.pc | pkg-config 元数据 |
| bin/makedng、bin/dumpdng | 附带工具 |

## 注意事项

- 本库非系统同名库，默认动态链接，由 Conan 管理依赖链（R26 不适用）
- `makedng`/`dumpdng` 为开发调试小工具，未声明 `commands.json`（主产物为库；工具随包安装但非独立 CLI 包口径）
- 真机 `TMPDIR` 由 HMBS 注入；配方不硬编码 `/tmp`，临时文件落在 conan 构建目录
