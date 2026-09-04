# CMake 对 HarmonyOS 平台提示 unknown 且 Conan 消费者测试需验证被测包安装的 CLI 工具

- **草稿 ID**: DRAFT-nng-1.10.1-cmake-unknown-platform-conan-cli-test
- **来源**: NNG 1.10.1 HarmonyOS PC 适配（CMake unknown platform + Conan consumer CLI test 修复）
- **分类**: cmake / conan / posix-library / consumer-test / cli-tool
- **状态**: 本地草稿（已创建 PR #7698 和 Issue #2534，路径 B 知识库扩展申请中）

## 问题 / 错误签名

- **CMake 配置阶段**：输出 `System is unknown to cmake, create: Platform/HarmonyOS`（警告级，不阻止构建）
- **CI test_package 失败**：`nngcat: command not found` 或 `sh: nngcat: not found`，exit code 127
- **复现命令**：`conan create archives/n/nng/1.10.1` 在 test_package 阶段执行 `self.run("nngcat --version", env="conanrun")` 失败

## 根因

1. **CMake 平台识别**：CMake 对 HarmonyOS/OHOS 系统名没有内置 `Platform/HarmonyOS.cmake` 模块，配置时输出 "System is unknown to cmake"。对于不依赖 Linux 专有平台逻辑的 POSIX C/C++ 库（如 NNG），该提示不阻止构建，Conan CMakeToolchain 已正确注入工具链，但需确认工具链注入完整。

2. **Conan 消费者测试 CLI 路径**：当库同时交付静态库和 CLI 工具时，test_package 需验证：
   - 消费者能通过 CMake target 链接库（验证 `cpp_info.libs` 和 CMake target 导出）
   - 消费者能执行安装后的可执行文件（验证 `cpp_info.bindirs` 和工具可用性）
   
   直接执行命令名（如 `self.run("nngcat --version")`）会因 PATH 未包含被测包的 `bin/` 而失败。Conan 2.x 的 test_package 运行环境由 `VirtualRunEnv` 生成，但该生成器**不会自动将被测包的 bin/ 加入 PATH**，只处理库依赖的 `LD_LIBRARY_PATH`。

## 最小修复方案

在 `archives/n/nng/1.10.1/**` 范围内：

1. **配方** `conanfile.py`：
   - `generate()` 中使用 `CMakeToolchain` 注入 Conan 工具链，显式配置：
     ```python
     tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
     tc.variables["NNG_TESTS"] = "OFF"  # 关闭上游测试，避免 CI 时间预算消耗
     tc.variables["NNG_TOOLS"] = "ON"   # 启用 nngcat 等 CLI 工具
     ```
   - `package_info()` 中声明：
     ```python
     self.cpp_info.bindirs = ["bin"]
     ```

2. **test_package** `conanfile.py`：
   - 通过 `self.dependencies["nng"]` 获取被测包元数据
   - 拼接 CLI 绝对路径：
     ```python
     import os
     dependency = self.dependencies["nng"]
     nngcat = os.path.join(
         dependency.package_folder,
         dependency.cpp_info.bindirs[0],
         "nngcat",
     )
     self.run(f'"{nngcat}" --version', env="conanrun")
     ```
   - **不依赖系统 PATH**，在 CI 隔离环境中可复现

3. **test_package** `test.c`：
   - 实际调用 NNG API（如 `nng_pair0_open`、`nng_close`、`nng_version`）
   - 验证库链接和头文件导出，而非空壳测试

## 实际验证结果

- **本地 conan-verify**：G0-G4/L2/L4/L5 全部 PASS，exit=0
- **上游测试**：`ctest -j 4 --output-on-failure` 共 87 项，84 项通过（96.55%）
  - 3 项失败为 `nng.sp.transport.ipc.ipc_test`、`nng.multistress`、`nng.reqstress`
  - 失败原因：HarmonyOS Unix domain socket 权限限制（`Permission denied`），已记录在 `notes.md` 和测试报告中，与 NNG 1.11 历史记录一致
