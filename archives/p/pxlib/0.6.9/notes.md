# pxlib 0.6.9 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-19
- 编译器: clang/clang++
- 状态: built

## 编译步骤

`conan create archives/p/pxlib/0.6.9 -pr:h ohos-aarch64 -pr:b ohos-aarch64`

全链路 PASS：OHOS aarch64 交叉编译 → 打包 → test_package 编译/链接/运行，
2 个测试可执行文件（`test_pxlib`、`test_ohos`）均 PASS。

上游 0.6.9 无自动化测试入口（`CMakeLists.txt` 无 `enable_testing()`/`add_test()`，
`Makefile.am` 无 `TESTS=`，仓库无 `tests/` 目录），故 test_package 为自建冒烟。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `cmake.install()` 装不出任何产物 | 上游 `CMakeLists.txt` 全无 `install()` 规则 | 配方 `package()` 中用 `copy()` 手动拷贝 `libpxlib.{a,so}` 与公开头到 `package_folder` |
| 2 | 版本宏与 release tag 不符 | 0.6.9 发布 tarball 里 `PXLIB_MICRO_VERSION` 写死 `"8"` | `patches/0001-fix-version-macro-0.6.9.patch` 改为 `"9"` |
| 3 | `shared` 选项不生效，产物恒为 `.so` | 上游 `add_library(pxlib SHARED ...)` 硬编码 `SHARED` | `patches/0002-honor-BUILD_SHARED_LIBS.patch` 去掉 `SHARED`，交给 CMake 的 `BUILD_SHARED_LIBS` |
| 4 | consumer 侧找不到公开头 | `paradox.h`/`paradox-gsf.h`/`pxversion.h` 是 `*.h.in` 经 `configure_file` 的**构建期产物**，落在 `CMAKE_BINARY_DIR/include` | 从 `self.build_folder/include`（及 `build_folder` 根取 `pxversion.h`）拷贝；`*.h.in` 模板**不随包分发** |
| 5 | CI 上 `fopen` 写临时文件失败 | OHOS aarch64 的 `/tmp` 是 HMDFS 只读分区 | test 临时文件改写 `$HOME/tmp`，且先 `mkdir()` 再写（`test_pxlib.c:26-27`、`test_ohos.c:63-64`） |

## 源码修改

| 补丁 | 修改内容 |
|------|----------|
| `patches/0001-fix-version-macro-0.6.9.patch` | `CMakeLists.txt`：`set(PXLIB_MICRO_VERSION "8")` → `"9"` |
| `patches/0002-honor-BUILD_SHARED_LIBS.patch` | `CMakeLists.txt`：`add_library(pxlib SHARED ${SOURCES})` → `add_library(pxlib ${SOURCES})` |

两补丁经 `conandata.yml` 的 `patches` 登记，由 `export_sources()` +
`apply_conandata_patches()` 在 `build()` 中应用。补丁新增行**不含**任何平台宏。

## 依赖版本

无强制第三方 conan 依赖：
- `iconv` —— 由 OHOS musl 系统 libc 提供，不走 conan
- `libgsf-1` —— 上游可选特性（`ENABLE_GSF`，默认 OFF），未启用

## 验证结果

```bash
conan create archives/p/pxlib/0.6.9 -pr:h ohos-aarch64 -pr:b ohos-aarch64
# Conan test_package: 通过
# L0 门禁 (结构完整性): 通过
# L1 门禁 (测试执行验证): 通过
# CI build #59785 (2026-09-24) CI 校验通过
```

上游测试清点（实测 N=0，声明 N=0，未少报）：

```bash
find . -type d -name tests | wc -l                                    # 0
find . -type f \( -name 'test*.c' -o -name '*_test.c' \) | wc -l       # 0
grep -cE 'enable_testing|add_test|include\(CTest\)' CMakeLists.txt     # 0
grep -cE '^\s*TESTS\s*=' Makefile.am                                  # 0
```

自建 test_package 用例 M=2（闸门自清点）：
- `test_pxlib.c` —— 写 `$HOME/tmp` 下 512B 最小 Paradox 4.x 头，`PX_new()` + `PX_open_file()` 解析冒烟
- `test_ohos.c` —— 鸿蒙特有：`OHOS_TARGET` 工具链身份 + `/tmp` `EROFS` 只读断言 + `$HOME/tmp` 回退路径端到端

## 注意事项

- **`/tmp` 在 OHOS 上只读**（HMDFS）。任何测试/构建脚本禁止硬编码 `/tmp` 写入。
  `test_ohos.c:85` 的 `/tmp` 写探测是**故意的**——它就是 EROFS 断言本体，不要删。
- **`*.h.in` 不随包分发**：consumer 侧拿到模板会遮蔽 `configure_file` 生成的真实头。
- `test_ohos.c` 在非 OHOS 平台自动 SKIP 并 `return 0`，不影响跨平台复用。
- `test_ohos.c:87-95` 断言「`/tmp` 必须只读」，若在 `/tmp` 可写的宿主上运行会判 FAIL；
  这是环境属性断言而非库属性断言，评审时需知悉。
