# Conan copy() excludes 按相对 src 完整路径 fnmatch 精确匹配，只写 basename 挡不住嵌套目录同名文件

- **草稿 ID**: DRAFT-lebiniou-data-3.67.0-conan-copy-excludes-relpath-fnmatch
- **来源**: lebiniou-data 3.67.0 HarmonyOS PC 适配（真机 conan 2.29.1 首验：`excludes=["Makefile.am"]` 只挡 src 顶层，10 个嵌套 Makefile.am 漏进安装树，消费者探针 16 条失败）
- **分类**: conan / recipe / packaging
- **状态**: 本地草稿（已挂 PR #12693，位于 knowledge/drafts/；路径 B 申请暂缓，等 inform6-compiler 路径 B 评审结果后决定）

## 问题 / 错误签名

- **嵌套同名文件漏装**：`copy(self, "*", src=..., dst=..., excludes=["Makefile.am"])` 意图排除构建文件，但排除只对 src 顶层生效；嵌套目录（图像主题目录、vue 子目录、sequences/json）里的同名 Makefile.am 全部被复制进 package_folder。
- **可观测特征**：安装树文件数多于预期（lebiniou-data 实测 1737 ≠ 1727，多出 10 个 Makefile.am）；消费者探针逐目录精确计数失败（`[FAIL] xxx has exactly N files (got M)`，共 16 条断言失败）。
- **复现**：真机 conan 2.29.1（HarmonyOS PC aarch64）直接复现；本地按 conan `_filter_files` 同款语义模拟（fnmatch 对相对路径逐文件整串匹配）可完全复现漏装集合。

## 根因

1. **conan `copy()` 的 excludes 匹配对象是"相对 src 的完整路径"**：`conan/tools/files/copy_pattern.py::_filter_files` 用 `os.walk(src)` 收集每个文件 `os.path.join(relative_path, f)` 的完整相对名，再 `fnmatch.fnmatch(f.lower(), exclude)`。模式不含通配符时必须与整条路径完全相等。
2. **basename 模式只等于 src 顶层文件**：`"Makefile.am"` 与 `"covid-19/Makefile.am"` 不匹配——fnmatch 是整串匹配，目录前缀直接导致失败。
3. **`**` 不是 fnmatch 的通配符**：fnmatch 的 `*` 本身可跨 `/`；`"**/X"` 退化为 `"*/X"`，而当 `*` 匹配空串时 `"*/X"` 变成 `"/X"`，仍不等于顶层 `"X"`——单一模式无法同时覆盖顶层与任意深度。

## 最小修复方案

在配方的 `package()` 内，对每个要排除的 basename 写两条模式：

```python
# 顶层精确匹配 + 任意深度前缀匹配（fnmatch 的 * 可跨 "/"）
copy(self, "*", src=..., dst=...,
     excludes=["Makefile.am", "*/Makefile.am"])
```

要点：

- `"*/Makefile.am"` 的 `*` 匹配任意级目录前缀，配合 `"Makefile.am"` 覆盖全部深度。
- 本地预验：按 conan `_filter_files` 同款语义（fnmatch 对完整相对路径）写模拟脚本跑解包源码树，断言"漏装 basename 数 = 0 且安装文件数 = 预期值"后再上真机。
- 真机复验：`conan create` 后 `find <package_folder> -name Makefile.am` 应为空；消费者探针逐目录精确计数全过。

回退方案（excludes 不可用时的兜底）：复制完成后显式清理：

```python
for root, _, files in os.walk(dst):
    for f in files:
        if f == "Makefile.am":
            os.remove(os.path.join(root, f))
```

该写法破坏 `copy()` 单步声明式语义，仅作兜底。

## 验证结果

| 环境 | 结果 |
|------|------|
| 本地（Windows）· 按 conan 2.29.1 `_filter_files` 语义模拟 | 修复前复现 10 个漏装；修复后漏装 0、安装文件数 1727 与预期一致 |
| HarmonyOS PC aarch64 真机 · Conan 2.29.1 | 修复前探针 4613 断言/16 失败；修复后 `conan-verify` G0-G4 全 PASS、探针 **4608 断言 0 失败、exit 0** |
| 消费者探针（test_package） | 逐目录精确计数 + "无 Makefile.am 残留"断言，修复后全过 |

## 禁止策略

- 禁止只写 basename 单模式（`excludes=["Makefile.am"]`）——只对 src 顶层生效，嵌套同名文件静默漏装，安装树漂移且构建不报错。
- 禁止用 `"**/X"` 单一模式试图覆盖全部深度——fnmatch 不识别 `**`（退化为两个 `*`），顶层文件仍漏网。
- 禁止"发现漏装后放宽测试计数而不是修配方"——漏装是配方缺陷，必须修排除声明；消费者逐目录精确计数断言正是抓此类漂移的手段，不应弱化。

## 相关

- 相似条目：E073（fallback 含 copy-replace-symlink，同属 conan copy 语义主题但方向不同）
- 关联经验：消费者探针"逐目录精确计数 + 无构建文件残留"断言是抓安装树漂移的有效手段（本条目由它真机首验抓出）
