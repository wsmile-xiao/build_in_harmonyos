# mlv-smile 1.47 — 适配笔记

任务：平台 8941｜档位【中】｜语言 c（66 文件）｜构建系统 裸 Makefile（递归）｜首次适配
上游：SMILE v1.47（经 Debian pool orig tarball 引入）
源码：`mlv-smile_1.47.orig.tar.gz` 234150 B
sha256 `5924b49ca138c1ec086fde04a78d52081b93d27e1ba3dd855bbdc49646fe2a75`（与 Debian 索引一致）

---

## 1. 构建结构

顶层 Makefile 递归三个子目录：P_BLOCS（bin/x-smile 主程序）、P_BLOCS+DELTA
（bin/x-smile_delta）、SigStat（bin/e-smile_shuffling、bin/e-smile_against、bin/grep+）。
无 configure、无 install 目标、零外部依赖（preflight 零依赖通过）。

## 2. M18：CC=gcc 烧死 → make 命令行覆盖

三个子 Makefile 均 `CC=gcc` 硬编码，OHOS 无 gcc（gcc: No such file or directory，
实测首轮 create）。修法：make 命令行 `CC="<ohos clang>"` 覆盖，经 MAKEFLAGS 传入递归
子 make；C_FLAG= $(OPT) -I... 结构使旗标无需改动（-ansi/-Wall/-O3 clang 兼容）。
**B 判定=create（取 B草稿库 M18 泳道）**，draft-review 见 §6。

## 3. E491：clang -fno-common 与 ALPHA_CARD 待议定义

include/define.h（三个子树各一份副本）第 23 行 `int ALPHA_CARD;` 是待议定义——
每个包含它的编译单元都成为定义，gcc 靠 -fcommon 合并公共符号，clang 默认
-fno-common ⇒ ld.lld `duplicate symbol: ALPHA_CARD`（8 组重复，实测）。
**按 E491 的 remedy 落地**（该条 forbid_1 明确禁用 -fcommon）：define.h 改
`extern int ALPHA_CARD;`，唯一定义放各子树的全局变量/初始化编译单元
（P_BLOCS→src/global_fonctions.c，DELTA/SigStat→src/global_variables.c）。
实现走配方内幂等 python 修正（notes 历史草稿：conandata 补丁形态曾因 patch-ng
对 DELTA 副本 hunk 匹配过严而放弃，配方内修正为 probabel/rrdtool 先例同款）。

## 4. SigStat 串行与工具面

SigStat 的上游 `all` 目标顺序依赖：先 `grep+` 规则填充 grep+/obj、Spell/obj，
再链接两个 e-smile 工具——该顺序对 -j 不安全（实测并行链接时 model.o 尚未产出）。
配方改为分目录调用：P_BLOCS、P_BLOCS+DELTA 各 -j2，SigStat 串行。

## 5. 功能实测（五维账本）

| 维度 | 读数 |
|---|---|
| 上游静态注册 N_static | **0**（上游无任何测试目标） |
| 本环境注册/执行 | 0 / 0 |
| 通过 | 0 |
| 未执行 | 0（无注册即无未执行） |
| 消费者 | **1 启动器驱动 / 3 组断言**，3/3 PASS |

消费者测试（test_package/test_smile.sh）驱动**上游 perl 启动器** Lanceur/smile——
真实用户入口——对打包产物执行：①x-smile 在 runenv PATH 可解析；②无参调用失败并
输出用法；③`perl smile param_example` 全链（参数解析→x-smile 抽取→输出文件非空）。
**能力边界（诚实声明）**：e-smile_shuffling/against 的统计评估由启动器 Phase-2 调用，
其数值正确性未深测（以抽取输出存在性 + 退出码为断言面）。

## 6. B 判定与知识沉淀

- **create（取 B草稿库 M18 泳道）**：
  `DRAFT-mlv-smile-1.47-suckless-baked-paths-makevar-override`（CC=gcc 烧死 →
  命令行覆盖），已随 PR 提交 knowledge/drafts/ 并跑 draft-review。
- **hit(E491)**：ALPHA_CARD 待议定义 → extern+单一定义（该条 remedy 原文即此法，
  且 forbid_1 禁 -fcommon，照办）。
- **顺带实测留档**：SigStat all 目标 -j 不安全（notes §4），未达独立条目门槛。

## 7. CI 取源风险预声明

源 URL = deb.debian.org（CI 镜像改写仅覆盖 github.com 域，本包直接拉取）；sha256
双向核对（实测 + Debian 索引），E299 类 404-HTML 伪装由 sha256 硬闸兜底。
---

**编译结束**: 2026-09-25 07:04
**最终状态**: built
