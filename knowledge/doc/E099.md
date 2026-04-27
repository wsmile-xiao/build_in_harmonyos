# E095 — Boost b2 构建系统不兼容 OHOS

## 错误特征

### 典型错误日志

```
Performing configuration checks

    - clang++ --version           : no  (cached, failure)
  
error: at /path/to/boost_1_90_0/tools/build/src/engine/build.sh:123
error: cannot deduce architecture from compiler
```

或

```
error: unable to find parent of '/path/to/boost_1_90_0'
```

### 触发条件
- 构建系统: Boost.Build (b2/bjam)
- 阶段: configuration (配置检测阶段)
- 软件版本: Boost 1.90.0 (及更早版本)
- 平台: OHOS (OpenHarmony OS)

## 根因分析

Boost 的 b2 构建系统是一个自定义的构建工具，存在以下 OHOS 平台兼容性问题：

1. **编译器版本检测失败**: b2 执行 `clang++ --version` 时，OHOS 的 clang 输出格式或返回码不符合 b2 的预期，导致退出码为 1

2. **平台架构检测失败**: b2 使用硬编码的平台三元组列表，无法匹配 OHOS 的目标三元组 `aarch64-unknown-linux-ohos`

3. **内部路径创建失败**: b2 的 Jamfile 引擎在 OHOS 环境下创建目录时失败

## 解决方案

### 方案 1: 使用 CMake 构建（推荐，Boost 1.90+ 支持）

```bash
cd boost_1_90_0
mkdir -p build && cd build
cmake .. -DBOOST_INCLUDE_LIBRARIES="system;filesystem;thread" -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX
cmake --build . -j$(nproc)
cmake --install .
```

### 方案 2: 仅使用 header-only 库（无需编译）

大部分 Boost 库是 header-only，无需编译即可使用：

```bash
export CPLUS_INCLUDE_PATH=/path/to/boost_1_90_0:$CPLUS_INCLUDE_PATH
```

### 方案 3: 创建 user-config.jam 手动配置（高级用户）

```bash
cat > user-config.jam << 'EOF'
using clang : ohos : clang++ : <archiver>llvm-ar <ranlib>llvm-ranlib ;
EOF

./b2 --user-config=user-config.jam --with-system --with-filesystem install
```

### 禁止做法
- ❌ 禁止使用 `--build/--host/--target` 参数 (b2 不支持这些参数)
- ❌ 禁止创建编译器符号链接 (无法解决平台检测问题)

## 验证

```bash
# 验证 CMake 构建
ls $DEFAULT_PREFIX/lib/libboost_*.so
ls $DEFAULT_PREFIX/include/boost/version.hpp

# 编译测试程序
cat > test_boost.cpp << 'EOF'
#include <boost/filesystem.hpp>
#include <iostream>
int main() {
    boost::filesystem::path p("/tmp");
    std::cout << "Boost version: " << BOOST_LIB_VERSION << std::endl;
    std::cout << "Path exists: " << boost::filesystem::exists(p) << std::endl;
    return 0;
}
EOF

clang++ -std=c++17 -I$DEFAULT_PREFIX/include -L$DEFAULT_PREFIX/lib test_boost.cpp -lboost_filesystem -lboost_system -o test_boost
LD_LIBRARY_PATH=$DEFAULT_PREFIX/lib ./test_boost
```

## 关联条目
- 相关: E007 (config.guess 不识别 OHOS)
- 相关: E008 (CMake 平台检测失败)

## 详细文档
完整文档见: [doc/E095.md](../doc/E095.md)
