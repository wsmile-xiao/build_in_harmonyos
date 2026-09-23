- **三方库名称**：libncurses
- **上游版本**：ncurses 6.6（上游正式版发布于 2025-12-30，patch date 20251230；Conan 版本号 `6.6_p20260516`）
- **上游仓库地址**：https://invisible-island.net/ncurses/
- **适配路径**：路径 A（基础适配）
- **使用知识库**：E007（`config.guess` 无法识别 HarmonyOS 系统）、E011/E129（HMDFS 上 `config.status` 的临时目录与权限）、E050/E079（HMDFS 不支持 `ln -s`，需以复制替代）

---

## 本包与既有 ncurses 归档的关系（必读）

本归档提供 **窄字符（8-bit）ABI** 的 ncurses 静态库。仓库中已存在的是宽字符版本：

| 归档 | ABI | 关键配置 |
|---|---|---|
| `archives/n/ncurses/6.6` | 宽字符 | `--enable-widec`，产物 `libncursesw.a` / `ncursesw6-config` |
| **`archives/l/libncurses/6.6_p20260516`（本 PR）** | **窄字符** | **`--disable-widec`，产物 `libncurses.a` / `ncurses6-config`** |

需要注意：ncurses 自 ABI 6 起**默认启用 widec**（`configure` 中 `cf_dft_widec=yes` 对 `cf_cv_abi_version=6` 生效），所以「不写 `--enable-widec`」并不等于窄字符构建。要得到 8-bit ABI 必须显式 `--disable-widec`；该开关同时决定库名后缀、`ncurses6-config` 脚本名与 pkg-config 模块名（`ncurses/form/menu/panel/ncurses++`）。这一结论已随本 PR 沉淀为知识草稿（见「补充说明」）。

版本号 `6.6_p20260516` 沿用适配任务给出的上游版本表示法；源码为上游 ncurses 6.6 正式发布包（configure 自报 patch date `20251230`）。

---

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | ncurses 6.6 不提供单元测试框架 |
| 集成测试 | 144 | 上游 `make -j1 check`：86 个 `test/programs` 程序入口全部构建 + 57 个头文件独立编译自检 + 1 个 `link_test` 全 API 链接完整性检查 |
| 其他测试 | 0 | 上游 `make check` 不运行交互式测试程序（上游自述 "The test-programs are interactive"），本适配不改变该行为，也不把这些程序谎报为已执行用例 |
| **合计** | **144** | |

> 清点依据：`ncurses-6.6/test/programs`（86 行）与 `make -j1 check` 的 `** testing <header>` 输出（57 行）逐行计数。

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 不变 | 上游无单元测试框架，未新增单元测试 |
| 集成测试 | 144 | 不变 | 上游 `make -j1 check` 在 `conan build()` 中全量执行，144/144 通过 |
| 鸿蒙特有测试 | 10 | 新增 | `test_package` 的 10 个消费者工作流，全部在 HarmonyOS 目标上编译、链接 packaged 静态库并运行；含 4 个 CMake 消费者、1 个 `ncurses6-config` 消费者、5 个 pkg-config 消费者，另有 4 项包级静态链接契约断言 |
| **合计** | **154** | **+10** | |

---

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改、删除或弱化任何上游测试断言（`0005` 仅修正非 wide 配置下 `link_test` 的生成守卫，被排除的 9 个扩展颜色 SP 入口在窄字符库中本就无实现）
- [ ] **是**，存在对上游测试用例的修改

> 补充说明：本 PR 的 5 个补丁均为可移植性补丁（Autotools 探测、静态链接、HMDFS 文件权限、平台三元组、非 wide 配置的链接完整性守卫），未修改、删除或弱化任何上游测试断言。其中 `0005` 只调整「非 wide 配置下 `link_test` 允许引用哪些入口点」——被排除的 9 个扩展颜色 SP 入口在窄字符配置下上游本就没有实现（见「补丁说明」）。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无测试用例，适配后补全了测试

