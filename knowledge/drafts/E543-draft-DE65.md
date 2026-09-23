# E543 — 新建文件补丁头必须用 `--- /dev/null`（patch_ng 拒收 `--- a/` 头）

## 错误特征

conan create 阶段 `apply_conandata_patches` 失败，日志含：

```
patch_ng: source/target file does not exist: <build>/patches/0001-xxx.patch
Failed to apply patch: <build>/patches/0001-xxx.patch
```

或 `git apply --check` 报补丁无法应用。

## 触发条件

- 构建系统: conan 配方（apply_conandata_patches）
- 阶段: build（打补丁）

## 根因分析

`refresh_patch.py` 在生成「新建文件」补丁时，若 `.orig` 工作目录已被污染
（例如 toybox `patch --dry-run` 对 new-file 补丁真实创建了目标文件，产生
0 字节 `.orig` 残留），会把这个本应是新文件的补丁重新判定为「修改已有文件」，
生成 `--- a/xxx` 补丁头。patch_ng 应用 new-file 补丁时要求源文件不存在，
遇到 `--- a/` 头且无对应源文件即拒收，导致 `conan create` 失败。

## 解决方案

### 推荐方案

1. 新建文件补丁首行统一写 `--- /dev/null`（`+++ b/...` 保持不变）。
2. 生成/刷新补丁前清空 `.orig` 中的 0 字节污染，避免 refresh 把新文件误判为修改。
3. 用干净解包重新生成补丁，并双验证：

```bash
git apply --check patches/*.patch
conan create . --build=missing
```

### 禁止做法

- ❌ 用 `--- a/` 头提交新建文件补丁——patch_ng 拒收，构建必然失败。
- ❌ 在污染过的 `.orig` 上直接 refresh-patch。

## 验证

```bash
git apply --check patches/0001-CMakeLists.txt.patch
git apply --check patches/0002-cmake-FindGSettings.cmake.patch
conan create . --build=missing
```

## 关联条目

- 相关: E544（FindGSettings shim）
