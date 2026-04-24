# E081: HMDFS config.status 临时文件创建失败

## 错误现象
```
./config.status[769]: can't create ./confXXXXXX/subs1.awk: Permission denied
config.status: error: could not setup config files machinery
```

或类似错误：
```
./config.status[851]: can't create ./confXXXXXX/defines.awk: Permission denied
config.status: error: could not setup config headers machinery
```

## 根本原因
HMDFS（HarmonyOS Distributed File System）对临时文件创建有特殊的安全限制，导致 autotools 的 `config.status` 脚本无法在当前目录创建临时目录（如 `confXXXXXX/`）并在其中创建文件（如 `subs1.awk`、`defines.awk`）。

这是平台特定的行为，与标准 Linux 文件系统不同。即使目录权限正常（`drwxrws--x`），HMDFS 的安全机制仍然会阻止某些临时文件操作。

## 适用范围
- **受影响软件**：使用 autotools 构建系统的软件，特别是 header-only 库（如 sparsehash）
- **平台**：HarmonyOS (HMDFS)
- **场景**：configure 成功完成后，config.status 生成输出文件时

## 解决方案

### 方案 A：手动创建配置文件（推荐用于 header-only 库）

对于 header-only 库，可以绕过 config.status，手动创建必要的配置文件：

```bash
# 1. 从 config.log 提取配置值
# config.log 中包含所有 configure 检测到的宏定义

# 2. 手动创建 config.h
cat > src/config.h << 'EOF'
#define PACKAGE_NAME "sparsehash"
#define PACKAGE_VERSION "2.0.2"
#define HASH_MAP_H <unordered_map>
#define HASH_NAMESPACE std
#define SPARSEHASH_HASH HASH_NAMESPACE::hash
# ... 其他必要的宏
EOF

# 3. 手动安装头文件
mkdir -p $PREFIX/include/google
mkdir -p $PREFIX/include/sparsehash
cp -r src/google/* $PREFIX/include/google/
cp -r src/sparsehash/* $PREFIX/include/sparsehash/
```

### 方案 B：修改 config.status 临时目录位置（实验性）

尝试修改 config.status 使用外部临时目录：

```bash
# 修改 config.status 脚本
sed -i 's|mktemp -d "./confXXXXXX"|mktemp -d "/tmp/confXXXXXX"|g' config.status
```

注意：此方案在某些情况下可能仍然失败。

### 方案 C：使用原始 tarball 在外部文件系统构建

如果系统有其他文件系统（如 ext4），可以在那里构建：

```bash
# 在 ext4 文件系统中解压并构建
cd /tmp/ext4_build_area
tar xzf sparsehash-2.0.4.tar.gz
cd sparsehash-2.0.4
./configure --prefix=$PREFIX && make && make install DESTDIR=$DESTDIR
```

## 验证方法

创建简单测试程序验证头文件可用性：

```cpp
#include <google/sparse_hash_map>
#include <google/dense_hash_map>
#include <iostream>

int main() {
    google::sparse_hash_map<int, std::string> map;
    map[1] = "test";
    std::cout << "OK" << std::endl;
    return 0;
}
```

编译并运行：
```bash
clang++ -std=c++11 -I$PREFIX/include test.cpp -o test && ./test
```

## 关键要点
- HMDFS 的限制是平台特有的，不影响软件的功能
- Header-only 库可以手动安装头文件，无需完整构建
- 对于需要编译二进制的软件，可能需要使用外部文件系统或等待平台更新
- 编译日志（config.log）包含所有必要的配置信息，可以手动提取

## 相关模式
- **E002**：TMPDIR 只读问题
- **E053**：平台限制问题
- **R23**：平台检测机制优先于改生成文件

## 编译记录示例
**sparsehash 2.0.4**：
- 问题：config.status 无法创建临时文件
- 解决：手动创建 config.h，手动安装头文件
- 结果：成功安装，头文件可用
- 日期：2026-04-24
- 平台：HarmonyOS (HongMeng Kernel 1.12.0)