> 说明：上游确实提供 `make -j1 check`（144 项编译期自检，本 PR 已全量执行并通过），但**没有单元测试框架，也没有任何"消费者视角"的集成测试**——`test/programs` 里的 86 个程序是交互式的，上游 `make check` 只编译不运行。下表"补全"指的是后一类缺失。
> - **补全的测试范围**：上游只有交互式 `test/programs` 程序（不执行）与编译期自检，既无单元测试也没有「消费者视角」的集成测试。适配后按本仓规范补全 `test_package` 消费者测试：10 个工作流 / 43 条断言，覆盖 Conan CMake config 目标、上游 CMake `FindCurses` 模块、`ncurses6-config`、5 个 pkg-config 模块（含 C++ 的 `ncurses++`），以及 HarmonyOS 平台静态链接契约。
> - **补全原因**：ncurses 在 HarmonyOS PC 上只能以静态库形式分发（共享库会劫持系统 shell 依赖的终端库），「产物确实是静态的、符号确实可用、元数据确实可重定位」这三件事必须由消费者测试而非上游编译通过来证明；同时需要一个只对鸿蒙平台成立的契约测试。
> - **新增测试文件清单**：
>   1. `test_package/CMakeLists.txt` — Conan CMake config 消费者 + 上游 `FindCurses` 模块消费者（并断言其解析结果落在 Conan 包内）
>   2. `test_package/src/test_curses_module.c` — 8-bit `chtype` 往返、`tputs` 回调、packaged terminfo、窗口刷新
>   3. `test_package/src/test_ncurses_components.c` — panel / menu / form 生命周期
>   4. `test_package/src/test_metadata.c` — `ncurses6-config` 与 pkg-config 静态链接消费者（`-Wl,-t` 校验只选中包内静态库）
>   5. `test_package/src/test_metadata_cpp.cpp` — `ncurses++` C++ 消费者
>   6. `test_package/src/test_ohos_platform.c` — **鸿蒙特有测试**：运行时确认平台为 HarmonyOS、`/proc/self/maps` 中无任何共享 curses/tinfo 对象、packaged terminfo 驱动真实窗口刷新
>   7. `test_package/conanfile.py` — 元数据接口验证 + 包级鸿蒙静态链接契约（无 `.so`、5 个静态库齐备、消费者二进制为 AArch64 且无 curses/tinfo 的 `DT_NEEDED`）

---

## 验证结果

### 编译验证

- 编译器：`clang 15.0.4`（`/data/service/hnp/bin/clang`，Target: `aarch64-unknown-linux-ohos`）
- 编译状态：**通过**
- 构建系统：Autotools（configure + make，`make -j1 SHELL=/bin/sh`）
- 配置选项：`--disable-shared --enable-static --without-shared --with-normal --without-debug --with-trace --without-ada --without-manpages --disable-widec --enable-overwrite --enable-pc-files --with-pkg-config-libdir=/lib/pkgconfig`
- 平台识别：`aarch64-unknown-linux-ohos`（原生构建，非交叉）
- 本地 CI 模拟：`ci/conan/setup.sh` + `ci/conan/build_and_test.sh archives/l/libncurses/6.6_p20260516`（与平台 CI 同源脚本）通过；L0/L1/L1e/L2/L4/L5 全 pass、`Success: 1 Failed: 0 (100%)`，W3 结果与日志完整性哈希记录在工作区的 `.ci-result.json`（`log_sha256=f9b674334d357bcf1c5ca036d29b7a05e6a52b5e7a30adc6eaebc108fa8b35ab`；该文件与 `reports/*.log` 按仓库惯例被 .gitignore 排除、不随 PR 提交，可用 `ci/conan/build_and_test.sh` 复跑复核）
- 构建步骤日志：OHOS 侧 `configure`/`make`/`make check`/`make install` 四步的输出分别绑定到私有构建目录下的 `logs/*.log` 并回显进 conan 输出，避免 `ConanFile.run()` 直接把进程输出流交给子进程时 clang 在首个编译单元静默失败（详见「补充说明」）

### 产物验证

| 检查项 | 状态 | 详情 |
|--------|------|------|
| 编译无错误 | 通过 | `make -j1` 与 `make -j1 check` 退出码均为 0 |
| 产物存在性 | 通过 | `libncurses.a` `libform.a` `libmenu.a` `libpanel.a` `libncurses++.a`；`bin/` 下 11 个工具（`tic` `infocmp` `toe` `tput` `tset` `clear` `reset` `tabs` `captoinfo` `infotocap` `ncurses6-config`）；`include/` 18 个头文件；`share/terminfo` 上游 `tic` 报告 2897 条目、包内落盘 2872 个文件 |
| ELF 格式 | 通过 | 消费者二进制 `readelf -h` 为 AArch64（`aarch64-unknown-linux-ohos`） |
| 运行测试 | 通过 | 10 个消费者工作流全部在目标上运行成功；上游 `make -j1 check` 144/144 |
| 动态依赖 | 通过 | 消费者二进制 `readelf -d` 无任何 `libncurses*`/`libtinfo*`/`libform*`/`libmenu*`/`libpanel*` 的 `DT_NEEDED`；包内 `.so` 数量为 0 |
| 元数据可重定位 | 通过 | `ncurses6-config --prefix/--includedir/--libdir/--terminfo` 全部指向包内；5 个 `.pc` 的 `prefix` 重写为 `${pcfiledir}/../..`，`-L/-I` 重写为 `${libdir}`/`${includedir}` |

### 补丁说明

| 补丁 | 类型 | 说明 |
|------|------|------|
| `0001-detect-compound-expr.patch` | portability | 当平台 `expr` 无法求值 Autoconf 复合表达式时拒绝它，改用构建环境的 GNU 实现 |
| `0002-lib-mvcur-static-link.patch` | portability | 允许上游 `lib_mvcur` 测试在静态链接时覆盖其故意设置的桩符号（`--allow-multiple-definition`） |
| `0003-install-headers-shell.patch` | portability | 生成的头部安装脚本在 HMDFS 上没有执行位，改为通过已配置的 shell 调用 |
| `0004-config-guess.patch` | portability | 让上游平台探测在不需要 `--build/--host/--target` 的情况下返回 `aarch64-unknown-linux-ohos` |
| `0005-link-test-ext-colors.patch` | portability | **本归档新增**：修复非 wide 配置下上游链接完整性测试的守卫缺失 |

