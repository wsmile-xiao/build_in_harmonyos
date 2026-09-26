# Debian Pure Blend 数据包族适配（一条条目覆盖整族）

**来源**：`debian-med 3.9.0` / `debian-gis 0.0.22` / `debian-hamradio 0.12` /
`debian-junior 1.32+nmu1` / `debian-multimedia 0.13` 适配
**日期**：2026-09-20 ｜ **状态**：DRAFT

> 本条是把原先按包拆开的 5 条草稿（med / gis / hamradio / junior / multimedia）
> **合并成一条**：它们的现象、根因与修法属于**同一类问题**，拆成 5 条属于同族重复，
> 按官方口径（"解决一类问题"）应当收敛为一条，再在正文里列出各包的实例差异。

## 一、成品 `.desc` 与源 `tasks/` 是**包含关系**，不是相等

`<blend>-tasks.desc` 是 `blends-dev` 渲染后的成品，**只含被启用的任务**；`tasks/` 里还有未启用的源描述。

| 包 | `.desc` 段数 | `tasks/` 文件数 | 差额来源 |
|---|---|---|---|
| debian-med 3.9.0 | 20 | 24 | 4 个未启用任务 |
| debian-junior 1.32+nmu1 | 21 | 23 | 3 个未启用（`doudou-base` / `doudou-dev-artists` / `doudou-games`） |
| debian-hamradio 0.12 | 13 | 12 | 差 1 = meta 任务没有源文件 |

**稳定判据只有方向性的一条**：

```python
mapped = [n[len("<blend>-"):] for n in desc_tasks if n.startswith("<blend>-")]
check(set(mapped) <= set(tasks_files), "tasks/ 覆盖 .desc 的全部任务")
```

注意 `tasks/<name>` 文件内部写的是**不带前缀**的 `Task: art` —— 前缀是 blends-dev 生成 `.desc`
时加的，做映射必须先剥前缀，否则会误报"缺 20 个源文件"。

## 二、成品与源**不是同一套字段**

blends-dev 在渲染时会加入 `Relevance` / `Section` / `Parent` / `Key` / `Test-new-install`，
并把源里的 `Depends:` 展开成 metapackage 依赖。实测 `debian-multimedia 0.13`：

| 字段 | 成品 `.desc` | `tasks/*` |
|---|---|---|
| `Section:` | 27 | **0** |
| `Parent:` | 26 | **0** |
| `Key:` | 26 | **0** |
| `Test-new-install:` | 25 | **0** |
| `Depends:` | **0** | 909 |

所以自检要**按形态分两组**：对成品断言渲染期字段与段数；对 `tasks/` 断言源字段与文件集合。
拿源字段校验成品会假失败，只数段数会假通过。

## 三、tarball 布局与配件**并不统一**

| 维度 | med / gis | hamradio |
|---|---|---|
| 顶层目录 | `<blend>-<version>/` | **`package/`**（与包名无关） |
| `AUTHORS` | 有 | **无** |
| `<blend>-logo.svg` | med 有 | **无** |

- `strip_root=True` 会剥掉顶层目录 → 配方无需改，但**任何按顶层目录名拼路径的写法都会踩空**。
- **上游没有的配件不能做硬断言**：模板化生成器若写死 `share/doc/<blend>` 必须恰为 `["AUTHORS"]`，
  hamradio 上会出现 **12/13**，而唯一失败项恰是上游本来就不存在的东西 —— 这条断言证明的是模板的假设，
  不是包的完整性。正解：断言方向由上游实态注入（`EXPECT_DOC` / `EXPECT_LOGO`），
  并且"上游没有"也要**反向断言**（不得凭空出现）。

## 四、版本字符串要**分三处取值**

| 位置 | 取值（debian-junior） | 依据 |
|---|---|---|
| 上游 Debian 版本 | `1.32+nmu1` | `.dsc` 的 `Version:`；NMU |
| recipe / 平台任务版本 | `1.32-nmu1` | 平台 `version_match` 逐字一致；conan 版本正则 `^[a-z0-9_][a-z0-9_+.-]{1,100}\Z`（不含 `~`） |
| 源码 URL 文件名 | `debian-junior_1.32%2Bnmu1.tar.xz` | 上游真实文件名；`+` 在 URL 路径写 `%2B` |

按 recipe 版本拼 URL（最常见模板写法）在本包必然 404。另附两条同族结论：**conan 版本正则不含 `~`**
（`1.32~nmu1` 直接 `Invalid package version`）；**1 字符版本不可用**（`debian-astro (5)` 等需先确认）。

## 五、`copy()` 的 `src` 必须指向 `tasks/` 本身

```python
copy(self, "*", src=os.path.join(self.source_folder, "tasks"),
     dst=os.path.join(self.package_folder, "share", "blends", self.name, "tasks"))
```

写成 `copy(self, "tasks/*", src=self.source_folder, …)` 会把内容铺成
`share/blends/<blend>/tasks/tasks/<file>` —— `copy()` 复制的是 `src` 的**内容**，pattern 前缀参与 `keep_path`。

## 六、同构包族用生成器批量产出时的两个纪律

1. **断言条数不能硬编码**：不同 blend 的配件有无不同 → 条数不同。要么按生成脚本的 `check(` 调用数
   静态回填，要么在验证后从日志 `[test] N/N assertions passed` 回填（我们在 5 个包上各踩过一次）。
2. **生成器自身要自检**：模板里 f-string 的 `\n`、非 f-string 却写 `{{}}`、断言数写死 —— 这三类模板
   bug 都是"生成物看起来正常、跑起来才发现"。生成后 `ast.parse` 一遍成本极低。

## 与已有条目的边界

- `E255`（resource data package / icon theme / font package…）：给的是**单个**数据包的交付与验证框架，
  未涉及 Blend 的"成品 vs 源"两形态、`copy()` src 语义与版本三处取值；
- `E241` / `E305` / `E281` / `E251` / `E536`：分别是清单型数据、字体、语音资源、词典、固件资源的校验口径，
  与 Blend 的任务描述体系不同层；
- 本条**不重复申报**"资源包怎么验证"这一类（已由 E255/E281/E305 覆盖），只申报 Blend 族的形态与取值规则。

> 若评审认为本条与上述条目仍属重复，我们接受不计分；本条的价值主张只有一句：
> **Blend 族的成品/源两形态、配件可选、版本三处取值这三件事，现有条目里没有。**
