# nsnake 3.0.1.1 适配笔记

### 对话 #1
在 3.0.1 复核结论的基础上做打包完整性修复（R37 递增 3.0.1.1），完成 conan create /
conan-verify / verify-build / finish(W2+W3) / 功能用例 16 项全通过。

## 版本与动机（R37 递增）

- 上游源码不变：仍是 tag `v3.0.1`（commit `2d9ee72c`），`sha256 7240dafe…09ea61`。
- 制品仓已存在 `nsnake/3.0.1` 且配方内容一致，同版本不可并存 → 按 §1.2 版本号策略与 R37，适配修复递增为 **3.0.1.1**。
- 本版本的变化集中在 `package()` / `package_info()` 与 `build()` 的日期传参
（`source()`/`requirements()`/`layout()` 与补丁逐字节不变）：3.0.1 只打包 `bin/nsnake`，丢掉了上游 `make install` 会安装的
  31 个关卡、`man6` 手册、16/32 图标、`xpm` 与 `desktop` 入口。

## 为什么必须在配方里做，而不是 `make install`

OHOS 设备上没有 `install(1)`，也没有知识条目 E108 方案要求的 `ginstall`
（`/data/service/hnp/bin` 452 个二进制中均无），原生 `make install` 直接
`make: install: No such file or directory`（exit 127）。因此改用 Conan 的
`copy()` / `save()` 复现同一套 FHS 布局，不依赖宿主 `install` 工具，也不碰共享系统前缀（R49）。

另一个必须显式传变量的坑：GNU Make 不把命令行覆盖传播给嵌套求值，
`make install` 若不重复传 `CC/CXX/CXXFLAGS/CFLAGS_PLATFORM/LDFLAGS`，会退回 Makefile 默认
`LDFLAGS = -lncurses` 并报 `ld.lld: error: unable to find library -lncurses`（设备上无系统 ncurses 开发文件）。

## 对 3.0.1 notes 的两处纠正（含执行证据）

1. **`KEY_CTAB` 说法不成立**：3.0.1 记录"OHOS ncurses 中 `KEY_CTAB` 与 `KEY_ENTER` 均为 `0527`"。
   实测本依赖图实际链接的 `ncurses/6.4` 包（package_id `21b17f8b…`）头文件
   `KEY_CTAB 0525` / `KEY_ENTER 0527`，并不冲突；对**未打补丁**的 `src/Flow/InputManager.cpp`
   执行 `clang++ -fsyntax-only` 退出码 0。取值同为 `0527/0527` 的那份头文件来自无关包
   `pick/2.0.2` 自带的资源副本。补丁 `0001` 用的是 `#if KEY_CTAB != KEY_ENTER` 条件守卫，
   在本图为 no-op，保留仅作防御。
2. **`SYSTEM_LEVEL_DIR` 不是关卡加载路径**：上游只把它用在帮助文本里
   （`src/Flow/GameStateMainMenu.cpp:275`）。真实关卡目录由
   `src/Config/Globals.cpp:136` 设为 `Globals::Config::directory + "levels/"`
   （即 `~/.local/share/nsnake/levels/`），`BoardParser::listLevels()` 只
   `Utils::File::ls(BoardParser::directory)`。上游 README 也明说"installs stock levels on
   `/usr/share/games/nsnake/levels`, so make sure to copy them before playing"。
   → 因此"关卡没出现"是上游按用户目录设计的既有行为，不是本适配引入的回归；
   但**包内必须带着这些数据**，否则用户连复制的来源都没有。

执行证据（`nsnake-3.0.1-build/audit/A19…A21`，用游戏自身的 `BoardParser` 代码，非字符串匹配）：

| 目录 | listLevels | loadOK | loadFail |
|---|---|---|---|
| 3.0.1.1 包内 `share/games/nsnake/levels/` | **31** | **31** | 0 |
| 3.0.1 包内（无 `share/`） | 0 | 0 | 0 |
| 空目录（反证：不会去别处发现关卡） | 0 | 0 | 0 |
| 播种后的 `~/.local/share/nsnake/levels/` | **31** | **31** | 0 |

pty 真实交互复核：播种后主菜单 → Level Select 屏幕出现 `arena00 arena01 lenny retro00 3-hearts balls cave00`
且**无** "Sorry, it seems you have no levels" 对话框（`A21-pty-level-select-positive.log`）。

## 打包内容（3.0.1.1）

