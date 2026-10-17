# g810-led 0.4.3 适配笔记（OHOS aarch64）

## 1. 基本信息

- 上游：https://github.com/MatMoul/g810-led （GPL-3.0-only），tag v0.4.3（commit efa3c35e）
- 构建系统：GNU makefile（C++ gnu++11），无 configure
- 产物：`bin/g810-led`（CLI）+ `lib/libg810-led.so.0.4.3`（共享库）+ 公开头文件
- 依赖：hidapi/0.12.1（hidraw 后端，`-lhidapi-hidraw`）→ 传递依赖 libudev-zero/1.0.4（`-ludev`）
- 源码 SHA-256：`8af6275aa190fd17fdef36079d51361874c88e2df0b23a76e7651d4f7c7c99fc`
  （codeload.github.com 与 ghfast.top 双端点下载校验一致）

## 2. 上游测试枚举台账（双口径）

枚举命令与结论（覆盖用户测试源/框架头源码/样例/基准/fixture/测试脚本/构建目标）：

| 枚举项 | 位置/命令 | 分类结论 |
|---|---|---|
| tests/ 目录 | `find . -type d -iname '*test*'` → 无 | 无测试源 |
| 测试文件 | `find . -type f \( -iname '*test*' -o -iname '*spec*' -o -iname '*check*' \)` → 0 个 | 无独立测试文件 |
| makefile 测试目标 | `grep -E '^[a-zA-Z-]+:' makefile` → all/bin/debug/lib/clean/setup/install/uninstall 等 | 无 test/check 目标 |
| CI 配置 | `.travis.yml`/`.github/` 等 → 无 | 无 CI 测试 |
| 样例（非独立用例） | `sample_effects/`、`sample_profiles/`（bash/python 效果脚本、配置示例） | 样例，非独立上游用例 |
| 基准/fixture | 无 | 无 |

**双口径统计**：
- `source_declared_total` = 0（官方 tag 源码无可复制枚举的测试声明）
- `configured_executable_total` = 0
- `executed_passed_total` = 0 / 0；全量通过率 N/A（无测试声明）
- 未实例化项 = 0

结论：上游 v0.4.3 确无任何测试（R51 清点证据如上）。本适配新增两类测试（与上游分别计数）：
- 消费者用例：`test_package/consumer.cpp`（公开 API 编译/链接/运行）+ `test_package/cli_smoke.sh`
- 鸿蒙专项测试：`test_ohos/run_ohos_test.py`（4 项真实行为断言，实测 4/4 PASS）

## 3. 适配要点与修复记录

1. **makefile 变量覆盖语义**：官方 `CPPFLAGS=-Dhidapi` 为条件赋值、`CXXFLAGS?=-Wall -O2`
   后用 `+=` 追加 `-std=gnu++11 -DVERSION=...`。环境变量注入的 CPPFLAGS 会被 makefile
   赋值覆盖；命令行传 CXXFLAGS 会让 `+=` 追加失效（丢失 -DVERSION，help 显示
   "Version : unspecified"）。配方最终：CXX 取自 Conan conf，CPPFLAGS/LDFLAGS/LIBS
   作为 make 命令行参数传入，CXXFLAGS 不传（保留 makefile 默认与 +=）。
2. **Conan dict conf**：`tools.build:compiler_executables` 为字典型 conf，子键不能
   用 `self.conf.get("...:cpp")` 直读（报 does not exist），必须
   `check_type=dict` 整体取出再 `.get("cpp")`（与 E392/E430-draft-8060 一致）。
3. **conan copy keep_path 嵌套**：默认 keep_path=True 将带 `bin/`、`lib/` 前缀的
   makefile 产物拷成 `pkg/bin/bin/`、`pkg/lib/lib/`，软链悬空，消费者
   `-lg810-led` 报 unable to find library → 显式 `keep_path=False` + `os.symlink` 重建。
4. 不使用官方 `install`/`setup` 目标（依赖 udevadm/systemctl，OHOS 不可用），
   package() 手工拷贝。
5. github.com 直连不可达：conan-verify 按 E017 机制临时注入 ghfast.top 镜像
   （conandata.yml 保持官方 URL，验证后自动恢复）。

## 4. 知识候选台账（四范围查重 + 七轴 + 路径决定）

候选清单（非噪声项）：

| # | 候选（真实错误→根因→修复→验证） | 适用范围 | 四范围查重 | 七轴结论 | 决定 |
|---|---|---|---|---|---|
| c1 | makefile `?=`+`+=` 与命令行 CXXFLAGS 覆盖 → -DVERSION 丢失（Version : unspecified）→ 不传 CXXFLAGS、其余作为 make 命令行参数 | 所有 raw makefile C++ 配方 | 草稿 E429-draft-0E26（sluice/0.03.01）已收录同一机制与同一方案 | exact_duplicate=true，causal_duplicate=true，solution_overlap=true，无独立新增差异（env-CPPFLAGS 细节属同根因边界注释） | **复用既有 E429-draft-0E26**（本条不再新建草稿） |
| c2 | `tools.build:compiler_executables` 字典型 conf 子键直读报 does not exist → check_type=dict 整体取 | 所有 OHOS Conan 配方 | 正式 E392（raw-makefile-conan-recipe-pattern）+ 草稿 E430-draft-8060 均覆盖 | exact_duplicate=true | **复用 E392**（配方已按此实现） |
| c3 | conan copy() 默认 keep_path=True → bin/bin、lib/lib 嵌套 + 软链悬空 → 消费者 unable to find library → keep_path=False + 显式重建软链 | 产物自带 bin//lib/ 前缀的 makefile 配方 | 正式/图谱/草稿均未命中；E362（依赖资源物化）仅手段重叠、根因不同 | exact_duplicate=false，causal_duplicate=false（vs E362），trigger_overlap=部分，solution_overlap=部分，combination_novelty=true，boundary_novelty=true，test_migration_novelty=true | **新建草稿 E430-draft-A7AC**（已验证、可跨库复用） |

**七轴汇总（c3 相对既有知识面）**：见 `knowledge/drafts/E430-draft-A7AC.md` 查重差异表。

**关系字段**：
- similar_to: E392（raw makefile 配方三陷阱）、E362（依赖资源物化）
- caused_by: 官方 makefile 产物前缀目录 + conan copy 默认 keep_path 行为
- prerequisite_of: 无
- conflicts_with: 无

**路径决定**：`new_draft`（c3 建草稿 E430-draft-A7AC，随本库 PR 交付）
+ `reuse_existing`（c1→E429-draft-0E26、c2→E392）→ **路径 B（知识库扩展）**，
标题前缀 `【知识库扩展】`。c1/c2 的复用不产生新草稿；唯一新草稿为 E430-draft-A7AC。
---

**编译结束**: 2026-09-27 02:05
**最终状态**: built
