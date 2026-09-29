# polkit 124.1 适配笔记（libs-only 模式补出 libpolkit-agent-1，OHOS）

> **结论：可行，本地 conan create 通过。** 124.1 是 polkit **124 的适配修复版本**
> （R37 版本号策略：同上游版本 + 适配后缀），在 `-Dlibs-only=true` 下**同时构建
> `src/polkitagent`**，补出下游认证代理所需的 `libpolkit-agent-1` +
> `polkit-agent-1.pc` + `polkitagent/` 头文件；`polkitbackend`/`programs`
> （polkitd 等）保持跳过，与 polkit/124 的 `libs-only` 口径一致。

## 为什么派生 124.1（依赖先行）

下游 `lomiri-polkit-agent 0.3.3` 的构建依赖包含 **`polkit-agent-1`**
（`debian/control` + CMake `pkg_check_modules(... polkit-agent-1)`）。制品仓现有
`polkit/124` **不提供**该模块：

| 证据 | 内容 |
|---|---|
| `src/meson.build` | `subdir('polkit')` → `if not get_option('libs-only')` → `subdir('polkitbackend'); subdir('polkitagent'); subdir('programs')` —— **libs-only 一次性跳过 polkitagent** |
| `src/polkitagent/meson.build` | `shared_library('@0@-agent-@1@'.format(meson.project_name(), pk_api_version), ...)` → 即 `libpolkit-agent-1`，安装 `polkit-agent-1.pc` 与 `polkitagent/` 头 |
| 制品仓实测 | `polkit/124` 包内只有 `libpolkit-gobject-1.so*` 与 `polkit-gobject-1.pc`，无 `polkit-agent-1.pc`（`polkit/127` 为 polkitd 侧，同样不含 agent 库） |

因此按「依赖先行」（R36）派生 `polkit/124.1`：源码、sha256、上游版本均与 124
一致，仅增加一个让 `libs-only` 也构建 agent 库的 meson 补丁。

## 补丁 1：`patches/polkitagent-libs-only.patch`（2 个文件）

| 文件 | 改动 | 目的 |
|---|---|---|
| `src/meson.build` | `if not get_option('libs-only')` → `if get_option('libs-only')` … `subdir('polkitagent')` … `else`（原三分支不变） | libs-only 下也构建 agent 库 |
| `src/polkitagent/meson.build` | 特权 helper 的 `executable(...)` 包进 `if not get_option('libs-only')` … `endif` | libs-only 包只交付库，特权 helper 留给 full 构建 |

两处改动均以**上游自身的 `libs-only` 选项**表达（补丁中不含任何平台宏，
符合 R8/PF5），生成方式为真实 `git diff --no-index`（零转写），并在纯净源码树上
验证 `busybox patch -p1` rc=0、`git apply --check` OK、无 `.rej`/`.orig`。

## 补丁 2：`patches/mocklibc-ohos-fgetgrent-fgetpwent.patch`（沿用 124）

上游单测经 `LD_PRELOAD` 使用 `subprojects/mocklibc`；OHOS (musl-based) libc 头文件
无 `fgetgrent()`/`fgetpwent()` 声明，该补丁在 mocklibc 内本地实现，使上游 4 个
单元测试可在 OHOS 上运行（124 起沿用，本次未改动）。

## OHOS 关键缺口：musl libc 无 shadow 口令 API（helper 无法构建）

首次 `conan create` 在编译 agent 特权 helper 时失败：

```
src/polkitagent/polkitagenthelper-shadow.c:100:10: error: incompatible integer to pointer
      conversion assigning to 'struct spwd *' from 'int'
  100 |   shadow = getspnam (user_to_auth);
```

根因实测取证（**OHOS libc 完全没有 shadow 口令 API，不只是缺声明**）：

