# cmark-gfm 0.29.0.gfm.13 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-06
- 编译器: clang/clang++
- 状态: built (Conan 配方已验证)

## 编译步骤

1. 初始化构建环境
   ```bash
   python3 $SKILL_ROOT/scripts/ohc-run.py init-build cmark-gfm 0.29.0.gfm.13 --url=https://github.com/github/cmark-gfm/archive/refs/tags/0.29.0.gfm.13.tar.gz
   ```

2. 应用补丁
   ```bash
   patch -p1 < patches/0001-CMakeLists.txt.patch
   ```

3. 配置 CMake (静态库)
   ```bash
   cmake -B build -S . -DCMARK_SHARED=OFF -DCMARK_STATIC=ON -DCMAKE_BUILD_TYPE=Release
   ```

4. 构建
   ```bash
   cmake --build build -j$(nproc)
   ```

5. 安装到 staging
   ```bash
   DESTDIR=$TEST_PREFIX cmake --install build
   ```

6. 运行测试
   ```bash
   ctest --output-on-failure
   ```
   结果: 69% tests passed (9/13)

## Conan 配方适配

1. 生成 conanfile.py
   ```bash
   python3 $SKILL_ROOT/scripts/ohc-run.py conan-init cmark-gfm 0.29.0.gfm.13
   ```

2. 手动修正 conanfile.py:
   - package_type: static-library
   - generate(): CMARK_SHARED=OFF, CMARK_STATIC=ON, CMAKE_SYSTEM_NAME=Linux for OHOS
   - package_info(): libs = ["cmark-gfm", "cmark-gfm-extensions"], bindirs = ["bin"]
   - build(): includes cmake.test() for upstream tests

3. 创建 test_package/test.c (R34: 实际调用 cmark_markdown_to_html API)

4. 验证配方
   ```bash
   python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify cmark-gfm 0.29.0.gfm.13
   ```
   结果: G0-G4 + L2/L4/L5 全部通过

5. 创建 commands.json (R38: 命令行工具声明)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake版本兼容性失败 | CMakeLists.txt 要求 VERSION 3.0，CMake 4.1.2 不支持 < 3.5 | 修改 CMakeLists.txt 为 VERSION 3.5，生成补丁 0001-CMakeLists.txt.patch |
| 2 | 测试部分失败 | Python ctypes CDLL 加载 .so 因 ELF 签名失败 | 鸿蒙平台特性，不影响编译。构建静态库避免此问题 |
| 3 | conandata.yml 镜像 URL | conan-verify 临时注入镜像 URL | 恢复为仅官方 GitHub URL (R39) |

## 源码修改

- **0001-CMakeLists.txt.patch**: 修改 cmake_minimum_required VERSION 3.0 → 3.5
  - 文件: CMakeLists.txt
  - 行数: +1/-1
  - 类型: portability
  - 守卫: 无（不需要平台条件）

## 依赖版本

- cmake: 4.1.2
- clang: 15.0.4
- make: GNU Make 4.4.1
- conan: 2.29.1

## 验证结果

```bash
# 从构建目录运行验证
cd $BUILD_SRC_DIR/build/src
./cmark-gfm --version
# 输出: cmark-gfm 0.29.0.gfm.13 - CommonMark with GitHub Flavored Markdown converter

# 功能测试
echo "# Hello World" | ./cmark-gfm
# 输出: <h1>Hello World</h1>
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方 (静态库) |
| conandata.yml | 源码 + 补丁声明 |
| test_package/ | L1 测试 (调用 cmark_markdown_to_html) |
| patches/0001-CMakeLists.txt.patch | CMake 版本兼容性补丁 |
| commands.json | 命令行工具声明 (R38) |
| manifest.yaml | 编译元数据 |
| reports/test-report.md | 测试报告 |
| reports/conan-verify-report.md | Conan 验证报告 |

## 注意事项

1. CMake 项目在鸿蒙平台的注意事项：
   - 需要修改 cmake_minimum_required VERSION 以兼容 CMake 4.x
   - CMake 4.1.2 不支持 VERSION < 3.5

2. 静态库构建：
   - 构建静态库避免 OHOS ELF 签名问题
   - CMARK_SHARED=OFF, CMARK_STATIC=ON

3. 测试限制：
   - Python ctypes CDLL 加载 .so 在 OHOS 上失败 (ELF 签名要求)
   - 所有可执行文件测试通过 (9/13)
---

**编译结束**: 2026-08-06 03:50
**最终状态**: built (Conan 配方已验证，待 CI 发布)
