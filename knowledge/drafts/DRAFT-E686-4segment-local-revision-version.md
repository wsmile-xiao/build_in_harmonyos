# DRAFT-E686：4 段版本号=本仓本地修订版本；W0-1 命中后按同源字节裁决 + 四项披露

> Contributor: Awstme | Status: Draft | Updated: 2026-09-23
> Source: 任务卡 4316（火种 5）libgsf 1.14.58.2，W0-1 命中止损 → 编排方裁决授权恢复

## 背景

任务卡派发 `libgsf/1.14.58.2`（4 段版本）。W0-1 版本可得性实核：

```text
git ls-remote --tags https://gitlab.gnome.org/GNOME/libgsf.git
  → 全量 84 个 tag，历史从无 4 段 tag；1_14_58 → 1_14_59 直跳
  → 精确 grep 1_14_58_1 / 1_14_58_2 零命中（全 refs 同零命中）
curl -sIL .../libgsf-1.14.58.2.tar.xz → 404（download.gnome.org / GitLab archive / 镜像全部无）
sha256sum 候选源 = 5254e2a571f6… = 1.14.58.1 conandata 记录值（逐字节同源）
```

按生死关「版本不可得=止损上报」命中 → 上报。编排方裁决：**采信止损上报，但按
「本仓 4 段=本地修订版本」约定授权恢复执行**，并要求四项强制披露。

## 判据：先分两类任务

| 类型 | 特征 | W0-1 口径 |
|---|---|---|
| A 类：上游真实新版本 | 3 段版本；上游 tag/官方 tarball 在档 | `git ls-remote --tags` 实核 + sha256 锚定（原判据不变） |
| B 类：本仓本地修订版本 | 4 段 `x.y.z.w`；同包存在同基版本先例 | 实核无 tag/404 时先查先例与 4 段目录计数 → 上报歧义 → **编排方裁决 + 同源字节授权** |

B 类客观证据（libgsf 本轮实测）：

- 本仓 `archives/` 现存 **247 个 4 段版本目录**（`find -mindepth 3 … grep -cE`）。
- 同包先例 `libgsf/1.14.58.1`：上游同样无独立 tag、源同为 `LIBGSF_1_14_58` 归档，
  已合入 main `6568938da` 且 `conan list -r=ohpcd` published。
- `glib/2.84.0.1` notes 明文：「原位修订：…**上游源码仍为 2.84.0 tarball**」。
- 先例 PR !5333 正文自述版本来源：「按 R37 版本递增为 1.14.58.1（cnb 制品仓不支持
  同版本多 revision，需用版本号区分）」。

## 授权前提（缺一不可）

1. 候选源 sha256 与同包先例 conandata **逐字节相同**（同源检测）；
2. 复用既有补丁与 compat（本例 6 补丁全复用）；
3. 构建输入 diff 若仅版本号 → 明写「原位修订=版本号位移、零源码 delta」；
4. 不改版本号（任务卡钉的版本 = 分支名门禁 `包目录名-版本 == 分支`，擅改=越权）。

## 四项强制披露（裁决原文口径）

1. `notes.md` 问题表登记：上游无 `1_14_58_2` tag、官方渠道 404、本版本=本仓本地修订约定
   （引 58.1 / glib 2.84.0.1 先例）；
2. `feedback/pending/` 同款条目；
3. PR 正文「已知限制/版本说明」段写明同源关系（源字节=1.14.58 归档）；
4. notes 与汇报明写「原位修订=版本号位移、零源码 delta」，不得包装成上游新版本。

## 禁止

- **伪造上游出处**：上游无此 tag/release 却在 notes/PR 正文写成上游新版本 → W4 P0。
- **未核同源即复用先例源**：省掉 sha256 同源检测直接写配方 = 硬写配方（libradsec/libzippp/
  net-tools/myman 止损先例同族）。
- **执行体擅改版本号**「顺手升级到真实存在的 1.14.59」：破坏分支名门禁；上游真实新版本
  单列「建议后续升级任务」另案派发（本例 1.14.59 于 2026-09-20 发布，tag+tar.xz 在档）。

## 复现命令

```sh
sh $HOME/tmp/libgsf-1.14.58.2/w0-evidence/run-w0-gates.sh   # 只读 W0 实核（tag 全量/URL HEAD/sha256/list）
git -C $HOME/ws/build_in_harmonyos log --oneline -1 -- archives/l/libgsf/1.14.58.1/   # 先例合入 6568938da
find $HOME/ws/build_in_harmonyos/archives -mindepth 3 -maxdepth 3 -type d | grep -cE '/[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$'   # 247
sha256sum $HOME/tmp/libgsf-1.14.58.2/w0-evidence/gl-1.14.58.tar.gz   # 5254e2a5… 与先例 conandata 一致
```

## 同族差异

- 与 **E478**（点号版本导致 G4/L2/L4/L5 跳过但标 PASS）：E478 是 verify 门禁对多点号
  版本的路径解析缺陷；本条是 W0 派发判据对 4 段版本的口径缺失，阶段不同（w0 vs verify）。
- 与 **R37**（版本号未占用检查）：R37 查本仓/制品仓占用；本条查上游存在性与本地修订授权。
