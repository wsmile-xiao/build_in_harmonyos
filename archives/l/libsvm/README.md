# libsvm

libsvm is a widely used Support Vector Machine (SVM) library developed by
Professor Chih-Jen Lin's team at National Taiwan University. It provides
efficient implementations of SVM classification, regression, and distribution
estimation.

## Key Features
- SVM training (svm-train), prediction (svm-predict), and data scaling (svm-scale)
- C++ shared library (libsvm.so) for integration into other applications
- Python interface included
- Supports C-SVC, nu-SVC, one-class SVM, epsilon-SVR, nu-SVR

## Compiled Versions
- **3.37.1** (upstream 3.37, 2026-08-25): HarmonyOS aarch64, extended consumer tests
- **3.37.1.1** (upstream 3.37, 2026-08-30): HarmonyOS aarch64, CI 门禁修复
- **3.37** (2026-06-10): HarmonyOS aarch64, compiled with clang++ 15.0.4,
  含鸿蒙特有测试 4 用例（版本断言/线性核训练预测/模型保存加载往返/RBF 决策函数）

## Tests
- 冒烟测试：`svm_check_parameter()` API 校验（test_package/test_libsvm.cpp）
- 鸿蒙特有测试：`test_package/test_libsvm_ohos.cpp`（4 用例，真实调用
  svm_train/svm_predict/svm_save_model/svm_load_model/svm_predict_values）
- 上游无官方自动化测试入口（无 make check/ctest），README 命令行示例
  （heart_scale 训练/预测/缩放）已验证：准确率 86.67% (234/270)