`0005` 详细说明：`ncurses/curses.priv.h` 把 `USE_EXT_SP_FUNC_SUPPORT` 定义为 `(NCURSES_SP_FUNCS && NCURSES_EXT_FUNCS)`，但扩展颜色入口（`init_extended_color`、`init_extended_pair`、`extended_color_content`、`extended_pair_content`、`extended_slk_color`、`find_pair`、`free_pair`、`alloc_pair`、`reset_color_pairs`）只在 `NCURSES_EXT_COLORS` 打开时才有实现，而上游把该宏限制在 wide 库（configure 明确告警 “applies only to wide-character library”）。因此在窄字符配置下，由 `MKlib_gen.sh` 生成的 `link_test.c` 会引用 9 个库中不存在的 `_sp` 符号，`make check` 必然停在 `ncurses/Makefile: link_test`。补丁给这 9 条声明换上独立 tag（`EXT_COLOR_SP_FUNC`）并补上 `NCURSES_EXT_COLORS` 感知的守卫，**只排除本就未实现的入口**，其余入口的链接完整性覆盖不变；没有使用 `-Wl,--unresolved-symbols=ignore-all` 之类整体关闭检查的做法。

### 依赖

- Conan 依赖：无（`requires`/`tool_requires` 均为空）
- 构建工具依赖：`clang`/`clang++`、`make`、`sed`、`rm`、`expr`、`gawk`（配方在 `build()` 中显式校验）与 GNU bash（`CONFIG_SHELL`）

### 测试结论

- 总体评价：**通过**。上游 `make -j1 check` 全量 144/144 通过；新增 10 个 HarmonyOS 消费者工作流、43/43 断言通过；包内无共享库、元数据可重定位、消费者二进制静态链接且目标为 AArch64。
- 上游测试用例通过率：**144/144（100%）**
- 新增测试用例通过率：**43/43（100%）**

---

## 补充说明

1. **静态-only 的取舍**：ncurses 共享库在 HarmonyOS 上会劫持系统终端库并可能导致 shell 崩溃，因此配方在 `configure()` 中直接拒绝 `shared=True`，产物只含静态库。这正是本包存在的意义：需要 8-bit ABI 的下游可以用 `libncurses.a`，而不必引入 wide 共享库。
2. **构建步骤输出绑定日志（本轮实测踩坑）**：`ConanFile.run()` 直接把 recipe 进程的输出流交给子进程时，本地 worker 上 clang 在**首个编译单元**（`make -j1 make_hash`）失败且**不输出任何诊断行**，make 只报 `Error 1`；同一条命令在 shell 中执行正常，且**把输出重定向到文件后经同一个 `run()` 调用也正常**（用探针配方在同一已配置构建目录上逐项对照 5 种调用方式确认）。因此 `_build_ohos()` 统一把四步输出绑定到 `logs/<step>.log`，失败时回显日志尾部并抛出带日志路径的异常。这同时解决了"静默失败无从诊断"的问题。
3. **包内不落符号链接**：上游安装会在 `lib/` 下建立 `libcurses.a -> libncurses.a` 别名；HMDFS 无法承载符号链接（E050/E079），复制进 Conan 包时按内容物化为真实文件（`libcurses.a` 实为 `libncurses.a` 的副本；上游 `make install` 日志原文为 `linking libcurses.a to libncurses.a`）。包内 `lib/` 只有 5 个静态库 + `libcurses.a` 副本 + `pkgconfig/`，termcap/terminfo 消费者应使用包内 `share/terminfo`。
4. **知识沉淀**：本 PR 附两份草稿——`knowledge/drafts/DRAFT-libncurses-6.6-narrow-abi-link-test.{kv,md}`（ABI 6 默认 widec + `--disable-widec` + 非 wide 配置 link_test 守卫缺失）与 `knowledge/drafts/DRAFT-libncurses-6.6-conan-run-log-bound-steps.{kv,md}`（conan `run()` 输出流继承导致 clang 静默失败及解法）。正式条目编号由主编审核后分配。
5. **已知限制**：本包的窄字符 API 不提供扩展颜色（`NCURSES_EXT_COLORS`）——这是上游对非 wide 库的限制，不是适配问题；需要扩展颜色的下游应使用宽字符包（`archives/n/ncurses/6.6`）。
6. **仓库既有脏状态**：工作树中 `archives/l/libXext/README.md`、`archives/l/libXext/manifest.yaml` 显示为 modified 属于本机 `core.ignorecase` 与本仓 `archives/l/libXext`、`archives/l/libxext` 并存的既有现象，与本 PR 无关，未纳入提交。
