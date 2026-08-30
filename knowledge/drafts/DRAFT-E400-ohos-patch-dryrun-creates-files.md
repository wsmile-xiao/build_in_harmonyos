# E400 — OHOS 平台 patch --dry-run 会真实创建新文件（污染 .orig 基线目录）

## 错误特征

在 HarmonyOS PC (aarch64) 上执行 `patch --dry-run -p1` 时，本应"只预览不落盘"，
但实际会**真实创建**补丁中的新文件（0 字节占位文件）。例如：

```
$ printf -- '--- /dev/null\n+++ b/t.go\n@@ -0,0 +1 @@\n+x\n' | patch --dry-run -p1
creating t.go
$ ls t.go        # 文件确实被创建了！
```

下游症状：conan `apply_conandata_patches`（基于 patch_ng）应用新文件补丁时报：

```
source/target file does not exist:
  --- a/core.go
  +++ b/core.go
ConanException: Failed to apply patch: .../patches/0001-xxx.patch
```

## 触发条件

- 构建系统: 任意（Go/C/C++ 均会触发）
- 阶段: configuration（refresh-patch --auto 的 _dry_run 步骤）
- 平台: HarmonyOS PC

## 根因分析

1. HarmonyOS PC 的 GNU `patch` 在 `--dry-run` 模式下仍真实创建新文件
   （0 字节占位），与常规 Linux 行为不同。
2. skill 的 `refresh-patch --auto` 在 `.orig` 基线目录中对每个新文件补丁执行
   `patch --dry-run -p1` 做校验 → 新源文件（如 `core.go`）被写成 0 字节占位。
3. 下次 refresh-patch 看到 `.orig/core.go` "已存在"，把新增文件误判为"已修改文件"，
   生成 `--- a/core.go` 而非 `--- /dev/null` 的新文件补丁。
4. conan `apply_conandata_patches`（patch_ng）要求新文件补丁源路径为 `/dev/null`，
   `--- a/xxx` 无法解析 → 构建失败。
5. conan 缓存（recipe revision 未变）会复用旧导出，即使磁盘补丁已修正，
   conan create 仍用缓存里的旧补丁。

## 解决方案

### 推荐方案

1. **恢复干净基线**：每次 finish/refresh-patch 前，从原始 tarball 恢复 `.orig`，
   删除其中的 0 字节占位文件，使新增文件被正确识别为 `/dev/null` 新文件补丁。
   ```bash
   rm -f "${ORIG_DIR}"/core.go "${ORIG_DIR}"/core_test.go ...   # 清理占位
   ```
2. **清空 conan 缓存**：修改补丁后必须使 conan 重新导出，否则复用旧补丁。
   ```bash
   conan remove "captive/1.0.0*" -c
   ```
3. **校验补丁头**：生成后确认新文件补丁首行为 `--- /dev/null` 而非 `--- a/xxx`。

### 禁止做法

- ❌ 不要认为 `patch --dry-run` 无副作用而忽略；OHOS 上它会落盘。
- ❌ 不要只改磁盘补丁不清 conan 缓存——conan create 会用缓存旧导出。

## 验证

```bash
# 验证 dry-run 真实创建文件
printf -- '--- /dev/null\n+++ b/t.go\n@@ -0,0 +1 @@\n+x\n' | patch --dry-run -p1; ls t.go
# 验证补丁头格式
head -1 patches/0001-core.go.patch   # 应为 --- /dev/null
```

## 关联条目

- 相关: E282（apply patch 失败）、E058（补丁格式）
