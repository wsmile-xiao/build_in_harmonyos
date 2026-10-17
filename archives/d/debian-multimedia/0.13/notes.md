# debian-multimedia 0.13 适配笔记

## 概述

把 `debian-multimedia`（Debian Pure Blend 的任务数据包）适配为 HarmonyOS PC 的 Conan 纯数据包。
Pure Blend 的"任务"机制：`tasks/<name>` 是每个任务的**源描述**，blends-dev 把它们
合并成 `debian-multimedia-tasks.desc`（tasksel 消费的成品）。

## 上游形态

- `debian-multimedia-tasks.desc`：成品任务描述，共 **27 个 Task 段**（含 meta 任务 debian-multimedia）
- `tasks/`：**26 个**逐任务源描述，与 .desc 的任务集合**完全一致**（前缀 `multimedia-`）
- 其余顶层目录（`Makefile`/`debian/`/`dependency_data/`/`files/`/`hooks/`/`packages/`）
  是打包与维护辅助，不属于交付数据

## 安装内容

```
share/tasksel/descs/debian-multimedia-tasks.desc
share/blends/debian-multimedia/tasks/<name>          （26 个）
licenses/copyright
```

## 为什么没有编译步骤

上游 `Makefile` 需要 blends-dev 才能重新生成 .desc，但**生成结果已随源包发布**，
本包直接交付成品；不需要任何构建工具。

## 上游测试情况

没有测试目录、没有测试框架，`debian/rules` 只有 `dh`，也没有 autopkgtest。**上游用例数 N = 0。**

## 新增自检（test_package/test_blend.py，13 条断言）

- `.desc` 结构：存在；含 27 个 Task 段；Task 名无重复；首个是 meta 任务；每段都有 Description
- 源描述齐备：`tasks/` 存在；文件数 26；**.desc 里除 meta 外每个任务都能找到同名源文件**；
  任务集合与 `tasks/` **完全一致**；每个源文件都含 `Task:` 与 `Description:`
- 许可/纯净性：`licenses/` 已发布；未混入 `Makefile`/`debian/`/`src`/`dependency_data`

## 构建与验证

```bash
source /home/silhouette/conanenv/bin/activate
export CONAN_HOME=/home/silhouette/.conan2-ohos
python3 scripts/ohc-run.py conan-verify debian-multimedia 0.13
```

## 来源

- Source URL: `https://mirrors.tuna.tsinghua.edu.cn/debian/pool/main/d/debian-multimedia/debian-multimedia_0.13.tar.xz`
- SHA256: `a48e68618042f04270c63e7f15cbf9e6b5093ebb41a86b6019112df18207277d`（与 .dsc 的 Checksums-Sha256 一致）
- License: GPL-2.0-or-later

---

**编译结束**: 2026-09-19
**最终状态**: built
