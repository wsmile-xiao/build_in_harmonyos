# debian-pan 0.4 — HarmonyOS PC 适配笔记

## 一、包性质（为什么"没有可编译的代码"）

debian-pan 0.4 是 **Debian Pure Blend 的元数据包**（PAN = Photons And Neutrons，
X 射线/中子科学软件选集）。一个 Debian-native 源包（35 文件）声明并生成
**18 个 `Architecture: all` 二进制包**：

| 类 | 数量 | 说明 |
|---|---|---|
| 基础设施 | 2 | `pan-tasks`（tasksel 描述包）、`pan-config`（blend 配置包） |
| 领域元包 | 16 | `pan-<主题>`：coherent-diffraction / control-systems / control-systems-dev / data-reduction-frameworks / data-reduction-frameworks-dev / diffraction / grazing-incidence / imaging / machine-learning / modelling / mx / powder / small-angle-scattering / spectroscopy / tomography / xas |

软件本体是**任务选单元数据**：Deb822 task 文件（`tasks/`，18 个）+ tasksel 描述
（`debian-pan-tasks.desc`）+ dpkg 依赖选择语义（`dependency_data/debian-pan_0.4.json`）。
全树 **零 C/C++ 源文件、零可执行程序、零测试框架**；顶层 `Makefile` 只有一行
`include /usr/share/blends-dev/Makefile`，构建完全委托 Debian 特有的 `blends-dev`
+ `debhelper-compat (= 12)`（OHOS CI 不存在该工具链）。

## 二、建模决策（诚实、零伪造）

按 SKILL 铁律 R8/R34（禁止空壳 stub、test 必须实质依赖被测包）与 R26/R38：

1. **单一 data/metadata 配方**，`package_type = "unknown"`（Conan 2.29 无元包枚举）。
2. `package()` 只装**真实上游制品**：18 个 task 文件、genblends 生成的
   `debian-pan-tasks.desc`、官方快照 `debian-pan_0.4.json`、以及 `build()` 中
   纯解析派生的 `registry.json`（不调用 apt/blends-dev/genblends，不重写任何上游文件）。
3. **零 Conan `requires`**：18 个二进制包的 Depends/Recommends/Suggests 全是
   OS/distro 包选择（0.4 快照 446 条去重引用），硬拷成 Conan requires 会造出
   虚假且不可满足的依赖图，故如实置空并在 `registry.semantics.conan_requires`
   记录 `none`。
4. **不产假 bin/**：`cpp_info.bindirs = []`，包内无 bin/、无 ELF（test_package 有
   显式诚实性断言），避免触发 L0k/R38 的 commands.json 要求，也避免伪造 CLI 工具。
5. `settings = "os","compiler","build_type","arch"` 仅为满足 CI L0p 结构门禁；
   数据包无真实平台语义（注释中已标明）。`package_info` 仅声明 `resdirs = ["share"]`。

## 三、与同族先例 debian-science 1.15 的关键差异

| 维度 | debian-science 1.15 | debian-pan 0.4（本包） |
|---|---|---|
| task 文件格式 | **旧格式**（无 `Format:` 头） | **新格式 blends 1.1**（每文件带 `Format: https://blends.debian.org/blends/1.1`） |
| 文件级 Depends 降级 | 有（文件级 Depends → 元包 Recommends） | **无**（新格式不写文件级 Depends） |
| 元包附加依赖 | `Depends: debian-science-tasks (=1.15)` | `Depends: pan-config (=${source:Version})` + `pan-tasks (=${source:Version})` |
| 任务/元包映射 | 部分重叠（4 元包无任务文件 / 5 任务文件无元包） | tasks ⊋ 元包：`laue`、`mx-dev` 有任务文件但无 `pan-laue`/`pan-mx-dev` 元包 |
| 规模 | 46 任务 / 42 desc 段落 / 45 二进制包 / 1976 引用 | 18 任务 / 17 desc 段落 / 18 二进制包 / 446 引用 |

映射不对称**如实记录在 `registry.semantics.mapping_asymmetry`**，不做 1:1 归一化。

## 四、R47 语言预检实测（重要）

```
python3 scripts/ohc-run.py lang-preflight debian-pan 0.4 --src <src>
→ exit 0, detected_language=c（expected=cpp，c↔cpp 兼容族）
  language_evidence: build_system=make / manifest=顶层 Makefile（无更强 manifest）
                     / source_stats=无源文件可统计
```

**这是检测器盲区**：顶层 Makefile 使检测器把本包推入 c/cpp 族，而源码统计为零
（无任何可统计源文件），于是给出 `detected=c` 的假阳性。人工核验结论是
**纯打包元数据，无可编译单元**。本 PR 的处置：不因盲区而硬编空壳编译，也不
因"没有 C 代码"就放弃适配——而是按 data/metadata package 诚实建模并给出
可复现的 `conan create` 验证（详见 knowledge/drafts/E560、E563）。

## 五、构建与验证

```bash
# 本地 W3（使用 OHOS profile；数据包无实际交叉编译步骤）
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64

# test_package 实质校验（48 项断言）
python3 test_package/test_debian_pan.py <package_folder>
```

- 源 URL：salsa.debian.org 官方 Git 归档（R39 合规；**不用** deb.debian.org pool URL，
  后者会被 PF7 判为"Debian 下游重打包源"）。
- sha256 两次独立下载一致：`2f4e8f68…e9ac`；归档内 35 文件清单与官方
  `debian-pan_0.4.tar.xz` 逐项 diff 一致。
- 上游测试：**0/0**（`find . -iname '*test*'` 为空、无 tests/ 目录、无 ctest/pytest
  注册、零 C/C++ 源文件）——R51 清点证据见 `test_package/MANIFEST.yml`。
- test_package：48 项断言（含 5 项鸿蒙特有测试 / OHOS 平台适配预检），覆盖打包布局、Deb822 结构、tasksel desc、registry
  交叉复核、control 声明、官方快照一致性、诚实性（无 bin/、无 ELF）、semantics。

## 六、平台限制与已知事实

- Debian 侧构建依赖 `blends-dev`/`debhelper` 在 HarmonyOS PC 不存在，**不影响本
  配方**：本配方不执行 Debian 打包流程，只装元数据并做纯解析派生。
- 18 个 Debian 二进制包（pan-*）本身是 dpkg 层的软件选择，**不在本包内重新打包
  为 conan 包**；本包交付的是其机器可读语义（任务、描述、依赖选择）。
- 不打包 `dependency_data/` 中的历史快照（0.1~0.3），避免被误读为当前依赖。
---

**编译结束**: 2026-09-11 00:52
**最终状态**: built
