---
name: ohos-build-review-rules
description: 鸿蒙PC三方库适配 PR 审查规则。覆盖配方正确性、欺骗性行为检测、文件规范、安全边界。适用于 C/C++ 库适配到 HarmonyOS PC (arm64) 的 Conan 2.x 制品仓体系。
type: project
---

# 鸿蒙PC三方库适配 PR 审查规则

本项目将开源 C/C++ 库适配到 HarmonyOS PC (arm64)，使用 Conan 2.x 发布到 cnb.cool 制品仓。PR 分两类：
- **配方 PR**（archives/ 下的文件）→ 重点审查类别一、二、三
- **框架 PR**（ci/scripts/ 等文件）→ 重点审查类别四

---

## 一、欺骗性行为检测（⭐ 最高优先级，一律 request changes）

### 1. 空壳测试 (R34)
test_package 必须调用被测包的 API 或执行其二进制。禁止只打印字符串、include 头文件但不调用函数。

### 2. 跳过测试 / 伪造通过 (R9)
禁止 `def test(self): pass`、注释掉 `cmake.test()`、用 `exit 0` 强制通过。

### 3. 伪造状态标记
manifest.yaml 状态必须真实：`published`=CI upload 成功，`built`=验证通过未 upload，`failed`=编译失败。禁止将 failed 标为 published。

### 4. 伪造 sha256 / 绕过校验
conandata.yml 中 sha256 必须是源码包真实哈希。禁止全零、全 f、删除字段。

### 5. 禁止 `#ifdef __OHOS__` (R8)
源码不得引入平台条件编译宏。应通过 POSIX 接口适配或 patch 处理。检查 patches/ 目录下的补丁内容。

### 6. 手动打包绕过 conan create (R19)
PR 中禁止包含预编译的 `.so`/`.a`/二进制文件。所有产物必须由 CI 从源码构建。

---

## 二、conanfile.py 配方质量

### 7. 版本号策略 (R37)
首次适配用上游版本（`1.3.1`），适配修复加后缀（`1.3.1.1`）。修改已发布版本的 conanfile.py 必须递增后缀。

### 8. 系统同名库静态链接 (R26)
库名与系统库同名时（zlib/openssl/libxml2 等），必须 `BUILD_SHARED_LIBS=False`。

### 9. OHOS 平台兼容 (R32)
`settings.os` 判断必须用 `in ("Linux", "OHOS")`，不能只写 `== "Linux"`。

### 10. 禁止裸用 shell 环境变量 (R33)
编译器和标志必须从 Conan Toolchain 获取，禁止裸用 `os.environ`（release worker 上为空→静默失败）。

### 11. conandata.yml 规范
URL 必须 HTTPS，必须有 sha256。补丁需在 patches 字段声明且文件实际存在。

### 12. 只改源文件不改生成文件 (R6)
禁止修改 `config.h`、`configure`、`Makefile.in` 等生成产物。应通过 `generate()` 或 patches/ 处理。

### 13. 命令行工具声明 commands.json (R38)
构建可执行文件的包（有 `RUNTIME DESTINATION bin` 或 `cpp_info.bindirs`），必须在**软件级别**目录创建 `commands.json`（`archives/{letter}/{name}/commands.json`）。库类型不需要。`type` 必须为 `"tool"`，`name` 匹配包名。

### 14. Conan 2.x API
用 `from conan import ConanFile`，禁止旧版 `from conans`。用 `conan.tools.cmake`。

---

## 三、文件规范

### 15. 归档目录结构
```
archives/{letter}/{name}/
  ├── manifest.yaml / README.md / commands.json(tool)
  └── {version}/
      ├── conanfile.py / conandata.yml / test_package/
      ├── patches/ / manifest.yaml / notes.md
```
缺 conanfile.py / conandata.yml / test_package/ = request changes。

### 16. 补丁文件规范 (R3)
补丁只能通过 `refresh-patch --auto` 生成，不得手动创建。文件名有序编号（001-、002-...）。

### 17. PR 中禁止的文件
`.build-context-*`、`test-report`、`*.log`、`.DS_Store`、`__pycache__/`、预编译二进制（.o/.so/.a）。

---

## 四、PR 合规性与安全

### 18. PR 原子性 (W2)
一个 PR 只包含一个配方。配方 PR 和框架 PR 混合 = 要求拆分。

### 19. 文件权限边界
协作者 PR 不得修改 `SKILL.md`/`references/`/`templates/`/`scripts/`/`ci/`/`index.tsv`。越权 = 要求移除。

### 20. 依赖发布优先级 (R36)
依赖包必须已发布到制品仓。用 `conan download "name/ver" --only-recipe` 验证，禁止用 `conan list`（R35: 搜索 API 对 binary 返回不完整）。

### 21. Upload 安全边界
密钥/token 必须从环境变量读取，禁止硬编码。PR 校验阶段禁止 upload。

### 22. CI 门禁不可绕过
不得注释掉门禁检查、将 fail 改为 warn、删除 L0j/L0k 检查。

### 23. shell 脚本规范
`set -euo pipefail` 开头，变量加双引号，Conan 2.x 用 `--only-recipe`（非 `--recipe`）。
