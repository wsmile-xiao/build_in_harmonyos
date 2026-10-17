# kicad-footprints 10.0.4 测试报告

> **项目**: kicad-footprints 10.0.4
> **测试日期**: 2026-09-20
> **测试环境**: Windows x86_64 Conan 主机；HarmonyOS 6.0 PC 真机（aarch64，10.53.45.8:8022）
> **测试类型**: Conan 消费者测试、资源清单测试、仓库门禁测试

## 一、测试摘要

| 指标 | 数值 | 说明 |
|:----:|:----:|:------|
| Conan 消费者断言 | 478 | 478 PASS（包含资源环境变量契约） |
| 资源库目录 | 155 | 与官方 10.0.4 归档一致 |
| `.kicad_mod` 文件 | 15435 | 安装后全量计数一致 |
| 上游 CTest | 0 | 上游没有本地测试，CTest 正常返回 0 |
| HarmonyOS 特有运行断言 | 478 | 真机 `conan create` 运行通过，`ohos_build=true` |
| `__OHOS__` 宏路径探针 | 478 | 真机 Clang 编译并以 `--require-ohos` 运行通过 |
| `conan-verify` G1 | 通过 | 配方结构/元数据门禁通过 |
| HarmonyOS 原生 Conan CI | 1/1 | L0/L1/L4 通过，L2 因资源包无可执行文件跳过 |

## 二、测试结论

✅ **本地 Conan、HarmonyOS 真机 Conan 以及仓库原生 zsh CI 均已通过；包满足当前验收要求。**

### 2.1 已通过

```text
✅ 官方源码 URL 和 SHA-256 校验通过
✅ CMake configure/build/install 通过
✅ Conan test_package 编译并运行通过（478 assertions）
✅ fp-lib-table 155 项与 .pretty 目录一致
✅ 安装树包含 15435 个 .kicad_mod 文件
✅ 3 个代表性 footprint 可解析
✅ 截断 footprint 负向断言通过
✅ CTest 无本地测试时返回 0
✅ `ohc-run.py conan-verify` 的 G1 配方门禁通过
✅ `KICAD10_FOOTPRINT_DIR` 错配时探针拒绝，正确导出时通过
✅ 本地 `__OHOS__` 编译宏路径和 `--require-ohos` 断言通过
✅ HarmonyOS 6.0 真机 `conan create` 通过，探针报告 `assertions=478`、`ohos_build=true`
✅ HarmonyOS 真机 `ci/conan/build_and_test.sh` 通过：L0 pass、L1 pass、L4 pass、1/1 成功
```

### 2.2 未完成或受环境阻塞

```text
⚠️ tests/run_all.py：test_v1220.py 硬编码使用 HarmonyOS worker 的 git 路径，Windows 主机缺失；其余测试已执行
⚠️ `ohc-run.py finish` 的 Windows 本地包装流程因 OHOS profile 工具链路径不存在而停止，未生成 `.ci-result.json`；同一仓库原生 W3 脚本已在真机通过
⚠️ 全局 preflight PF9 会把 ARCHIVE-SPEC 要求的软件级 `README.md`/`manifest.yaml` 误判为缺少版本目录层；包级结构门禁已通过，未删除这两个必需文件
```

## 三、测试详情

### 3.1 通过的测试

| 测试项 | 命令/证据 | 结果 |
|--------|-----------|------|
| 生产配方语法 | `python -m py_compile conanfile.py test_package/conanfile.py` | ✅ PASS |
| YAML 结构 | `yaml.safe_load(conandata.yml, manifest.yaml, MANIFEST.yml)` | ✅ PASS |
| TDD 红测 | 探针针对空资源根，报告 `fp-lib-table is missing`，退出码 1 | ✅ 预期 FAIL |
| 资源探针 | `kicad_footprints_probe` | ✅ 478 assertions |
| Conan 集成 | `conan create ... --profile:host default --profile:build default --build=missing` | ✅ PASS |
| CTest | `ctest --test-dir <upstream build>` | ✅ 0 tests, exit 0 |
| W3 配方门禁 | `python scripts/ohc-run.py conan-verify kicad-footprints 10.0.4` | ✅ G1 PASS；G2 受 OHOS 工具链环境阻塞 |
| HarmonyOS 真机 Conan | `conan create ... -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing` | ✅ PASS；478 assertions，`ohos_build=true` |
| HarmonyOS 原生 CI | `zsh ci/conan/build_and_test.sh` | ✅ PASS；1/1，L0/L1/L4 PASS |

### 3.2 失败的测试

| 测试项 | 原因 | 说明 |
|--------|------|------|
| `tests/run_all.py` 的 `test_v1220.py` | Windows 主机缺少 `/data/service/hnp/git.org/git_2.45.2/bin/git` | 测试脚本将 HarmonyOS worker 路径硬编码为 `GITBIN`；不是本包测试失败，未修改仓库测试文件 |
| Windows W3 G2 包装流程 | Windows 主机没有 `/data/service/hnp/bin/clang` 和 zsh | 环境限制；真机原生 CI 已通过 |

### 3.3 环境限制下未执行的测试

| 测试项 | 执行条件 |
|--------|----------|
| Windows 完整 `tests/run_all.py` | `test_v1220.py` 需要仓库测试脚本不再硬编码 HarmonyOS worker 的 Git 路径 |

## 四、关键问题分析

### 问题1: Windows 与 HarmonyOS CI 工具链不同

Windows 主机无法执行 `ohos-aarch64` profile 指定的 `/data/service/hnp/bin/clang`，也没有 zsh，因此 `ohc-run.py finish` 的本地包装流程和 `tests/test_v1220.py` 的 worker 路径检查不能在 Windows 完成。已使用真机的 OHOS Clang、CMake 4.1.2、Conan 2.29.1 和 zsh 5.9 完成等价的 Conan、test_package 与原生 CI 验证。

### 问题2: 上游没有本地测试套件

上游 `.gitlab-ci.yml` 只 include 外部 `kicad-library-utils` GitLab CI 模板，源码归档没有 CTest 注册项。已直接运行 CTest 验证该事实；适配质量由真实消费者探针覆盖。

## 五、测试环境

```text
Conan: 2.29.1
CMake: 3.26.4
Ninja: 1.11.1
Compiler: Windows MinGW GCC 14.2.0；HarmonyOS Clang 15.0.4 (aarch64-unknown-linux-ohos)
Source: kicad-footprints 10.0.4 official GitLab archive
SHA-256: bd9ac36dd8bc5ae9089cf7593d2e8137dc5d3ce35d75e870aa3cd497f2070d0e
Package layout: share/kicad/footprints + share/kicad/template/fp-lib-table
Latest local Conan result: exit 0, test_package probe assertions=478
OHOS-specific device Conan result: exit 0, assertions=478, ohos_build=true
Latest HarmonyOS native CI result: exit 0, 1/1 package, L0/L1/L4 pass
Latest Windows finish result: W3 wrapper blocked by unavailable OHOS toolchain; .ci-result.json not generated locally
```
