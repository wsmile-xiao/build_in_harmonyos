# libmanticore-columnar

## 软件简介

Manticore Columnar Library 是一个面向列的存储和二级索引库，旨在**在大数据量下提供良好的性能和低内存占用**。

与 Manticore Search 结合使用，适用于以下场景：
- 日志分析，包括丰富的全文搜索功能
- 更快/低资源消耗的日志/指标分析
- 在 Docker/Kubernetes 中运行日志/指标分析（最低仅需 30MB RAM）
- 强大的 SQL 日志/指标分析能力

**技术特点**：
- C++ 编写，针对底层优化
- 列式存储，支持二级索引
- ARM64 和 x86_64 架构支持
- 低内存占用，快速启动

## 编译依赖

### 构建工具
- cmake >= 3.15
- clang/clang++ >= 15.0（推荐）
- make 或 ninja

### 库依赖
- 无外部库依赖（FastPFOR 和 SIMDe 通过 FetchContent 自动获取）

### 平台要求
- HarmonyOS ARM64
- SSE >= 4.2（x86_64）或 ARM NEON

## 编译说明

### 源码获取
```bash
# 从 GitHub 下载
wget https://github.com/manticoresoftware/columnar/archive/refs/heads/master.tar.gz
tar xf master.tar.gz
cd columnar-master
```

### 配置选项
```bash
cmake -DCMAKE_BUILD_TYPE=Release \
      -DCMAKE_INSTALL_PREFIX=$HOME/usr/local \
      -DBUILD_TESTING=OFF \
      ..
```

### 编译和安装
```bash
make -j$(nproc)
make install DESTDIR=/path/to/staging
```

### 补丁说明

本软件需要 2 个补丁：

1. **0001-knn-CMakeLists.txt.patch** - 修复 embeddings 库未找到时的安装错误
   - 添加条件判断，仅在找到 embeddings 库时才安装
   - 避免因库未找到导致的安装失败

2. **0002-libfastpfor-CMakeLists.txt.patch** - 支持 HarmonyOS ARM64
   - 添加 SIMDe 支持（ARM SIMD 模拟）
   - 使用本地缓存的 SIMDe（避免 GitHub 网络问题）
   - 修复 FastPFORConfig.cmake 路径问题

## 使用说明

### 安装预编译包
```bash
# 通过 cmd-pkgs 安装
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- libmanticore-columnar
```

### 验证安装
```bash
# 检查库文件
ls ~/usr/local/share/manticore/modules/
# 应看到：
# lib_manticore_columnar.so  (24MB)
# lib_manticore_knn.so       (17MB)
# lib_manticore_secondary.so (16MB)
```

### 与 Manticore Search 集成
安装后，Manticore Search 会自动检测并加载这些模块：
```bash
searchd -v
# 输出示例：
# Manticore X.X.X (columnar 2.0.0) (secondary 2.0.0)
```

## 产物说明

预编译包包含以下共享库模块：
- **lib_manticore_columnar.so** - 列式存储核心库
- **lib_manticore_knn.so** - K-近邻搜索支持
- **lib_manticore_secondary.so** - 二级索引支持

**注意**：
- 这是库模块包，不包含可执行文件
- 需要 Manticore Search 作为主程序使用
- Embeddings 库未包含（编译时未找到该库）

## 性能参考

根据官方基准测试：
- 日志分析：比 Elasticsearch 快 6 倍
- 日志分析：比 Clickhouse 快 1.4 倍
- 中等数据（110M Hackernews）：比 Elasticsearch 快 5 倍
- 中等数据（110M Hackernews）：比 Clickhouse 快 11 倍
- 大数据（1.7B NYC taxi）：比 Elasticsearch 快 4 倍
- 大数据（1.7B NYC taxi）：比 Clickhouse 快 1.8 倍

## 许可证

- 源码：Apache 2.0 License
- 二进制组件：参见 LICENSE-binary 文件

## 相关链接

- 官方网站：https://manticoresearch.com
- GitHub：https://github.com/manticoresoftware/columnar
- 文档：https://manual.manticoresearch.com