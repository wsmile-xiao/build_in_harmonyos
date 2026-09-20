# resolv-wrapper 1.1.8 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-20
- 编译器: clang/clang++（OHOS SDK llvm 15.0.4）
- 状态: built

## 编译步骤

```bash
# init-build：官方上游 tarball（gitlab.com/cwrap/resolv_wrapper tag resolv_wrapper-1.1.8）
#   sha256 92830fbc691151c348d40813c39e4f6d1876046a28c705439105982a25af7115
# 直接 CMake 交叉编译验证（OHOS 6.0 aarch64）：
cmake -S . -B build \
  -DCMAKE_C_COMPILER=clang \
  -DCMAKE_C_COMPILER_TARGET=aarch64-linux-ohos \
  -DCMAKE_SYSROOT=$OHOS_SDK/native/sysroot \
  -DUNIT_TESTING=OFF
cmake --build build -j2
# 上游测试单独以 UNIT_TESTING=ON 构建并实际执行（cmocka/2.0.2 + socket-wrapper/1.4.1）
# Conan 配方构建：
conan create . --version=1.1.8 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `#error "No res_nquery function"` 等 4 处 | OHOS libc 只有经典 `res_init/res_query/res_search`，无线程安全 `res_n*` 系列，且 `libresolv.a` 为空壳 | dlsym 绑定 libc 经典符号 + wrapper 自行导出 `res_n*`（patch 0001）|
| 2 | 上游测试链接/运行失败 | 测试源硬编码 `res_n*` 符号，OHOS 头文件与 libc 均无 | tests/CMakeLists 对 OHOS 目标 force-include compat 声明并链接 wrapper 导出符号（patch 0002）|
| 3 | `test_res_fake_srv_query_minimal` 解析失败（ns_rr_type=0）| OHOS `ns_initparse` 要求真实应答长度，传缓冲区大小 256 时解析失败 | 测试改用 `res_nquery` 返回的真实长度（patch 0003）|

## 源码修改

- `patches/0001-src-resolv_wrapper.c.patch`：libc `res_*` 符号经 dlsym 绑定（避免 LD_PRELOAD 递归拦截自身），wrapper 导出 `res_n*` 符号
- `patches/0002-tests-CMakeLists.txt.patch`：OHOS 测试目标接入 compat 头与 wrapper 链接
- `patches/0003-tests-test_dns_fake.c.patch`：`ns_initparse` 传真实应答长度

## 依赖版本

- cmocka/2.0.2（测试框架，制品仓可消费）
- socket-wrapper/1.4.1（上游测试 LD_PRELOAD 助测库，制品仓可消费）
- 系统：OHOS 6.0 sysroot（libc + libdl）

## 验证结果

```bash
# 上游测试（UNIT_TESTING=ON，本机真机 PC 实际运行）
#   test_res_init:  2/2 通过
#   test_dns_fake: 16/16 通过
#   合计: 18/18 = 100%
# Conan test_package 消费者用例（res_ninit/res_nquery/res_nclose 公开 API）
#   1/1 通过
# conan-verify: G1/G0/G2/G3/G4 + L2/L4/L5 全 PASS
# finish: W3 本地 CI 通过，.ci-result.json exit_code=0
```

## 注意事项

- 本库为 LD_PRELOAD 注入型动态库（libresolv_wrapper.so），按 shared 打包，不属于 R26 系统同名库静态化场景
- 适配基于能力检测（`HAVE_RES_INIT/HAVE_RES_NQUERY` 等）与 `CMAKE_SYSTEM_NAME`，在 glibc/musl/OHOS 间可切换，无平台宏硬编码
