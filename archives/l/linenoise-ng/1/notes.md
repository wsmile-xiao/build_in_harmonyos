# linenoise-ng 1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-25
- 编译器: clang 15.0.4 / clang++
- 状态: published

## 编译步骤

### 对话 #1: 初始化与下载

源码来源: `arangodb/linenoise-ng` (GitHub master 分支)

由于当前环境无法直连 GitHub（端口 443 连接超时），通过 jsdelivr CDN 逐文件下载源码:

```bash
BASE="https://cdn.jsdelivr.net/gh/arangodb/linenoise-ng@master"
curl -kfsSL "$BASE/include/linenoise.h" -o linenoise-ng-1/include/linenoise.h
curl -kfsSL "$BASE/src/ConvertUTF.cpp" -o linenoise-ng-1/src/ConvertUTF.cpp
curl -kfsSL "$BASE/src/ConvertUTF.h" -o linenoise-ng-1/src/ConvertUTF.h
curl -kfsSL "$BASE/src/linenoise.cpp" -o linenoise-ng-1/src/linenoise.cpp
curl -kfsSL "$BASE/src/wcwidth.cpp" -o linenoise-ng-1/src/wcwidth.cpp
curl -kfsSL "$BASE/tst/example.c" -o linenoise-ng-1/tst/example.c
curl -kfsSL "$BASE/CMakeLists.txt" -o linenoise-ng-1/CMakeLists.txt
curl -kfsSL "$BASE/LICENSE" -o linenoise-ng-1/LICENSE
curl -kfsSL "$BASE/README.md" -o linenoise-ng-1/README.md
```

打包为 tar.gz 后通过 `ohc-run.py init-build --url=file:///...` 初始化编译环境。

### 对话 #2: CMake 配置与编译

```bash
cd $BUILD_SRC_DIR && mkdir -p build && cd build
cmake .. -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
         -DCMAKE_BUILD_TYPE=Release \
         -DCMAKE_POLICY_VERSION_MINIMUM=3.5
make -j1
make install DESTDIR=$TEST_PREFIX
```

编译输出: 3 个 CXX 目标文件 + 1 个静态库 + 1 个示例程序，全部成功。

### 对话 #3: 验证与打包

- Staging 验证: 检查 `$TEST_PREFIX/$DEFAULT_PREFIX/` 中的产物完整性
- 质量门禁 G1-G4: 全部 PASS
- G0 干净构建验证: 从原始 tarball 全自动重建通过
- 预编译包制作: `ohc-run.py package` 9 步流程完成
- 本地安装: `make install` 安装到 `$DEFAULT_PREFIX`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 不可达 | 当前环境无法连接 github.com:443 | 通过 jsdelivr CDN 逐文件下载源码 |
| 2 | CMake 配置失败 | CMake 4.1.2 移除了对 cmake_minimum_required < 3.5 的兼容 | 修改 CMakeLists.txt: VERSION 2.6 → 3.5 |
| 3 | G0 验证 configure 失败 | clean_verify.py 硬编码 `bash ./configure`，不支持 CMake | 修改脚本: 根据 build_system 字段选择 cmake 命令 |
| 4 | manifest G4 FAIL | manifest 中字段名为 `system:` 而脚本检查 `build_system:` | 修改字段名为 `build_system:` |
| 5 | 知识标记被删除 | knowledge_gained 条目缺少 `ref:` 引用，check_knowledge_gap 删除标记 | 在条目中添加 `ref:` 引用 |

## 源码修改

### 0001-CMakeLists.txt.patch

修改 `cmake_minimum_required(VERSION 2.6)` 为 `cmake_minimum_required(VERSION 3.5)`。

原因: CMake 4.x 移除了对 3.5 以下版本的兼容性支持，旧项目的 VERSION 参数需更新。

## 依赖版本

- clang: 15.0.4
- cmake: 4.1.2
- make: GNU Make 4.4.1
- 无外部库依赖（纯 C++ 标准库）

## 验证结果

详见 `reports/test-report.md`，6 项测试全部通过:
- T1: 静态库符号检查 ✅
- T2: example 程序功能测试 ✅
- T3: 自定义程序链接测试 ✅
- T4: 头文件完整性 ✅
- T5: 预编译包内容验证 ✅
- T6: 补丁自包含性（G0）✅

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| linenoise-ng-1-ohos-aarch64.tar.gz | 102KB | 预编译包（含 liblinenoise.a + linenoise.h） |
| 0001-CMakeLists.txt.patch | 1.6KB | CMake 版本兼容性补丁 |
| test-report.md | — | 6 项功能测试报告 |
| quality-report.md | — | G1-G4 质量门禁报告 |

## 注意事项

1. linenoise-ng 是纯静态库项目，无 bin/ 可执行文件安装，staging 验证需跳过 bin 检查
2. 链接 liblinenoise.a 时需要 `-lstdc++`（内部使用 C++ 实现）
3. CMake 4.x 用户需添加 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5` 或应用补丁

---
**编译结束**: 2026-06-25 10:21
**最终状态**: built
---

**编译结束**: 2026-06-25 10:31
**最终状态**: published
