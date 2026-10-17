# libtsm 4.3.0 — OHOS 适配笔记

## 概述

libtsm（TSM）是终端模拟器状态机库：把终端应用的字节流解析成屏幕状态，实现
DEC VT100–VT520 兼容的转义序列、屏幕/滚动缓冲、字符集、鼠标与键盘编码，不含 UI。
本次适配的是官方仓库 **kmscon/libtsm**（libtsm 起源于 David Herrmann 的 kmscon 项目）。

- 上游（官方）：https://github.com/kmscon/libtsm（tag `v4.3.0` = commit `9d2817b727f61c09e19994b2431af716652f330b`）
- 源码：官方仓库 tag 归档 `libtsm-4.3.0.tar.gz`（顶层目录 `libtsm-4.3.0`）
- SHA-256：`7e858bece0df5b0cc61fbcc99275f6828bf54007a88fa8459a8447a7ee7e67ad`
  （设备多次独立下载 `cmp` 逐字节一致；官方 tag 归档与个人分支 Aetf/libtsm 的同名 tag
  归档也逐字节一致 —— 两者 `v4.3.0` 指向同一 commit，故采信官方源不改变任何构建输入）
- 来源说明：早期取源曾用 Aetf/libtsm，该仓库 README 自述 "This is a personal modified
  version. Upstream development has restarted from this fork at [official repository]
  (https://github.com/kmscon/libtsm)"，即个人分支明确指向 kmscon/libtsm 为官方上游；
  按 R39「不使用个人 fork 作源」改用官方 URL（sha256 不变）。
- 许可证：MIT
- 构建系统：meson（>= 1.1），上游 `project('libtsm', 'c', version: '4.3.0', c_std=gnu99)`
- 适配路径：**路径 B**（携带知识草稿 `knowledge/drafts/DRAFT-E571-*`）

## 构建方案

- **目标产物**：`lib/libtsm.so.4.3.0` + `lib/libtsm.so.4`（SONAME）+ `lib/libtsm.so`
  符号链接、`include/libtsm.h`、`lib/pkgconfig/libtsm.pc`、`licenses/COPYING`。
- **共享库限定**：上游 `src/tsm/meson.build` 用 `shared_library('tsm', ...)` 无条件
  产出共享库（`version: 4.3.0` / `soversion: 4`，并带 `src/tsm/libtsm.sym` 版本脚本，
  导出符号版本 `LIBTSM_3` / `LIBTSM_4`），没有静态变体。因此配方
  `options = {"shared": [True, False]}` 且 `default_options = {"shared": True}`，
  在 `validate()` / `generate()` 中对 `shared=False` 明确抛
  `ConanInvalidConfiguration` —— 不让声明的选项与实际产物形态不一致（不静默产出 `.so`）。
- **meson 选项**：`-Dtests=false -Dgtktsm=false -Dextra_debug=false`。
  `tests` 必须关闭：上游 `test/meson.build` 无条件 `dependency('check')`，而 check
  只是测试框架，不能进入包的依赖链（与 coeurl 0.3.2 的处理口径一致）。
  `gtktsm` / `extra_debug` 上游默认即为关闭，这里显式钉住以防上游默认值漂移。
- **工具链**：`MesonToolchain` + `Meson`，`--prefix=/` 由 conan 注入，安装走
  `meson install --destdir <package_folder>`，因此包内是标准 `lib/`、`include/` 布局。
  `tc.binaries["ar"]` 钉为 `llvm-ar` 的绝对路径（CI worker PATH 较短时 meson 按裸名
  `llvm-ar` 探测会失败，报 `Unknown linker(s): [['llvm-ar']]`）。
  上游默认 `werror=true` / `warning_level=1` 未改动，clang 15 交叉编译零告警。
- **依赖**：无必选依赖。`xkbcommon` 是上游可选依赖（`dependency('xkbcommon',
  required: false)`，只用于 keysym 翻译），ohpcd 未发布该包，于是走上游自带的
  `external/xkbcommon/xkbcommon-keysyms.h` 回退路径（上游明确支持），**零补丁**。
  交付物 `readelf -d` 实测 `DT_NEEDED` 只有 `libc.so`。
- **补丁**：无（`conandata.yml` 为 `patches: {}`，配方零补丁、不交付 `patches/` 目录）。

## 上游测试执行与真实计数

设备原生（非交叉）构建与测试：

```sh
cd <src>/libtsm-4.3.0
PKG_CONFIG_PATH=<conan PkgConfigDeps 目录> meson setup build-native
PKG_CONFIG_PATH=<conan PkgConfigDeps 目录> meson compile -C build-native -j 2
TEMP=<任务可写目录> meson test -C build-native --print-errorlogs
```

结果：`Ok: 7  Fail: 0`（7 个套件全部 OK）；逐套件 `check` 自报用例数

| 套件 | 源文件 | 用例数（`Checks:`） |
| --- | --- | --- |
| htable | `test/test_htable.c` | 2 |
| screen | `test/test_screen.c` | 4 |
| selection | `test/test_selection.c` | 12 |
| symbol | `test/test_symbol.c` | 2 |
| valgrind | `test/test_valgrind.c` | 1 |
| vte_mouse | `test/test_vte_mouse.c` | 7 |
| vte | `test/test_vte.c` | 9 |
| **合计** | 7 套件 | **37（37 pass / 0 fail / 0 skip / 0 not_run）** |

统计单位 = `check` 注册用例（`TEST(...)` → `tcase_add_test`），即各套件自报的
`100%: Checks: N, Failures: 0, Errors: 0` 中的 N。取数命令：

```sh
cd build-native/test
for t in test_htable test_screen test_selection test_symbol test_valgrind test_vte_mouse test_vte; do
  TEMP=<任务可写目录> ./$t
done | grep -o 'Checks: [0-9]*' | awk '{s+=$2} END {print s}'      # -> 37
```

套件清单（审方数法对齐）：`meson test -C build-native --list` → 7 条。
**三种口径互相印证**，避免与审方的独立数法不一致：框架自报用例数 37、
源码级 `START_TEST` 块数 37（`grep -c '^START_TEST' test/*.c` 求和 = 2+4+12+2+1+7+9）、
meson 注册套件数 7（`grep -c '^test(' test/meson.build`）。

关于 `valgrind` 套件：`test/test_valgrind.c` 的注释写明它是"故意泄漏内存用于验证
valgrind memcheck"的哑用例，函数体只有 `malloc(0x100)` + 断言非 NULL，**没有任何断言以
"运行在 valgrind 下"为条件**。上游 CI 跑的就是普通 `meson test`（其 workflow 中并未调用
valgrind），本次设备运行与之完全一致，不声称做过 valgrind 插桩。

### 测试框架临时文件：必须 `export TEMP=<可写目录>`

OHOS 设备 `/tmp` 是 root 属主只读目录，libcheck 0.15.x 的 `open_tmp_file()`
（`src/check_msg.c:317`）按 `TEMP → P_tmpdir → TMPDIR → "."` 探测候选目录，musl 下
`P_tmpdir` 固定为 `/tmp` 且排在 `TMPDIR` 之前。因此：

- 只设 `TMPDIR` **无效**（每个用例 exit status 2，`0%: Checks: 0`）；
- 设 `TEMP=<可写目录>` **有效**，且 check 是探测顺序中的第一项候选，所以
  **不需要私有自建 libcheck**：直接用 ohpcd 发行包 `check/0.15.2` 即可跑通全部用例。

设备 A/B 反证（探针链接发行包 `check/0.15.2`，`package_id
21b17f8b2bc0e9511e276e3d57a23893067cefe5`，未改任何源码）：

```text
默认环境                → check_msg.c:317: Unable to create temporary file ...  rc=2
TMPDIR=<可写目录>       → check_msg.c:317: Unable to create temporary file ...  rc=2
TEMP=<可写目录>         → 100%: Checks: 1, Failures: 0, Errors: 0               rc=0
```

该结论已沉淀为知识草稿 `knowledge/drafts/DRAFT-E571-ohos-libcheck-temp-env-first-probe.{kv,md}`
（对既有草稿 DRAFT-E547 的"私有重建并调整探测顺序"给出实测反证），并用于关联 Issue。
错误日志经 `ohc-run.py engine`（默认 `--top-n 5`）命中的是 E002（`/tmp` 只读时设
`TMPDIR`），该条建议在本场景**不生效**，已在草稿中写明区分依据。复现命令：

```sh
python3 scripts/ohc-run.py engine --file <含 check_msg.c:317 的日志> --project-dir <repo>
# -> 🎯 命中: E002 （默认参数，无需 --top-n）
```

### 上游测试覆盖范围（如实声明）

上游 `src/tsm/meson.build` 的 `libtsm_dep = declare_dependency(..., sources:
libtsm_srcs)` 把库源码直接编进每个测试二进制（`readelf -d test/test_vte` 中没有
`DT_NEEDED: libtsm.so*`，`nm` 可见本地定义的多份 `tsm_screen_new`）。因此：

- 上游 7 套件验证的是**源码树行为**，不覆盖交付的 `libtsm.so.4`；
- 交付物另由 `test_package`（真实链接包内 `.so` 的消费者，47 项断言）与设备端
  dlopen / 字节一致性补测覆盖（见下）；
- 未修改、未跳过、未删除任何上游测试或测试声明。

## 交付物验证（包内产物）

```text
lib/libtsm.so -> libtsm.so.4 -> libtsm.so.4.3.0
include/libtsm.h
lib/pkgconfig/libtsm.pc      (prefix=/  Version: 4.3.0  Libs: -ltsm)
licenses/COPYING
```

- `readelf -d <pkg>/lib/libtsm.so.4.3.0`：`SONAME libtsm.so.4`，`NEEDED libc.so`（无其它运行时依赖）。
- `meson install` 未重链共享库：`sha256sum <builddir>/src/tsm/libtsm.so.4.3.0
  <pkg>/lib/libtsm.so.4.3.0` 两份**逐字节一致**（实测哈希值见 PR 正文），hnp clang 的
  `.codesign` 段（`readelf -S` 的 `[38] .codesign`）因此完好。这与"`meson install` 改写 `.dynstr`
  破坏 `.codesign` 导致加载失败"的已知模式相反，判据就是两份 sha256 对比
  （conan-verify L5 未实现该对比，本次人工补测）。
- dlopen 探针（`RTLD_NOW`）对实体文件与 SONAME 符号链接均加载成功并调用
  `tsm_screen_new` → 默认 `80x24`，证明签名未坏、可被运行时加载器接受。
- **已知的上游元数据残留（如实记录）**：包内 `lib/pkgconfig/libtsm.pc` 的
  `URL:` 字段仍是 `https://github.com/Aetf/libtsm` —— 该字段由上游
  `src/tsm/meson.build` 的 `pkg.generate(url: ...)` **硬编码**，官方仓库
  kmscon/libtsm 的 v4.3.0 源码里同样如此。本适配为零补丁，不修改上游源码文件，
  故不为此改 URL；该字段仅是人读元数据，不影响链接、加载或任何构建行为
  （消费者用 `-ltsm`，package_info 不读 `.pc` 的 URL）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
| --- | --- | --- | --- |
| 1 | 设备原生 `meson test` 每个用例 `exit status 2`，报 `check_msg.c:317: Unable to create temporary file for communication` | /tmp 只读；libcheck 探测顺序 `TEMP → P_tmpdir(="/tmp") → TMPDIR`，只设 TMPDIR 不生效 | 运行测试前 `export TEMP=<任务可写目录>`；无需自建 check（知识草稿 E571） |
| 2 | 上游 `dependency('xkbcommon', required: false)` 在 ohpcd 找不到 | ohpcd 未发布 xkbcommon | 使用上游自带的 `external/xkbcommon/xkbcommon-keysyms.h` 回退（上游明确支持的路径），不需要补丁，也不把 xkbcommon 带进依赖链 |
| 3 | 配方的 `shared` 选项无法真正表达上游形态 | 上游只声明 `shared_library('tsm')`，无静态变体 | `default_options={"shared": True}`，`shared=False` 时抛 `ConanInvalidConfiguration`（诚实失败，不静默产出 `.so`） |
| 4 | 上游测试不覆盖交付物 | `declare_dependency(sources:)` 把库源码编进测试二进制 | 在 `test_package` 写真实链接包内 `.so` 的消费者（47 项断言），并补 dlopen / sha256 人工验证；在本文件与 `MANIFEST.yml` 如实声明口径 |
| 5 | CI worker PATH 较短时 meson 归档器探测失败风险 | meson 对 clang 按裸名 `llvm-ar` 走 PATH | `tc.binaries["ar"]` 钉 `llvm-ar` 绝对路径（coeurl 已实测模式） |

## 依赖版本

- 编译/运行依赖：无（仅 libc）。
- 测试框架：`check/0.15.2`（ohpcd 发行二进制；仅用于设备原生上游测试，不进包依赖链，
  不写入 `conanfile.py` 的 `requirements()`）。
- 工具链：`clang 15.0.4`（`/data/service/hnp/bin/clang`，target
  `aarch64-unknown-linux-ohos`）、`meson 1.12.0`、`ninja 1.13.1`、`cmake 4.1.2`、
  Conan 2.29.1（OHOS 适配版）、profile `ci/conan/profiles/ohos-aarch64`。

## 验证结果

```sh
# 1) 上游原生构建 + 测试（设备，见上）
TEMP=<可写> meson test -C build-native --print-errorlogs
#    -> Ok: 7  Fail: 0 ；逐套件 37 用例全过

# 2) 干净 Conan 构建 + test_package
#    注意：reports/conan-create.log 会被 finish 内嵌重跑以「缓存命中轮」覆盖
#    （缓存轮无 Calling build()/Meson compile 段）；干净轮在跑完 conan-verify
#    后立即留存副本，本任务副本见 PR 正文与 reports/conan-verify-supplement.md §6
conan create archives/l/libtsm/4.3.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
#    -> libtsm/4.3.0: Package '...' built ；test_package: CHECKS: 47/47 passed / RESULT: PASS

# 3) 交付物完整性
sha256sum <builddir>/src/tsm/libtsm.so.4.3.0 <pkg>/lib/libtsm.so.4.3.0   # 两份一致
readelf -d <pkg>/lib/libtsm.so.4.3.0 | grep -E 'SONAME|NEEDED'          # libtsm.so.4 / libc.so
./dlopen_libtsm <pkg>/lib/libtsm.so.4.3.0                               # DLOPEN-OK default=80x24
```

`test_package`（消费者视角）47 项断言覆盖：屏幕/VTE 构造与几何、resize、绘制回调取回
文本、SGR 粗体/下划线/斜体/反显、16 色与 24 位真彩色、命名调色板（4.x 分支特性）、
ED/CUP、宽字符（U+4E2D 宽度 2）、滚动缓冲计数、选择复制 UTF-8 文本、普通模式与 DEC
光标键应用模式的键盘编码、`tsm_ucs4_*` 助手、引用计数。**断言总数固定校验**
（`EXPECTED_CHECKS = 47`），少于预期即判失败，避免空跑假绿。

## 注意事项

- 上游 libtsm 的测试二进制是"源码级"测试：评估交付物质量时必须结合 `test_package`
  与 dlopen 结果一起看，不能把上游 37 个用例当作 `.so` 的验证。
- 设备的 `/tmp` 只读，任何 check/ctest 类测试运行前都要提供可写临时目录（本条用
  `TEMP`，勿只设 `TMPDIR`）。
- 上游 `werror=true` 保持开启；若将来上游代码在更新工具链下产生告警，优先按上游修复，
  不要在本仓库关闭 `werror`。
