# embedmq 1.0.1 packaging

本目录存放 embedmq 1.0.1 的 Conan 打包产物（`embedmq-1.0.1.tar.gz`，
由本地 `conan create` 成功后按归档约定打包生成；tar.gz 已被 .gitignore
排除，不入 PR）。

- 配方：`archives/e/embedmq/1.0.1/conanfile.py`
- 源码声明：`conandata.yml`（官方 GitHub tag v1.0.1，SHA-256 2f4526b8...）
- 构建：CMake 静态库（OHOS aarch64, clang 15, ohos-aarch64 profile）
- 验证：conan-verify 全门禁通过（G0-G4 + L2/L4/L5）；上游测试 16/16、
  鸿蒙专项 test_ohos 与消费者 test_package 均通过
