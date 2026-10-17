# libxeddsa 2.0.0-20231128.d725c81 适配笔记

## 上游

- 仓库：https://github.com/Syndace/libxeddsa（wireapp/libxeddsa 已 404，现归 Syndace）
- 版本：commit `d725c816bb26483ac397ce0d19de5ad2972955f1` = tag `v2.0.0`（2023-11-28；
  2.0.0 发布于 2022-04-02，该 commit 在 tag 之上仅补 docs/.readthedocs.yaml，代码一致）
- 许可：MIT；纯 C；CMake >= 3.5（CMake 4.x 兼容下限恰为 3.5，无需升级）
- 功能：Curve25519/Ed25519 密钥对工具集——双向公钥转换（RFC 7748 §4.1）、
  XEdDSA 私钥签名（Signal 规范）、种子签名/验签（RFC 8032）、X25519 密钥协商；
  ref10（djb 参考实现）作为子目录内置

## W0 依赖检查（2026-09-19）

唯一外部依赖 libsodium（核实方式：conan download，--only-recipe，remote 选 ohpcd）：

```
# libsodium/1.0.20 (a080c1f36d) 与 libsodium/1.0.22 (1b4ff2170) 均已发布
# libsodium/1.0.22 的 OHOS 二进制 4b977264131a1c74e82bd6bb51b63cc9aadc4cfa 存在
```

libxeddsa 所需符号（`sodium_init/sodium_memzero/sodium_stackzero/randombytes_buf/
crypto_hash_sha512_{init,update,final}/crypto_sign_*/crypto_scalarmult_curve25519`）
已在 ohpcd 1.0.22 包头文件与静态归档中逐一验证（sodium_stackzero 在
sodium/utils.h:27 声明、归档字节扫描 2 次命中）。

**双远程遮蔽问题在此不成立**：ci/conan/setup.sh 明确 `conan remote disable
conancenter`，CI 环境仅 ohpcd 生效，裸 `requires("libsodium/1.0.22")` 解析到
ohpcd 的 OHOS 二进制。liboprf/libetebase 的 vendored sodium 方案是老预检环境
（conancenter 在前 + 无 ohpcd 二进制）的历史产物；et/7.0.0（已合入 main）即用
直接 requires。本配方跟随 et 先例。

## 构建系统分析与决策

| 问题 | 根因 | 对策 |
|------|------|------|
| `CMAKE_SYSTEM_NAME=HarmonyOS` | OHOS 适配版 CMakeToolchain 的映射，vanilla CMake 无此平台文件；ref10 `if (UNIX)` 与 FindSodium `elseif (UNIX)` 双双落空 → FATAL_ERROR | `tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"`（et/7.0.0 先例） |
| FindSodium 定位不到 conan sodium | 上游自带 module 模式 FindSodium.cmake；其 `sodium_USE_STATIC_LIBS EQUAL _LAST` 看门狗对非数值 "NO" 恒为 false，每次 configure 先 unset 全部 `sodium_*` CACHE，`-D` 注入失效 | 喂 `CMAKE_INCLUDE_PATH`/`CMAKE_LIBRARY_PATH`（+`CMAKE_PREFIX_PATH`），find_path/find_library 的文档化搜索变量，从 `self.dependencies["libsodium"].package_folder` 取路径 |
| 无条件构建动态库 | 上游静态+动态并行；`libxeddsa.so` 需吸收 ohpcd 静态非 PIC `libsodium.a`，真机有重定位风险；仓库规范静态优先（R26） | 补丁 0001：动态库目标/动态测试/动态 ctest 三处以 `BUILD_SHARED_LIBS` 门控；静态构建不受影响 |
| 上游无头文件安装规则 | `install(TARGETS xeddsa_static)` 只装库 | package() 手工补装 `include/xeddsa.h` + `ref10/include/cross_platform.h`（公开头直接 `#include <cross_platform.h>`） |
| 随机源探测 | ref10 用 CHECK_SYMBOL_EXISTS 选 kernelrandombytes 实现；OHOS musl unistd.h 声明 getentropy → 选中 getentropy2.c；即使无也有 getrandom/urandom 多级回退 | 无需处理，交叉编译下符号存在性检查可用 |

## 测试

- 上游（build() 内 `cmake.test()`，CI 同 profile 原生执行）：
  - `xeddsa_test_static`：单二进制 3 套件（signing 64×64、conversion_uniqueness
    8192 键、pub_derivation）
  - `kernelrandombytes_test_static`：getentropy 路径自检
  - BUILD_SHARED_LIBS=OFF 后共注册 2 项 ctest
