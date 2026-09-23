# Eigen 5.0.1 适配记录

## 适配范围

- 官方 Eigen 5.0.1 tar.gz，SHA-256 `e9c326dc8c05cd1e044c71f30f1b2e34a6161a3b6ecf445d56b53ff1669e3dec`。
- 头文件库，使用 CMake 安装导出 `Eigen3::Eigen`，最低 C++ 标准为 C++14。
- 关闭 BLAS、LAPACK、文档、demo 和测试构建选项；无额外 Conan 依赖。

## 问题与处理

| 问题 | 根因 | 解决方案 |
| --- | --- | --- |
| Windows Conan test_package 报 `Test binary not found: .\\test_eigen` | MinGW 生成 `test_eigen.exe`，配方假设目标无后缀 | 按 host OS 选择 `.exe` 或无后缀，再通过 `self.run(..., env="conanrun")` 显式执行 |
| WSL 全量 CTest 首次有 2 项随机数值失败 | `polynomialsolver_9`、`bicgstabl_1` 使用随机输入，初次 seed 触发数值边界 | 独立复跑两项均通过；随后在同一构建目录完成全量 1255/1255 |

## 验证结果

- Windows Conan `conan create --build=missing --test-folder test_package`: RC 0，`eigen smoke test: PASS (matmul + norm OK)`。
- WSL Ubuntu-D upstream CTest: 1255/1255 passed，RC 0。
- OHOS 真机 W3 r006：唯一 launch，目标 smoke 2/2，target RC 0，11/11 receipt chain validator PASS，任务远端根已清理。

## 结束

适配候选已冻结，后续 CI、AI Review 和提审必须绑定创建 PR 后的当前 HEAD。
