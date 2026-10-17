# libtsm 4.6.0 — OHOS 适配笔记

## 概述

libtsm（TSM）是终端模拟器状态机库：把终端应用的字节流解析成屏幕状态，实现
DEC VT100–VT520 兼容的转义序列、屏幕/滚动缓冲、字符集、鼠标与键盘编码，不含 UI。
本次适配的是官方仓库 **kmscon/libtsm** 的 `v4.6.0` tag。

- 上游（官方）：https://github.com/kmscon/libtsm（tag `v4.6.0` = commit `e1e4d296f0963d1641456f1f778f0ac090429a3e`，2026-06-22 发布）
- 源码：官方仓库 tag 归档 `libtsm-4.6.0.tar.gz`（顶层目录 `libtsm-4.6.0`，155191 字节）
- SHA-256：`5c64411fd558aa004170af9a04c12c3095e593b9e38a2fec7da1dafa7793dbb7`
- 许可证：MIT
- 构建系统：meson（>= 1.1），上游 `project('libtsm', 'c', version: '4.6.0', c_std=gnu99)`
- 适配路径：**路径 A（基础适配）**——零补丁、零新知识草稿，复用 4.3.0 已验证模式
- 与 4.3.0 的差异（上游 v4.5.0...v4.6.0）：新增 `tsm_screen_draw2()` 简化绘制接口、
  SGR 2 `dim` 支持、CSI 默认参数修复、ctrl+shift+方向键修复、滚轮上下按钮映射修正；
  构建系统与测试框架无变化（仍是 7 套件 `check`，用例数 37 → 44）

## 构建方案

- **目标产物**：`lib/libtsm.so.4.6.0` + `lib/libtsm.so.4`（SONAME）+ `lib/libtsm.so`
  符号链接、`include/libtsm.h`、`lib/pkgconfig/libtsm.pc`、`licenses/COPYING`。
- **共享库限定**：上游 `src/tsm/meson.build` 用 `shared_library('tsm', ...)` 无条件
  产出共享库（`version: 4.6.0` / `soversion: 4`，并带 `src/tsm/libtsm.sym` 版本脚本，
  导出符号版本 `LIBTSM_3` / `LIBTSM_4`），没有静态变体。因此配方
  `options = {"shared": [True, False]}` 且 `default_options = {"shared": True}`，
  在 `validate()` / `generate()` 中对 `shared=False` 明确抛
  `ConanInvalidConfiguration`。
- **meson 选项**：`-Dtests=true -Dgtktsm=false -Dextra_debug=false`。
  `tests` 保持开启：上游 `test/meson.build` 无条件 `dependency('check')`，而 check
  经 `test_requires("check/0.15.2")+PkgConfigDeps` 供给，只进测试链、不进包依赖链。
  `gtktsm` / `extra_debug` 上游默认即为关闭，这里显式钉住以防上游默认值漂移。
- **工具链**：`MesonToolchain` + `Meson`，`--prefix=/` 由 conan 注入，安装走
  `meson install --destdir <package_folder>`。`tc.binaries["ar"]` 钉为 `llvm-ar`
  的绝对路径（CI worker PATH 较短时 meson 按裸名 `llvm-ar` 探测会失败）。
  上游默认 `werror=true` / `warning_level=1` 未改动。
- **依赖**：无必选依赖。`xkbcommon` 是上游可选依赖（`dependency('xkbcommon',
  required: false)`，只用于 keysym 翻译），ohpcd 未发布该包，于是走上游自带的
  `external/xkbcommon/xkbcommon-keysyms.h` 回退路径（上游明确支持），**零补丁**。
- **补丁**：无（`conandata.yml` 为 `patches: {}`）。

## 上游测试审计与计数

源码级审计（无需运行，直接数源码）：

```sh
# START_TEST 块数 = check 注册用例数
grep -c '^START_TEST' test/*.c
# test_htable.c:2 test_screen.c:4 test_selection.c:13 test_symbol.c:2
# test_valgrind.c:1 test_vte_mouse.c:7 test_vte.c:15 → 合计 44
grep -c '^test(' test/meson.build  # → 7 套件
```

