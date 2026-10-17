# oclgrind

OpenCL device simulator and debugger (James Price, University of Bristol).

## OHOS 适配
- **构建系统**: CMake, C++17, 需 LLVM/Clang >= 18.0
- **产物**: bin/oclgrind, bin/oclgrind-kernel, liboclgrind, liboclgrind-rt (SONAME libOpenCL.so)
- **依赖**: readline/8.3 (交互历史记录); LLVM/Clang 由真机环境提供
- **测试**: 上游 97 个 ctest 用例 + 2 个消费者用例 (OpenCL 平台枚举 + CLI 版本)

## 依赖
- readline 8.3

## 功能验证
```bash
oclgrind --version  # 期望输出: Oclgrind 26.03.1
```

## 参考
- 官网: https://github.com/jrprice/Oclgrind
- 源码: https://github.com/jrprice/Oclgrind/archive/refs/tags/v26.03.1.tar.gz