| 探测 | 结果 |
|---|---|
| `sysroot/usr/include/shadow.h` 内 `grep getspnam` | **0 命中**（musl 的 shadow.h 只有 `struct spwd`/`SHADOW` 等，无 `getspnam` 声明） |
| `nm -D sysroot/usr/lib/aarch64-linux-ohos/libc.so \| grep getspnam` | **0 个符号**（`getspent`/`setspent` 同为 0） |
| 对照组 `nm -D … \| grep getpwnam` | **存在**（`getpwnam`/`getpwnam_r`）→ 说明是 shadow 专项缺口，非工具误读 |

即：C 编译器按隐式声明处理 `getspnam`（未声明函数默认返回 `int`）→ 赋值给
`struct spwd *` 直接报错；即便补上声明，链接期也会因 libc 无该符号而失败。

**适配口径**：`polkit-agent-helper-1` 是 **setuid root 特权程序**，其鉴权实现依赖
`authfw`：`shadow`（`getspnam` 读 `/etc/shadow`）或 `pam`（libpam，OHOS 亦无）。
两条路径在 OHOS 均不可用，因此 `libs-only` 语义下**只交付库、不构建 helper**，
helper 留给 full 构建（与 polkit/124「libs-only 不出 agent」同源语义）。

**同类缺口（知识库拓展价值）**：OHOS musl 的**口令/组数据库 API 缺口**已两次踩到同
一类问题——`fgetgrent`/`fgetpwent`（124 的 mocklibc 补丁）与 `getspnam`/`getspent`
（本版本实测）；属「一类共性问题」而非单库专属，具备独立知识库拓展价值（检测特征
+ 处理策略可覆盖同类库）。

## 产物（conan create 实测）

| 类别 | 内容 |
|---|---|
| 库 | `lib/libpolkit-agent-1.so` → `.so.0` → `.so.0.0.0`（63,872 B）、`lib/libpolkit-gobject-1.so` → `.so.0` → `.so.0.0.0`（158,080 B） |
| 头文件 | `include/polkit-1/`（共 28 个 .h）；agent 侧 6 个：`polkitagent.h`、`polkitagenttypes.h`、`polkitagentlistener.h`、`polkitagenttextlistener.h`、`polkitagentsession.h`、`polkitagentenumtypes.h`（mkenums 生成） |
| pkg-config | `lib/pkgconfig/polkit-agent-1.pc`（本次新增）、`polkit-gobject-1.pc` |
| 签名 | 两个 `.so` 均 `llvm-objcopy --remove-section .codesign` + `binary-sign-tool sign -selfSign 1`（沿用 124 流程） |
| licenses | `licenses/COPYING` 随包分发 |

## test_package（组件级消费者）

`find_package(polkit CONFIG REQUIRED)` 后分别以 **CMakeDeps 组件目标**链接：

| 用例 | 链接目标 | 覆盖 |
|---|---|---|
| `test_polkit` | `polkit::gobject` | 身份/主题序列化（124 既有用例，保留回归） |
| `test_polkit_agent` | `polkit::agent` | agent 库消费者：`<polkitagent/polkitagent.h>`（含 API 稳定性守卫宏）→ `polkit_agent_listener_get_type()` / `polkit_agent_text_listener_get_type()` 类型名与继承关系 → `g_object_new(POLKIT_AGENT_TYPE_TEXT_LISTENER)` 实例化并校验 `POLKIT_AGENT_IS_LISTENER`/`POLKIT_AGENT_IS_TEXT_LISTENER` |

**为何不用 `polkit_agent_text_listener_new()`**：该构造函数走 `GInitable`，
`initable_init` 用 `ctermid(NULL)` + `fopen("/dev/tty")` 打开**控制终端**，CI 无 tty
必然返回 NULL（属环境限制而非库缺陷）。改走类型系统 + `g_object_new()`，
在无 tty、无 D-Bus 系统总线、无 polkitd 的环境下等价证明库可加载、类可注册、
GObject vtable 可用。

## 编译步骤（conan create 实测 EXIT=0）

```bash
conan create archives/p/polkit/124.1 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --build="polkit/*"
```

test_package 实测输出：

