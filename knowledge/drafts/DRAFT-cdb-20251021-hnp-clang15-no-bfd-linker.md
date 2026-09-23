# DRAFT-cdb-20251021-hnp-clang15-no-bfd-linker：HNP clang 15 真机拒绝 -fuse-ld=bfd

> **Contributor**: gcw_6YxinkyD | **Status**: VERIFIED DRAFT | **Updated**: 2026-09-08
> **Source event**: cdb 20251021 HarmonyOS PC 适配真机验证（PR #8907，设备 10.62.134.118:2222）
> 对应：knowledge/drafts/DRAFT-cdb-20251021-hnp-clang15-no-bfd-linker.kv

## 知识类型与提升边界

本条目是路径 B 知识库扩展草稿，不预占正式 E 编号。只进入 `knowledge/drafts/**`，
不修改 `knowledge/graph/`、`knowledge/doc/`、索引或运维规则；是否提升由知识库
维护者和赛事评审决定。

## 现象

配方沿用旧经验（tinycdb 对照 + CI worker 的 lld/libxml2 规避法）注入
`-fuse-ld=bfd` 后，真机链接立即失败：

```text
clang-15: error: invalid linker name in argument '-fuse-ld=bfd'
```

同机对照组（`echo 'int main(){}' > t.c`）：

- 不注入任何 `-fuse-ld`：rc=0，`file` 显示正常 PIE ELF（aarch64）；
- `-fuse-ld=lld`：rc=0，正常 PIE ELF，无 libxml2 问题；
- `-fuse-ld=bfd`：直接报错，驱动层拒绝。

## 根因

环境异构：`-fuse-ld=bfd` 的有效前提是工具链里存在 ld.bfd——CI worker 的 SDK
有，而真机 10.62.134.118 的 HNP clang 15.0.4（/data/service/hnp/bin）没有，
clang 驱动对不认识的 linker 名直接报 `invalid linker name`，没有回退机会。
反向硬编码 lld 同样有反例（E544 层：部分 CI worker 的 ld.lld 缺
libxml2.so.16）。**bfd 与 lld 各有"存在/可用"的反例环境，任何全局硬编码
都会在另一类环境翻车。**

## 修复（真实证据）

配方默认不注入任何 `-fuse-ld`（跟随 clang 默认 linker）；提供 conf 开关
`user.cdb:ld`（接受名称或绝对路径）opt-in 注入。去掉默认 bfd 后真机
`conan create` 全绿（14 个工具全部链接成功）。

## 与已有知识的差异（查重关键）

- **E544-draft-j669539（pillow 四重适配链）**：其 linker 层讲的是"CI worker
  上用 bfd 规避 lld 缺 libxml2.so.16"——是 bfd 的**适用面**；本条目补充其
  **反例面**（HNP clang 15 真机无 bfd），两者合成完整判据：先探测、再选择，
  都不硬编码。
- **tinycdb/0.81（已发布配方）**：内置 `-fuse-ld=bfd`（OHOS 分支），在
  HNP clang 15 类真机上将无法复用——本条目是其环境边界的勘误。

## 禁止做法

- 把 `-fuse-ld=bfd` 设为任何包的默认值（HNP clang 15 真机必挂）；
- 反向把 `-fuse-ld=lld` 设为全局默认（部分 CI worker 的 lld 缺 libxml2.so.16）。

## 适用边界

- 环境定型两行命令：`$CC t.c -fuse-ld=bfd -o t`（报 invalid linker name →
  本环境无 bfd）；不注入能否出 PIE ELF（`file t | grep -i pie`）；
- conf 开关模式（`user.<pkg>:ld`）适用于任何"按环境二选一 linker"的配方。
