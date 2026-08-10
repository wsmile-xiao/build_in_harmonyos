# E216：多源码 Conan 配方必须为每个补丁声明独立 `base_path`

## 错误特征
同一 recipe 下载多个源码包后，补丁阶段出现：

```text
Failed to apply patch: patches/000x-component.patch
can't find file to patch
```

或者为了修复某个嵌套源码而给全部补丁硬编码同一个 `base_path`，使原本属于主源码
的补丁随后必然在错误目录应用。

## 触发条件
- 构建系统: Conan 2，底层构建系统不限
- 阶段: source/build 前的补丁应用
- 源码布局: `self.source_folder` 下同时存在主源码根和一个或多个嵌套配套源码目录。

## 根因分析
补丁路径是相对某个源码根生成的。多源码 recipe 中，不同补丁可能分别面向
`self.source_folder` 和 `self.source_folder/nested-source`。单一硬编码
`base_path` 无法同时满足这两个根目录。

Conan 2.29.1 的 `apply_conandata_patches()` 会复制每个 conandata patch 条目，并
把除 `patch_file` 外的字段作为关键字参数传给 `patch()`；`patch()` 原生接受
`base_path`。因此无需自写路由 helper，只需在每条补丁元数据中声明正确根目录。

## 解决方案

### 推荐方案
在 `conandata.yml` 为每个补丁逐条声明相对 `self.source_folder` 的根目录：

```yaml
patches:
  - patch_file: patches/0001-main.patch
    base_path: "."
  - patch_file: patches/0002-toolchain.patch
    base_path: "toolchain"
```

配方使用标准 helper：

```python
apply_conandata_patches(self)
```

`export_conandata_patches(self)` 继续按 `patch_file` 导出补丁，不受 `base_path` 影响。

### 禁止做法
- 不要为异构补丁集硬编码单一 `base_path`。
- 不要用 build() 中的临时 `sed` 或 `copy` 代替可复现补丁。
- 不要把绝对机器路径写入 `base_path`；应保持相对 `self.source_folder`。

## 验证
```bash
export SOURCE_ROOT=/actual/materialized/source
export RECIPE_DIR=/actual/recipe
python3 - <<'PY'
import os
import subprocess
from pathlib import Path

import yaml

source = Path(os.environ["SOURCE_ROOT"])
recipe = Path(os.environ["RECIPE_DIR"])
entries = yaml.safe_load((recipe / "conandata.yml").read_text())["patches"]
for entry in entries:
    patch_file = recipe / entry["patch_file"]
    base_path = source / entry.get("base_path", ".")
    with patch_file.open("rb") as stream:
        subprocess.run(
            ["patch", "--dry-run", "--fuzz=0", "-p1", "-d", str(base_path)],
            stdin=stream,
            check=True,
        )
PY
```

该循环读取当前 recipe 的每个真实 `patch_file`/`base_path` 配对，不依赖示意文件名。

## 关联条目
- 原则: P005（可上游补丁）、P011（补丁元数据）
- 来源: Conan 2.29.1 `conan/tools/files/patches.py`；Cling 1.3 双源码配方