```text
polkit/124.1 (test package): RUN: "./test_polkit"
polkit-gobject-1 OK: identity=unix-user:root subject=system-bus-name::1.42
polkit/124.1 (test package): RUN: "./test_polkit_agent"
polkit-agent-1 OK: listener=PolkitAgentListener text_listener=PolkitAgentTextListener instance=0x5b49064d10
```

## 上游测试台账（R51）

- **上游测试清点（全量口径，2026-09-28 复审纠正）**：上游 `test/` 目录 **20 项** ——
  `find test -type f ! -path 'test/mocklibc/*' ! -path 'test/meson.build'`（vendored 子项目
  `test/mocklibc/` 的 22 文件与其根 `test/meson.build` 不计入）= 单元用例 4 + 集成用例 1
  + 注册脚本 2（`test/polkit/meson.build`、`test/polkitbackend/meson.build`）
  + 支撑代码 2（`test/polkittesthelper.c/.h`）+ 数据夹具 10（`test/data/**`）。
  其中**可独立执行用例 5 个**。
- **实跑**：上游单元用例 4 个（`test/polkit/`：`polkitunixusertest`、`polkitunixgrouptest`、
  `polkitunixnetgrouptest`、`polkitidentitytest`）：配方 `-Dtests=true`，由 `build()` 内
  `meson test` **实跑 4/4 通过（100%）**；经 `LD_PRELOAD` mocklibc 隔离，无需 polkitd/系统总线。
- **test_package 2 个**：`test_polkit`、`test_polkit_agent`，实测 2/2 通过（100%）。
- **上游未执行项**：集成用例 `test-polkitbackendjsauthority` 未运行——本包
  `-Dlibs-only=true` ⇒ `test/meson.build` 不 `subdir('polkitbackend')`（未注册到构建），
  且其运行需 polkitd + D-Bus 系统总线 + 厂商 JS 规则（OHOS 侧均不具备）。用例源码与
  注册脚本**未裁剪**。其余 15 项为注册脚本/支撑代码/夹具（非可执行用例）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 首次 create 编译 `polkitagenthelper-shadow.c` 报 `int → struct spwd *` | OHOS musl libc 无 shadow 口令 API（`shadow.h` 无 `getspnam`，libc.so 无该符号） | 补丁：`libs-only` 下不构建特权 helper |
| 2 | 首次 create 无 agent 产物（若照搬 124 的 libs-only） | 上游 libs-only 一次性跳过 `polkitagent` | 补丁：libs-only 下也 `subdir('polkitagent')` |
| 3 | 构建日志出现补丁 `already patched` WARN | 配方在 `source()` 与 `build()` 各调用一次 `apply_conandata_patches`（沿用 124 既有结构），第二次为幂等重放 | 非缺陷：conan 幂等、产物正确；保持与 124 一致，避免无谓偏离 |

## 依赖版本

- `glib/2.84.0.1`（glib-2.0 / gobject-2.0 / gio-2.0 / gio-unix-2.0）
- `expat/2.8.2`（构建期私有，`visible=False`）
- 工具链：clang 15.0.4 (aarch64-linux-ohos)、meson、ninja

## 注意事项

- **OHOS 无 D-Bus 系统总线、无 polkitd**（见 polkit/124 notes 的可行性评估）：
  本包交付**构建期依赖**（头/库/.pc 齐备，下游 agent 可编译链接）；运行期完整授权链
  需 polkitd + 系统总线 + agent helper，属后续独立任务范围。
- **本包不含 `polkit-agent-helper-1`**（见上文 shadow 缺口）——下游若在运行期触发
  鉴权，需在具备该能力的环境中另行提供 helper。
- `/tmp` 只读（E002）：中间产物走 `$HOME/tmp`。
- 下游引用请使用 `polkit/124.1`（R37：制品仓不支持同版本多 revision 并存，适配修复
  必须以版本后缀区分）。

