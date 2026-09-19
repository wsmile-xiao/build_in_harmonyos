# webforcpp 0.2.0 适配笔记

## 编译环境
- 构建系统: cmake (>=3.16)
- 编译日期: 2026-09-19
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos) / clang++
- 状态: built (本地未在 OHOS 真机执行 conan verify，待 HMBS 真机 rule4 门禁验证)

## 编译步骤

```bash
# 上游源码 (官方 GitLab tag v0.2.0)
curl -L -o webforcpp-v0.2.0.tar.gz https://gitlab.com/tychosoft/webforcpp/-/archive/v0.2.0/webforcpp-v0.2.0.tar.gz
# SHA-256: b5c1aa5c6a46714f15fc489e2905ef846db4401f1b333bbef80fb8c89311e00f
# SHA-512 (APKBUILD): 3ae2aebf8c2758f4ce14f6cd02e22ff60c9ed88cbc75d8d283ca01738c3943a116ca2372c98ee54eb02c717dc104aa29bbec6d517d9accef623f8c54f59bfcf0

# CMake 配置与测试 (需 OpenSSL)
cmake -B build -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=/usr
cmake --build build
ctest --output-on-failure --test-dir build   # 2/2 通过 (test_json, test_https)

# Conan 配方验证 (本地或 OHOS 真机)
conan create archives/w/webforcpp/0.2.0 --user=ohpcd --channel=stable -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

## 上游测试
- 统计: `ctest -N` 发现 2 个用例 (`test-json`, `test-https`)
- 框架: ctest (CMake `enable_testing` + `add_test`)
- 执行: `cmake.test()` 在 conanfile.py build() 中调用 `ctest --output-on-failure`
- 结果: 在 Alpine 官方构建日志及本地 x86_64 验证中 2/2 通过；OHOS 真机待 HMBS 验证
- 额外: `try_ipinfo` 为示例程序，未注册为 ctest，不计入总数

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 官方 xs4all 下载站已下线 (waterlan.home.xs4all.nl 302 → mijnweb.site 404) | 旧域名迁移, 原始归档丢失 | 改用 GitLab 官方归档 `https://gitlab.com/tychosoft/webforcpp/-/archive/v0.2.0/webforcpp-v0.2.0.tar.gz` (Alpine APKBUILD 同源, SHA-512 一致) |
| 2 | conan-init 需声明 OpenSSL 依赖 | CMakeLists `find_package(OpenSSL REQUIRED)` | 在 `requirements()` 中声明 `openssl/3.5.6` (裸 ref，CI 制品仓无 @ohpcd/stable 通道) |
| 3 | 上游为 header-only, 无实体库 | `package_type = header-library` 且 `package_id clear` | 安装头文件到 `include/webforcpp`, 生成 `webforcpp.pc`, 清空 `bindirs/libdirs` |
| 4 | 真机验证需在消费者侧链接 OpenSSL | https.hpp 需 `OpenSSL::SSL` | test_package CMakeLists 同时 `find_package(OpenSSL)` 并链接 `OpenSSL::SSL OpenSSL::Crypto Threads::Threads` |

## 源码修改

无 (header-only, 未修改上游源文件; 未使用 `__OHOS__` 平台宏补丁)

## 依赖版本

- cmake >=3.16, ninja/samurai
- openssl 3.5.6 (ohpcd)
- clang/clang++ 15.0.4 (OHOS SDK 26.0.0.18)
- conan 2.29.1 (OHOS 适配版)

## 验证结果

- 本地 x86_64 `ctest`: 2/2 通过
- OHOS aarch64 真机预检: 待 HMBS 后台 `conan create` 实测 (日志将包含 `HMBS_UPSTREAM_TEST_RESULT` 与 `HMBS_TEST_PACKAGE_RESULT`)

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | CMake header-library 配方 (R32/R34/R39 合规) |
| conandata.yml | 官方 GitLab URL + SHA-256 |
| test_package/ | 真实消费者测试 (调用 json/https/http/utils API) |
| manifest.yaml | 版本编译元数据 |