```
bin/nsnake                                   555520 B   PIE + FULL RELRO(BIND_NOW) + GNU_STACK=RW
share/games/nsnake/levels/*.nsnake           31 个
share/man/man6/nsnake.6                      VERSION→3.0.0、DATE→Jul2014 已替换（与 -DDATE 同源）
share/icons/hicolor/16x16/apps/nsnake.png    上游 nsnake16.png 重命名
share/icons/hicolor/32x32/apps/nsnake.png    上游 nsnake32.png 重命名
share/pixmaps/nsnake.xpm
share/applications/nsnake.desktop            Exec=nsnake / Icon=nsnake（与重命名后的 png 对齐）
```
共 39 个文件（含 conaninfo/conanmanifest），包内 `.so` 数 = 0（R26 无系统同名库污染）。

确定性说明（本轮已彻底修复）：上游 `Makefile:42 DATE = $(shell date "+%b%Y")` 会把构建
月份编进二进制（`-DDATE=...`，`nsnake --version` 随之变化）并写进手册，两者都不可复现。
本版本引入单一常量 `_BUILD_DATE = "Jul2014"`（上游 v3.0.x 发布月的 `%b%Y` 形态，经
`ChangeLog` 首行 `07-28-2014 v3.0.0` 佐证），同时用于两处：
① `build()` 的 make 命令行 `DATE='Jul2014'`（GNU Make 命令行赋值优先于 Makefile 赋值）；
② man6 的 `DATE` 占位符替换（`VERSION` 仍从上游 `Makefile:41` 解析，=3.0.0）。
因此 `bin/nsnake` 与 `nsnake.6` 在多次独立重建（不同 build folder → 同一 package folder，
bin sha256 前缀 `5d9b59bc721408c4`，39 文件 `conanmanifest` 仅首行时间戳不同）下一致，
L5 产物基线可复现；`--version` 现输出
`nsnake v3.0.0 (Jul2014)`，并由 `test_package` 新增断言（`--version | grep -q Jul2014`）
纳入 CI 门禁防回归。

`package()` 内置完整性自检：任一资产缺失/为空、或关卡数 ≠ 31 → 直接 `ConanException`，
防止再次退化成"只发一个二进制"。

## 依赖

- Conan 强制第三方依赖：`ncurses/6.4`（唯一）。配方 `requires` 无变化，
  静态 widec 构建，`cpp_info.libs = formw menuw panelw ncursesw`。
- 依赖可消费性（W0/R36，均 exit 0）：`conan download ncurses/6.4 -r=ohpcd --only-recipe`；
  `conan install --requires=ncurses/6.4 --build=never` → `Package installed 21b17f8b…`。
- 内置第三方：`deps/commander`（clibs/commander 1.3.2，MIT）随源码编译，不需单独适配。

## 提交口径与门禁互斥（需评审确认）

本 PR 必须同时包含软件级伴随文件，否则 CI 会红：

- `archives/n/nsnake/commands.json`：CI `L0k` 要求 `versions` 含本版本
  （`build_and_test.sh:723` `'$pkg_ver' not in d.get('versions',{}) → BAD_VERSION`），
  同版本 `3.0.1` 无法覆盖 `3.0.1.1`；
- `archives/n/nsnake/manifest.yaml`：软件级 `versions` 列表需登记新版本。

但本地 `create-pr` 前置硬闸 **PF9**（`scripts/ohc/preflight.py` `check_branch_and_paths()`（v12.20 代码行 570）
`bad = [f for f in arch if len(f.split("/")) < 5]`）把所有 4 段路径
（`archives/<字母>/<包>/<软件级文件>`）判为"变更路径缺版本目录层"，与 PF8/R38 的
要求互斥。实测两种口径（`nsnake-3.0.1-build/audit/A34-preflight-dryrun-311.log`）：

| 变体 | PF8 | PF9 | 说明 |
|---|---|---|---|
| A：仅版本目录 8 文件 | pass（读的是工作区已改好的 commands.json） | pass | 但该文件不进 PR → CI 检出旧 commands.json → **L0k BAD_VERSION** |
| B：版本目录 + 2 个软件级文件（共 10 文件） | pass | ❌ 1 项发现 | 语义正确、CI 可绿，但被本地 PF9 拦 |

