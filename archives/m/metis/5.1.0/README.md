# metis 5.1.0 — OpenHarmony 编译记录

## 基本信息
- 软件: metis
- 版本: 5.1.0
- 构建系统: cmake
- 目标: ohos-aarch64
- 编译日期: 2026-05-06
- 状态: success

## 编译指导

### 前置依赖
- cmake >= 3.5
- C 编译器 (clang 15.0.4)
- GNU make

### 编译步骤
```bash
# 1. 解压源码
tar xzf metis-5.1.0.tar.gz

# 2. 创建构建目录
mkdir -p metis-5.1.0/build && cd metis-5.1.0/build

# 3. cmake 配置（关键参数）
cmake -DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local \
      -DCMAKE_BUILD_TYPE=Release \
      -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
      -DGKLIB_PATH=/storage/Users/currentUser/builds/metis-5.1.0.work/GKlib ..

# 4. 编译
make -j$(nproc)

# 5. 安装到 staging 目录
make install DESTDIR=/storage/Users/currentUser/test-install-metis-5.1.0

# 6. 安装到本地
make install
```

### 关键注意事项
1. **cmake_minimum_required 版本兼容性**: metis-5.1.0 使用 `cmake_minimum_required(VERSION 2.8)`，与新版 cmake 4.x 不兼容。必须添加 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5` 参数。

2. **GKLIB_PATH 绝对路径**: cmake 的 `try_compile` 机制会从 build 目录查找源文件，必须将 `GKLIB_PATH` 设置为绝对路径，否则无法找到 `GKlib/conf/check_thread_storage.c` 等测试文件。

3. **无官方测试套件**: 项目没有 ctest 配置，使用 `graphs/` 目录下的示例文件进行功能验证。

## 补丁清单
本版本无补丁。

## 已知限制
1. 仅编译为静态库，无动态库选项
2. 无官方测试套件
3. 部分编译警告（abs/fabs 类型不匹配），不影响功能

## 功能验证

### 验证方法
使用 `graphs/4elt.graph` 示例文件测试分区功能。

### 验证命令
```bash
# 图分区测试 (2分区)
gpmetis graphs/4elt.graph 2

# 图分区测试 (4分区)
gpmetis graphs/4elt.graph 4

# 图检查
graphchk graphs/4elt.graph
```

### 验证结果
- gpmetis 2分区: Edgecut=161, Balance=1.007 ✅ PASS
- gpmetis 4分区: Edgecut=361, Balance=1.011 ✅ PASS
- graphchk 图检查: ✅ PASS

## 产物清单

### 二进制程序
| 程序 | 大小 | 说明 |
|------|------|------|
| gpmetis | 277KB | 图分区 |
| ndmetis | 281KB | 嵌套剖分 |
| mpmetis | 277KB | 多级分区 |
| m2gmetis | 134KB | 网格转图 |
| graphchk | 126KB | 图检查 |
| cmpfillin | 126KB | 填入比较 |

### 库文件
| 文件 | 大小 | 说明 |
|------|------|------|
| libmetis.a | 590KB | 静态库 |

### 头文件
| 文件 | 说明 |
|------|------|
| metis.h | C API 头文件 |

## 知识沉淀
1. cmake_minimum_required 版本过低时，使用 `CMAKE_POLICY_VERSION_MINIMUM` 参数解决兼容性问题
2. cmake 项目使用 `try_compile` 时，路径参数必须使用绝对路径