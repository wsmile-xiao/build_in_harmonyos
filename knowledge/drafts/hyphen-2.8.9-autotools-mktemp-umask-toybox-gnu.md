# autotools config.status 临时目录 Permission denied：toybox vs GNU mktemp 的 umask 行为差异

> 草稿（DRAFT）。与同目录 `hyphen-2.8.9-autotools-mktemp-umask-toybox-gnu.kv` 成对。
> 关联：E011（主条目，umask 077+config.status 家族）、DRAFT-6507-cln-mktemp-0700-hmdfs（GNU mktemp 恒 0700 变体）。

## 现象

autotools 项目在 HarmonyOS PC（HMDFS）上 configure 时：

```text
./config.status: line 797: ./confDIJ5Ce/subs1.awk: Permission denied
config.status: error: could not setup config files machinery
```

本地手动 configure 与 conan create（`conan create ... -pr:h=ci/conan/profiles/ohos-aarch64`）均复现。

## 根因

config.status 硬编码创建临时目录：

```sh
tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&
...
(umask 077 && mkdir "$tmp")
```

HMDFS 上 uid 被映射（目录属主显示 20001006，而进程实际 uid 是 20020101 等），
`umask 077` 创建的目录为 `drwx--S--- 2700`（setgid 由 HMDFS 强制），当前进程
既非属主也无组权限 → 无法在其中创建 `subs1.awk`。

关键分诊点：**修复处方取决于 mktemp 的具体实现**：

| mktemp 实现 | 行为 | 有效处方 |
|---|---|---|
| toybox（设备 `/usr/bin/mktemp -> /system/bin/toybox`，0.8.12） | 目录模式遵循 umask；`umask 002` 时创建 `drwxrws--x 2771`（组可写） | E011 处方（umask 放宽到 002）直接有效 |
| GNU coreutils（部分 CI/worker `/usr/local/bin/mktemp`，165760B） | `mktemp -d` 恒以 0700 创建，umask 放宽无效 | DRAFT-6507 处方（`mkdir -m 0777` 或 `$$-$RANDOM` fallback） |

设备与 CI worker 的 mktemp 实现可能不同，修复前先确认解析到的 mktemp：
`readlink -f $(command -v mktemp)`。

## 方案（toybox 环境，本库实证）

补丁将 configure 中两处 `umask 077` → `umask 002`（config.status 由 configure
生成，随之为 2771 组可写目录）：

```bash
sed -i 's/umask 077 \&\& mktemp -d/umask 002 \&\& mktemp -d/g' configure
sed -i 's/(umask 077 \&\& mkdir/(umask 002 \&\& mkdir/g' configure
```

Conan 配方中以 `conandata.yml` patches 固化（`apply_conandata_patches` 在
build() 先于 configure 应用）。

若不便改 configure：可在 PATH 前置组可写 umask 的 mktemp 包装（见 .kv
fallback_command），注意 conanbuild env 的 PATH 前缀会覆盖自制包装，须确认
解析顺序。

## 验证（hyphen/2.8.9，2026-09-21，HarmonyOS PC aarch64）

1. 设备 `/usr/bin/mktemp` 为 toybox 0.8.12：
   - `(umask 002 && /usr/bin/mktemp -d ./confXXXXXX)` → `drwxrws--x 2771`，写入 OK；
   - `(umask 077 && mktemp -d ./confXXXXXX)` → `drwx--S--- 2700`，写入 Permission denied。
2. 补丁 0003（umask 077→002，两处）应用后：
   - 手动 `./configure` 通过，`make`、`make check`（37/37 PASS）通过；
   - `conan create`（ohos-aarch64 profile）G2 全绿，test_package L1 实跑通过；
   - 日志：`archives/h/hyphen/2.8.9/reports/conan-create.log`。

## 适用边界与反例

- **适用**：任何 autotools 包在 HMDFS/HarmonyOS 上遇到 `config.status ... subs1.awk:
  Permission denied`，且解析到的 mktemp 为 toybox（umask 生效）。
- **反例**：若 mktemp 为 GNU coreutils（umask 放宽无效，目录仍 0700），须改用
  DRAFT-6507 的 `mkdir -m 0777` 路径；chmod 事后修复在 HMDFS 上被忽略（E046），
  不能作为补救。

## 查重差异（vs DRAFT-6507）

- DRAFT-6507 断言 "mktemp -d 恒 0700、umask 放宽无效" 且以 cln/1.3.7 实证；
  本条以 hyphen/2.8.9 实证 toybox mktemp 遵循 umask（002→2771 可写），
  E011 处方在该环境直接有效 —— 两条合起来构成 **mktemp 实现分诊边界**
  （先确认实现，再选处方），互不否定。
