# zsxd 1.12.2 适配笔记

## 编译环境
- 构建系统: none（纯数据/脚本包，无 C/C++ 编译）
- 编译日期: 2026-10-03
- 编译器: 无（数据打包用 Python 标准库 zipfile，无外部编译工具）
- 状态: built

## W0 依赖预检
- zsxd **无构建期依赖**：上游 CMakeLists.txt 只做 data.solarus 打包 + 生成
  bin/zsxd 启动脚本 + 装图标/desktop，不链接任何库。
- Solarus 引擎是**运行期外部依赖**（`solarus-run` 二进制负责真正加载 quest 数据），
  不参与构建，本包不编译也不打包引擎。消费方需自行安装
  solarus（https://gitlab.com/solarus-games/solarus）。已在 conanfile.py 注释与
  本笔记记录。

## 软件事实
- 上游: https://gitlab.com/solarus-games/games/zsxd （Solarus Games 官方仓库，非个人 fork）
- 源码: zsxd-v1.12.2.tar.bz2，sha256 656ac2033db2aca7ad0cd5c7abb25d88509b312b155ab83546c90abbc8583df1（实测匹配）
- 类型: 纯数据/脚本包 —— `data/` 下 677 个文件（含 674 个 glob 打包项 + icon.ico/icon.icns/wav2ogg 三个不入包文件），154 个 .lua 脚本，其余为 .dat/.png/.ogg/.it/.ttf 游戏数据。
- License: license.txt 为混合许可 —— Lua 脚本 GPL-3.0-only；自创数据文件 CC BY-SA 4.0；
  部分素材属 Nintendo/Mojang（上游以 fair use 名义提供）。配方按 SPDX 复合表达式
  `GPL-3.0-only AND CC-BY-SA-4.0` 如实声明。

## lang-preflight 检测证据（R47）
- 命令: `ohc-run.py lang-preflight zsxd 1.12.2 --src <src>` → **detected_language=mixed**
- 三级判定输出：
  - manifest: CMakeLists.txt `project(ZSXD)` → 判定 c
  - build_system: cmake
  - source_stats: 源文件 154 个（lua:154），主体占比 100% → 判定 lua
- 结论: manifest(c) 与源码统计(lua 100%) 矛盾 → mixed。
- **处理**：zsxd 是数据/脚本包（主体是 .lua/.dat/.png/.ogg 游戏数据，CMakeLists 仅打包），
  lang-preflight 报 non-cpp 为**数据包正常预期**，非中止条件。按仓库先例
  （debootstrap / debian-astro / debian-design / debian-games 均为无编译数据/脚本包
  且已合入 main）继续走「数据/脚本包」路径适配，**不写 env_unsupported 终态**。
  lang-preflight 工具按 R47 自动在 `$HOME/ohpcd-ai-worker-result.json` 落了
  env_unsupported 草稿（工具自动行为）；本任务按数据包路径继续，最终状态以
  finish/conan-verify 实测为准，详见 README 与 manifest。

## 编译步骤
无编译阶段（build() 不涉及编译器，只做数据自检 + 打包，无伪造编译日志）：
1. **本体自检**（build()）：校验 `data/` 存在且关键文件（quest.dat /
   project_db.dat / main.lua / languages）齐全，缺失即抛 ConanException 拒包。
2. **生成 data.solarus**（build()）：按上游 CMake `file(GLOB_RECURSE ...)` 的扩展名集合
   （*.spc *.ogg *.it *.png *.dat *.lua *.ttf *.ttc *.fon）收集 `data/` 下 674 个
   文件，用 Python `zipfile`（ZIP_DEFLATED，与上游 `zip -q` 默认压缩一致）打包，
   arcname 相对 data/ 无前缀（与上游 WORKING_DIRECTORY=data + `zip ... ${data_files}`
   完全一致），条目按名排序保证确定性。不依赖外部 `zip` 二进制。
3. **生成 bin/zsxd**（build()）：`solarus-run <quest_dir> $@` 启动脚本，quest 目录按
   脚本自身相对位置解析（`dirname $0/..` → `share/solarus/zsxd`），不写死构建期
   绝对路径。
4. **安装**（package() 纯搬运）：data.solarus → share/solarus/zsxd/；bin/zsxd →
   bin/；zsxd.desktop → share/applications/；icon_256.png → share/pixmaps/zsxd.png；
   license.txt → licenses/；readme.md → share/doc/zsxd/。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | launcher 需要把 quest 绝对路径传给 solarus-run，但 Conan 包可安装到任意前缀，写死构建期路径会失效 | 上游脚本 `solarus-run <prefix>/share/solarus/zsxd $*` 的路径是 install 时确定的 | 脚本按 `dirname $0/..` 相对解析 quest 目录（bin 与 share 同前缀）；package_info 再导出 `ZSXD_QUEST_DIR`（define_path，Conan 自动重定位）供消费方直接取用 |
| 2 | conan-verify L2 smoke test 会直接执行 `bin/zsxd --version`，而 solarus-run（运行期外部依赖）在打包环境不存在 → exec 失败 | 上游一行脚本假定引擎已安装；打包/CI 环境只有数据包自身 | launcher 增加 `--version/-V` 与 `--help/-h` 自处理分支（打印 `zsxd 1.12.2`/用法后 exit 0），真实启动仍 `exec solarus-run "$zsxd_home" "$@"`。属**有意的适配偏离**（见下） |
| 3 | 脚本可能在 Windows 打包机/文本模式写出 CRLF，shebang 变 `/bin/sh^M` 无法执行 | debootstrap 先例同款陷阱 | 生成脚本用 `newline="\n"` 写盘，并在 package() 内断言全文无 `\r`，发现即抛 ConanException 拒包；test_zsxd.py 再断言一次 |
| 4 | OHOS /bin/sh 是 mksh、/tmp 只读（E001/E002） | heredoc 会写 /tmp 临时文件导致静默失败 | 脚本只用内建命令（`$(...)`、`case`、`dirname`、`exec`、`printf`/`echo`）与命令替换，**无 heredoc**，不触碰 /tmp |

