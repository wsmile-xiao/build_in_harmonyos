---
name: ohos-build-review-rules
description: 鸿蒙PC三方库适配项目的 PR 审查规则。覆盖配方正确性、欺骗性行为检测、文件规范、安全边界。适用于 C/C++ 库适配到 HarmonyOS PC (arm64) 场景的 Conan 2.x 制品仓体系。
type: project
---

# 鸿蒙PC三方库适配 PR 审查规则

本项目将开源 C/C++ 库适配到 HarmonyOS PC 平台 (arm64)，使用 Conan 2.x 管理依赖和发布到 cnb.cool 制品仓。PR 分两类，审查重点不同：

- **配方 PR**（archives/ 下的文件）→ 重点审查类别一、二、三
- **框架 PR**（ci/scripts/SKILL.md 等文件）→ 重点审查类别四、五

---

## 一、欺骗性行为检测（⭐ 最高优先级）

以下行为一律 **request changes / reject**，不论其他检查是否通过。

### 1. 空壳测试 (R34 违规)
test_package 必须调用被测包的 API 或执行被测包的二进制。以下属于欺骗性空壳测试：

```cpp
// 欺骗：只打印，不调用任何被测包 API
int main() { printf("test passed\n"); return 0; }

// 欺骗：include 了头文件但不调用任何函数
#include <zlib.h>
int main() { return 0; }

// 正确：实际调用 API
#include <zlib.h>
int main() { return zlibVersion() ? 0 : 1; }
```

### 2. 跳过测试 / 伪造通过 (R9 违规)
```python
# 欺骗：test() 方法为空或只 return
def test(self):
    pass

# 欺骗：注释掉失败的自定义测试步骤
def test(self):
    # cmake.test()  # commented out because it fails
    pass

# 欺骗：用 exit 0 强制通过
def test(self):
    os.system("exit 0")
```

### 3. 伪造状态标记
conanfile.py 中不应出现硬编码的状态覆盖。manifest.yaml 的状态值必须真实反映验证结果：
- `published`：conan-verify 全部门禁通过 + CI upload 成功
- `built`：conan-verify 通过但未 upload
- `failed`：编译或验证失败
- 禁止将 failed 标记为 published 或 built

### 4. 伪造 sha256 / 绕过校验
conandata.yml 中的 sha256 必须是真实的源码包哈希值。以下属于欺骗：
- sha256 值为全零、全 f、或明显不完整的值
- 删除 sha256 字段以跳过校验
- 使用与源码包不匹配的 sha256 值

### 5. 禁止 `#ifdef __OHOS__` 条件编译 (R8)
源码中不得引入平台条件编译宏。HarmonyOS PC 兼容 Linux ABI，应通过标准 POSIX 接口适配，不改源码逻辑：

```c
// 禁止：为通过编译而添加的平台条件
#ifdef __OHOS__
    return 0;  // 跳过不兼容的功能
#endif

// 正确：直接用 POSIX 接口，或通过 conanfile.py 的 patch 处理
```

如果 PR 包含 patches/ 目录下的补丁文件，检查补丁内容是否引入了 `#ifdef __OHOS__`。

### 6. 手动打包绕过 conan create (R19)
禁止在 PR 中包含预编译的 `.so`/`.a`/二进制文件。所有产物必须通过 CI 的 `conan create` 从源码构建：

```
# 禁止出现在 PR 中：
archives/z/zlib/1.3.1/prebuilt/libz.a    ← 预编译产物
archives/z/zlib/1.3.1/prebuilt/zlib.h     ← 手动复制头文件
```

---

## 二、conanfile.py 配方质量

### 7. 版本号策略 (R37)
- 首次适配：版本号 = 上游版本（如 `1.3.1`）
- 适配修复（修改 conanfile.py/conandata.yml）：版本号加后缀（`1.3.1.1`）
- 如果 PR 修改了已发布版本的 conanfile.py，必须递增版本号后缀

### 8. 系统同名库静态链接 (R26)
库名与系统库同名时（如 `zlib`、`openssl`、`libxml2`、`ncurses`），必须静态编译：

```python
def generate(self):
    tc = CMakeToolchain(self)
    tc.variables["BUILD_SHARED_LIBS"] = False
    tc.generate()
```

### 9. OHOS 平台兼容 (R32)
`settings.os` 判断必须用 `in ("Linux", "OHOS")`：

```python
# 正确
if self.settings.os in ("Linux", "OHOS"):
    ...

# 错误 — OHOS 场景下漏匹配
if self.settings.os == "Linux":
    ...
```

### 10. 禁止裸用 shell 环境变量 (R33)
编译器和标志必须从 Conan Toolchain 获取，不能裸用 shell 变量（release worker 上为空→静默失败）：

```python
# 错误
os.environ["CC"] = "aarch64-linux-gnu-gcc"
os.environ["CFLAGS"] = "-fPIC"

# 正确
tc = CMakeToolchain(self)
tc.variables["CMAKE_C_FLAGS"] = "-fPIC"
```

