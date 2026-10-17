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

以下行为不论其他检查是否通过，一律拒绝。

### 1. 空壳测试 (R34)
test_package 必须调用被测包的 API 或执行其二进制。
```cpp
// 欺骗 — 只打印不调用 API
int main() { printf("test passed\n"); return 0; }
// 欺骗 — include 了但不用
#include <zlib.h>
int main() { return 0; }
// 正确 — 实际调用
#include <zlib.h>
int main() { return zlibVersion() ? 0 : 1; }
```

### 2. 跳过测试 / 伪造通过 (R9)
禁止 `def test(self): pass`、注释掉 `cmake.test()`、用 `os.system("exit 0")` 强制通过。

### 3. 伪造状态标记
manifest.yaml 状态必须真实：`published`=CI upload 成功，`built`=验证通过未 upload，`failed`=编译失败。禁止将 failed 标为 published。

### 4. 伪造 sha256
conandata.yml 中 sha256 必须是源码包真实哈希。禁止全零、全 f、明显过短、删除字段。

### 5. `#ifdef __OHOS__` 必须有实质逻辑 (R8)
源码中可以使用 `#ifdef __OHOS__` 平台守卫（须有实质适配逻辑）；**patches/ 补丁文件中默认禁止引入平台宏**，应通过 POSIX 兼容方式修复（config.guess/config.sub、feature detection 等）。例外（如识别 libc 的探针程序、无 POSIX 等价物场景）须在 PR 中说明理由——口径以 `references/iron-rules.md` R8 为唯一权威（ding-libs PR #7133 教训：三方口径不一致导致检视与作者双标）：
```c
// 禁止 — 空壳 stub, 绕过功能
#ifdef __OHOS__
    return 0;  // 直接返回, 无实际适配
#endif
// 正确 — 有实质逻辑的平台分支
#ifdef __OHOS__
    // 鸿蒙使用 procfs 读取, 替代 /sys/class 读取
    fd = open("/proc/cpuinfo", O_RDONLY);
#else
    fd = open("/sys/class/...", O_RDONLY);
#endif
```

### 6. 手动打包绕过 conan create (R19)
PR 中禁止包含预编译的 `.so`/`.a`/二进制文件。所有产物必须由 CI 从源码构建。

### 7. 深度适配验证 (R40)
部分库"编译通过 + 接口测试"不等于适配完成。当 conanfile.py/patches/test_package 涉及以下领域时，必须检查是否有**实质性平台适配代码**（非简单 stub/return 0）：
- **图形/渲染**：OpenGL/EGL/Vulkan/Skia/cairo/SDL/GTK，需适配鸿蒙图形栈
- **UI 框架**：Qt/FLTK/imgui，需适配窗口系统和输入事件
- **多媒体**：FFmpeg/GStreamer/编解码，需适配硬件加速或编解码器
- **外设/硬件**：USB/蓝牙/摄像头/传感器，需适配 HAL 或驱动接口
- **系统底层**：procfs/sysfs/netlink/dl，需适配鸿蒙对应接口

检查要点：
1. patches/ 中是否有针对鸿蒙的适配补丁（非空 ifdef 占位）
2. test_package 是否覆盖了平台相关功能（非仅 `version()` 调用）
3. conanfile.py 是否正确声明了系统依赖（如 `egl`、`hilog` 等）
```cmake
# 欺骗 — stub 掉渲染接口, 编译通过但无法实际渲染
target_link_libraries(app PRIVATE EGL GLESv3)
# 但 test_package 只调用eglQueryString(DPY, EGL_VERSION), 无实际 EGL context 创建
```
发现此类库时在 review 中标注「需人工确认适配完整性」。

---

## 二、conanfile.py 配方质量

### 8. 版本号策略 (R37)
首次适配用上游版本（`1.3.1`），适配修复加后缀（`1.3.1.1`、`1.3.1.2`）。修改已发布版本的 conanfile.py/conandata.yml 必须递增后缀。

### 9. 系统同名库静态链接 (R26)
库名与系统库同名时（zlib/openssl/libxml2/ncurses 等），必须静态编译：
```python
tc.variables["BUILD_SHARED_LIBS"] = False
```

### 10. OHOS 平台兼容 (R32)
```python
# 正确
if self.settings.os in ("Linux", "OHOS"):
# 错误 — OHOS 场景下漏匹配
if self.settings.os == "Linux":
```

### 11. 禁止裸用 shell 环境变量 (R33)
```python
# 错误 — release worker 上为空→静默失败
os.environ["CC"] = "aarch64-linux-gnu-gcc"
# 正确 — 从 Conan Toolchain 获取
tc = CMakeToolchain(self)
```

### 12. conandata.yml 规范
URL 必须 HTTPS，必须有 sha256。补丁需在 patches 字段声明且文件实际存在。

