# DRAFT-conan2-patch-tool-keyword-call

## 使用说明

Conan 2 配方手动应用 `patches/*.patch`（不用 conandata.yml）时，`patch()`
工具在不同 Conan 2.x 构建间存在**两重 API 漂移**：① 导出名（新版本有
`apply`，设备端旧构建只有 `patch`）；② `patch()` 的位置参数次序（设备端为
`(conanfile, base_path=None, patch_file=None, …)`）。本条给出一次过的
防漂移写法与本机校验流程，避免每轮真机烧一次窗口。

## 适用范围

- 触发一：真机 `conan create` 报
  `ImportError: cannot import name 'apply' from 'conan.tools.files'`。
- 触发二：报 `TypeError: patch() got multiple values for argument 'base_path'`
  （位置参数撞名——本机 conan 2.29.1 签名为
  `(conanfile, patch_file, base_path…)`，设备端为
  `(conanfile, base_path, patch_file…)`，次序相反）。
- 适用：所有需要在 source() 应用导出补丁、且不使用 conandata.yml patches
  段的配方；两台及以上 conan 部署（本机 Windows + 真机 runner）交叉验证
  的场景。

## 输入输出定义

- 输入：conanfile.py；`patches/*.patch`（必须 `exports_sources = "patches/*"`
  导出，否则 `export_sources_folder` 为 None）。
- 本机校验（30 秒，push 前必做）：
  ```python
  import inspect
  from conan.tools.files import patch
  print(inspect.signature(patch))
  # 若 ImportError → 该部署只能用 patch()；两台部署签名不一致 → 全关键字调用
  ```
- 输出：全关键字 `patch()` 调用；补丁路径取
  `os.path.join(self.export_sources_folder, "patches", "<file>")`。

## 示例

防漂移的标准形态（本机 2.29.1 与真机旧构建均通过）：

```python
import os
from conan.tools.files import get, patch   # 只 import patch，不要 import apply

class XConan(ConanFile):
    exports_sources = "patches/*"

    def source(self):
        get(self, url=_url, sha256=_sha, strip_root=True)
        patch(
            self,
            patch_file=os.path.join(
                self.export_sources_folder, "patches", "0001-fix.patch"),
            base_path=self.source_folder,
        )
```

## 不适用 / 反例

- 用 conandata.yml patches 段的配方应继续用
  `apply_conandata_patches(self)`（补丁路径/次序由 Conan 管理），不要混用
  本条的手动 `patch()`。
- 位置参数调用 `patch(self, "<path>", base_path=...)` 在设备端必然
  TypeError——这是本条要消灭的形态。
- `export_sources_folder` 在 build()/package() 阶段语义不同（None/源目录），
  本条只在 source() 内使用。

## 关联

与 E282（多源码配方每补丁独立 base_path）互补：E282 讲 base_path 该指向
哪里，本条讲 patch/apply 导出名漂移与参数次序漂移的统一防御写法。
