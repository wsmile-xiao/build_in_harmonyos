# DRAFT-glpk-4.65-ohos-conan-os-version-rm-safe

> 草稿：OHOS conan profile 的 `os.version` 子设置在配方 `configure()` 中
> `rm_safe` 以通过 package_id 校验。触发自 glpk 4.65 适配（2026-09-16）。

## 问题描述

在 HarmonyOS PC（armv8）上执行：

```bash
conan create archives/g/glpk/4.65 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

报错：

```
glpk/4.65: Invalid: 'settings.os.version' value not defined
ERROR: There are invalid packages:
gmp/6.3.0: Invalid: 'settings.os.version' value not defined
```

即使把 profile 中的 `os.version=6.0` 行删掉仍复现——因为 `settings.yml`
为 `os=OHOS` 定义了 `version: ["5.0", "6.0"]` 子设置，当配方 settings 声明
（`"os", "arch", "compiler", "build_type"`）未包含 `os.version` 时，
conan 在计算 package_id 时对 settings 树做 `validate()`，`os.version` 节点
值缺失即抛 "value not defined"。

## 根因

- `ci/conan/profiles/ohos-aarch64` 设 `os.version=6.0`；
- `~/.conan2/settings.yml` 中 `OHOS: version: ["5.0", "6.0"]`；
- 配方未声明 `os.version` 时，settings 校验层不接受该子设置的缺失值。

## 修复（验证通过）

在配方 `configure()` 中守卫式 `rm_safe`：

```python
def configure(self):
    if hasattr(self.settings, "os") and hasattr(self.settings.os, "version"):
        self.settings.rm_safe("os.version")
    ...
```

删除 `os.version` 子设置后 package_id 可正常计算；依赖 gmp/6.3.0 的
graph 计算同步恢复。glpk/4.65 `conan create` 与 `conan-verify`（G1-G4）
实测全绿。

## 适用边界

- 适用：任意在含 `os.version` 的 OHOS profile 下 `conan create/verify` 的配方；
  本仓已有 8+ 配方（afdko、au、expect、fcheck、loom、mdurl、msgpack-cxx、
  astc-encoder）隐式使用同款修复。
- 反例/不适用：Windows 等无 `os.version` 子设置的平台不受影响（守卫天然安全）；
  若配方确实需要按 os.version 区分 package_id，则不应删，而应声明
  `settings = "os", "os.version", ...` 并显式维护其值。

## 验证证据（glpk 4.65 实测）

- `conan create`（修复前）: exit 6，`Invalid: 'settings.os.version' value not defined`
- 修复后 `conan create`: exit 0，test_package 5 断言全绿
- `conan-verify`: G0/G1/G2/G3/G4 全 PASS