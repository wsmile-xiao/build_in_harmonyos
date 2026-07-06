---
name: ohos-build-review-rules
description: 鸿蒙PC三方库适配项目的 PR 审查规则。检查 conanfile.py 配方规范、CI 门禁逻辑、版本号策略、依赖引用格式、测试包质量等。适用于 C/C++ 库适配到 HarmonyOS PC (arm64) 场景。
type: project
---

# 鸿蒙PC三方库适配 PR 审查规则

本项目将开源 C/C++ 库适配到 HarmonyOS PC 平台 (arm64)，使用 Conan 2.x 管理依赖和发布。以下规则在 PR 审查中**必须全部检查**。

## 一、conanfile.py 配方审查（最常见 PR 类型）

### 1. 依赖引用格式 (R27) — 关键
依赖引用必须使用**无 channel 格式**，不加 `@ohpcd/stable`：

```python
# 正确
self.requires("zlib/1.3.1")
self.requires("openssl/1.1.1w")

# 错误 — 会导致制品仓匹配失败
self.requires("zlib/1.3.1@ohpcd/stable")
```

### 2. 版本号策略 (R37) — 关键
- 首次适配：版本号 = 上游版本（如 `1.3.1`）
- 适配修复（修改 conanfile.py/conandata.yml）：版本号加后缀（`1.3.1.1`、`1.3.1.2`）
- 原因：cnb.cool 制品仓不支持同版本多 revision 并存（上传新 revision 返回 409）
- 如果 PR 修改了已发布版本的 conanfile.py，**必须递增版本号后缀**

### 3. 系统同名库静态链接 (R26)
库名与系统库同名时（如 `zlib`、`openssl`、`libxml2`），必须静态编译，避免污染目标系统的 `/lib`、`/lib64`：

```python
def generate(self):
    tc = CMakeToolchain(self)
    tc.variables["BUILD_SHARED_LIBS"] = False  # 静态
    tc.generate()
```

### 4. OHOS 平台兼容 (R32)
`settings.os` 判断必须用 `in ("Linux", "OHOS")`，不能只写 `== "Linux"`：

```python
# 正确
if self.settings.os in ("Linux", "OHOS"):
    ...

# 错误 — HarmonyOS PC 场景下会漏匹配
if self.settings.os == "Linux":
    ...
```

### 5. 禁止裸用 shell 环境变量 (R33)
编译器和编译标志必须从 Conan Toolchain 或 `self.conf_info` 获取：

```python
# 正确
tc = CMakeToolchain(self)
tc.variables["CMAKE_C_FLAGS"] = "-fPIC"

# 错误 — release worker 上 shell 变量为空，静默失败
os.environ["CC"] = "aarch64-linux-gnu-gcc"
os.environ["CFLAGS"] = "-fPIC"
```

### 6. test_package 必须实质测试 (R34)
test_package 的源文件必须**调用被测包的 API** 或执行被测包的二进制：

```python
# 正确 — 调用了 zlib 的压缩 API
from conan import ConanFile
from conan.tools.cmake import CMake

class TestZlib(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cmake = CMake(self)
        cmake.test()
```

```cpp
// test_package/src/example.cpp — 正确
#include <zlib.h>
int main() {
    z_stream strm;
    strm.zalloc = Z_NULL;
    zlibVersion();  // 实际调用被测包 API
    return 0;
}
```

禁止只打印字符串的空壳测试（如 `printf("hello\n"); return 0;`）。

### 7. conandata.yml 安全规范
源码 URL 必须使用 HTTPS，且必须包含 `sha256` 校验：

```yaml
# 正确
sources:
  "1.3.1":
    url: "https://github.com/madler/zlib/releases/download/v1.3.1/zlib-1.3.1.tar.gz"
    sha256: "1234567890abcdef..."

# 错误 — 缺少 sha256
sources:
  "1.3.1":
    url: "http://example.com/zlib-1.3.1.tar.gz"
```

## 二、PR 结构审查

### 8. PR 原子性 (W2)
- 一个 PR **只允许包含一个配方软件**及其知识图谱草稿
- 对 `ci/`、`scripts/`、`SKILL.md`、`references/`、`templates/` 的修改必须**单独提交 PR**
- 配方 PR 和框架 PR 混合 = **要求拆分**

### 9. 文件权限边界
协作者提交的 PR **不得修改**以下文件（主编专属）：
- `SKILL.md` / `references/` / `templates/`
- `scripts/` / `ci/`
- `index.tsv` / `SUMMARY.md`

### 10. 归档目录规范
配方文件必须放在 `archives/` 下的标准路径：
```
archives/{首字母}/{软件名}/{版本}/
  ├── conanfile.py
  ├── conandata.yml
  ├── test_package/
  │   ├── conanfile.py
  │   └── src/
  └── notes.md
```

## 三、制品仓与依赖链审查

### 11. 依赖发布优先级 (R36)
如果 PR 中的配方依赖了其他包，那些依赖包**必须已经发布到制品仓**。检查方法：

```bash
# R35: 禁止用 conan list 判断（cnb.cool 搜索 API 对 binary 返回不完整）
# 必须用 conan download 验证
conan download "zlib/1.3.1" -r=ohpcd --only-recipe
```

多层依赖链（C→B→A）必须按拓扑序 A→B→C 逐层发布。

## 四、CI 门禁逻辑审查（仅当 PR 修改 ci/ 目录时）

### 12. L0i 门禁
检查 conanfile.py 中的依赖引用格式和依赖发布状态。PR 阶段为 warn（软提示），release 阶段为 fail（硬拦截）。

### 13. L0j 门禁
检查版本号是否与制品仓中已有版本冲突。如果制品仓已有同名同版本，且 conanfile.py 内容不同，直接 fail。

### 14. 禁止用 conan list 判断 binary (R35)
CI 脚本中判断预编译包是否存在时，必须用 `conan download` 或 `conan install --requires=`，禁止用 `conan list`（cnb.cool 搜索 API 对 binary 返回不完整）。

## 五、通用代码规范

### 15. shell 脚本
- 使用 `set -euo pipefail` 开头
- 变量引用加双引号：`"$VAR"` 而非 `$VAR`
- 不使用 `--recipe`（已废弃），Conan 2.x 正确参数是 `--only-recipe`

### 16. Python 脚本
- conanfile.py 中 `from conan import ConanFile`（不是旧版 `from conans`）
- 使用 `conan.tools.cmake`（不是旧版 `cmake`）
- Python 3 类型注解可选，不强制
