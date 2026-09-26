# DRAFT-probcons-1.12-toybox-patch-cannot-apply-unified-diff-use-conan-patchng

**机制**：鸿蒙 PC 的 `/usr/bin/patch` 是 toybox 实现，对字节正确的标准 unified diff 报 `Hunk FAILED`，对自产 diff 的回环应用也会内容漂移 ⇒ 一切经外部 `patch` 命令的补丁管线不可信；补丁统一改走 **conan 内置 patch-ng**（`conandata.yml` 的 `patches:` 两键声明 + `patch_strip` 显式 + 配方 `export_conandata_patches`/`apply_conandata_patches`），验证以 conan-verify 的补丁检查为准，不依赖 patch 退出码。

## 症状与签名（probcons 1.12 实证）

- 字节正确的标准 unified diff，toybox `patch` 报 `Hunk #N FAILED`；
- 用 toybox 自产的 diff 回环 `patch` 应用，结果内容仍漂移；
- `conan-verify` 实证：同一补丁由 conan 内置 patch-ng 应用则逐字节正确（本包 patches/0001-Main.cc.patch 经 G3/L4 验证通过）。

## 根因

toybox patch 的 hunk 解析/应用实现与 GNU patch 语义不兼容，且失败语义同样不可信（假败与静默错改都无法用退出码区分）。E254 记录其 `--dry-run` 真实应用 new-file 补丁的污染变体；本条是更基础的一层：正常应用就不保真。

## 已试方案（含失败）

- 外部 `patch` 命令（标准用法、`--dry-run` 预检、回环自检）：全部不保真，弃用。
- 安装 GNU patch 替代：污染环境、CI 不可复现，仅可作临时人工排查（E254 fallback 同口径），不作为方案。

## 最终方案与验证

补丁全部走 conan patch-ng（本包实证：`patches/0001-Main.cc.patch` + `patch_strip: 1`，conan-verify G3/L4 pass；该补丁同时是 K0 合规实例——ParseParams 最小补丁使主命令 `probcons --help/--version` rc=0，主命令名与包名一致故无需包装入口，与 lammps 的包装入口条互为 K0 两路径）。

## 适用边界 / 反例 / 风险

- 补丁语义简单稳定时可等价改写为配方内 python 文本替换（不发补丁文件）。
- 需要按条件跳过的补丁用 patch_ng 的 patch options；不要为此退回 shell patch。
- 二进制文件补丁不适用文本 patch 工具链（另行处理，不在本条范围）。

## 查重与新增价值

- knowledge/graph E254 为 `--dry-run` 管线污染变体，其 fallback（装 GNU patch）与本条结论相反；本条主机制（toybox patch 正常应用不保真 ⇒ 强制 conan patch-ng）在 E254 无覆盖（`grep -rn toybox knowledge/graph/*.kv` 仅 E254 命中，且不含本签名）。
- 新增价值：把「外部 patch 不可信」从个案教训升为可预扫描的机制条目（prescan 可搜配方/脚本内的 `patch ` 命令调用），并给出与 K0 补丁实例的组合用法。
