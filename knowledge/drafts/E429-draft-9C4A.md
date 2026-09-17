# E429 — 新增文件补丁头与 .orig 污染导致 conan patch_ng 失败

## 错误特征

```
[curtain/0.3] patches/000X-....patch: source/target file does not exist:
  --- b'a/<path>'
  +++ b'b/<path>'
ERROR: Error in source() method ... ConanException: Failed to apply patch
```

或（更早的错误）：`patch stream is incomplete!`（二进制文件被当作文本生成补丁）。

## 触发条件

- 构建系统: cmake（conan create，`apply_conandata_patches`）
- 阶段: source（打补丁）
- 场景: 归档补丁包含**新增文件**（如宿主工程、移植源码）

## 根因分析

1. Conan 2 使用 `patch_ng` 应用 `conandata.yml` 中的补丁，默认 `strip=0`；
   `patch_ng` 仅在补丁类型判定为 GIT/HG（需 `diff --git` 头）或源文件为 `/dev/null`
   时才正确规范化路径。若新增文件补丁写成 `--- a/<path>`（目标不存在），
   `patch_ng` 报 `source/target file does not exist`。
2. `refresh-patch` 生成新增文件补丁时用 GNU `patch --dry-run -p1` 校验，
   该校验会在 `.orig` 树中**创建同名空文件**；下一次 refresh-patch 把这些空文件
   当作已存在的基线文件，生成 `--- a/<path>` 形式的补丁，conan 随即失败，
   且 `.orig` 不再是纯净基线（空文件不改变 sha256 聚合值，但会误导分类）。

## 解决方案

### 推荐方案

- 新增文件补丁头必须是 `--- /dev/null` 与 `+++ b/<相对路径>`（本仓库 refresh-patch
  在 `.orig` 干净时即生成该格式，可直接被 `patch_ng` strip=0 应用）。
- 每次 refresh-patch 之后立即删除 `.orig` 下被 dry-run 创建的新增目录/空文件；
  若已被污染，先删除 `.orig` 中对应新增目录再重新生成补丁。
- 二进制文件（png/ico 等）不进补丁：由配方在 `package()` 阶段从上游源码复制到目标位置。

### 禁止做法

- 不要给补丁添加 `diff -ruN`/`diff --git` 头来"绕过"（pre-commit 会拒绝或与仓库规范冲突）。
- 不要把 `.orig` 中出现的空文件当作真实源码修改。
- 不要手工修改已生成的补丁，应重新运行 refresh-patch。

## 验证

```bash
python3 -c "import patch_ng; ps=patch_ng.fromfile('patches/0001.patch'); \
print(ps.items[0].source, ps.items[0].target); \
print(ps.apply(strip=0, root='/tmp/probe'))"
# 期望 source=b'/dev/null'、target=b'b/<path>'、apply=True 且生成相对路径文件
```

## 关联条目

- 相关: E540（CI runner PATH）、E463/E527（GTK/Broadway 适配背景）
