# E434 — preflight PF9 误报 archives 软件级元数据文件（与 PF8/L0k/ARCHIVE-SPEC 矛盾）

> 草稿条目，来源：`rtl-wmbus/1.1.0` 适配 HarmonyOS PC（OHOS aarch64）。
> 状态：draft，待主编审核后 promote 为正式知识条目。

## 错误特征

```text
PF9 分支/路径闸: 变更路径缺版本目录层（指向 commands.json/README.md/manifest.yaml）
```

实际遇到的报错：

```text
PF9 分支/路径闸: 变更路径缺版本目录层 ... archives/r/rtl-wmbus/commands.json, README.md, manifest.yaml
```

## 触发条件

- 分类：`framework`
- 阶段：`testing`
- 工具：`preflight`
- 适用范围：新增带可执行产物的 CLI 包（按 R38 需软件级 commands.json）并在建 PR 前跑 preflight 的贡献者

## 根因分析

scripts/ohc/preflight.py 的 check_branch_and_paths 要求所有 archives/ 变更路径段数 >= 5；但 PF8(R38/L0k) 要求 CLI 包必须有软件级 archives/<字母>/<包>/commands.json（4 段），ARCHIVE-SPEC 也把 README.md/manifest.yaml 定为软件级；CI 侧 L0n 只校验分支名不校验路径深度。三者互相矛盾，导致 PF9 对所有软件级元数据文件误报。

## 解决方案

### 推荐方案

预期命中该误报：保留软件级 commands.json（删掉会触发 CI L0k 硬失败），建 PR 时用框架自带逃生口 --no-preflight / OHC_PREFLIGHT=0，并在 notes.md 留证；框架侧应把 PF9 的 <5 段判断收窄为仅对版本目录下的文件生效。

**方案说明**：软件级元数据文件命中 PF9 属框架缺陷，按逃生口处理并留证，不要为过闸删除 commands.json。

```bash
python3 scripts/ohc/preflight.py . origin/main HEAD   # 观察 PF9 是否指向软件级文件
```

### 禁止做法

- ❌ 不要为绕过 PF9 而删除软件级 commands.json——那会直接触发 CI L0k 硬失败（L0k 对 CLI 包是 fail）。
  - 原因：PF8/R38 与 CI L0k 都把软件级 commands.json 定为 CLI 包必需项，PF9 的路径段数判断与之矛盾。
  - 后果：CI L0k 硬失败，PR 无法通过质量门禁。

### 回退方案

若编辑器不接受 --no-preflight，可先建 PR 再在 MR 评论中说明 PF9 为已知框架误判并附复现证据。

## 验证

```bash
把既有已合并配方 archives/a/a52dec（同样含软件级三文件）的文件清单喂给 preflight.check_branch_and_paths()，得到完全相同的 PF9 命中，确认非本包问题；其余 PF1-PF8/R52 全部 pass。
```

## 关联条目

- 相关软件包：`rtl-wmbus/1.1.0`
- 完整踩坑记录：`archives/r/rtl-wmbus/1.1.0/notes.md` 第 7 节