---
**编译结束**: 2026-09-25
**最终状态**: built（本地 conan create 通过；未 push 制品仓）
## 流程告警说明（finish step5b / step8，均非阻塞）

- **step5b（submit 就绪预检）**：报 `packaging/` 与 `.staging-verified` 缺失。二者按
  `knowledge/ARCHIVE-SPEC.md` §2.3（v3.0）**已废弃**——`packaging/` 由 Conan 体系替代、
  `.staging-verified` 由 Conan 自带隔离验证替代；`scripts/ohc/finish.py`
  `step8_submit_readiness()` 中这两项检查为旧工作流残留。**未创建已废弃文件**
  （同 `archives/b/barvinok/0.41.9` 先例）；submit 侧
  `scripts/ohc/submission.py::_check_packaging_present()` 对缺失仅记 **WARN**
  （Check 9「打包产物」），不构成硬门禁。
- **step8（gen_summary）**：触发框架既有缺陷 `'str' object has no attribute 'append'`
  （`scripts/ohc/finish.py:342-345`，捕获后记 `⚠️部分`，非致命）。未手工改写
  `SUMMARY.md`；框架缺陷修复须独立 PR（W2：配方 PR 不混入框架变更）。
- finish 退出码 0（`EXIT_REASON: finish_success`）；W3 本地 CI 证据
  `.ci-result.json`（`exit_code=0`、`integrity_hash=ad15164171c1f209`）有效。
- W5：`graph validate` 通过（541 条目全一致、169 条既有 C13/C14 告警）；本包暴露的
  「musl libc 无 shadow 口令 API」缺口已落草稿
  `knowledge/drafts/E429-draft-1314.kv`（+ 配套 `.md`）。

---
---

**编译结束**: 2026-09-28 00:29
**最终状态**: built

## 复审修复记录（2026-09-28，PR #13432 质检 FAIL → 已修）

**评审结论**：质检机器人（`2402_87729496`）14:29 判 `VERDICT=FAIL`，唯一失败项
**rule4（验证结果：编译 + 通过率 + 少报）**：`少报: 上游实测 N=20 > 声明 N=5`。

**根因**：PR 正文/台账旧稿只按「可独立执行的用例数」单口径记 **5**（4 单元 + 1 集成），
未把上游 `test/` 目录内的**注册脚本 2 + 支撑代码 2 + 数据夹具 10** 计入，导致声明的上游
用例数小于评审方实测值（20）→ 判少报。

**修复动作**（口径对齐 + 全量清单化，不改任何 CI 输入文件）：

| 文件 | 改动 |
|---|---|
| `reports/pr-body.md`（PR 正文源） | 上游表重写为**全量 20 项口径**（含可复核命令与逐类明细）；适配后表改为「上游 20 项保留 + 新增 2 = 22」；验证结果补口径说明 |
| `README.md` | §4 验证结果行改为 20 项清点口径 + 可运行 4/4 |
| `reports/test-report.md` | §2 台账「清点」补 20 项全量口径；「未执行项」由 `无` 修正为集成用例未运行（含具体技术原因） |
| `notes.md`（本节） | R51 台账改为 20 项口径 |

**关键澄清（纠正旧稿的另一处不准确）**：旧稿称集成用例「保留 1 不可运行」，
实际是**双重原因**——① 本包 `-Dlibs-only=true` 使 `test/meson.build` 不 `subdir('polkitbackend')`，
该用例**未注册到本包构建**；② 即便注册，其运行仍需 polkitd + D-Bus 系统总线 + 厂商 JS 规则
（OHOS 侧均不具备）。用例源码与注册脚本**未裁剪**。

**口径复核命令**（上游 124 源码包内）：
```bash
find test -type f ! -path 'test/mocklibc/*' ! -path 'test/meson.build' | wc -l   # → 20
```

**未改动**：`conanfile.py` / `conandata.yml` / `test_package/**` / `patches/**` 全部未动
（本次为声明口径纠错，非配方变更，故**不需要**递增版本后缀）。