### 11. conandata.yml 规范
- 源码 URL 必须使用 HTTPS
- 必须包含 sha256 校验
- 补丁文件必须在 patches 字段中声明，且文件实际存在于 patches/ 目录

```yaml
sources:
  "1.3.1":
    url: "https://github.com/madler/zlib/releases/download/v1.3.1/zlib-1.3.1.tar.gz"
    sha256: "1234567890abcdef..."

patches:
  "1.3.1":
    - patch_file: "patches/001-fix-cmake.patch"
      patch_description: "Fix CMake flags for OHOS"
      patch_type: "portability"
```

### 12. 只改源文件不改生成文件 (R6)
PR 中不应包含对自动生成文件的修改（如 `config.h`、`configure`、`Makefile.in`、`CMakeCache.txt`）。如果需要修改构建系统行为，应通过：
- conanfile.py 的 `generate()` 方法设置 CMake 变量
- patches/ 目录下的补丁文件（仅修改源文件）
- 不直接修改 configure 脚本等生成产物

### 13. Conan 2.x API 规范
```python
# 正确 — Conan 2.x
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout

# 错误 — Conan 1.x 旧 API（已废弃）
from conans import ConanFile
from conans.tools import CMake
```

---

## 三、文件规范与归档结构

### 14. 归档目录结构
配方文件必须放在标准路径下：
```
archives/{首字母}/{软件名}/{版本}/
  ├── conanfile.py           # 【必须】Conan 配方
  ├── conandata.yml          # 【必须】源码 + 补丁声明
  ├── test_package/          # 【必须】Conan 测试包
  │   ├── conanfile.py
  │   └── src/
  │       └── example.c
  ├── patches/               # 【可选】补丁文件
  ├── manifest.yaml          # 【AI 元数据】
  └── notes.md               # 【AI 元数据】
```

缺失 conanfile.py / conandata.yml / test_package/ 中的任何一个 = **request changes**。

### 15. 补丁文件规范 (R3)
- 补丁只能通过 `ohc-run.py refresh-patch --auto` 生成
- 不得手动创建 .patch 文件后直接提交
- 补丁文件名应有序编号（001-、002-...）
- 补丁内容不得修改自动生成文件（configure、Makefile.in 等）

### 16. PR 中不应包含的文件
以下文件出现在 PR 中应标记为 **需要清理**：
- `.build-context-*`（构建上下文临时文件）
- `test-report`（测试报告临时文件）
- `*.log`（日志文件）
- `.DS_Store` / `Thumbs.db`（系统文件）
- `__pycache__/`（Python 缓存）
- 预编译二进制文件（.o / .so / .a / 可执行文件）

---

## 四、PR 合规性审查

### 17. PR 原子性 (W2)
- 一个 PR 只允许包含一个配方软件及其知识图谱草稿
- 对 `ci/`、`scripts/`、`SKILL.md`、`references/`、`templates/` 的修改必须单独提交 PR
- 配方 PR 和框架 PR 混合 = **要求拆分**

### 18. 文件权限边界
协作者提交的 PR **不得修改**以下文件（主编专属）：
- `SKILL.md` / `references/` / `templates/`
- `scripts/` / `ci/`
- `index.tsv` / `SUMMARY.md`
- `knowledge/graph/index.tsv`（主编通过 graph promote 维护）

如果协作者 PR 包含对以上文件的修改 = **标记越权，要求移除**。

### 19. 依赖发布优先级 (R36)
如果 PR 中的配方依赖了其他包，检查那些依赖是否已发布：

```bash
# 正确验证方式（R35）
conan download "zlib/1.3.1" -r=ohpcd --only-recipe

# 禁止用 conan list（cnb.cool 搜索 API 对 binary 返回不完整）
```

多层依赖链（C→B→A）必须按拓扑序 A→B→C 逐层发布。

---

## 五、CI 脚本与安全审查（仅当 PR 修改 ci/ 或 scripts/ 时）

### 20. Upload 安全边界
- CI upload 只在 PR 合并到 main 后执行，PR 校验阶段禁止 upload
- 密钥/token 不得硬编码在脚本中，必须从环境变量读取
- PR 中不应出现 token、密钥、密码等敏感信息

```bash
# 正确
CONAN_REMOTE_URL="${CONAN_REMOTE_URL}"  # 从环境变量读取

# 错误 — 硬编码密钥
CONAN_TOKEN="ghp_xxxxxxxxxxxx"
```

### 21. CI 门禁不可绕过
ci/ 目录下的门禁脚本（L0a-L0j）不得被修改为降低检查标准：
- 不得注释掉门禁检查逻辑
- 不得将 fail 改为 warn 来放行问题
- 不得删除 L0j 版本号占用检查
- 新增门禁需要说明理由

### 22. 禁止用 conan list 判断 binary (R35)
CI 脚本中判断预编译包是否存在时，必须用 `conan download` 或 `conan install --requires=`。

### 23. shell 脚本规范
- 使用 `set -euo pipefail` 开头
- 变量引用加双引号：`"$VAR"`
- Conan 2.x 参数用 `--only-recipe`，不用已废弃的 `--recipe`
