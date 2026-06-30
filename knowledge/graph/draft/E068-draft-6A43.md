# E068 — Boost.Build SHELL 执行失败（鸿蒙兼容性问题）

## 错误特征
典型的错误日志包含以下特征：
```
error: '"clang++" --version' exited with error code 1
/storage/Users/currentUser/builds/boost-1.84.0.work/tools/build/src/tools/common.jam:1164: in common.match-command-output from module common
```

错误发生在 Boost.Build 尝试执行 SHELL 命令（如版本检测）时。

## 触发条件
- 构建系统: Boost.Build (b2/bjam)
- 阶段: configure (版本检测、工具链配置)
- 平台: OpenHarmony（鸿蒙）

## 根因分析
Boost.Build 的 SHELL 执行机制使用 Python subprocess 或类似机制来执行命令并捕获输出。在鸿蒙平台上，由于 shell 环境的差异，导致：
1. 命令执行失败（如 `clang++ --version`）
2. Boost.Build 无法正确解析 SHELL 输出
3. 错误发生在 `tools/build/src/tools/common.jam` 的 `match-command-output` 函数

这是一个平台兼容性问题，Boost.Build 未针对鸿蒙环境进行适配。

## 解决方案

### 推荐方案：Header-only 安装
Boost 大部分库是 header-only，无需编译即可使用。对于这些库：
```bash
# 直接复制 boost 头文件目录
cp -r boost $DEFAULT_PREFIX/include/
```

优点：
- 无需编译，避免 Boost.Build 兼容性问题
- Boost 大部分核心库是 header-only（如 smart_ptr, bind, tuple, mpl, optional, variant 等）
- 满足大多数项目的基本需求

缺点：
- 无法使用需要编译的库（如 filesystem, thread, chrono, context, coroutine 等）

### 回退方案：使用 C++ 标准库替代
对于需要编译的 Boost 库，可以使用 C++ 标准库替代：
- `boost::filesystem` → C++17 `std::filesystem`
- `boost::thread` → C++11 `std::thread`
- `boost::chrono` → C++11 `std::chrono`
- `boost::bind` → C++11 `std::bind`

### 禁止做法
- ❌ 不要尝试使用 b2 编译 Boost（会导致 SHELL 执行失败）
- ❌ 不要修改 Boost.Build 的源码（复杂且可能引入新问题）
- ❌ 不要使用 `--build/--host` 参数绕过（这是 native 编译，不适用）

## 验证
```bash
# 验证 header-only 安装成功
ls -la $DEFAULT_PREFIX/include/boost/

# 验证可使用 header-only 库
echo '#include <boost/smart_ptr.hpp>' | clang++ -c -x c++ -I$DEFAULT_PREFIX/include -o /dev/null
```

## 关联条目
- 相关: 无（这是 Boost.Build 特有的问题）
- 类似: 其他构建系统的 SHELL 执行兼容性问题
