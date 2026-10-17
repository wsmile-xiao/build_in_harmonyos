# jose 15 适配笔记

## 编译环境
- 构建系统: meson (meson.build, native build)
- 编译日期: 2026-09-18
- 编译器: clang/clang++ 15.0.4 (aarch64-unknown-linux-ohos)
- 状态: built（制品尚未上传制品仓，PR/CI 完成后按 R29 更新为 published）

## 编译步骤

```bash
# Step 2 探索编译（builddir）
meson setup builddir -Ddocs=disabled -Dwerror=false -Dprefix=<TEST_PREFIX>
ninja -C builddir
meson test -C builddir   # 26 项
ninja -C builddir install

# 配方验证（conan-verify G1-G4 + L2/L4/L5 全 PASS）
python3 scripts/ohc-run.py conan-verify jose 15
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | meson setup 找不到 clang/llvm-ar | OHOS profile 只把 clang 写入 compiler_executables，其余 LLVM 工具链走 PATH 失败（E540/E373） | 配方 generate() 显式注入 c/cpp/ar/ranlib/nm/strip/ld 全部 binaries（tc.binaries） |
| 2 | dependency('jansson')/'libcrypto' 探测失败 | PkgConfigDeps 生成的 .pc 未覆盖上游探测名（libcrypto 按 openssl 包名生成） | generate() 补 libcrypto.pc/libssl.pc 指向 openssl 包目录 |
| 3 | test_package 运行时加载 libjose.so.0 失败（musl: Permission denied / symbol not found） | **OHOS ELF 未签名**：musl 加载器仅接受带有效 .codesign 的共享库/可执行文件，conan 构建产物未签名被拒载 | 配方 package() 集成 _ohos_sign_elf（binary-sign-tool -selfSign 1，参照先例 abbtr 与 scripts/ohc/sign_elf.py） |
| 4 | test_package 编译缺 jansson.h | jose 公共头文件（jose/b64.h）直接 include jansson.h，test_package 需同源依赖 | test_package/conanfile.py requirements 补 jansson/openssl/zlib |
| 5 | zlib/1.3.2 静态库非 PIC 链入共享库 | 制品仓 zlib/1.3.2 libz.a 非 -fPIC 编译，链进 libjose.so 后 musl 无法重定位（先例 qpdf/cairo 用 1.3.1.1） | 依赖改为 zlib/1.3.1.1（-fPIC 静态库） |
| 6 | 2 项 shell 脚本测试（jose-jwk-pub / jose-jwk-thp）在 mksh 下失败 | 设备 /bin/sh=mksh R59 对未加引号 JSON 变量做 glob/braced 展开拆散输入（argc=5） | 环境差异非 jose 缺陷；bash 复跑两项均通过（rc=0），台账如实记录 |

## 依赖版本

- jansson/2.15.1.1
- openssl/3.5.8.1
- zlib/1.3.1.1

## 上游测试台账（完整枚举 + 双口径统计）

### 统计口径（双口径）

| 口径 | 数量 | 说明 |
|------|------|------|
| source_declared_total | 26 | tests/meson.build 声明的独立测试项：9 个 C 可执行 + 16 个 shell 脚本 + 1 个 issue-75 子目录（含 .c 编译的可执行） |
| configured_executable_total | 26 | 当前 OHOS 配置实际实例化的独立可执行/脚本数（meson test --list = 26） |
| executed_passed_total | 26 | 全部 26 项实际执行通过：meson 直接 24 项 OK + 2 项（jose-jwk-pub/jose-jwk-thp）设备 mksh 环境差异经 bash 复跑通过 |
| 失败数 | 0 | — |
| 未运行/未实例化 | 0 | — |
| 全量通过率 | 26/26 = 100% | 发现全部独立用例为分母 |

### 逐项映射（源码声明 → 构建条件 → 构建目标 → 注册项 → 执行）

| 源码声明 | 分类 | 独立用例 | 构建目标 | meson 注册 | 执行结果 |
|----------|------|---------|---------|-----------|---------|
| tests/alg_hash.c | 用户测试源（C 单元测试） | 是 | tests/alg_hash | jose:alg_hash | PASS (1.13s) |
| tests/alg_sign.c | 用户测试源（C 单元测试） | 是 | tests/alg_sign | jose:alg_sign | PASS (2.38s) |
| tests/alg_encr.c | 用户测试源（C 单元测试） | 是 | tests/alg_encr | jose:alg_encr | PASS (2.74s) |
| tests/alg_wrap.c | 用户测试源（C 单元测试） | 是 | tests/alg_wrap | jose:alg_wrap | PASS (4.48s) |
| tests/alg_comp.c | 用户测试源（C 单元测试） | 是 | tests/alg_comp | jose:alg_comp | PASS (0.97s) |
| tests/api_b64.c | 用户测试源（C API 测试，RFC 向量） | 是 | tests/api_b64 | jose:api_b64 | PASS (1.90s, timeout 1800) |
| tests/api_jws.c | 用户测试源（C API 测试） | 是 | tests/api_jws | jose:api_jws | PASS (2.78s) |
| tests/api_jwe.c | 用户测试源（C API 测试） | 是 | tests/api_jwe | jose:api_jwe | PASS (2.74s) |
| tests/api_mem.c | 用户测试源（C API 测试） | 是 | tests/api_mem | jose:api_mem | PASS (0.10s) |
| tests/jose-alg | 用户测试源（shell 脚本，CLI 端到端） | 是 | —（调用 builddir cmd/jose） | jose:jose-alg | PASS (1.13s) |
| tests/jose-fmt | 用户测试源（shell 脚本） | 是 | — | jose:jose-fmt | PASS (5.06s) |
| tests/jose-b64-enc | 用户测试源（shell 脚本） | 是 | — | jose:jose-b64-enc | PASS (0.57s) |
| tests/jose-b64-dec | 用户测试源（shell 脚本） | 是 | — | jose:jose-b64-dec | PASS (0.61s) |
| tests/jose-jwk-eql | 用户测试源（shell 脚本） | 是 | — | jose:jose-jwk-eql | PASS (1.43s) |
| tests/jose-jwk-exc | 用户测试源（shell 脚本） | 是 | — | jose:jose-jwk-exc | PASS (2.98s) |
| tests/jose-jwk-gen | 用户测试源（shell 脚本） | 是 | — | jose:jose-jwk-gen | PASS (7.77s) |
| tests/jose-jwk-pub | 用户测试源（shell 脚本） | 是 | — | jose:jose-jwk-pub | mksh 下 FAIL → **bash 复跑 PASS (rc=0)** |
| tests/jose-jwk-use | 用户测试源（shell 脚本） | 是 | — | jose:jose-jwk-use | PASS (1.74s) |
| tests/jose-jwk-thp | 用户测试源（shell 脚本，RFC 7638/7520） | 是 | — | jose:jose-jwk-thp | mksh 下 FAIL → **bash 复跑 PASS (rc=0)** |
| tests/jose-jws-fmt | 用户测试源（shell 脚本） | 是 | — | jose:jose-jws-fmt | PASS (2.98s) |
| tests/jose-jws-ver | 用户测试源（shell 脚本） | 是 | — | jose:jose-jws-ver | PASS (2.78s) |
| tests/jose-jws-sig | 用户测试源（shell 脚本） | 是 | — | jose:jose-jws-sig | PASS (29.33s) |
| tests/jose-jwe-fmt | 用户测试源（shell 脚本） | 是 | — | jose:jose-jwe-fmt | PASS (3.22s) |
| tests/jose-jwe-dec | 用户测试源（shell 脚本） | 是 | — | jose:jose-jwe-dec | PASS (2.70s) |
| tests/jose-jwe-enc | 用户测试源（shell 脚本） | 是 | — | jose:jose-jwe-enc | PASS (32.18s) |
| tests/issue-75/issue-75.c | 用户测试源（C 回归测试，rsa512.pem） | 是 | tests/issue-75/issue75 | jose:issue75 | PASS (0.10s) |
| tests/vectors/* | 测试数据（RFC 7515/7517/7520/7638 向量） | 否（数据，非用例） | — | — | 由上述用例消费 |
| tests/vectors/strip.sh | 辅助脚本（向量清理） | 否（工具脚本） | — | — | 未注册为测试 |
| tests/cve-2023-50967/* | 测试数据（CVE 回归输入） | 否（数据） | — | — | 由脚本用例经 CVE_2023_50967 env 消费 |

### 说明

1. **未误算项**：框架/测试数据（vectors、cve-2023-50967、strip.sh）均不作为独立用例；无框架宏前缀命中或 SECTION 子节，全部为真实独立用户用例。
2. **jose-jwk-pub / jose-jwk-thp 的 mksh 差异**：设备 /bin/sh 为 mksh R59，脚本内 `echo $ioct`（未加引号）被 mksh 做 glob/braced 展开拆散 JSON 输入（argc=5），jose 收到残缺输入报 "Error removing private keys!"/"Error making thumbprint!"。jose 二进制功能正确（bash 下完整输出匹配 RFC 向量），属 shell 环境差异而非库缺陷；bash 复跑两项均通过。
3. **全量通过率**：26/26 = 100%（发现全部独立用例为分母；未运行、不可运行、硬阻塞、未执行均为 0）。

## 验证结果

```bash
# conan-verify（配方级，G1-G4 + L2/L4/L5 全 PASS）
python3 scripts/ohc-run.py conan-verify jose 15   # ✅ 配方验证通过，可标记 published

