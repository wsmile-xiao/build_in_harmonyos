# zsdx 1.12.3 适配笔记

## 编译环境
- **构建系统**: custom（python zipfile 打包；上游 `project(ZSDX NONE)` 零编译单元）
- **编译日期**: 2026-09-30
- **平台**: arm64-ohos（OpenHarmony PC）
- **状态**: built（Conan 配方验证通过）
- **补丁数量**: 0

## 上游形态

zsdx（The Legend of Zelda - Mystery of Solarus DX）是 Solarus 2D 引擎的
quest 数据包：`data/` 下 1143 个文件（293 个 .lua 游戏脚本、384 个 .dat 地图/
动画数据、331 个 .png、97 个 .ogg、32 个 .it 等），无任何编译单元。

- 权威源：GitLab `solarus-games/games/zsdx`（GitHub 同名仓库为 archived 镜像，
  tag 停在 1.11.0，v1.12.3 归档实测 404）。
- tag `v1.12.3`（带 v 前缀），commit 9635bfc2；`data/quest.dat` 内
  `quest_version = "1.12.3"` 三方佐证。
- 上游"构建"：CMake 唯一动作是把 `data/` 打成 `data.solarus` zip；免 CMake
  路径为根目录 `make_zip` 脚本：`cd data && zip -r ../../data.solarus *`。
  **契约：zip 条目必须以 data/ 内容为根**，引擎按根级路径（main.lua、
  quest.dat、project_db.dat…）加载。
- 上游 install：`data.solarus` → `share/solarus/zsdx/`，另装启动脚本/图标
  （启动脚本调用 `solarus-run`，属引擎运行期议题，本包不涉及）。

## 编译步骤（conan create 全流程）

```bash
conan create archives/z/zsdx/1.12.3 --build=missing \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

1. **source()**: `get()` 取 GitLab 官方归档并 `strip_root=True`（剥离顶层
   `zsdx-v1.12.3/`）。
2. **build()**: python 标准库 `zipfile` 复刻 make_zip——`os.walk` 收集 data/
   全部文件（`arcname` 相对 data/、POSIX 斜杠），写出 `data.solarus`。
   不依赖设备 `zip` 命令；`os.walk` 显式收集对点文件安全（ieee-data
   `copy("*")` 丢 `.lastupdate` 教训；zsdx data/ 实测无点文件）。
3. **package()**: `data.solarus` → `share/solarus/zsdx/`（对齐上游 install
   语义）；`license.txt` → `licenses/`。
4. **package_info()**: 纯数据包，`includedirs/libdirs/bindirs` 全空，
   `resdirs = ["share/solarus/zsdx"]`，`buildenv_info` 导出 `ZSDX_QUEST_DIR`。

## 依赖轨道

无 conan 依赖。运行时需要 Solarus 1.6.x 引擎（`data/quest.dat`:
`solarus_version = "1.6"`），但官方仓无 solarus recipe——引擎缺失只影响
"实跑游戏"，不影响本数据包的构建/交付，故不声明对引擎的 conan 依赖
（参考 lomiri-sounds 等纯数据先例）。

## 上游测试（NO_UPSTREAM_TESTS 记录）

结论：**zsdx 无自有测试套件，上游 CI 的测试为引擎级运行时测试，在 OHOS CI
不可复现，按 NO_UPSTREAM_TESTS 如实记录（upstream_tests: []）**。

检查过的入口与证据：

| 入口 | 检查方式 | 结果 |
|------|----------|------|
| 仓库根 `.gitlab-ci.yml` | 读取原文（v1.12.3 归档） | 全文仅 2 行：`include: https://gitlab.com/solarus-games/solarus-devops/raw/master/gitlab/quests.yml` |
| `solarus-devops` 仓 `gitlab/quests.yml` | 抓取 raw 原文 | 引擎级运行时测试：`wget` 下载预编译 Solarus linux 工件 + `7za x` + Xvfb 跑 `solarus-test-initialization`、逐地图 `solarus-test-lua-map`；与 zsdx 自身代码无关 |
| `tests/`、`test runner` | 遍历上游根目录 12 个条目 | 不存在（仅 data/build/work/CMakeLists.txt/changelog.md/license.txt/make_quest_package/make_zip/readme.md/zsdx.desktop/.gitignore/.gitlab-ci.yml） |
| test 地图 | 归档内 `find data/maps -iname "test_*"` | **0 个文件**（data/maps 下全是游戏地图 `N.dat`/`N.lua`）→ quests.yml 的 map 测试循环对 zsdx 为空 |
| 可移植性 | — | 剩余的 `solarus-test-initialization` 依赖 linux x86 预编译引擎 + Xvfb + 7za，OHOS CI 无此基础设施（官方仓亦无 solarus 引擎 recipe） |

佐证：本包 test_package 的 18 项断言（全量 CRC + 条目数/类型学 + 根条目契约 +
quest 元数据）是对数据包可验证面的真实验证；不声称"游戏可玩"（box2d
"ctest 空套件退出码 0"教训：不得把无测试当作测试通过）。

## 复合许可

`license.txt`（24 行许可声明）：
- Lua 脚本：GPL-3.0（声明措辞 "in version 3" → `GPL-3.0-only`）；
- 自创数据：CC BY-SA 4.0（`CC-BY-SA-4.0`）；
- 部分图形/音效/名称属 Nintendo 版权内容，按 fair use 提供（事实记录，
  不改许可表达式）。

conan `license` 字段按 SPDX 复合表达：`GPL-3.0-only AND CC-BY-SA-4.0`。

## 已知限制
- 未做引擎级运行验证（无 solarus 引擎包、无显示环境）；验收面为数据包结构
  完整性（CRC + 条目计数 + quest 元数据）。
- zip 只含文件条目、不含目录条目（`zip -r` 会附带目录条目，但 Solarus 引擎
  只按文件路径读取，目录条目非必需；test_package 断言 1143 个文件条目逐一
  对账，无静默丢失）。
- `write_dir = "zsdx"`（quest.dat）为引擎运行期存档目录语义，与打包无关。

---
**编译结束**: 2026-09-30
**最终状态**: built
