# DRAFT：CMake header-only INTERFACE 库 + CLI 的 install() 补丁与 runenv PATH 注入

> Status: **Draft**（待审核 promote）| severity: `P1` | category: `cmake, packaging, cli-tool` | Updated: 2026-09-28
> 对应: `knowledge/drafts/DRAFT-matrix_hub-2.0-cmake-interface-cli-install-rules-runenv-path.kv`

---

**匹配关键词**：runenv_info, prepend_path, install(), GNUInstallDirs, header-only, INTERFACE, CLI, test_package, conanrun, Error 127, inaccessible or not found

## 错误签名（error_signature）

```text
Error in test() method|inaccessible or not found|command not found|Error 127 while executing
```

## 错误摘录（error_excerpt）

```text
/system/bin/sh: Matrix_Hub_v2_0_cli: inaccessible or not found
```

## 根因（root_cause）

CMake 构建的 header-only INTERFACE 库 + CLI 工具包（如 matrix_hub 2.0）：
1. 上游 CMakeLists.txt 通常只声明 INTERFACE 目标与可执行文件，**没有任何 `install()` 规则**。
   此时 conan create 的 `cmake.install()` 不会安装头文件或可执行文件，
   包内 bin/include 为空（G4 产物完整性虽不拦截，但交付物缺失）。
2. 即使加上了 install() 规则，CLI 可执行文件若未在 `package_info()` 通过
   `runenv_info.prepend_path("PATH", bin)` 注入 PATH，test_package 的 conanrun
   阶段仍然无法解析该 CLI：`/system/bin/sh: Matrix_Hub_v2_0_cli: inaccessible or not found`，
   `self.run(...)` 以 Error 127 失败（本库实测 G2 首错）。

## 推荐方案（rec_approach）

1. **最小补丁补 install() 规则**（patches/ 目录）：
   ```cmake
   include(GNUInstallDirs)
   install(DIRECTORY include/ DESTINATION ${CMAKE_INSTALL_INCLUDEDIR})
   install(TARGETS MatrixHub MatrixHubSolvers EXPORT MatrixHubTargets
           INCLUDES DESTINATION ${CMAKE_INSTALL_INCLUDEDIR})
   install(TARGETS Matrix_Hub_v2_0_cli Matrix_Hub_v2_0_solver
           RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR})
   ```
2. **package_info() 注入 PATH**（可跨库复用）：
   ```python
   def package_info(self):
       self.cpp_info.bindirs = ["bin"]
       self.cpp_info.includedirs = ["include"]
       self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
   ```
3. **test_package 显式运行真实 CLI 入口**（R34 消费者验证）：
   ```python
   self.run(f"Matrix_Hub_v2_0_cli {os.path.join(self.source_folder, 'basic.m')}", env="conanrun")
   ```

## 验证（验证/命令）

- conan-verify G2 conan create（OHOS armv8, clang 15）：补丁 + PATH 注入后 PASS
- test_matrix_hub 消费者测试：`ctest` 1/1 Passed（Matrix_gen/M_mul/M_I 数值断言）
- `Matrix_Hub_v2_0_cli basic.m`：上游示例脚本 exit 0（修复前 Error 127）

## 适用边界

- 适用：CMake header-only/INTERFACE 库同时产出 CLI 工具的包；
  `runenv_info.prepend_path` 对任何需要把 bin 暴露给消费者的包都成立（不限于 cmake）。
- 边界/反例：纯库包（无 bindirs）无需 PATH 注入；有 install() 的上游无需补丁；
  `commands.json`（R38/L0k）只解决 CLI 声明，不解决 conanrun 运行时 PATH。

## 查重（本候选与既有知识）

- E298（conan test_package 显式运行与环境）：trigger 部分重叠（都在 test() 阶段
  Error 127/环境路径缺失），但 E298 解决的是 consumer 侧 VirtualRunEnv/conanrun，
  未覆盖本候选的**生产者侧** `package_info` PATH 注入与 install() 缺失补丁。
- E504（CMake install 期 RPATH_CHANGE）：仅 error signature 部分重叠，根因/方案不同。
- E424（commands.json 声明）：元数据门禁，与运行时 PATH 注入不同层。
- 结论：部分覆盖、存在新增差异（生产者侧 runenv PATH 注入 + install() 补丁组合），
  可跨库复用 → 走路径 B，new_draft。