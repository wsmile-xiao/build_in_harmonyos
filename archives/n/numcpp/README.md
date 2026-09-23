# NumCpp

NumCpp 是一个 **header-only 的 C++17 模板数值库**，以 C++ 重新实现 Python
NumPy 的核心接口（templatized implementation of the Python NumPy library）。

## 功能概述

- 核心容器 `nc::NdArray<T>`：2D 数组，支持广播语义的算术/比较/逻辑运算
- NumPy 风格模块：`nc::random`、`nc::linalg`、`nc::fft`、`nc::filter`、
  `nc::special`、`nc::polynomial`、`nc::DateTime`、`nc::logger`、
  `nc::integrate`、`nc::roots`、`nc::rotations`、`nc::vector` …
- 纯头文件实现：`include/` 下 544 个公开 `.hpp`，无编译产物、无自有链接依赖
- 默认配置依赖 Boost 头（math special functions / DateTime / Random 分布 /
  Polynomial / Log），Conan 配方将 Boost 头文件传递（transitive_headers）
  给所有消费者

## OHOS 适配

- **header-library 打包**：`package_type = header-library`，`build()` 不产生
  二进制，`package()` 拷贝 `include/` 与 LICENSE；`package_id()` clear（所有
  settings 组合产物一致）。
- **Boost 依赖传递**：公共头在默认配置下 include Boost 头，配方
  `requires("boost/1.84.0", transitive_headers=True)`，并通过
  `cpp_info.requires = ["boost::boost_headers"]` 把 Boost 头目录与
  `BOOST_SP_NO_PTHREAD_SETCANCELSTATE`（musl 无 pthread_setcancelstate）定义
  一并传播给消费者。
- **已知限制（如实申报）**：`nc::logger` 等真正输出日志时需要 Boost.Log 编译库
  （libboost_log/libboost_log_setup），当前 ohpcd 已发布的 boost 变体仅提供
  头文件 + filesystem/regex/program_options/iostreams 静态库，不提供 Boost.Log，
  属生态缺口（已用本机自建 Boost.Log 跑通上游 gtest LoggerTests 5/5，证据见
  版本级 reports/）；上游官方 pytest 套件（25 文件 / 748 定义 / 747 收集）需
  Python+NumPy 科学栈 + pybind11，已在 OHOS PC venv 全量真实运行
  （numpy 2.2.6：732 passed / 12 上游 skip / 3 平台差异豁免），但默认 conan
  create/CI 不依赖该环境。详见版本级 `2.16.1/notes.md`、`reports/` 与
  `test_package/MANIFEST.yml`。

## 依赖关系

| 依赖 | 版本 | 用途 |
|------|------|------|
| boost | 1.84.0 | 公共头引用的 Boost 头文件（math/date_time/random/polynomial/log），header-only 传播 |

编译环境：HarmonyOS PC (aarch64) clang 15 / libc++ / C++17；无运行时二进制依赖。

## 版本

| 版本 | 状态 | 日期 |
|------|------|------|
| 2.16.1 | built | 2026-09-04 |

## 使用

```python
# conanfile.txt / conanfile.py
[requires]
numcpp/2.16.1
```

```cmake
find_package(NumCpp REQUIRED)          # CMakeDeps 生成（cmake_file_name=NumCpp）
target_link_libraries(app PRIVATE NumCpp::NumCpp)
```

```cpp
#include "NumCpp.hpp"
nc::NdArray<double> a = nc::random::randN<double>({4, 4});
auto b = nc::dot(a, a.transpose());
```

## 参考资料

- 上游仓库：<https://github.com/dpilger26/NumCpp>
- 许可证：MIT
