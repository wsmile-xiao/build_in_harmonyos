---
name: ohos-build-code-style
description: 鸿蒙PC三方库适配项目的代码规范性标准。覆盖 conanfile.py、shell 脚本、C/C++ 测试源码、YAML/JSON 配置文件的编码规范与命名约定。供 AI 代码检视自动识别风格违规。
type: project
---

# 鸿蒙PC三方库适配 代码规范性标准

## 一、conanfile.py 规范

### 1. 文件头
必须有 shebang + docstring 说明软件名和构建系统：
```python
#!/usr/bin/env python3
"""Conan recipe — zlib 1.3.1 (CMake)"""
```

### 2. 类与属性
类名用 PascalCase，格式为 `{软件名}Conan`：
```python
class ZlibConan(ConanFile):
    name = "zlib"
    version = "1.3.1"            # 硬编码版本, 不读外部
    description = "..."          # 一句话英文描述
    license = "Zlib"
    homepage = "https://..."
    settings = "os", "compiler", "build_type", "arch"
```
禁止 `package_type` 留空或写错（库=`"library"`，工具=`"application"`）。

### 3. 方法顺序
标准顺序：`export_sources` → `requirements` → `layout` → `source` → `generate` → `build` → `package` → `package_info`。不可随意调换。

### 4. 包信息
`package_info()` 必须设置 `cpp_info.libs`：
```python
def package_info(self):
    self.cpp_info.libs = ["zlib"]
```
工具类必须设置 `cpp_info.bindirs`：
```python
    self.cpp_info.bindirs = ["bin"]
```

### 5. 禁止残留模板占位符
以下内容出现在合入的代码中 = 未完成：
- `TODO`、`FIXME`、`XXX`
- `pass  # TODO: implement`
- `url = ""  # CI fills this`（应由适配者填写）

---

## 二、shell 脚本规范

### 6. 文件头
```bash
#!/usr/bin/zsh
# ci/conan/build_and_test.sh — 一句话说明
```

### 7. 安全模式
所有脚本必须以安全模式开头：
```bash
set -euo pipefail
```
- `set -e`：命令失败即退出
- `set -u`：未定义变量报错
- `set -o pipefail`：管道中任意命令失败即失败

### 8. 变量引用
```bash
# 正确 — 双引号包裹
conan create "$CONANFILE" -pr="$PROFILE"
# 错误 — 裸变量, 含空格时会断裂
conan create $CONANFILE -pr=$PROFILE
```

### 9. 输出格式
步骤标记用 `[step]`，成功用 `[ok]`，失败用 `[fail]`，警告用 `[warn]`：
```bash
echo "[step] L0i: Checking dependencies..."
echo "        [ok] all dependencies published"
echo "        [fail] missing dependency: openssl/1.1.1w"
echo "[hint]  请先发布 openssl/1.1.1w"
```
`[ok]`/`[fail]` 前加 8 空格缩进，对齐步骤输出。

### 10. 错误处理
禁止 `|| true` 吞掉错误（除非有明确注释说明为何忽略）：
```bash
# 错误 — 静默吞错
conan download "$REF" || true
# 可接受 — 有注释说明
rm -f "$TMPDIR"/* 2>/dev/null || true  # tmp 可能不存在
```

---

## 三、C/C++ 测试源码规范

### 11. test_package 源文件
- 文件名用小写：`example.c` / `test_main.cpp`
- 必须有 `main()` 函数且返回 `int`
- 头文件引用必须与被测包的 `cpp_info.libs` 对应

```cpp
// 正确 — 调用真实 API
#include <zlib.h>
int main() {
    z_stream strm;
    strm.zalloc = Z_NULL;
    return zlibVersion() == NULL ? 1 : 0;
}
```

### 12. 补丁文件规范
- 文件名格式：`{序号4位}-{源文件路径用连字符}.patch`
- 例：`0001-build-aux-config.guess.patch`
- patch_description 用空格分隔（非连字符）：`"0001 build aux config.guess"`
- patch_type 固定 `"portability"`

---

## 四、YAML/JSON 规范

### 13. conandata.yml
```yaml
sources:
  url: "https://..."        # 必须 HTTPS, 带引号
  sha256: "abc123..."       # 必须有, 带引号

patches:
  - patch_file: "patches/0001-xxx.patch"
    patch_description: "0001 xxx"
    patch_type: "portability"
```
- 缩进 2 空格
- 字符串值带双引号
- URL 禁止用 `http://`（除非上游不支持 HTTPS）

### 14. manifest.yaml
```yaml
name: zlib
version: "1.3.1"
build_system: cmake          # cmake | autotools | makefile | meson
status: published            # published | built | failed
```

### 15. commands.json
- 缩进 2 空格
- 字符串值带双引号
- `type` 只能是 `"tool"` 或 `"library"`
- 禁止尾逗号

```json
{
  "name": "strace",
  "type": "tool",
  "versions": {
    "6.19": { "ref": "strace/6.19", "binary": true }
  }
}
```

---

## 五、Python 脚本规范

### 16. import 顺序
标准库 → 第三方库 → 项目内部，组间空行：
```python
import os
import re

from conan import ConanFile
from conan.tools.cmake import CMake

from .utils import log_info
```

### 17. 函数命名
- 公有函数：`snake_case`
- 私有函数：`_snake_case`（前缀下划线）
- 类名：`PascalCase`
- 常量：`UPPER_SNAKE_CASE`

### 18. 类型注解
项目内部脚本（`scripts/ohc/`）推荐加类型注解，conanfile.py 不强制：
```python
def _parse_manifest(manifest_path: Path) -> dict:
```

### 19. 日志输出
```python
from .utils import log_info, log_ok, log_warn, log_fail

log_info("Checking dependencies...")
log_ok("All dependencies published")
log_warn("Missing commands.json for CLI tool")
log_fail("Dependency not found: openssl/1.1.1w")
```
禁止 `print()` 直接输出（调试用途除外，合入前需删除）。

---

## 六、Git 提交规范

### 20. commit message
```
type(scope): 简短描述（中文）

可选详细说明
```
type 取值：`feat`(新功能) / `fix`(修复) / `chore`(杂项) / `refactor`(重构) / `docs`(文档)
scope 取值：软件名 或 模块名（如 `R38`、`zlib`、`CI`）

### 21. 行尾
- 文本文件用 LF（Unix 风格），禁止 CRLF
- 文件末尾保留一个空行