- test_package：direct-cc（无 CMake，规避 CMAKE_SYSTEM_NAME=HarmonyOS 坑；
  libsodium/1.0.20 + libmacaroons/0.3.0 先例），17 个确定性断言：
  - RFC 8032 §7.1 TEST 1/2：ed25519_seed_sign 精确签名字节、verify 接受/篡改拒绝、
    seed→pub、seed_to_priv+priv_to_ed25519_pub 一致性
  - RFC 7748 §5.2 向量 1/2 + §6.1 Alice/Bob 共享密钥 + priv_to_curve25519_pub 已知答案
  - 固定 nonce 的 ed25519_priv_sign 回环、错符号位拒绝、篡改消息拒绝、
    priv_force_sign 翻转符号位、转换回环

## 本机验证（无编译器，静态检查）

- [x] 源码 tarball 下载 + sha256 = `b54af487fb6278fa7832be3cf5e7f88cd65900e635f85e47cc1286bc1920f7ed`
- [x] 补丁对原始 tarball `git apply --check` 通过
- [x] conanfile.py / test_package/conanfile.py `py_compile` 通过
- [x] conandata.yml / manifest.yaml / MANIFEST.yml YAML 解析通过
- [x] W0：libsodium/1.0.22 ohpcd 二进制存在且符号齐备

## 真机验证（2026-09-19，frp-tip.com:56267 ✅ 全绿）

设备：frp 机（20 核/23.9G，clang-15 + sysroot 在 /storage/Users/currentUser/usr/local，
profile=ohos-local，conan 2.31.1 OHOS 适配版，conancenter 已禁用）。构建全程
`-c tools.build:jobs=2` 控内存（free 维持 ~450M + 48G swap 未动）。

```
conan create . --build=libxeddsa/* -pr:h=ohos-local -pr:b=ohos-local -c tools.build:jobs=2
```

- 上游 ctest：**100% tests passed, 0 failed, 3/3**（xeddsa_test_static 7.4s 含
  signing 64×64/conversion_uniqueness 8192/pub_derivation 三套件 +
  kernelrandombytes 静 12.8s/动 13.5s——ref10 内部动态目标不受顶层门控影响，不链
  sodium，无害照跑）
- test_package：**RESULT: PASS (20/20)**（RFC 8032 两向量精确签名 + RFC 7748
  KAT + XEdDSA 符号位交叉验证 + 篡改拒绝）
- 产物（L5）：lib/libxeddsa.a（155KB）+ include/xeddsa.h + include/cross_platform.h
  + licenses/LICENSE
- 无外网真机预置实操：github 不可达 → `core.sources:download_cache` 指向
  ~/conan_dl_cache 并以 sha256 命名预置 tarball（pcapfix 先例）；scp/sftp 均被
  设备 sshd 拒绝（无 sftp 子系统 + umask fortify），用 `cat | ssh 'cat > file'` 管道传输

## 真机三轮修复记录（配方与测试的增量）

1. `cmake.test(output_on_failure=True)` TypeError——该 conan 的 CMake.test() 无此
   形参；改 libzmq 先例 `self.run("ctest --output-on-failure", env="conanbuild")`
2. test_package 裸调 conf 里的 clang-15 缺 --sysroot（stdio.h not found）；改用
   conanbuild 环境的 `${CC} ${CFLAGS}`（profile buildenv 自带 sysroot/code-sign，
   libsodium/1.0.22 test_package 同款）
3. test 断言误用：`priv_to_ed25519_pub` 内部 sc_clamp 会破坏 `priv_force_sign`
   输出的取反标量，直接读其符号位必然错；改为功能等价的交叉签名/验签断言
   （上游 test_signing 的正确用法是从 curve 公钥+显式符号位推导）

## 下一步

- shadow CI / 平台 CI：`CI_PACKAGES="archives/l/libxeddsa/2.0.0-20231128.d725c81" zsh ci/conan/build_and_test.sh`（真机已绿，CI 主要走 L0-L5 门禁口径）
- 建 issue + 推 fork + PR（分支 feat/libxeddsa-2.0.0-20231128.d725c81）

## 风险与备注

- 若真机环境存在系统级 libsodium + pkg-config（FindSodium 的 pkg-config HINTS
  优先于 CMAKE_LIBRARY_PATH），理论上可能链到系统 sodium——按 minisign 笔记，
  预检环境不预装系统 libsodium，此风险仅在有人手工装过时成立。
- shared=True 未在真机验证：动态库会吸收静态 sodium，理论上 aarch64 可链接，
  但默认 shared=False，PR 不承诺动态制品。
- 分支：feat/libxeddsa-2.0.0-20231128.d725c81（worktree：
  D:\harmonyos\worktrees\libxeddsa）