| 套件 | 源文件 | 用例数（`Checks:`） |
| --- | --- | --- |
| htable | `test/test_htable.c` | 2 |
| screen | `test/test_screen.c` | 4 |
| selection | `test/test_selection.c` | 13 |
| symbol | `test/test_symbol.c` | 2 |
| valgrind | `test/test_valgrind.c` | 1 |
| vte_mouse | `test/test_vte_mouse.c` | 7 |
| vte | `test/test_vte.c` | 15 |
| **合计** | 7 套件 | **44** |

相对 4.3.0（37 用例）：selection 12→13（+1）、vte 9→15（+6），对应上游
CSI 默认参数、ctrl+shift+方向键与滚轮映射等修复的新增覆盖。统计单位与 4.3.0
一致：`check` 注册用例（`TEST(...)` → `tcase_add_test`），即各套件自报的
`100%: Checks: N, Failures: 0, Errors: 0` 中的 N。

设备原生运行方式（与 4.3.0 同口径，待真机 evidence 轮实测回填）：

```sh
cd <src>/libtsm-4.6.0
meson setup build-native
meson compile -C build-native
TEMP=<任务可写目录> meson test -C build-native --print-errorlogs
# 预期 Ok: 7 Fail: 0；逐套件 44 用例全过
```

关于 `valgrind` 套件：与 4.3.0 同理，`test/test_valgrind.c` 只是分配 0x100 字节
并断言非 NULL 的哑用例，上游 CI 跑的就是普通 `meson test`（未调用 valgrind），
本次运行与之完全一致，不声称做过 valgrind 插桩。

### 测试框架临时文件：必须 `export TEMP=<可写目录>`

沿用 4.3.0 实测结论（知识 E571）：OHOS 设备 `/tmp` 只读，libcheck 探测顺序
`TEMP → P_tmpdir(="/tmp") → TMPDIR`，只设 `TMPDIR` 无效，必须设 `TEMP`。
直接用 ohpcd 发行包 `check/0.15.2` 即可，无需私有自建。

### 上游测试覆盖范围（如实声明）

上游 `src/tsm/meson.build` 的 `libtsm_dep = declare_dependency(...,
sources: libtsm_srcs)` 把库源码直接编进每个测试二进制，因此上游 7 套件验证的是
**源码树行为**，不覆盖交付的 `libtsm.so.4`；交付物另由 `test_package`
（真实链接包内 `.so` 的消费者，53 项断言）与 dlopen / 字节一致性补测覆盖。
未修改、未跳过、未删除任何上游测试或测试声明。

## 交付物验证（包内产物，待真机回填实测哈希）

```text
lib/libtsm.so -> libtsm.so.4 -> libtsm.so.4.6.0
include/libtsm.h
lib/pkgconfig/libtsm.pc      (prefix=/  Version: 4.6.0  Libs: -ltsm)
licenses/COPYING
```

- `readelf -d <pkg>/lib/libtsm.so.4.6.0`：`SONAME libtsm.so.4`，`NEEDED` 仅 `libc.so`。
- `sha256sum <builddir>/src/tsm/libtsm.so.4.6.0 <pkg>/lib/libtsm.so.4.6.0`
  两份预期逐字节一致（4.3.0 已实测模式：meson install 不重链，hnp clang 的
  `.codesign` 段完好；4.6.0 同工程结构，判据相同）。
- dlopen 探针（`RTLD_NOW`）对实体文件与 SONAME 符号链接均应加载成功并调用
  `tsm_screen_new` → 默认 `80x24`。
- **上游元数据残留（如实记录）**：包内 `lib/pkgconfig/libtsm.pc` 的 `URL:` 字段
  仍是 `https://github.com/Aetf/libtsm`——由上游 `src/tsm/meson.build` 的
  `pkg.generate(url: ...)` 硬编码，kmscon/libtsm 的 v4.6.0 同样如此。
  本适配为零补丁，故不改该字段；仅人读元数据，不影响链接/加载。

## test_package（消费者视角，53 项断言）

