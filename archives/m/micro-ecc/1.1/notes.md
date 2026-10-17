# micro-ecc 1.1 适配笔记

## 编译环境
- 构建系统: custom（上游无构建系统，直接 clang 编译 uECC.c）
- 编译日期: 2026-09-07
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos, OHOS PC 工具链)
- 状态: built

## 编译步骤
1. 官方源码: https://github.com/kmackay/micro-ecc/archive/refs/tags/v1.1.tar.gz，SHA-256 `0e39fba553f6ae1870c3033201d3eaa61a59bf4aa3bdbabed7a26e1bb5b7e890`
2. conanfile.py: `clang -fPIC -O2 -I. -c uECC.c` → `llvm-ar rcs libuecc.a uECC.o`（静态库），package 头文件 + .inc 汇编包含文件
3. `conan create archives/m/micro-ecc/1.1 -pr:h=ohos-aarch64 -pr:b=default --build=missing` 通过（ctest 2/2 通过）

## 上游测试申报表（全量枚举台账，R51）

### 枚举清单（按用户测试源/框架/样例/基准/fixture/脚本/构建目标分类）

| 条目 | 类别 | 是否独立上游用例 | 是否实际运行 | 结果/原因 |
|------|------|------------------|--------------|-----------|
| test/test_ecdh.c | 用户测试源（main） | ✅ 独立用例 | ✅ | 通过（256 次/曲线 × 5 曲线 keygen+ECDH 一致性） |
| test/test_ecdsa.c | 用户测试源（main） | ✅ 独立用例 | ✅ | 通过（256 签名/曲线 × 5 曲线 sign+verify） |
| test/test_compress.c | 用户测试源（main） | ✅ 独立用例 | ✅ | 通过（256 点/曲线 × 5 曲线 compress/decompress 往返） |
| test/test_compute.c | 用户测试源（main） | ✅ 独立用例 | ✅ | 通过（256 私钥/曲线 × 5 曲线 compute_public_key；私钥=0 拒否） |
| test/ecdsa_test_vectors.c | 用户测试源（main，携带固定向量） | ✅ 独立用例 | ✅ | 通过（secp256k1 官方向量 sign_with_k/verify） |
| test/public_key_test_vectors.c | 用户测试源（main，携带固定向量） | ✅ 独立用例 | ✅ | 通过（5 曲线固定 K→Q 向量合法性） |
| test/test_ecdsa_deterministic.c.example | 样例（上游以 `.example` 后缀隔离，依赖外部 SHA256 实现，仅 `extern` 声明未提供） | ❌ 样例，不计独立用例 | ❌ 不可运行 | 编译失败 `unknown directive: typedef`（clang 把 .example 非 C 头处理；上游本身不编译该文件，需自行带入 SHA256 实现才算独立程序，非上游注册用例） |
| test/emk_rules.py | 构建脚本（emk 构建系统，被 emk_project.py 引用） | ❌ 非测试 | ❌ | 构建系统元数据 |
| emk_project.py / emk_rules.py | 构建目标定义（emk：osx/avr/arm_thumb/rpi 交叉目标） | ❌ 非测试 | ❌ | 上游专属构建系统，未注册 ctest/Makefile 测试目标 |
| examples/ecc_test/ecc_test.ino | 样例（Arduino 示例） | ❌ 样例，不计独立用例 | ❌ | Arduino IDE 示例，非上游测试 |
| scripts/mult_arm.py etc. | 代码生成脚本 | ❌ 非测试 | ❌ | 汇编生成工具脚本 |
| library.properties / README / LICENSE | 元数据 | ❌ 非测试 | ❌ | 文档/元数据 |
| uECC.c/uECC.h/uECC_vli.h/types.h/platform-specific.inc/curve-specific.inc/asm_*.inc | 框架头/源码（被测库本体） | ❌ 非测试 | ❌ | 被测库实现 |

### 双口径统计

- `source_declared_total`（官方 tag 源码中可复制枚举的独立测试用例）：**6**
- `configured_executable_total`（OHOS 配置实际实例化/注册的可执行用例）：**6**
- `executed_passed_total`：**6** | 失败：**0** | 未运行/未实例化：**0**
- 全量通过率：**6/6 = 100%**；当前配置可执行集合通过率：**6/6 = 100%**

### 逐项映射（源码声明 → 构建条件 → 构建目标 → 执行日志）

| 源码声明 | 构建条件 | 构建目标 | 执行证据 |
|----------|----------|----------|----------|
| test_ecdh.c main() | `clang -std=c99 -O2 -fPIC -I<src>` + uECC.c，OHOS clang 15 | 可直接运行可执行 | rc=0，日志 `.ohc/evidence/upstream-tests/test_ecdh.run.log` SHA-256 `5b349438bab10af674cd07a786999a4f52b38fd6c1b472d38fe066b24ed668c7` |
| test_ecdsa.c main() | 同上 | 可直接运行可执行 | rc=0，`test_ecdsa.run.log` SHA-256 `1b54fe29dc6adf5fe6d9926bc8133f89bd518fbdfefe01eabb2517d189768059` |
| test_compress.c main() | 同上 | 可直接运行可执行 | rc=0，`test_compress.run.log` SHA-256 `454531f1135f8cfa4e1a939669ebaefdb81a4ecfcfb984479fdddd1d14e6bf59` |
| test_compute.c main() | 同上 | 可直接运行可执行 | rc=0，`test_compute.run.log` SHA-256 `41f1085f83cb71d8954455383cc101c3d19fe9aed9f25c5aac18594e155bf1be` |
| ecdsa_test_vectors.c main() | 同上 | 可直接运行可执行 | rc=0，`ecdsa_test_vectors.run.log` SHA-256 `43c3916c1aea488b73a02ab157cc299f20e9ad5abb4928cb2077eeac3ee87aea` |
| public_key_test_vectors.c main() | 同上 | 可直接运行可执行 | rc=0，`public_key_test_vectors.run.log` SHA-256 `2e9d647511525c61b58224cf5cb4bfe3f0b6640ff31d98bc57d0cede03942d1f` |

> 编译命令均为实际 clang 命令（无占位符）；6 个独立用例全部在 OHOS aarch64 工具链编译并原生运行，exit 0。
> 未实例化项：无。样例 `.example` 与 Arduino 示例不计入独立用例（任务规则：样例不得误算为独立用例）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | test_ohos.c 引用 `uECC_PLATFORM` 编译失败 | 该宏是 types.h 内部宏，未随 uECC.h 公开 | 改用编译器宏 `__aarch64__` 断言 OHOS arm64 平台识别 |
| 2 | GitHub API 限流、github.com 直连超时 | 网络环境限制 | 使用官方 codeload.github.com 下载端点获取同一官方 tarball，SHA-256 核验一致 |

## 源码修改
无补丁（patches/ 为空）。上游原样编译。

## 依赖版本
无外部依赖（micro-ecc 为自包含 C 库）。工具链：clang 15.0.4 / llvm-ar（OHOS PC SDK 26.0.0.18）。

## 验证结果
- `conan create`（ohos-aarch64）：成功，ctest 2/2（test_micro_ecc + test_micro_ecc_ohos）
- 上游测试 6/6 通过（详见台账）
---

**编译结束**: 2026-09-07 23:36
**最终状态**: built