- **消费者测试**：
  - CMake 编译链接测试：`test.c` 调用 `nng_pair0_open`、`nng_close`、`nng_version`，编译链接成功
  - CLI 执行测试：`nngcat --version` 通过绝对路径执行成功，输出版本信息
- **W3 本地 CI**：
  - 首轮失败原因：直接执行 `nngcat --version`，PATH 找不到命令
  - 修复后：`.ci-result.json exit_code 0`，Junk Files: 0
- **PR CI 状态**：PR #7698 已推送修复，触发 `/rebuild`，构建中

## 适用范围

- 在 HarmonyOS PC（CMake 不识别该平台）上使用 Conan 构建的 POSIX C/C++ 项目
- 同时交付库（静态或动态）和 CLI 工具的软件包
- 不依赖 Linux 专有平台模块（如 systemd、dbus、X11）的跨平台 POSIX 库

## 非适用边界

- 深度依赖 Linux 专有 CMake 平台逻辑的项目，不能简单用 CMakeToolchain 注入工具链，需单独平台适配
- 仅交付库、不交付 CLI 工具的包，不需要 test_package CLI 测试部分（但仍需 API 消费者测试）
- 已有完整平台适配且 test_package 已正确定位 CLI 路径的包，无需本方案

## 查重差异

- 与 **E092**（CMake 平台识别 / 平台模块风险）主题相关，但本条目补充了：
  - HarmonyOS 作为 CMake unknown platform 的非阻塞性边界（POSIX 库可构建）
  - Conan 2.x test_package 中 CLI 工具的绝对路径调用模式
  - 上游测试中 HarmonyOS IPC 权限限制的测试边界记录
  - 从 CMake 配置、Conan 配方、消费者测试到 CI 修复的完整可复用实践

## 关联交付

- 本草稿与 `archives/n/nng/1.10.1/**` 属于同一 NNG 交付范围
- 已创建 PR #7698（`feat/nng-1.10.1`）和 Issue #2534（路径 B 知识库扩展申请）
- 本轮提交草稿到 PR 分支，随 PR 合并后进入主仓库知识库
- 正式 E 编号由知识库主编审核后分配

## 禁止模式

1. **直接执行命令名**：
   ```python
   # ❌ 错误：依赖系统 PATH
   self.run("nngcat --version", env="conanrun")
   ```
   - 原因：Conan test_package 的运行环境不会自动将被测包的 bin/ 加入 PATH
   - 后果：本地开发机可能通过（若系统 PATH 碰巧包含该工具），但 CI 隔离环境中失败

2. **伪装 HarmonyOS 为 Linux**：
   ```python
   # ❌ 错误：平台身份伪装
   tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
   ```
   - 原因：将 HarmonyOS 伪装为 Linux 可能导致 CMake 加载 Linux 专有平台逻辑（如 systemd、dbus、X11）
   - 后果：对 POSIX 纯库无影响，但对平台集成类项目会引入错误依赖；W4 审计可能标记平台身份伪装

## 推荐模式

```python
# ✅ 正确：通过 Conan 依赖元数据定位 CLI
import os
from conan import ConanFile

class NngTestConan(ConanFile):
    def test(self):
        dependency = self.dependencies["nng"]
        nngcat = os.path.join(
            dependency.package_folder,
            dependency.cpp_info.bindirs[0],
            "nngcat",
        )
        self.run(f'"{nngcat}" --version', env="conanrun")
```

## 关联原则

- P010：尊重上游构建逻辑，使用 Conan 工具链注入而非修改上游 CMake
- P020：消费者测试必须验证真实使用场景，包括 API 调用和 CLI 执行

## 相似条目

- E092：CMake 平台识别 / 平台模块风险（主题相关，但本条目补充了 Conan 消费者测试的完整实践）
