# E429 — refresh-patch --auto 重命名补丁后 conandata.yml 的 patch_file 路径失效

## 错误特征

`finish`（或 `conan-verify`）在补丁相关步骤失败，输出形如：

```
❌   ❌ build_and_test.sh 失败 (RC=1)
❌     L1_RESULT=fail: conan create failed
❌     [hint] patch 文件路径或格式错误
❌                   请检查 conandata.yml 中 patch_file 路径与 patches/ 目录下文件是否一致
```

同时在同一个 finish 日志的前部，`refresh-patch --auto` 步骤会把补丁文件按工具约定改名：

```
0001-CMakeLists.txt.patch (0 files, +90/-16)
0002-src-misc.c.patch (0 files, +6/-1)
```

而 `conandata.yml` 里仍然是作者手工写的描述式文件名（本次实测：
`patches/0001-ohos-cmake-portability.patch`、`patches/0002-ohos-wconversion-cast.patch`）。

## 触发条件

- 构建系统: 任意（本例为 CMake）
- 阶段: 补丁生成 / 配方验证（`finish`、`conan-verify` G2、本地 CI W3）
- 前提: 作者曾手工命名 `patches/` 内文件，并在 `conandata.yml` 的 `patch_file` 中引用该名字
- 触发动作: 任何再次调用 `refresh-patch --auto` 的流程（`finish` 内部即会调用）

## 根因分析

`scripts/ohc/refresh_patch.py` 的 `--auto` 模式固定用「序号-源文件相对路径」命名补丁
（`NNNN-<path>`，`/` 换成 `-`），这是仓库内主流命名约定（本地统计：`CMakeLists.txt.patch`
563 处、`configure.patch` 351 处…）；但它**不回写 `conandata.yml`**。

于是出现两套事实来源：`patches/` 内文件名（工具命名）与 `conandata.yml` 的 `patch_file`
（作者命名）。第二次 `refresh-patch --auto` 之后二者分叉，Conan 的
`apply_conandata_patches()` 按 `conandata.yml` 去找文件 → 找不到 → `conan create` 失败
→ G2 与 W3 连锁失败。因为错误信息只以「patch 文件路径或格式错误」的提示出现，
真实原因（改名）容易被误判为补丁内容/格式问题。

## 解决方案

### 推荐方案

以 `patches/` 目录内**实际文件名**为唯一事实来源，把 `conandata.yml` 的每个
`patch_file` 改成工具命名：

```bash
ls archives/<字母>/<包>/<版本>/patches/
# → 0001-CMakeLists.txt.patch  0002-src-misc.c.patch
grep -n patch_file archives/<字母>/<包>/<版本>/conandata.yml
# → patch_file: "patches/0001-ohos-cmake-portability.patch"   # ← 旧名，需改成 0001-CMakeLists.txt.patch
```

改完在**纯净源码**上逐个 `patch --dry-run -p1` 验证可应用，再跑
`python3 scripts/ohc-run.py conan-verify <包> <版本>` 确认 G2 通过。

### 禁止做法

- ❌ 直接 `mv` 改 `patches/` 内文件名而不更新 `conandata.yml`（换个方向的分叉，同样失败）
- ❌ 手写补丁文件绕过 `refresh-patch`（无法保证与工作目录源码逐字一致，违反 R8）
- ❌ 看到「patch 文件路径或格式错误」就去改补丁的 `-p` 层级 / 补丁内容
  （真正的分叉在文件名，不在 strip 层级）

## 验证

```bash
# 1. 文件名与 conandata 引用一致（无 MISSING）
python3 -c 'import pathlib;d=pathlib.Path("archives/<字母>/<包>/<版本>");t=(d/"conandata.yml").read_text();print("\n".join(f"{p.name} {\"ok\" if p.name in t else \"MISSING\"}" for p in sorted((d/"patches").glob("*.patch"))))'

# 2. 补丁仍可应用到纯净源码
cd <纯净源码目录> && for f in <归档>/patches/*.patch; do patch --dry-run -p1 < "$f"; done

# 3. 门禁复验
python3 scripts/ohc-run.py conan-verify <包> <版本>     # 期望 G0-G4 + L2/L4/L5 全 PASS
python3 scripts/ohc-run.py finish <包> <版本> published
```

## 关联条目

- 相似: E484（patch --dry-run 真实创建文件污染 .orig 基线，同属 refresh-patch 家族）
- 相似: E254（toybox patch --dry-run 会真实应用 new-file 补丁）
- 相似: E282（多源码 Conan 配方需为每个补丁声明独立 base_path）
