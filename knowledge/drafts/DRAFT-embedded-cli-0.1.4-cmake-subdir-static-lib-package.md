# DRAFT-embedded-cli-0.1.4-cmake-subdir-static-lib-package

> 草稿（Path B 知识库扩展候选），由 embedded-cli 0.1.4 适配中 test_package
> `find_package` 找不到静态库的真实失败与已验证修复产生。
> 本文与同名 `.kv` 配对，逐字段一致。仅为本地知识草稿。

## topic

CMake add_subdirectory 布局下静态库产物位于 CMake binary dir 子目录，conan package() 顶层 glob 复制漏包

## error_signature

`conan create` test_package 阶段 `find_package(<pkg>)` 报
`Library '<lib>' not found in package. If '<lib>' is a system library, declare it with 'cpp_info.system_libs'`，
同时主包日志显示静态库已成功链接（`Linking C static library lib<name>.a`）但 package() 未打包。

## root_cause

上游 CMake 项目用 `add_subdirectory(lib)` 组织子目录时，静态库目标定义在
`lib/CMakeLists.txt`，CMake 默认把产物输出到 binary dir 对应的 `lib/` 子目录
（如 `build/clang-15-armv8-17-release/lib/libembedded_cli_lib.a`），而非 build 顶层。
conan 配方 package() 若按 build 顶层 glob / 单文件 copy 复制 `lib<name>.a`，找不到产物，
导致包内缺库文件，test_package 的 CMakeDeps find_package 校验失败。
主包 build 本身成功，错误只在消费侧暴露，属于"产物复制路径与实际输出位置不一致"。

## durable_solution

1. 在 package() 中优先显式定位
   `os.path.join(self.build_folder, "lib", "lib<name>.a")`（add_subdirectory 子目录
   布局的标准输出位置）。
2. 未命中时用 `os.walk(self.build_folder)` 递归兜底查找同名归档并复制到包内 `lib/`：
   ```python
   candidates = [os.path.join(root, n) for root, _d, files in os.walk(self.build_folder)
                 for n in files if n == "lib<name>.a"]
   ```
3. `copy(..., keep_path=False)` 拍平到 `package_folder/lib/`。
4. 复跑 conan-verify 确认 G2（test_package）通过。

## impact

任何上游用 add_subdirectory 组织、静态库产物落子目录的 CMake 库配方都会遇到
"主包编译通过但 test_package find_package 找不到库" 的同类失败；用
build_folder 子目录显式定位 + os.walk 递归兜底可跨库复用。

## evidence_references

- embedded-cli 0.1.4 conan-verify 报告（G2 修复后 PASS，test_package 2/2）
- conan-create.log: `Library 'embedded_cli_lib' not found in package` 首错 → 修复后 `ohos_static_alloc_test Passed`

## recovery_condition

不适用（适配配方修复，无恢复动作）；后续同类库按上述 package() 模式处理即可。

## status

draft_pending_review
