【申请人账号】2301_80739235

【队伍名称】天天开心

【申请日期】2026/08/08

【库名称】libXrender

【库版本】0.9.12

【上游地址】https://xorg.freedesktop.org/archive/individual/lib/libXrender-0.9.12.tar.xz

【任务来源】OpenJ9 0.59.0（Issue #1084）真实前置依赖

## 关联 PR

| 字段 | 内容 |
|------|------|
| 唯一源分支 | `2301_80739235:feat/libxrender-0.9.12` |
| 目标分支 | `OpenHarmonyPCDeveloper/build_in_harmonyos:main` |
| 关联约束 | 仅允许本 Issue 与该源分支创建的唯一 PR 建立双向结构化关联 |

## 路径 B 申请理由

libxrender 0.9.12 是 OpenJ9 0.59.0 的真实 X11 前置依赖。适配使用官方源码和最小 Autotools 可移植修复，并在授权 OHOS/arm64 设备上完成 shared/static 构建和 2/2 安装包消费者。

官方 finish 设备闭环还暴露了一个可跨软件复用的 Git/HMDFS 问题：进程局部 `safe.directory` 只能解决 ownership 门禁，不能修复 `/storage` 上 `.git/branches` 的原生元数据操作失败。有效修复是保留 HMDFS 工作树，用 `git init --separate-git-dir` 将任务私有 Git 元数据放到原生 `/data` 路径，并禁用自动 maintenance/gc。该边界已形成本 PR 的 E2154 草稿对。

## 知识库查重情况

| 查重范围 | 查询 | 结论 |
|------------|------|------|
| `knowledge/graph` | `dubious ownership`, `safe.directory` | 命中 E101，仅覆盖 ownership 信任门禁 |
| `knowledge/drafts` | `cannot stat .git/branches`, `separate-git-dir` | 无等价条目 |
| `knowledge/doc` | `HMDFS Git metadata`, `native /data` | 无等价条目 |
| `knowledge/operations` | `maintenance.auto`, `gc.auto` | 无等价条目 |

综合结论为 `NO_EQUIVALENT_REUSABLE_KNOWLEDGE`。E101 作为部分复用条目保留，E2154 专门补充 ownership 通过后仍失败的 Git 元数据文件系统边界。

## 证据材料

| 证据 | 结果 |
|------|------|
| W0 r12 | shared/static graph+install 全部 RC0，`--build=never` |
| 真机 W3 r11 | shared/static RC0，消费者 2/2，`launch_count=1` |
| 官方 finish r27 | W3 子阶段 PASS，aggregate `PARTIAL_POST_W3`，原生 RC1 如实保留 |
| Git r26 probe 2/3 | 原生 `/data` metadata + `/storage` worktree 均 RC0；probe 3 stderr 为空并清理双路径 |
| 知识草稿 | `knowledge/drafts/E2154-draft-2301.kv` 与同 stem Markdown |

## 分值说明

本 Issue 按路径 A（基础适配）+路径 B（贡献创新）申请，不申请路径 C。实际计分以社区评审结果为准。
