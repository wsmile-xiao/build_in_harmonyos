# sc 7.16-1.1.3 适配笔记

任务：积分赛。为 sc（Spreadsheet Calculator，curses 终端电子表格）准备 HarmonyOS PC 适配。
上游为 `n-t-roff/sc`（James Gosling 原创、Chuck Martin 等维护的 7.16 分支），
产物为 CLI 工具组 `sc` + `psc` + `scqref` + `xsc`（application，无库产物；
软件级 `archives/s/sc/commands.json` 已声明 type=tool）。

## 上游形态

- **版本锚点**：上游 tag `7.16_1.1.3` → commit `77c8e5879bc364bcc6f34711fd187cf002ba827d`
 （GitHub API 实核；另有 `7.16_1.1.4`、`7.16_1.2.0` 等更新 tag，本任务按任务卡锁定 `7.16_1.1.3`）。
  conan 版本 `7.16-1.1.3` 中的 `-` 为任务卡目录命名，上游 tag 对应位置为 `_`。
- 源 tarball（GitHub tag 归档，按需生成）：
  `https://github.com/n-t-roff/sc/archive/refs/tags/7.16_1.1.3.tar.gz`
  `sha256=a734a399967f6a74772e9f169614b803d29c856b04fe289f965ab919feb7c625`
  （224811 字节，本机下载实测；CI 会对 github.com 自动追加镜像 fallback，
  故配方中只保留官方原始 URL）。
- **构建系统：手写 `configure`（POSIX sh）+ `Makefile.in`**，非 autotools/cmake/meson。
  `configure` 探测 make/VPATH/ncurses 系列/curses 扩展函数，生成 `Makefile` + `compat.h`；
  `make all` 构建 `sc`、`psc`、`scqref`、`xsc` 及 man 页；`make install` 以
  `prefix` 派生 `EXDIR/LIBDIR/MANDIR`。`gram.y` 需 `$(YACC) -d`（配方传入 btyacc 绝对路径）。
- 上游测试：**无**。源码树无 `tests/`、`test/` 目录，`Makefile.in` 无 `check/test`
  目标，无 ctest/gtest/pytest 注册；唯一数据文件为 `tutorial.sc` 示例。
  详见 `test_package/MANIFEST.yml` 的 `upstream_test_audit`。

## 依赖

| 依赖 | 在档 | 处置 |
|---|---|---|
| ncurses/6.6（curses 运行时，configure 优先探测 ncursesw） | 有（archives/n/ncurses/6.6） | `requires`，静态宽字符构建；build() 以 CPPFLAGS/LDFLAGS 指向其 include/lib |
| YACC（gram.y → gram.c） | 不需要（零依赖） | 预生成 `pregenerated/gram.c`+`pregenerated/y.tab.h`（bison 3.8.2 `-y -d`，点命名与 Makefile 一致），build() 装入源码树后 make 永不触发 YACC 规则 |

## OHOS 适配要点

- R32：`validate()` 限 `Linux/OHOS`。
- R33：编译器从 `tools.build:compiler_executables`（dict conf）取 `c`，不读 `$CC` 裸变量；
  `CC`/`YACC` 显式传入 configure/make。
- R9：`make -j1`。
- R38：纯 CLI（`package_type="application"`，只暴露 `bindirs=["bin"]`），
  软件级 `commands.json` 声明 `sc/psc/scqref/xsc`。
- `package()` 内 `PATH` 前置 `/system/bin`：toybox `install` 仅在此目录，
  与 sc-im 同族问题，worker 上幂等。
- 首轮零补丁：未引入 `__OHOS__` 平台宏；若真机预检暴露移植问题再按
  `refresh-patch --auto` 规范编号补丁。

## 构建与验证