### 13. 源码 URL 必须为官方源 (R39)
conandata.yml 中的 URL 必须指向**官方正式源**或**权威镜像源**，禁止不明来源：
```yaml
# 正确 — 官方 GitHub release/tag
url: "https://github.com/madler/zlib/releases/download/v1.3.1/zlib-1.3.1.tar.gz"
# 正确 — 官方网站
url: "https://www.zlib.net/zlib-1.3.1.tar.gz"
# 禁止 — 个人 fork / 非官方镜像 / 不明仓库
url: "https://github.com/someone/zlib/archive/v1.3.1.tar.gz"
# 禁止 — 网盘 / 不明 CDN
url: "https://pan.baidu.com/s/xxxx/zlib.tar.gz"
```
CI 会自动为 GitHub URL 添加镜像 fallback（gh-proxy/ghproxy/gitclone/moeyy/kkgithub），因此 conandata.yml 中只需写官方原始 URL，不要手动加镜像前缀。

### 14. 只改源文件不改生成文件 (R6)
禁止修改 `config.h`、`configure`、`Makefile.in`、`CMakeCache.txt` 等生成产物。应通过 `generate()` 或 patches/ 处理。

### 15. 命令行工具声明 commands.json (R38)
构建可执行文件的包（conanfile.py 中有 `RUNTIME DESTINATION bin` 或 `cpp_info.bindirs`），必须在**软件级别**目录创建 `commands.json`。库类型不需要。
```json
{
  "name": "strace", "type": "tool",
  "description": "系统调用追踪工具",
  "versions": { "6.19": { "ref": "strace/6.19", "binary": false } }
}
```
路径：`archives/{letter}/{name}/commands.json`（与 manifest.yaml 同级，非版本目录下）。`type` 必须为 `"tool"`，`name` 匹配包名。

### 16. Conan 2.x API
用 `from conan import ConanFile`，禁止旧版 `from conans`。用 `conan.tools.cmake`。

---

## 三、文件规范

### 17. 归档目录结构
```
archives/{letter}/{name}/
  ├── manifest.yaml / README.md / commands.json(仅tool)
  └── {version}/
      ├── conanfile.py / conandata.yml / test_package/
      ├── patches/ / manifest.yaml / notes.md
```
缺 conanfile.py / conandata.yml / test_package/ = request changes。

### 18. 补丁文件规范 (R3)
补丁只能通过 `refresh-patch --auto` 生成，不得手动创建。文件名有序编号（001-、002-...）。

### 19. PR 中禁止的文件
`.build-context-*`、`test-report`、`*.log`、`.DS_Store`、`__pycache__/`、预编译二进制（.o/.so/.a）。
**禁止修改 `SUMMARY.md`** — 该文件由 CI 自动生成维护，人工修改会被覆盖。

---

## 四、PR 合规性与安全

### 20. PR 原子性 (W2)
一个 PR 只包含一个配方。配方 PR 和框架 PR 混合 = 要求拆分。

### 21. 文件权限边界
协作者 PR 不得修改 `SKILL.md`/`references/`/`templates/`/`scripts/`/`ci/`/`index.tsv`。越权 = 要求移除。

### 22. 依赖发布优先级 (R36)
依赖包必须已发布到制品仓。用 `conan download "name/ver" --only-recipe` 验证，禁止用 `conan list`（R35: 搜索 API 对 binary 返回不完整）。

### 23. Upload 安全边界
密钥/token 必须从环境变量读取，禁止硬编码。PR 校验阶段禁止 upload。

### 24. CI 门禁不可绕过
不得注释掉门禁检查、将 fail 改为 warn、删除 L0j/L0k 检查。

### 25. shell 脚本规范
`set -euo pipefail` 开头，变量加双引号，Conan 2.x 用 `--only-recipe`（非 `--recipe`）。

### 26. PR body 禁止残留占位符
PR 描述中禁止出现 `(请填写)` 占位符。submit 命令从 conandata.yml/conanfile.py/test-report.md/notes.md/patches/ 自动填充。残留占位符 = 未完成，要求补充。

### 27. AI 检视意见必须闭环 (RV-27)
PR 创建后 atomgit-bot 自动进行 AI 代码检视。检视意见**不一定正确**，但**必须逐条响应**：
- 合理的意见 → 修改代码并 push
- 不合理的意见 → 在 PR 上回复说明原因
- 仅有"正在生成合并请求摘要"和"AI 代码检视正在进行中"→ 检视未完成，不应合并
- 检视意见未闭环（无回复/无修改）= request changes

---

## 五、SKILL_FEEDBACK 反馈规范

### 28. SKILL_FEEDBACK 强制生成
submit 成功后（CI 通过）自动进入 SKILL_FEEDBACK 阶段，生成 `feedback/SKILL_FEEDBACK_{random}.md`。PR 合并前应确认反馈报告已生成且完整（无 `(请填写)` 残留）。

### 29. 反馈报告完整性
SKILL_FEEDBACK 报告必须包含：
- **背景**：软件名称、版本、构建系统、上游仓库、依赖、补丁、状态
- **情况**：执行概要、失败分析、知识图谱、AI 检视、CI、效率分析
- **建议**：SKILL 设计改进、模板改进、自动化补全、知识图谱覆盖（禁止 `(请填写)` 残留）
- **作者**：姓名、邮箱（git config）、Agent ID、时间戳、PR 编号

### 30. 状态文件不可伪造
`.ci-result.json` 含 SHA256 完整性哈希，伪造 = 欺诈行为（参见规则 3）。`.submit-state.json` 和 `.feedback-state.json` 为流程状态文件，禁止手动编辑或伪造。
