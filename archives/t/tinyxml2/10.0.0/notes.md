# tinyxml2 10.0.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-05-21
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. 下载源码: `curl -fsSL https://github.com/leethomason/tinyxml2/archive/refs/tags/10.0.0.tar.gz -o tinyxml2-10.0.0.tar.gz`
2. 解压并重命名工作目录: `tar xzf tinyxml2-10.0.0.tar.gz && mv tinyxml2-10.0.0 tinyxml2-10.0.0.work`
3. CMake 配置: `cd build && cmake -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF -DBUILD_TESTING=ON ..`
4. 编译: `make -j2`
5. Staging 安装: `make install DESTDIR=$TEST_PREFIX`
6. 测试: `ctest --output-on-failure` → 1/1 test passed
7. 打包: `ohc-run.py package tinyxml2 10.0.0`
8. 用户部署安装: `make install` (不带 DESTDIR)
9. 用户验证: `pkg-config --modversion tinyxml2` → 10.0.0

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build SSL 下载失败 | Python urllib SSL 证书验证失败 | 手动 curl 下载后用 --no-download 模式 |
| 2 | CMake 不识别 HarmonyOS 平台 | CMake 无 HarmonyOS 平台定义 | 非致命警告，编译正常通过 |
| 3 | manifest build_system 字段缺失 | 初始模板嵌套在 build.system 下 | 添加顶层 build_system: cmake 字段 |
| 4 | G0 干净构建验证失败 | clean-verify 仅支持 autotools configure | CMake 项目已知限制，已手动验证 |

## 源码修改

无源码修改，编译无需补丁。

## 依赖版本

- cmake 4.1.2
- make 4.4.1
- clang 15.0.4

## 验证结果

```bash
$ pkg-config --modversion tinyxml2
10.0.0

$ ctest --output-on-failure
100% tests passed, 0 tests failed out of 1
Total Test time (real) = 0.10 sec

$ ls ~/usr/local/lib/libtinyxml2.a
/storage/Users/currentUser/usr/local/lib/libtinyxml2.a

$ ls ~/usr/local/include/tinyxml2.h
/storage/Users/currentUser/usr/local/include/tinyxml2.h
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| tinyxml2-10.0.0-ohos-aarch64.tar.gz | 236KB | 预编译包 |

## 注意事项

- tinyxml2 是纯静态库项目（libtinyxml2.a + 头文件），无可执行二进制
- CMake 项目在 HarmonyOS 上会有 "System is unknown" 警告，不影响编译
- G0 clean-verify 当前仅支持 autotools configure，CMake 项目需手动验证

---

**编译结束**: 2026-05-21 16:07
**最终状态**: published
---

**编译结束**: 2026-05-21 16:11
**最终状态**: published

## 上游测试实测（规则 4 补充，2026-08-12）

- tinyxml2 10.0.0 上游测试为**自包含单文件测试框架**（xmltest.cpp，内部自带断言与统计，**不依赖 Google Test**）。
- 实测环境：OHOS aarch64，clang 15.0.4（/data/service/hnp/bin/clang++），`-std=c++17 -O0` 编译 xmltest.cpp + tinyxml2.cpp。
- 实测结果：**Pass 508 / Fail 0，通过率 100%**。
- 已集成到 conanfile.py build()：OHOS 下编译并运行上游 xmltest，校验汇总行 "Fail 0"，失败即抛 ConanException 使 conan create 失败。
- 同步更新 test_package/MANIFEST.yml：`upstream_test_in_build: true`、`assertion_count: 508`。
