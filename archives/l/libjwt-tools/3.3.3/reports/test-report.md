# libjwt-tools 3.3.3 测试报告

> **项目**: libjwt-tools（libJWT 官方命令行工具集，上游仓库 benmcollins/libjwt 的 `tools/` 目录）
> **版本**: 3.3.3（同源父包 `libjwt/3.3.3`）
> **测试日期**: 2026-09-18
> **测试环境**: HarmonyOS PC（OHOS 6.0，aarch64，HongMeng Kernel，musl libc 1.2.x）
> **测试类型**: 上游测试套件（bats `tests/jwt-cli.bats`，9 例）+ test_package（3 个测试可执行文件，37 条断言）
> **编译配置**: clang 15（OHOS SDK / `aarch64-linux-ohos`），CMake + Conan 2，Release
> **包引用**: `libjwt-tools/3.3.3#034afc7511d9994b0a042ca28a46e161:d5638da3e804c734402caf87ffefdafa9e205fd9`

---

## 一、测试摘要

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 上游测试用例总数（discovered） | 9 | 100% |
| 上游实际执行（executed） | 9 | 100% |
| 上游通过（PASS） | 9 | 100% |
| 上游失败（FAIL） | 0 | 0% |
| 上游跳过（SKIP） | 0 | 0% |
| test_package 断言总数 | 37 | 100% |
| test_package 通过 | 37 | 100% |
| test_package 失败 | 0 | 0% |
| **合计断言/用例** | **46** | **100% 通过** |

**核心功能通过率**: ✅ **46/46（100%）**，无失败、无跳过。

test_package 的 37 条断言构成为：`test_consumer` 12 + `test_ohos`（本次适配新增的鸿蒙消费者用例）21 + 工具端到端 4。

---

## 二、测试结论

### 2.1 总体评价

✅ **通过**。libJWT 的 4 个命令行工具（`jwt-verify`、`jwt-generate`、`jwk2key`、`key2jwk`）在 HarmonyOS PC（aarch64）上完成构建、安装与运行验证：

- 上游 9 例 bats 用例在等价语义下逐条实测通过（镜像无 `bats`，见 3.2 偏差说明）；
- 3 个 test_package 测试程序全部编译、链接并运行成功；
- 4 个工具均为 ELF64 / AArch64 / 带 `PT_INTERP`，`DT_NEEDED` 仅 `libjansson.so` + `libc.so`；
- 工具经上游 `jwt_static` 静态链接 libjwt 本体，因此**不依赖** `libjwt.so`（下游消费者无需额外处理本体共享库）。

### 2.2 主要问题

| 问题类别 | 影响范围 | 严重程度 |
|----------|----------|----------|
| 镜像无 `bats`，上游 `add_test(NAME jwt_cli)` 不注册 | 上游测试执行方式（改为逐条等价复现） | 🟢 上游优雅降级，非缺陷 |
| 镜像无 `jq` | 上游用例 7 的 JSON 等价比较 | 🟢 已用 `python3` 复现同一语义 |
| 4 个工具均不实现 `--version` / `--help` | W3 的 L2 与 `verify-build` 的 G2 | 🟢 上游 CLI 本身无版本选项（非适配缺陷） |

### 2.3 可用功能清单

```
✅ jwt-generate  签发 JWT（alg none / HS256 / 带 claims）
✅ jwt-verify    校验 JWT（含篡改负样本拒绝，rc=1）
✅ jwk2key       JWK → PEM 私钥（RSA / OCT）
✅ key2jwk       PEM 密钥 → JWKS 文档
✅ 4 个 man page 安装至 share/man/man1/
✅ 许可证文件 licenses/LICENSE（MPL-2.0）
```

### 2.4 已知限制

1. 上游 `install()` 规则同时把 4 个工具装进本体包 `libjwt/3.3.3` 的 `bin/`（上游 `jwt_add_tool()` 内 `install(TARGETS ... RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR})` 的必然行为）。本包是同一源码的 `tools` 子包，交付物与本体包 `bin/` 存在同名文件——这是上游打包结构的客观事实，非本包引入的重复构建。
2. 工具不实现 `--version`，因此 `verify-build` G2 与 W3 L2 项只能给出 warn/skip（不影响质量判定）。

---

## 三、上游测试详情

