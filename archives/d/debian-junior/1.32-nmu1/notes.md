# debian-junior 1.32+nmu1（recipe 版本 1.32-nmu1）适配笔记

## 概述

把 `debian-junior`（Debian Jr. Pure Blend —— 面向儿童/教育机器的任务数据）适配为
HarmonyOS PC 的 Conan 纯数据包。Debian Pure Blend 的"任务"机制：`tasks/<name>` 是
每个任务的**源描述**，`blends-dev` 把它们合并成 `debian-junior-tasks.desc`
（tasksel 消费的成品）。

## 版本号要分两处看（本包最容易踩的点）

| 处 | 值 | 原因 |
|----|----|------|
| **上游 Debian 版本**（`.dsc` 的 `Version:`、文件名） | `1.32+nmu1` | Debian 用 `+nmu1` 表示非维护者上传（NMU） |
| **平台任务版本 / recipe `version`** | `1.32-nmu1` | 平台 `version_match` 要与任务版本一致；conan 版本正则 `^[a-z0-9_][a-z0-9_+.-]{1,100}\Z` 不含 `~` |
| **源码 URL** | `.../debian-junior_1.32%2Bnmu1.tar.xz` | 文件名按上游取，URL 里 `+` 写 `%2B` |

三者必须同时对上：recipe 版本写 `1.32-nmu1`，URL 指向 `1.32%2Bnmu1`，sha256 锁定真正
取到的那份文件（`2c52b1fd…`，与 `.dsc` 的 `Checksums-Sha256` 一致）。

## 上游形态

```
debian-junior_1.32+nmu1.tar.xz
└── debian-junior-1.32+nmu1/
    ├── debian-junior-tasks.desc   成品：21 个 Task 段（meta `debian-junior` + 20 个 `junior-*`）
    ├── tasks/                     23 个逐任务源描述
    ├── AUTHORS  COPYING  README  TODO
    ├── config/  dependency_data/  sources.list.unstable
    ├── Makefile                  需要 blends-dev 才能重新生成 .desc
    └── debian/
```

**tasks/ 有 23 个文件，但 `.desc` 只启用了 20 个**。多出来的 3 个是 **doudou-\***
（`doudou-base` / `doudou-dev-artists` / `doudou-games`，属于 Debian Jr. 下的
"doudou" 子项目），上游没有把它们并进成品 `.desc`。所以本包的自检**不能断言
"两个集合相等"**，只能断言方向：

> `.desc` 里除 meta 任务外每个任务，剥掉 `junior-` 前缀后必须能在 `tasks/` 找到同名源文件
> （20 ⊆ 23 成立，反之不成立）。

> 细节：`tasks/<name>` 文件内部写的是**不带前缀**的 `Task: art`，前缀是 blends-dev
> 生成 `.desc` 时加的 —— 自检做映射必须先剥前缀。

## 安装内容

```
share/tasksel/descs/debian-junior-tasks.desc   成品任务描述（21 段）
share/blends/debian-junior/tasks/<name>        23 个逐任务源描述
share/doc/debian-junior/AUTHORS
licenses/{COPYING,copyright}
```

（上游无 `debian-junior-logo.svg`，包内也不应有。）

## 为什么没有编译步骤

上游 `Makefile` 需要 `blends-dev`（`/usr/share/blends-dev/Makefile`）才能重新生成
`.desc`；但**生成结果已经随源包发布**，所以本包直接交付它，不执行 make、也不需要
`blends-dev`。`config/`、`dependency_data/`、`sources.list.unstable`、`debian/`
是维护辅助，不安装。

## 上游测试情况

没有测试目录、没有测试框架，`debian/rules` 只有 `dh`，也没有 autopkgtest。
**上游用例数 N = 0**。

## 新增自检（test_package/test_blend.py，13 条断言）

| 断言组 | 条数 | 内容 |
|--------|------|------|
| `.desc` 结构 | 5 | 存在；含 21 个 `Task:` 段；Task 名无重复；首个是 meta 任务 `debian-junior`；每段都有 `Description:` |
| 源描述齐备 | 5 | `tasks/` 存在；文件数 23；`.desc` 里除 meta 外每个任务剥 `junior-` 后都能找到同名源文件；**`tasks/` 覆盖 `.desc` 全部任务**（不是相等 —— 有 3 个未启用的 doudou-* 源）；每个源文件都含 `Task:` 与 `Description:` |
| 文档/许可/纯净性 | 3 | `share/doc/debian-junior` 含 `AUTHORS`；`licenses/` 含 `COPYING` + `copyright`；`share/` 下无 logo、无 `Makefile`/`debian/`/`config/` 等混入 |

## 本地验证

```
$ python3 scripts/ohc-run.py conan-verify debian-junior 1.32-nmu1
G0 PASS / G1 PASS / G2 PASS（干净 conan create + test_package 13/13）/ G3 PASS / G4 PASS
✅ 配方验证通过: debian-junior 1.32-nmu1
$ python3 scripts/ohc/preflight.py . main HEAD
✓ preflight PF1-PF9+R52 全部通过
```
