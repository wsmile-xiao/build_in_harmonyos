# status-value-lite

status-value-lite 是 Martin Moene 的 nonstd-lite 系列之一：为 C++11 及以后提供
`status_value` 类（状态 + 可选值），并附带 C++98 单文件头文件变体。

## OHOS 适配

- **构建系统**: CMake header-only（INTERFACE library），`include/nonstd/status_value.hpp`
- **依赖链**: 无任何第三方依赖，纯头文件
- **编译选项**: `-DNSSV_OPT_BUILD_TESTS=ON` 集成上游 lest 测试
- **CMake 目标**: `nonstd::status_value-lite`

## 功能验证

```bash
# 消费者测试通过 test_package 执行（构造/status()/value()/移动/swap）
# 上游 CTest：test-cpp11 等 17 用例 + test98-cpp98 等 16 用例
```

## 参考

- 官网: https://github.com/nonstd-lite/status-value-lite
- 版本: 1.1.0 (tag v1.1.0, commit 90ffc8e)
- 许可证: BSL-1.0