### 3.1 测试入口（对 pristine 上游源码树实测）

| 项 | 实测值 | 证据 |
|---|---|---|
| 测试框架 | bats（BATS shell 测试） | `tests/jwt-cli.bats` |
| 用例数 | 9 个 `@test` | `grep -c '^@test' tests/jwt-cli.bats` → `9` |
| 注册方式 | `add_test(NAME jwt_cli COMMAND /bin/bash -c ...)` | `CMakeLists.txt` 第 340 行（打补丁后）/ 第 342 行（上游 pristine） |
| 注册条件 | 仅当 `find_program(BATS_CMD bats)` 命中 | `CMakeLists.txt:295`（patched）/ `:297`（pristine），`if (BATS_CMD)` 于 `:339`/`:341` |
| 与 `WITH_TESTS` 的关系 | 工具目标在 `if (WITH_TESTS)`（`:290` patched / `:292` pristine）块**之外**，无条件构建 | `function(jwt_add_tool)` 位于 `:177`（patched）/ `:179`（pristine） |

**本机镜像无 `bats`**：`find_program(BATS_CMD bats)` 探测失败 ⇒ 上游不注册 `jwt_cli` 测试。此为**上游设计内的优雅降级**，不是配方裁剪。本配方按 `tests/jwt-cli.bats` 的 9 个 `@test` **逐条等价复现**，不删减任何用例。

### 3.2 逐例结果（总数 9 / 通过 9 / 失败 0 / 跳过 0）

日志：`reports/conan-create-final.log`（标记 `HMBS_UPSTREAM_TEST_RESULT`，本报告撰写时由 `conan create` EXIT=0 生成）

| # | 用例名 | 结果 |
|:-:|--------|:----:|
| 1 | Generate a JWT with alg none | ✅ PASS |
| 2 | Verify a JWT with alg none | ✅ PASS |
| 3 | Generate a JWT with alg HS256 | ✅ PASS |
| 4 | Verify a JWT with alg HS256 | ✅ PASS |
| 5 | Generate a JWT with alg HS256 and claims | ✅ PASS |
| 6 | Verify a JWT with alg HS256 with claims | ✅ PASS |
| 7 | Generate JWKS from PEM Files | ✅ PASS |
| 8 | Convert JWK to PEM - RSA | ✅ PASS |
| 9 | Convert JWK to PEM - OCT | ✅ PASS |

### 3.3 执行偏差（2 条，均已在 MANIFEST/manifest 登记，未裁剪用例）

1. **用例 3-6 的密钥路径**：上游 bats 写 `../tests/keys/oct_key_256.json`（假定 build 目录位于源码树内）。Conan 构建目录在缓存中，故本配方改用源码树绝对路径 `<source>/tests/keys/oct_key_256.json` 等价替代。
2. **用例 7 的 JSON 等价比较**：上游依赖 `jq`（`normalize = walk(if type == "array" then sort else . end)`）。OHOS 镜像内无 `jq`，改用 `python3` 复现同一 `normalize`/`equiv` 语义。

> 两条偏差都只替换**工具链等价实现**，不改断言、不删用例、不放松判定。

---

## 四、test_package 详情（37/37）

| 测试程序 | 语言 | 断言数 | 结果 | 日志 |
|---|---|:-:|:-:|---|
| `test_consumer` | C | 12 | ✅ 12/12 | `reports/testlogs/test_consumer.log` |
| `test_ohos`（鸿蒙消费者用例） | C | 21 | ✅ 21/21 | `reports/testlogs/test_ohos.log` |
| 工具端到端 | Python | 4 | ✅ 4/4 | `reports/conan-create-final.log`（`HMBS_TEST_PACKAGE_RESULT.tool_e2e`） |

### 4.1 `test_consumer`（12 条断言）

经 `requires("libjwt/3.3.3")` 调用本体公开 API，形成完整链路：

```
JWKS 文档装载 → jwks_item_get 取密钥 → jwt_builder_new/setkey/generate 签发
→ jwt_checker_new/setkey/verify 校验通过 → 篡改 token 后被拒绝（负样本）
```