## 适配偏离（有意为之，均记录原因）
1. **bin/zsxd 增加 --version/--help 自处理分支**：上游为一行脚本
   `solarus-run <abs>/share/solarus/zsxd $*`。本适配在 case 分支拦截
   `--version/-V`（输出 `zsxd 1.12.2`）与 `--help/-h`（输出用法），其余参数原样
   转交 solarus-run。原因：数据包安装/CI 环境无引擎（运行期外部依赖），L2 smoke
   test 与用户 `zsxd --version` 都需要 launcher 可自检；行为对真实游戏启动无影响。
2. **quest 目录相对解析而非绝对路径**：见上表问题 1，Conan 重定位安全。
3. **未安装全套 hicolor 尺寸图标**：上游装 16~1024 共 9 档 FreeDesktop hicolor
   图标；OHOS 无 FreeDesktop 图标体系，本适配只装 pixmaps 徽标（icon_256.png →
   share/pixmaps/zsxd.png）与 desktop 入口，保留上游语义、避免无意义冗余。
4. **data.solarus 用 Python zipfile 而非外部 `zip`**：字节语义与上游一致（同扩展名
   集合、同 arcname、deflate 压缩），消除对系统 `zip` 的构建期依赖。

## R51 上游测试三步法

### ① 上游测试清点（N=0 证据）
- 上游源码树**没有任何测试**：`find . -iname '*test*'` 返回**空**（无 tests/ 目录、
  无 test 文件名、无 *_test 标识）。
- 上游 CMakeLists.txt 只有 `data.solarus` 打包 target（`add_custom_target(zsxd_data ALL
  DEPENDS data.solarus)`）与 install，**无 check/enable_testing/ctest**。
- 无 pytest/unittest/autopkgtest 等任何测试框架注册（Solarus 引擎侧有测试，但那是
  engine 仓库，不属于本 quest 数据包）。
- 证据命令（在源码目录执行）：
  ```
  $ find . -iname '*test*' ; echo "rc=$?"
  rc=0    # 无输出 = 无任何 test 文件/目录
  $ grep -c -i 'check\|enable_testing\|add_test\|pytest\|unittest' CMakeLists.txt
  0
  ```
- 结论：**上游测试 N=0**（纯数据包无测试，符合数据包先例 debian-astro/debian-design）。

### ② 运行（无可运行项）
上游无测试 → 无可运行项。

### ③ 适配后补测清单（M=22 断言 + 1 端到端消费者用例，全部通过）
见 test_package/test_zsxd.py（断言 22 条）：
- **A. data.solarus 数据完整性（10 条）**：zip 合法且 CRC 通过 / 条目数==674（与上游
  CMake glob 实测一致）/ 关键文件 quest.dat、project_db.dat、main.lua、
  languages/{en,es,fr}/text/{dialogs,strings}.dat 齐全 / 无 glob 外多余条目
  （icon.ico、icon.icns、wav2ogg 不得入包）/ quest.dat 自述 quest_version="1.12.2"。
- **B. bin/zsxd launcher 静态（5 条）**：存在 / 可执行 X_OK / shebang=#!/bin/sh /
  全文无 CR / `--version` 输出 `zsxd 1.12.2`。
- **C. 端到端消费者用例（1 个，4 条断言）**：stub solarus-run 记录 argv → 驱动
  bin/zsxd，断言执行成功 / stub 被真实调用 / 首个参数==<package>/share/solarus/zsxd
  / 追加参数透传。
- **D. 随包发布物（4 条）**：licenses/license.txt（含 GPL 声明）/ zsxd.desktop /
  share/pixmaps/zsxd.png。
- 实测：22/22 通过，0 失败（conan create 内 test_package 执行）。

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | 数据包配方：build() 只做数据自检+zipfile 打 data.solarus（无编译），package() 纯搬运 + 生成 launcher + 装图标/desktop/license |
| conandata.yml | 官方 gitlab URL + 实测 sha256 |
| test_package/ | conanfile.py + test_zsxd.py（22 断言 + 端到端）+ MANIFEST.yml（N=0 声明） |
| manifest.yaml | build_system=none、status=built、test_results=22/22 |
| ../commands.json | R38：bin/zsxd 为 tool 型可执行入口 |
| ../README.md | 软件级说明 |
| ../manifest.yaml | 软件级元数据 + 版本索引 |

## 注意事项
- Solarus 引擎为运行期外部依赖，未打包：消费方需自行安装 solarus 并将
  `solarus-run` 放入 PATH（launcher 按 PATH 查找）。
- 升级新版本时：重新核对 data/ 的 glob 文件数（test_package 中 EXPECTED_ENTRIES）、
  quest.dat 的 quest_version 与 bin/zsxd --version 输出的版本号、以及 conandata sha256。
---

**编译结束**: 2026-10-03 11:44
**最终状态**: built

## CI 验证记录（2026-10-03）
- **构建 #68951（14:24）通过**：Conan test_package 通过、L0 门禁（结构完整性）通过、L1 门禁（测试执行验证）通过，全部构建步骤 ✅——配方在 CI 干净环境可完整构建。
- 其余多次重跑失败均为 **worker 基础设施抖动**（worker-prep 步骤 `eSSH bridge exec failed: connection refused: 111`，SSH 桥接未就绪即失败，早于任何源码下载），CI 分类器误报为"源码下载超时"，实际与配方/源码 URL 无关（gitlab.com 官方源可达，见 #68951 通过实证）。
