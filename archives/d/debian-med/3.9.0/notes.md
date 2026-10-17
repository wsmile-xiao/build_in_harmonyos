# debian-med 3.9.0 适配笔记

## 概述

把 `debian-med`（Debian Med —— 医学/生物信息学 Pure Blend）的任务数据适配为
HarmonyOS PC 的 Conan 纯数据包。Debian Pure Blend 的"任务"机制是：
`tasks/<name>` 是每个任务的**源描述**，`blends-dev` 把它们合并成
`debian-med-tasks.desc`（tasksel 消费的成品）。

## 上游形态

```
debian-med-3.9.0/
├── debian-med-tasks.desc     成品：20 个 Task 段（含 meta 任务 debian-med）
├── tasks/                    24 个逐任务源描述（bio / bio-dev / imaging / …）
├── config/ menu/ tasks.ctl   维护辅助
├── covid-19_doc/ dependency_data/   专题文档与依赖快照
├── AUTHORS COPYING README
└── debian/ Makefile
```

## 安装内容

```
share/tasksel/descs/debian-med-tasks.desc     成品任务描述
share/blends/debian-med/tasks/<name>          24 个逐任务源描述
share/doc/debian-med/AUTHORS
licenses/{COPYING,copyright}
```

## 为什么没有编译步骤

上游 `Makefile` 需要 `blends-dev`（`/usr/share/blends-dev/Makefile`）才能重新生成
`.desc`；但**生成结果已经随源包发布**（`debian-med-tasks.desc` 就在 tarball 里），
所以本包直接交付它，不执行 make、也不需要 blends-dev。
`config/`、`menu/`、`tasks.ctl`、`dependency_data/`、`covid-19_doc/` 是维护辅助
与依赖快照，不属于交付数据，不安装。

## 上游测试情况

没有测试目录、没有测试框架，`debian/rules` 只有 `dh`，也没有 autopkgtest。
**上游用例数 N = 0。**

## 新增自检（test_package/test_blend.py，12 条断言）

| 断言 | 内容 |
|------|------|
| `.desc` 结构 | 存在；含 20 个 Task 段；Task 名无重复；首个是 meta 任务 `debian-med`；每段都有 `Description` |
| 源描述齐备 | `tasks/` 存在；文件数 24；**`.desc` 里除 meta 外的每个任务都能在 tasks/ 找到同名源文件**；每个源文件都含 `Task:` 与 `Description:` |
| 文档/许可/纯净性 | `share/doc/debian-med` 含 AUTHORS；`licenses/` 含 COPYING + copyright；未混入 `Makefile`/`debian/`/`config/` 等 |

最有价值的是 **`.desc` ↔ `tasks/` 的对应关系**：成品 `.desc` 是给 tasksel 用的，
而 `tasks/` 是它下一次重新生成的输入；少一个源文件意味着该任务的描述再也无法
回溯/重建，而"目录里有 20 个 Task"这种断言发现不了。

## 两个踩过的点（已修，写进配方注释）

1. **`copy(self, "tasks/*", src=self.source_folder, ...)` 会把文件铺成
   `tasks/tasks/<file>`**：`copy()` 复制的是 src 的**内容**，pattern 里的目录前缀
   会参与 keep_path。正解是 `src=<source_folder>/tasks` + pattern `"*"`。
2. Debian Blend 的 `.desc` 里任务名带 Blend 前缀（`med-bio`），而 `tasks/` 里的
   文件名是**去掉前缀**的（`bio`）；比对时要去前缀。且 `.desc` 只包含**被启用**的
   任务（20 个），`tasks/` 里还有 4 个未启用的源（24 个），所以是"包含"而非"相等"。

## 构建与验证

```bash
source /home/silhouette/conanenv/bin/activate
export CONAN_HOME=/home/silhouette/.conan2-ohos
python3 scripts/ohc-run.py conan-verify debian-med 3.9.0
```

## 来源

- Source URL: `https://mirrors.tuna.tsinghua.edu.cn/debian/pool/main/d/debian-med/debian-med_3.9.0.tar.xz`
- SHA256: `b7d13baf54e78ba6f553ac7c51473df3065dc87eb20fff1bff183c470702ec40`
  （与 `.dsc` 的 `Checksums-Sha256` 一致）
- License: GPL-2.0-or-later

---

**编译结束**: 2026-09-19
**最终状态**: built