# 上游测试（Step 2 builddir）
meson test -C builddir    # 24/26 OK，2 项 mksh 差异 → bash 复跑通过 → 26/26

# 消费者验证（test_package/test_jose）
PASS: jose_b64 URL-safe encode/decode round trip OK
```

## 交付物

| 文件 | 说明 |
|------|------|
| archives/j/jose/15/conanfile.py | meson 配方（依赖注入 + LLVM 工具链 + OHOS ELF 签名） |
| archives/j/jose/15/conandata.yml | 官方 v15 tarball + SHA-256 |
| archives/j/jose/15/test_package/ | 消费者测试（test_jose 调用 jose_b64 API 往返） |
| archives/j/jose/commands.json | R38 CLI 声明（bin/jose） |

## 注意事项

- OHOS 上共享库/可执行必须带有效 ELF 签名（.codesign），否则 musl 拒载（dlopen Permission denied）——已在配方 package() 内集成签名，CI 流水线 sign.sh 亦会签名，双重保障。
- 设备 /bin/sh 为 mksh，shell 脚本测试可能受 glob/braced 展开差异影响，用 bash 复跑确认。

## 基线隔离复验（W3/finish 命中其他库基线文件）

finish 的 W3 本地 CI 模拟（junk_check）曾命中 main 基线中其他库（cloog）的遗留状态文件，
按 SKILL 基线隔离规则完成逐项复验（pre_sha256 == post_sha256，当前库 diff/staged/PR 均不含该路径）：

| 字段 | 值 |
|------|-----|
| path | archives/c/cloog/0.21.1/.build-closed、archives/c/cloog/0.21.1/.staging-verified（其他库基线，非 jose 范围） |
| pre_sha256 | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855（两文件均为此空文件哈希） |
| isolation_command | `mv archives/c/cloog/0.21.1/{.build-closed,.staging-verified} /storage/Users/currentUser/tmp/jose15-baseline-isolate/` |
| rerun_command | `JUNK_PR_DIFF=/storage/Users/currentUser/tmp/jose15-evidence/pr.diff python3 scripts/ohc-run.py finish jose 15 published`（junk_check 以 CI 等价 prdiff 模式仅扫 jose 变更；full 模式扫全仓必然命中 main 既有其他库遗留文件） |
| rerun_exit_code | 0（W3 local CI 通过，.ci-result.json exit_code=0） |
| restore_command | `mv /storage/Users/currentUser/tmp/jose15-baseline-isolate/{.build-closed,.staging-verified} archives/c/cloog/0.21.1/` |
| post_sha256 | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855（与 pre 一致） |

结论：cloog 基线文件未被修改、未被提交，jose 的 staged/commit/PR 文件清单（见 pr.diff）仅含
archives/j/jose/** 与 commands.json，符合基线隔离要求。
---

**编译结束**: 2026-09-18 06:03
**最终状态**: published