`JC1–JC6` 在变体 B 口径下全通过（`涉及软件数: 1（合规）`，
`audit/A33-final-conan-create-311.log`）。建议二选一：
①框架侧给 PF9 增加"同包软件级伴随文件豁免"（正解）；②本次用
`--no-preflight`/`OHC_PREFLIGHT=0` 并在 PR 描述里说明目录合规依据（pipemeter 有先例）。

## 上游测试清点与实测（R51 三步法）

上游测试资产清点（同一份 v3.0.1 源码，日志 `25-upstream-test-entry-attempts.log`）：
`tests/` 目录 0、`*test*`/`*spec*` 文件 0、Makefile 目标 9 个（无 `check`/`test`/`tests`）、
`CMakeLists.txt` 0、`.github`/`.travis.yml`/`appveyor.yml` 0。

实际执行：

```
$ make check   → make: *** No rule to make target 'check'.  Stop.     exit=2
$ make test    → make: *** No rule to make target 'test'.  Stop.      exit=2
$ ctest -N     → Test project …/staging-src   Total Tests: 0          exit=0
```

**上游测试统计：总数 0 / 通过 0 / 失败 0 / 跳过 0（确无测试入口，非环境缺失）。**

适配层功能用例（非上游测试，`nsnake-3.0.1-build/tests-logs/`）：
3.0.1 复核阶段的 12 项（T01–T12）全部通过（首轮 11/12：T10 失败是用例正则与设备 `file`
输出格式不符的脚手架缺陷，修正匹配串后复跑 12/12，非放宽判据）；3.0.1.1 新增 4 项：

| 用例 | 内容 | 实测 | 结果 | 日志 |
|---|---|---|---|---|
| T13 | `level_loader_probe` 指向包内关卡目录 | `listLevels=31 loadOK=31 loadFail=0` | PASS | `audit/A19-level-loader-probe-run.log` |
| T13b | 反证：指向空目录（关卡不会被从别处发现） | `listLevels=0 loadOK=0 loadFail=0` | PASS | 同上 |
| T13c | 对照：旧包 3.0.1（仅 `bin/`，无 `share/`） | `listLevels=0`（`ls` 证旧包只有 bin） | PASS | 同上 |
| T14 | 播种到 `~/.local/share/nsnake/levels/` 后 pty 进入 Level Select | 关卡名可见、无 "no levels" 对话框 | PASS | `audit/A20…A21-…log` |

**适配层功能用例合计 16 项（T01–T12 + T13/T13b/T13c/T14），16/16 通过。**
下段 test_package 的 17 项断言在 `conan create` 内执行，与本表口径不同，不可混计。

test_package（3.0.1.1）17 项断言：真实执行 `nsnake --version` + 管道 `grep -q 'nsnake v'`
+ 管道 `grep -q 'Jul2014'`（构建日期可复现）+ bin 存在 + 5 个数据文件存在且非空
+ 关卡数 31 + 手册无占位符 + `.TH nsnake 6` 头；`test_package/test.sh` 为其 shell 子集
（10 项，含修复后的显式 `if grep -qE ...; then exit 1; fi`，不再被 errexit 豁免）。

## 验证结果

```bash
conan create archives/n/nsnake/3.0.1.1 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=…   # exit 0，无 --build=missing
python3 scripts/ohc-run.py conan-verify nsnake 3.0.1.1                                  # exit 0，G1/G2/G3 PASS
python3 scripts/ohc-run.py finish nsnake 3.0.1.1 built                                  # 见下
```

- 交付包：`packaging/nsnake-3.0.1.1-ohos-aarch64.tar.gz`（684667 B）+ `-debug.tar.gz`（160299 B）
  由 `verify-build` 通过后经 `package_builder` 生成（该目录被 gitignore，非 PR 内容；
  正式制品仍按 R20 走 conan 流水线，不手工上传）。已在 DATE 传参修复后重新生成
  （2026-09-12 17:05），解包实测内嵌日期为 `Jul2014`、man6 为
  `.TH nsnake 6 "Jul2014" v3.0.0`；注意 `package_builder` 会 strip 二进制，
  故交付包内 bin 的 sha256（`b746fee2faa6421d…`）≠ 未 strip 的 conan 包 bin
  （`5d9b59bc721408c4…`），属预期差异。
- 关卡仍需用户复制到 `~/.local/share/nsnake/levels/`（上游设计）。若要在 OHOS 上免手动，
  需要给上游加"包内相对路径回退"补丁，属行为变更，本版本未做，留待评审决定。
---

**编译结束**: 2026-09-12 17:08
**最终状态**: built
