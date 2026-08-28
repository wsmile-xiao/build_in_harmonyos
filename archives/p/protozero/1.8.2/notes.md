# protozero 1.8.2 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-28
- 编译器: clang/clang++
- 状态: built

## 编译步骤

protozero 是 header-only C++14 库，CMake `install()` 仅安装 `include/protozero` 头文件，无编译产物库。

```bash
# 1) 上游测试构建（本地验证，BUILD_TESTING=ON）
cmake -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON -DCMAKE_INSTALL_PREFIX=... .
cmake --build . -j2
ctest --output-on-failure    # 100% tests passed, 0 failed out of 9

# 2) 配方构建（header-only 包，BUILD_TESTING=OFF）
# conan create 自动执行 cmake configure/build/install
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 官方 github.com 直连下载超时 | 本机到 github.com 连接不稳定 | 改用官方 codeload 托管主机下载同一 tag 归档并核验 SHA-256 |
| 2 | init-build 卡在 check_env SSL 证书更新 | SSL 证书检查尝试下载 CA 证书网络挂起（非致命警告） | 按 R14 手动模式继续，不阻塞构建 |
| 3 | conan-init 生成 Autotools 模板 | 模板按 URL 猜测构建系统为 autotools | 手工改写为 CMake header-library 配方 |

## 源码修改

无补丁（header-only，直接安装头文件，未修改上游源码）。

## 依赖版本

- 无第三方编译依赖（header-only）。
- writer_tests 需 protobuf 才启用（上游 test/CMakeLists.txt 按 PROTOBUF_FOUND 判断），非本包运行时依赖。

## 验证结果

```bash
# 上游测试（BUILD_TESTING=ON，9 个 ctest 用例全过）
reader_tests:    Passed (PBF reader, Catch2)
unit_tests:      Passed (unit: data_view/basic/buffer/endian/exceptions/iterators/varint/zigzag)
pbf-decoder-*:   Passed ×5 (no-args/help/empty/data/vt) + 2 WILL_FAIL 用例

# 消费验证：test_package 内 pbf_writer 编码 → pbf_reader 解码回环断言
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | CMake header-library 配方 |
| conandata.yml | 官方源 URL + SHA-256 |
| test_package/ | test_pbf.cpp 消费者回环测试 + MANIFEST.yml |

## 注意事项

- 版本号保持上游 1.8.2（首次适配）。
- 官方来源核验：仓库 https://github.com/mapbox/protozero，tag v1.8.2，SHA-256 68d1df951b4d8397355c8fc9ffed40d9c06282a877fe847403feac6edcee3ef1。