沿用 4.3.0 的 47 项（屏幕/VTE 构造与几何、resize、绘制回调取回文本、SGR
粗体/下划线/斜体/反显、16 色与 24 位真彩色、命名调色板、ED/CUP、宽字符
U+4E2D、滚动缓冲、选择复制、普通/DEC 应用模式键盘编码、`tsm_ucs4_*`、引用计数），
新增 6 项覆盖 4.6.0：

- SGR 2 `dim`：`\033[2mD` 后单元格 `attr.dim == 1`，`\033[0m` 后下一单元格
  `dim == 0`（2 项，不泄漏）；
- `tsm_screen_draw2()`：喂入 `\033[2J\033[HAB` 后返回非 NULL，且
  `cells[0].ch == 'A'`、`cells[1].ch == 'B'`、纯文本单元格 `attr2.u8 == 0`（4 项）。

**断言总数固定校验**（`EXPECTED_CHECKS = 53`），少于预期即判失败，避免空跑假绿。
`draw2` 分支的 if/else 两条路径都保持总数 53（NULL 时 3 项强制失败），总数稳定可审计。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
| --- | --- | --- | --- |
| 1 | 上游版本号跳跃（4.3.0 → 4.6.0，中间有 4.4.x/4.5.0）是否引入构建变化 | 需审计 | 对比 meson.build：构建选项、产物形态、依赖声明与 4.3.0 一致，仅新增源码与头文件 API，无构建系统变化，故配方直接沿用 4.3.0 模式，仅 bump 版本与 sha256 |
| 2 | 新增 `draw2`/`dim` 是否需要新依赖或补丁 | 否 | 纯头文件+源码新增，无新依赖；`dim` 是 `struct tsm_screen_attr` 新增位域，`draw2` 是新增导出函数，均随 `libtsm.so.4` 自然交付，零补丁 |
| 3 | 上游测试数 37→44，计数口径是否变化 | 否 | 仍是 `check` 的 `Checks: N`，`START_TEST` 块数同步增至 44，`meson test --list` 仍 7 套件；MANIFEST 按新数申报 |
| 4 | `/tmp` 只读导致 check 测试失败风险 | 同 4.3.0 | 运行前 `export TEMP=<可写目录>`，复用 E571 结论 |

## 依赖版本

- 编译/运行依赖：无（仅 libc）。
- 测试框架：`check/0.15.2`（ohpcd 发行二进制；仅用于设备原生上游测试，不进包依赖链）。
- 工具链：`clang 15`（`/data/service/hnp/bin/clang`）、meson、ninja、Conan 2.x（OHOS 适配版）、profile `ci/conan/profiles/ohos-aarch64`。

## 验证结果（待 HMBS 真机 evidence 轮回填实测数字）

```sh
# 1) 上游原生构建 + 测试（设备）
TEMP=<可写> meson test -C build-native --print-errorlogs
#    -> 待回填（审计预期 Ok: 7 Fail: 0，44 用例）

# 2) 干净 Conan 构建 + test_package（设备，真机预检）
conan create archives/l/libtsm/4.6.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
#    -> 待回填（预期 test_package: CHECKS: 53/53 passed / RESULT: PASS）

# 3) 交付物完整性
sha256sum <builddir>/src/tsm/libtsm.so.4.6.0 <pkg>/lib/libtsm.so.4.6.0
readelf -d <pkg>/lib/libtsm.so.4.6.0 | grep -E 'SONAME|NEEDED'
```

## 注意事项

- 上游测试是“源码级”测试：评估交付物质量时必须结合 `test_package` 与 dlopen
  结果一起看，不能把上游 44 个用例当作 `.so` 的验证。
- 设备的 `/tmp` 只读，任何 check/ctest 类测试运行前都要提供可写临时目录（本条用
  `TEMP`，勿只设 `TMPDIR`）。
- 上游 `werror=true` 保持开启；若将来上游代码在更新工具链下产生告警，优先按上游修复。
- 本版本为路径 A 基础适配，未产生新知识草稿；`TEMP` 结论复用 4.3.0 的 E571 草稿。
