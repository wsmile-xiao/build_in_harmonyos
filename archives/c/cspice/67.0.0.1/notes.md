# cspice 67.0.0.1 适配笔记（HarmonyOS PC · Conan cmake 重做版）

> 本目录为 cspice N0067（NAIF SPICE Toolkit，Conan 版本串不能用字母前缀故映射为 67.0.0.1）的
> 适配修复版本：制品仓已存在 cspice/67.0.0（R37/L0j），本次修改配方（build() 集成上游测试）
> 必须递增版本号后缀。

## 定位
- 产出动态 libcspice.so（CSPICE 天文导航/内核处理库，约 1500 个 C 函数），供 dlopen 及作依赖。

## 关键适配
- 构建：wrapper（AndrewAnnex/cspice-cmake-spiceypy）自发现 ohos.toolchain + 裸 cmake；
  `CSPICE_SRC` 环境变量喂本地 NAIF 源码（绕开 FetchContent）。
- 源码获取：NAIF 官方源（naif.jpl.nasa.gov）在本环境不可达（连接超时），配方增加
  GitHub N0067 源码镜像（MonsignorEduardo/cspice，与官方 N0067 同源）作为下载 fallback；
  官方源 URL 保留为主源（R39）。
- ELF 签名（E077/E083）：上游 test_cspice 测试二进制与构建树 .so 必须先签名才能执行。
- 上游测试集成：build() 加 `-DBUILD_TESTING=ON` + `ctest`（wrapper 自带 test_cspice 冒烟测试）。

## 状态
built（conan-verify 全门禁通过，上游测试 100%）

## 编译步骤

```bash
# 依赖：无外部依赖（W0 通过，requirements() 为空）
conan create archives/c/cspice/67.0.0.1 --user=ohpcd --channel=stable \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64

# 配方内 build() 实际执行：
cmake -B build-ohos -S . -DCMAKE_TOOLCHAIN_FILE=<ohos.toolchain.cmake> \
  -DOHOS_ARCH=arm64-v8a -DBUILD_SHARED_LIBS=ON -DBUILD_TESTING=ON \
  -DCSPICE_PATCH_SOURCE=ON -DCMAKE_POLICY_VERSION_MINIMUM=3.5
cmake --build build-ohos
# 上游测试（先签名测试二进制与构建树 .so，再运行）：
ctest --test-dir build-ohos --output-on-failure --no-tests=error
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | NAIF 官方源（naif.jpl.nasa.gov）连接超时，cspice.tar.Z 无法下载 | 本环境网络无法访问 NAIF（DNS 通但 TCP 连接超时） | conandata.yml 保留官方主源（R39），新增 `cspice_src_mirror`（GitHub N0067 完整源码镜像）作下载 fallback；source() 官方失败时自动回退镜像 |
| 2 | Conan 版本串 `N0067` 非法（字母前缀被拒） | Conan Version 类不接受字母开头版本号 | 版本映射为 `67.0.0.1`（N0067 = toolkit 67；制品仓已有 67.0.0 故升后缀） |
| 3 | 上游测试在 OHOS 上无法执行 | 测试二进制未签名，OHOS 要求 ELF 代码签名（E077/E083） | build() 新增 `_sign_build_artifacts(bdir)`：llvm-objcopy 移除 .codesign 段 + binary-sign-tool 自签名（jsoncpp/brotli 同款先例） |
| 4 | ctest 找不到 libcspice.so | 测试运行期需要 LD_LIBRARY_PATH 指向构建树库目录 | build() 显式把 build-ohos/lib、build-ohos/src 追加到 os.environ["LD_LIBRARY_PATH"] |
| 5 | `make: jobserver mkfifo: Operation not permitted` | HMDFS 平台限制（与 jsoncpp/c-blosc2/brotli 同） | 非致命，构建继续，可忽略 |

## 上游测试结果

```bash
$ ctest --test-dir build-ohos --output-on-failure --no-tests=error
Test #1: test_cspice ... Passed
100% tests passed, 0 tests failed out of 1

# test_package（消费者视角，R34 实质数值计算）：
[ok] tkvrsn_c 版本号含 N0067
[ok] vnorm_c((3,4,0)) == 5
[ok] vdot_c 正交 == 0
[ok] convrt_c 1KM == 1000 METERS
[ok] rpd_c * 180 == π
cspice: 全部断言通过
```

## 交付物

| 文件 | 说明 |
|------|------|
| lib/libcspice.so | CSPICE 共享库（已 ELF 签名） |
| include/cspice/*.h | SPICE 头文件（SpiceUsr.h 等） |
| test_package/ | 真实数值计算断言测试（R34，5 项） |

## 注意事项

- 上游测试：wrapper 自带 `test_cspice`（b1900_c 冒烟），CTest 注册 1 项，实测 100% 通过；
  NAIF 官方不随包发布独立 make check 套件。
- R38：纯库包，无可执行文件产物 → 无需 commands.json。
- R26：cspice 非系统同名库，动态链接无污染。
- 源码修改：无（纯配方级适配，conandata.yml `patches: {}`）。
---

**编译结束**: 2026-08-08 16:06
**最终状态**: built
