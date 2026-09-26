# debian-hamradio 0.12 适配笔记

## 概述

把 `debian-hamradio`（Debian Hamradio Pure Blend —— 业余无线电任务数据）的任务数据
适配为 HarmonyOS PC 的 Conan 纯数据包。Debian Pure Blend 的"任务"机制是：
`tasks/<name>` 是每个任务的**源描述**，`blends-dev` 把它们合并成
`debian-hamradio-tasks.desc`（tasksel 消费的成品）。

## 上游形态

```
debian-hamradio_0.12.tar.xz
└── package/                         ← 顶层目录不叫 debian-hamradio-0.12
    ├── debian-hamradio-tasks.desc   成品：13 个 Task 段（含 meta 任务 debian-hamradio）
    ├── tasks/                       12 个逐任务源描述（antenna / datamodes / morse / sdr / …）
    ├── COPYING
    ├── debian/                      只有 dh 规则与 changelog/copyright
    └── Makefile                     需要 blends-dev 才能重新生成 .desc
```

`get(..., strip_root=True)` 会剥掉 `package/`，所以配方无需改动；
但**顶层目录名不能进任何路径拼接**。

**本包与 debian-med / debian-gis 的两处不同形**：

| 维度 | debian-med 3.9.0 / debian-gis 0.0.22 | debian-hamradio 0.12 |
|------|--------------------------------------|----------------------|
| 顶层目录 | `<blend>-<version>/` | **`package/`** |
| `AUTHORS` | 有 | **无** |
| `<blend>-logo.svg` | med 有 | **无** |

## 安装内容

```
share/tasksel/descs/debian-hamradio-tasks.desc   成品任务描述
share/blends/debian-hamradio/tasks/<name>        12 个逐任务源描述
licenses/{COPYING,copyright}
```

（无 logo、无 AUTHORS —— 上游本来就没有，包内也不应凭空出现。）

## 为什么没有编译步骤

上游 `Makefile` 需要 `blends-dev`（`/usr/share/blends-dev/Makefile`）才能重新生成
`.desc`；但**生成结果已经随源包发布**（`debian-hamradio-tasks.desc` 就在 tarball 里），
所以本包直接交付它，不执行 make、也不需要 blends-dev。`debian/` 是维护辅助，不安装。

## 上游测试情况

没有测试目录、没有测试框架，`debian/rules` 只有 `dh`，也没有 autopkgtest。
**上游用例数 N = 0**。

## 新增自检（test_package/test_blend.py，13 条断言）

| 断言组 | 条数 | 内容 |
|--------|------|------|
| `.desc` 结构 | 5 | 存在；含 13 个 `Task:` 段；Task 名无重复；首个是 meta 任务 `debian-hamradio`；每段都有 `Description:` |
| 源描述齐备 | 5 | `tasks/` 存在；文件数 12；**`.desc` 里除 meta 外的每个任务都能在 `tasks/` 找到同名源文件**；**任务集合与 `tasks/` 完全一致**（前缀 `hamradio-`）；每个源文件都含 `Task:` 与 `Description:` |
| 文档/许可/纯净性 | 3 | 上游无 `AUTHORS` ⇒ `share/doc/debian-hamradio` 不得凭空出现（反向断言）；`licenses/` 含 COPYING + copyright；`share/` 下内容白名单校验 |

> 为什么断言方向要"取反"：模板化的生成器如果写死 `share/doc/<blend>` 必须恰为
> `["AUTHORS"]`，在 hamradio 上就会出现 12/13 —— 唯一失败项恰好是**上游本来就不存在**
> 的配件。这条断言证明的是模板的假设而不是包的完整性，方向必须由上游实态注入
> （`EXPECT_DOC` / `EXPECT_LOGO`），并且"上游没有"也要断言（不得凭空出现），
> 否则"配方把别的东西塞进去"这类污染会静默通过。
> 详见 `knowledge/drafts/DRAFT-debian-hamradio-0.12-blend-tarball-layout-and-asset-presence.md`。

## 本地验证

```
$ python3 scripts/ohc-run.py conan-verify debian-hamradio 0.12
G0 PASS / G1 PASS / G2 PASS（干净 conan create + test_package 13/13）/ G3 PASS / G4 PASS
✅ 配方验证通过: debian-hamradio 0.12
$ python3 scripts/ohc/preflight.py . main HEAD
✓ preflight PF1-PF9+R52 全部通过
```