> 该文件必须显式 `requires("libjwt/3.3.3")`：本包 `package_type="application"` 不 re-export 本体头/库，本体在 `test_package` 图中处于传递位置，会被按 `headers=false/libs=false` 过滤，CMakeDeps 生成的 `libjwt_INCLUDE_DIRS_RELEASE` / `libjwt_LIBS_RELEASE` 为空。

### 4.2 `test_ohos` —— 本次适配新增的鸿蒙消费者用例（21 条断言）

对 4 个工具各做 5 项断言（4 × 5 = 20），外加 1 项解释器断言：

| # | 断言 | 验证内容 |
|:-:|------|----------|
| 1 | `access("<bindir>/<tool>", X_OK) == 0` | 经 Conan `bindirs` 通道可达且可执行 |
| 2 | `e_machine == 183`（EM_AARCH64） | ELF 架构正确（ELF64 / AArch64） |
| 3 | 含 `PT_INTERP` | 是可执行 ELF（非纯共享库） |
| 4 | `DT_NEEDED` 含 `libjansson.so` | jansson 动态依赖真实建立 |
| 5 | `DT_NEEDED` **不含** `libjwt.so` | 工具经上游 `PRIVATE jwt_static` 静态链接本体，交付物不依赖本体共享库 |
| 21 | `/bin/sh` 存在且可执行 | 上游 `add_test` 硬编码 `/bin/bash` 的等价解释器可用性 |

**为何 C 层不 `fork/exec`**：OHOS 对跨二进制 `spawn` 有额外安全管控，测试内直接执行子进程不稳定。因此 C 层只做静态/文件系统层断言，**工具的动态功能验证放在 Python 层端到端**（第 4.3 节），两层合计覆盖「产物合法 + 功能可用」。

### 4.3 工具端到端（4/4）

```
key2jwk:      随机密钥 → 合法 JWK 文档                 rc=0  PASS
jwt-generate: 产出三段式 token（token_len=179）        rc=0  PASS
jwt-verify:   校验自签 token 通过                       rc=0  PASS
jwt-verify:   篡改 token 被拒绝（负样本）               rc=1  PASS
```

---

## 五、质量门禁结果

| 门禁 | 命令 / 日志 | 结果 |
|---|---|---|
| W3 本地 CI | `reports/w3-local-ci.log` | `G0/L0/L1/L4/L5 = pass`；`L2 = skip`（4 个工具不实现 `--version`/`--help`）；`Pass rate 100.0% (1/1)` |
| `verify-build` G1-G4 | 官方脚本，`.verify-passed` 标记 | `PASS-WARN`：G1 ✅4 ❌0；G2 ⚠️4 ❌0；G3 ⚠️8 ❌0；G4 ⚠️1 ❌0（⚠️ 全部来自「工具不实现 `--version`」与「patchelf 未设置 RPATH」，无失败项） |
| 打包 | 官方 `PackageBuilder` 10 步 | ✅ `packaging/libjwt-tools-3.3.3-ohos-aarch64.tar.gz`（主）+ `-debug.tar.gz`（调试符号）+ `.packaged` |
| conan-verify | `reports/conan-verify-report.md` | 见该报告；G0/G0e/G1/G2/G3 PASS |

---

## 六、测试环境

```
kernel/os : HarmonyOS PC（OHOS 6.0，aarch64，musl libc）
toolchain : clang 15（OHOS SDK native/llvm），target aarch64-linux-ohos
builder   : CMake + Conan 2，profile ci/conan/profiles/ohos-aarch64（host = build）
依赖       : libjwt/3.3.3（本体，静态链入工具）、openssl/3.5.6（direct require）、jansson（经 libjwt 动态依赖）
包引用     : libjwt-tools/3.3.3#034afc7511d9994b0a042ca28a46e161:d5638da3e804c734402caf87ffefdafa9e205fd9
执行方式   : conan create . -pr:h=<abs profile> -pr:b=<abs profile> --build="libjwt-tools/*"
```

---

## 七、附：产物清单

| 类型 | 路径 |
|---|---|
| 可执行文件 | `bin/jwt-verify`、`bin/jwt-generate`、`bin/jwk2key`、`bin/key2jwk` |
| 手册页 | `share/man/man1/{jwt-verify,jwt-generate,jwk2key,key2jwk}.1` |
| 许可证 | `licenses/LICENSE`（MPL-2.0） |

---

*报告生成时间: 2026-09-18*