```bash
conan create archives/s/sc/7.16-1.1.3 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

配方 `build()` 同款：`sh ./configure` → 装入预生成 `gram.c`/`y.tab.h`
（touch 新于 gram.y，使 make 的 `gram.c: gram.y` YACC 规则永不触发）→
`make -j1 CC=<可用编译器> prefix=...`（不再传 YACC）→
`./psc -v` 烟囱 → 发射 `HMBS_UPSTREAM_TEST_RESULT(status=no_tests)`；
`make install prefix=...` 落盘 `bin/sc bin/psc bin/scqref bin/xsc`、
`share/sc/tutorial.sc`、`share/man/man1/*`、`licenses/LICENSE`。

`test_package` 消费者断言 6 项（见 test_package/test.sh 与 MANIFEST.yml）：
`psc -v` 版本锚点、psc 文本转表格、sc 非交互表格计算（官方 `sc -v -P %` 管道求值后断言 `let C0 = 30` 且输出非空；直接 stdout 重定向只写未求值表达式 `let C0 = A0+B0`，grep 30 永不命中）、
scqref 可执行、xsc 脚本存在、安装树完整性。每项失败均有明确输出，
成功发射 `HMBS_TEST_PACKAGE_RESULT(discovered=6)`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|---|---|---|
| 1 | Windows 检出 `upstream/main` 报 `invalid path 'archives/g/gama/...patch??'` | 上游存在文件名含回车的文件，Windows 非法 | `core.protectNTFS=false` + sparse 排除该文件后 reset，本任务无关文件，保持原样 |
| 2 | Windows 同时存在 `archives/l/libXext` 与 `archives/l/libxext`，大小写不敏感冲突 | 上游同时保留大小写仅差别的目录 | 本地 `git status` 对该两文件恒脏，属环境现象；本 PR 不触碰该目录，真机/Linux 侧正常 |
| 3 | sc 无 `--version`，冒烟测试无锚点 | 上游 `sc -v` 为空操作，版本在 `rev[]` 中 | 用 `psc -v`（打印 `7.16_1.1.3` 到 stderr 且 rc=0）作版本锚点，sc 本体用非交互表格输出验证 |
| 4 | 真机预检 compile 阶段 `m4/1.4.19 configure[139]: /data/service/hnp/bin/bash: inaccessible or not found` | sc 经 `tool_requires("bison/3.8.2")` 拉起 conancenter bison→m4 源码构建；conancenter m4 配方无条件重执行 profile `[buildenv]` 硬编码的 `CONFIG_SHELL=/data/service/hnp/bin/bash`，在缺该路径的预检机上直接失败 | 删 `tool_requires`，复用 boxes/2.3.1 已验证模式：经 PATH 探测设备自带 `bison/byacc/yacc`（profile 已把 `/data/service/hnp/bin` 前置到 PATH），`YACC` 动态传入 make；`test_package` 的 shell 选择与 `test.sh` shebang 同步改为存在性探测 + `#!/bin/sh`（脚本仅 POSIX 语法） |
| 5 | 真机预检 compile 阶段 `Invalid configuration: sc needs a YACC generator ... none found`（2026-10-05） | #4 的 PATH 探测假设错误：该预检机 PATH（含 `/data/service/hnp/bin`）中 `bison/byacc/yacc` 三者皆无；且上游归档经核查只带 `gram.y`、无预生成 `gram.c`，`gram.c: gram.y` 规则必须执行 `$(YACC) -d`，无法跳过 | 改 `tool_requires("btyacc/3.0")`（在档纯 Makefile、无 m4/autotools/bash 硬编码，真机可从源码构建）；`build()` 优先用其 `bin/btyacc` 绝对路径作 `YACC`（Makefile 自带 `-d`，btyacc 直接输出 `y.tab.c/y.tab.h`；`gram.y` 实核仅含 `%union/%type/%token/%left/%right/%nonassoc` 纯 POSIX 文法、无 bison 扩展，兼容），PATH 探测仅保留作本地开发回退 |
| 6 | 真机预检 compile 阶段 `btyacc/3.0: CMake Error at CMakeLists.txt:1 ... Compatibility with CMake < 3.5 has been removed`（2026-10-08，cmake 4.4.3） | `tool_requires("btyacc/3.0")` 解析到 conancenter 的 CMake 版 btyacc（recipe revision 202124e7...），其 `cmake_minimum_required(<3.5)` 已被 CMake 4.x 移除支持；在档 btyacc/3.0（纯 Makefile）尚未发布到制品仓，`_index.yaml` 无条目，预检/CI 无法命中，只能回退到 conancenter；且单 PR 只允许一个库，不能在本 PR 顺带发布 btyacc | 删 `tool_requires`，配方 build() 内自举私用 btyacc（该方案在 2026-10-08 第二轮预检中失败，见 #7，不再采用） |
| 7 | 真机预检 compile 阶段私用 btyacc 构建 `make: /data/service/hnp/bin/clang: No such file or directory` Error 127（2026-10-08） | 上轮自举方案原样信任 `tools.build:compiler_executables` 的 `c` 值（该机为 `/data/service/hnp/bin/clang`），但该路径在本次预检机上根本不存在；真机工具链布局随机器而异 | 换策略：构建时不再需要任何 YACC（详见 #8） |
| 8 | 真机预检 compile 阶段 `Invalid configuration: sc: vendored parser missing: .../e/pregenerated/gram.c`（2026-10-08，exit 6） | 预生成文件已随配方导出（日志 `Copied 1 '.c' file: gram.c`），但导出布局被打平，`recipe_folder/pregenerated/<name>` 单一硬编码子路径在缓存中不存在 | 改查阅策略：不再假设导出子目录，`_find_vendored()` 按 basename 在 recipe/base_source 目录递归定位 gram.c 与 y.tab.h（找不到时附 recipe_folder 列表便于诊断；该方案在同日复检中失败，见 #9，不再采用） |
| 9 | 真机预检 compile 阶段同错 `vendored parser missing ... recipe_folder listing: ['conandata.yml','conanfile.py','conanmanifest.txt']`（2026-10-08，exit 6） | #8 根因假设错误：`exports_sources` 属性导出的文件根本不在 `recipe_folder`（缓存顶层仅 3 文件），而在 `export_sources_folder`；#8 只在 recipe/base_source 目录递归，自然找不到。属“路径假设错文件夹”而非“子路径打平” | 换实现路线（units-filter/4.2.1 已验证模式）：删 `exports_sources` 属性，改显式 `def export_sources(): copy(pregenerated/* → export_sources_folder)` 保目录结构；`build()` 优先 `copy(export_sources_folder/pregenerated/* → source_folder)` 直装，`_find_vendored()` 首查 export_sources_folder（含打平兼容与全树 walk），缺失诊断同时列三目录顶层与命中 |

## 知识沉淀

- 本轮无新错误模式草稿。若真机预检发现 curses 探测、yacc、install 路径等
  平台问题，将按规范新增 `knowledge/drafts/` 草稿。
