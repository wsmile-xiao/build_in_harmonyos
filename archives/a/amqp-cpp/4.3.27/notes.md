# amqp-cpp 4.3.27 适配笔记

## 编译环境
- 构建系统: cmake（C++17）
- 编译日期: 2026-09-03
- 编译器: clang/clang++ 15.0.4 (aarch64-linux-ohos)
- 状态: built

## 编译步骤

```bash
# 源码
git ls-remote --tags https://github.com/CopernicaMarketingSoftware/AMQP-CPP  # 确认 v4.3.27 官方标签
curl -fsSL https://github.com/CopernicaMarketingSoftware/AMQP-CPP/archive/refs/tags/v4.3.27.tar.gz
# sha256: af649ef8b14076325387e0a1d2d16dd8395ff3db75d79cc904eb6c179c1982fe

# 手动验证（探索性编译）
cmake .. -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DAMQP-CPP_BUILD_EXAMPLES=OFF \
         -DCMAKE_BUILD_TYPE=Release -DCMAKE_POLICY_VERSION_MINIMUM=3.5
make -j2 && make install DESTDIR=$TEST_PREFIX

# 上游测试（tests/table/table.cpp，唯一可独立编译的官方测试）
clang++ -std=c++17 -Iinclude tests/table/table.cpp -Lbuild/bin -lamqpcpp -o table_test
./table_test   # array(string(abc),string(xyz)) / string(abc) / string(xyz) → 通过

# 配方验证
python3 scripts/ohc-run.py conan-verify amqp-cpp 4.3.27   # G1-G4 全部 PASS

# 收尾
python3 scripts/ohc-run.py finish amqp-cpp 4.3.27 built   # W3 本地 CI 通过
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 下载报"下载内容是 HTML" | 直接传仓库首页 URL 而非 tag tarball | 使用官方 tag tarball URL `archive/refs/tags/v4.3.27.tar.gz` |
| 2 | CMake 配置失败：Compatibility with CMake < 3.5 has been removed | 上游 `cmake_minimum_required(3.4)` 与 CMake 4.1.2 不兼容 | 配方 `cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"})`；toolchain CACHE 变量对该检查不生效 |
| 3 | find_package(OpenSSL) 失败 | 开启 `AMQP-CPP_LINUX_TCP=ON` 才引入 OpenSSL | 核心库不依赖 IO 层，保持 `AMQP-CPP_LINUX_TCP=OFF`（上游默认） |
| 4 | test_package 断言失败 "array size mismatch" | `Array::size()` 返回线格式编码尺寸（含 4 字节头），非元素个数 | 改用 `Array::count()` |

## 源码修改

无补丁（纯配方层适配，未修改上游源码）。

## 依赖版本

无 Conan 外部依赖；仅系统 libc/libc++。

## 验证结果

```bash
# conan-verify: G0/G1/G2/G3/G4 全 PASS
# W3 本地 CI: setup.sh 通过 + build_and_test.sh 通过（1/1，Pass rate 100%）
# 上游测试: tests/table/table.cpp 编译运行通过
# test_package: AMQP::Array 构造/访问 + AMQP::Address URL 解析，6 断言
```

## 注意事项

- 库为 header+static lib 形态（`libamqpcpp.a` + `include/amqpcpp.h`），包内同时安装 `amqpcpp.pc` 与 `amqpcppConfig.cmake`。
- 消费者需自行提供网络/事件循环层；TLS 支持需消费者自行链 OpenSSL 并启用 linux_tcp 模块（本配方不携带）。

---

**编译结束**: 2026-09-03 10:33
**最终状态**: built
