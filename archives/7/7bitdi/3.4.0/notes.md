# 7bitdi 3.4.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-03
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos) / clang++
- 状态: built（conan-verify 8 门禁全部通过）

## 编译步骤

```bash
# 上游源码（官方 GitHub tag v3.4.0）
curl -L -o 7bitdi-3.4.0.tar.gz https://github.com/7bitcoder/7bitDI/archive/refs/tags/v3.4.0.tar.gz
# SHA-256: 8381102f5966a5d83cf590b8fa45904d055d74ec90822628240786ab100fb929

# 本地全量编译 + 上游测试（OHOS aarch64 工具链）
cmake -DCMAKE_CXX_STANDARD=17 -D_7BIT_DI_BUILD_ALL_TESTS=ON -D_7BIT_DI_INSTALL=ON -DCMAKE_INSTALL_PREFIX=$HOME/tmp/test-install-7bitdi-3.4.0 ..
make -j4
ctest --output-on-failure   # 745/745 通过

# Conan 配方验证（conan-verify：G0-G4 + L2/L4/L5 全过）
python3 scripts/ohc-run.py conan-verify 7bitdi 3.4.0
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Python urllib 下载 HTTPS 源报 SSL CERTIFICATE_VERIFY_FAILED | 执行机 CA 证书链未装 | 用 curl -k 下载官方 tarball 放入 ~/tmp/builds 后 init-build 复用；init-build 亦自动安装 CA 证书 |
| 2 | conan-init 生成的默认模板为 autotools 版 | 7bitDI 实际为 CMake 项目 | 重写 conanfile.py 为 CMakeToolchain 版，`_7BIT_DI_LIBRARY_TYPE=HeaderOnly` + package_type=header-library |
| 3 | test_package 空壳 C 测试 | 模板生成 test.c 只打印字符串 | 重写为 C++17 消费者测试，真实调用 7bitDI 服务注册/构建/注入 API 并断言 |
| 4 | test_package 运行时 ServiceNotFoundException | 接口以 singleton 注册而构造参数为 unique_ptr | 按上游 README 规范改为 addTransient<IMessage, HelloMessage> 注册 |
| 5 | 上游 googletest FetchContent 失败 | git dubious ownership | 添加 safe.directory 后重新配置 |

## 源码修改

无（纯 header-only 库，未修改任何上游源文件；未使用平台宏补丁）

## 依赖版本

- cmake 4.1.2 / make 4.4.1
- clang/clang++ 15.0.4 (OHOS SDK 26.0.0.18)
- googletest v1.15.0（仅测试期 FetchContent 使用，非运行时依赖）
- conan 2.32.0（OHOS 适配版）

## 验证结果

```bash
# 上游测试全量（OHOS aarch64 交叉工具链）
ctest --output-on-failure   # 100% tests passed, 745/745

# Conan 消费者验证（conan create 内 test_package）
test_7bitdi → "7bitdi consumer test: OK"
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | CMake header-only 配方（R32/R34/R39 合规） |
| conandata.yml | 官方 GitHub 源 + SHA-256 |
| test_package/ | 真实消费者测试（调用被测 API，R34 合规） |
| MANIFEST.yml | 上游测试声明（745 断言） |

## 注意事项

- 7bitDI 无运行时依赖，纯 header-only；Install 时仅安装 Include/ 头文件与 CMake config
- 上游测试通过 FetchContent 拉取 googletest，本地/CI 需可访问 github.com
- 已按 R39 使用官方 GitHub 源，无 file:// 或本地路径引用
---

**编译结束**: 2026-09-03 04:05
**最终状态**: built
