# metis 5.1.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-07-16
- 编译器: clang/clang++ (clang 15)
- 状态: built

## 编译步骤

1. 下载源码: `curl -L -o metis-5.1.0.tar.gz https://karypis.github.io/glaros/files/sw/metis/metis-5.1.0.tar.gz`
2. 解压源码: `tar xzf metis-5.1.0.tar.gz`
3. CMake 配置: `cmake -DCMAKE_BUILD_TYPE=Release -DCMAKE_POLICY_VERSION_MINIMUM=3.5 -DGKLIB_PATH=$BUILD_SRC_DIR/GKlib .`
4. 编译: `make -j1`
5. 安装: `make install DESTDIR=$TEST_PREFIX`
6. 功能测试: `./programs/graphchk graphs/4elt.graph` 和 `./programs/gpmetis graphs/4elt.graph 2`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | cmake_minimum_required(VERSION 2.8) 报错 | CMake 4.x 移除了对 < 3.5 的兼容 | 使用 `CMAKE_POLICY_VERSION_MINIMUM=3.5` (cache_variables) |
| 2 | GKLIB_PATH try_compile 路径问题 | 相对路径导致 try_compile 失败 | 设置为绝对路径 `self.source_folder/GKlib` (R33) |
| 3 | tc.variables 中 CMAKE_POLICY_VERSION_MINIMUM 不生效 | tc.variables 写入工具链文件，处理时机太晚 | 改用 tc.cache_variables 传递为 -D 命令行参数 |

## 源码修改

无补丁。所有构建问题通过 CMake 参数解决，无需修改源码。

## 依赖版本

无运行时依赖。构建工具: cmake (已安装)

## 验证结果

```bash
# conan-verify 8 道门禁全部通过
# G0: ✅ 预构建风险评估通过
# G1: ✅ 配方完整性通过
# G2: ✅ conan create 成功
# G3: ✅ 系统同名库隔离通过
# G4: ✅ 产物完整性通过
# L2: ✅ smoke test 通过
# L4: ✅ 安全扫描通过
# L5: ✅ 产物基线通过
# W3 CI 模拟: exit_code=0
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方 (CMake 构建系统) |
| conandata.yml | 源码 URL + SHA256 |
| test_package/ | L1 测试 (调用 METIS_PartGraphRecursive API) |
| commands.json | 命令行工具声明 (graphchk, gpmetis, ndmetis, mpmetis, m2gmetis, cmpfillin) |
| manifest.yaml | 软件元数据 |

## 注意事项

- metis 同时提供库 (libmetis.a) 和命令行工具，属于 library + tool 混合类型
- CMAKE_POLICY_VERSION_MINIMUM 必须用 cache_variables 而非 variables 传递
- GKLIB_PATH 必须用绝对路径 (self.source_folder/GKlib)，不能用 shell 变量
- conandata.yml 的 SHA256: 76faebe03f6c963127dbb73c13eab58c9a3faeae48779f049066a21c087c5db2
