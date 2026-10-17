# DRAFT-libudev-provider-is-eudev — ohpcd 无独立 `libudev` 包，须由提供者（eudev/systemd）以 `pkg_config_name = libudev` 冒充；上游硬要求 `dependency('libudev')` 且无 fallback

> Contributor: AtomCode / Status: **DRAFT** / Updated: 2026-09-24 / Severity: 2（🟡medium）

## 相关既有条目（同族差异化定位）

全库查重（`knowledge/graph/index.tsv` + `knowledge/graph/E*.kv` + `knowledge/drafts/`）：

| 既有条目 | 收录状态 | 问题面 | 本条的增量（差异化） |
|---|---|---|---|
| E 编号检索（`libudev` / `eudev`） | — | `graph/index.tsv` 与 `E*.kv` **0 命中** | 本条为**真增量** |
| `DRAFT-ohos-version-output-protocol-vs-package`、`DRAFT-ohos-musl-glibc-specific-symbols`、`DRAFT-ohos-github-tarball-sources-differ` 等 | 草稿 | 各自为「版本输出协议/符号/源差异」等**别的问题层**，仅同现 `libudev` 字样 | 本条讲的是**依赖包的「提供者」与「能力名」不一致**——包名 ≠ `pkg-config` 名，与本条机制无关 |

## Scope（何时用）

上游以 `dependency('libudev')`（meson）或 `pkg-config --exists libudev` 探测 udev 能力，而本仓/ohpcd **没有名为 `libudev` 的包** 时。

典型实例：`libinput` 1.26.2 —— `meson.build:146` **硬要求且无 fallback 分支**：

```meson
dep_udev = dependency('libudev')
dep_mtdev = dependency('mtdev', version : '>= 1.1.0')
dep_libevdev = dependency('libevdev')
```

## Symptom

- meson `configure` 期：`Dependency "libudev" not found`（`--fatal-meson-warnings` 下直接 fail）；
- 或 recipe 里写 `self.requires("libudev/...")` → conan 报找不到该 ref（ohpcd 实查 **0 条**）。

## Root Cause

`libudev` 是**能力名**（`pkg-config` 模块名），不是**包名**。它历史上由 systemd 提供、现亦可由 `eudev` 提供；两者都会把 `libudev.pc` 装上，故 `pkg-config --exists libudev` 能成立，但**仓库里并没有叫 `libudev` 的 conan 包**。ohpcd 的可用提供者：

| 包 | ohpcd 版本 | 是否提供 libudev |
|---|---|---|
| `eudev` | 3.2.14 | ✅ 配方内 `set_property("pkg_config_name", "libudev")` |
| `systemd` | 261 | ✅ 同样提供 |

因此在 conan 侧「依赖名」必须写**提供者包名**（`eudev`），而在 meson 侧「探测名」仍是 `libudev` —— 二者的桥就是提供者把 `pkg_config_name` 设为 `libudev`。

## Recommended Solution

1. **conan 侧 require 提供者**，不 require `libudev`：
   ```python
   self.requires("eudev/3.2.14")   # 轻量；不要把整个 systemd 拉进来
   ```
2. **确保 `.pc` 可被 meson 找到**：把提供者的 `.pc` 放进 `PKG_CONFIG_PATH`（或经 `PkgConfigDeps` 生成），并确认其模块名确为 `libudev`（`pkg-config --exists libudev` 返回 0）。
3. **meson 探测名不改**（保持上游 `dependency('libudev')`），**不要**把上游改写成 `dependency('eudev')` —— 那会让配方绑死单一提供者，也偏离上游。
4. 若同图内同时出现 `systemd` 与 `eudev`，二者都会提供 `libudev.pc` → 会产生**提供者冲突**，需在配方里用 `override` 或只保留一个。

## 单库实证

| 库 | 角色 | 结果 |
|---|---|---|
| libinput 1.26.2 | 消费者（路径 A 适配，PR #12300） | 选 `eudev/3.2.14` 作提供者；ohpcd 独立 `libudev` 包实查 0 条；meson `dependency('libudev')` 经 eudev 的 `libudev.pc` 满足，configure 通过 |

## 测试覆盖边界

本条只覆盖「提供者 ≠ 包名」这一探测/依赖声明层；不覆盖 udev **运行期**行为（无 udev daemon 时的降级路径由各库自行处理）。申报口径按上游实际执行的用例计，未执行部分逐条归因。
