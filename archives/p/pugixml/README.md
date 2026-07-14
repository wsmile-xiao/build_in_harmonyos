# pugixml — 轻量级 C++ XML 处理库

pugixml 是一个轻量、高性能的 C++ XML 处理库，支持 DOM 解析、XPath 1.0 查询、XML 文档修改和序列化。
本档案将 pugixml 1.15 适配到 OpenHarmony / HarmonyOS PC (aarch64) 平台。

## 版本列表

| 版本 | 状态 | 编译日期 |
|------|------|----------|
| [1.15-r0](./1.15-r0/) | built | 2026-07-13 |

---

## 1.15-r0 适配详情

- **官方源码**: https://github.com/zeux/pugixml/releases/download/v1.15/pugixml-1.15.tar.gz
- **上游仓库**: https://github.com/zeux/pugixml
- **官方网站**: https://pugixml.org/
- **许可证**: MIT

### 项目说明

pugixml 是一个轻量级的 C++ XML 处理库，具有以下特性：

- **DOM 解析**：支持从文件、内存缓冲区或流加载 XML 文档
- **XPath 1.0 查询**：支持完整的 XPath 1.0 表达式
- **文档修改**：支持增删改查 XML 节点和属性
- **序列化**：支持将 XML 文档输出为字符串或文件
- **Unicode 支持**：支持 UTF-8、UTF-16（BE/LE）、UTF-32（BE/LE）编码
- **紧凑模式**：可选的紧凑内存表示，减少内存占用
- **无外部依赖**：纯 C++ 实现，只需 C++ 标准库

### OHOS 构建方式

```bash
# 1. 解压源码
tar xzf pugixml-1.15.tar.gz
cd pugixml-1.15

# 2. CMake 配置（静态库 Release）
cmake -B build \
  -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_SHARED_LIBS=OFF \
  -DCMAKE_CXX_STANDARD=17 \
  -DCMAKE_CXX_COMPILER=clang++ \
  -DCMAKE_C_COMPILER=clang \
  -DCMAKE_INSTALL_PREFIX=/path/to/install

# 3. 编译
cmake --build build -j$(nproc)

# 4. 安装
cmake --install build

# 5. 运行测试（可选，需启用 PUGIXML_BUILD_TESTS）
cmake -B build-test \
  -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_SHARED_LIBS=OFF \
  -DPUGIXML_BUILD_TESTS=ON \
  -DCMAKE_CXX_COMPILER=clang++ \
  -DCMAKE_C_COMPILER=clang
cmake --build build-test -j$(nproc)
cd build-test && ctest --output-on-failure
```

### Conan 配方构建

```bash
# 使用 ohos-aarch64 profile 构建
conan create archives/p/pugixml/1.15-r0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

### 上游测试结果 (979 用例)

| 测试类别 | 测试数 | 通过 | 失败 |
|----------|--------|------|------|
| DOM 遍历 | 50+ | ✅ 全部通过 | 0 |
| DOM 修改 | 80+ | ✅ 全部通过 | 0 |
| DOM 文本 | 40+ | ✅ 全部通过 | 0 |
| 文档加载 | 70+ | ✅ 全部通过 | 0 |
| 内存管理 | 20+ | ✅ 全部通过 | 0 |
| 解析 | 100+ | ✅ 全部通过 | 0 |
| 写入/序列化 | 60+ | ✅ 全部通过 | 0 |
| XPath 查询 | 200+ | ✅ 全部通过 | 0 |
| XPath 函数 | 80+ | ✅ 全部通过 | 0 |
| 其他 | 200+ | ✅ 全部通过 | 0 |
| **总计** | **979** | **979** | **0** |

### Conan 验证结果

所有 8 道门禁全部通过：

| 门禁 | 检查项 | 结果 |
|------|--------|------|
| G0 | 预构建风险评估 | ✅ PASS |
| G1 | 配方完整性 | ✅ PASS |
| G2 | conan create 干净构建 | ✅ PASS |
| G3 | 系统同名库隔离 (R26) | ✅ PASS |
| G4 | 产物完整性 | ✅ PASS |
| L2 | 烟雾测试 | ✅ PASS |
| L4 | 安全扫描 (NX/PIE/RELRO) | ✅ PASS |
| L5 | 产物基线对比 | ✅ PASS |

### 依赖关系

| 依赖 | 版本 | 说明 |
|------|------|------|
| 无 | — | **pugixml 无外部依赖**，纯 C++ 标准库实现，仅需 C++17 编译器 |

### 参考资料

- 上游仓库：https://github.com/zeux/pugixml
- 官方文档：https://pugixml.org/docs/manual.html
- 快速入门：https://pugixml.org/docs/quickstart.html
- 许可证：MIT