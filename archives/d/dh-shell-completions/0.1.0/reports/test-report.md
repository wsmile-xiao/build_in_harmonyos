# dh-shell-completions 0.1.0 验证报告

> **项目**: dh-shell-completions 0.1.0
> **测试日期**: 2026-09-17
> **测试环境**: HarmonyOS PC / OpenHarmony aarch64（clang 15.0.4，Conan 2.29.1，perl 5.42.0 [HNP]）
> **测试类型**: 上游官方用例实跑（tests/run.sh 三组）+ 包产物消费者断言

---

## 一、测试摘要

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 上游测试用例总数 | 3（gen / composite / separate） | 100% |
| 上游用例实跑通过 | **3** | **100%** |
| 上游用例失败 | 0 | 0% |
| 适配侧包产物断言 | 10 | 100% |
| 通过 (PASS) | 10 | 100% |
| 失败 (FAIL) | 0 | 0% |

**上游用例通过率**: ✅ **3/3（100%）** ｜ **包产物断言通过率**: ✅ **10/10（100%）**

---

## 二、测试结论

### 2.1 总体评价

✅ 上游官方测试在 OHOS 上**真实执行并通过 3/3**；包产物完整且内容一致（10/10 断言通过）。

### 2.2 执行方式

上游测试由顶层 `Makefile` 的 `test` target 驱动（`tests/run.sh <case>`）。
配方 `build()` 内搭建 perl 测试工具链后逐项执行，任一用例失败即构建失败：

| 依赖 | OHOS 上的来源 |
|------|---------------|
| perl 5.42.0 | HNP：`/data/service/hnp/bin/perl`（位于 PATH） |
| debhelper 13.3.4（`dh` + 全部 `dh_*` + `Dh_Lib`/`Sequence`） | 官方源码 tarball（deb.debian.org，sha256 固定） |
| dh-autoreconf 20（compat 13 默认启用的 `autoreconf` 序列 addon） | 官方 `.deb`（deb.debian.org，sha256 固定） |
| `dpkg-architecture` | 不需要：以 `DEB_*` 环境变量替代（OHOS 无 dpkg） |

shebang 适配：OHOS 无 `/usr/bin/perl`，上游 `dh_shell_completions` 经
`patches/0001-dh_shell_completions-env-perl-shebang.patch` 适配为 `#!/usr/bin/env perl`；
build 目录内工具链命令副本做同样适配。上游测试脚本本身未修改。

### 2.3 已知限制

| 限制 | 影响范围 | 严重程度 |
|------|----------|----------|
| `dh_shell_completions --version` 需 debhelper 的 `Dh_Lib`（运行时依赖，不在包内） | CI L2 冒烟探测（警告级、非阻断） | 🟢 |
| 手册页依赖 `pod2man` | 不生成/不安装手册页 | 🟢 |

---

## 三、测试详情

### 3.1 上游用例（tests/run.sh，实跑通过）

| # | 用例 | 上游断言 | 结果 |
|---|------|----------|------|
| 1 | `tests/run.sh gen` | generation 模式：按 `debian/shell-completions`（`mode=gen`，`command=echo _SHELL_ _SHELL_ _SHELL_ _SHELL_`，`shells=bash,fish,zsh`）生成补全并安装到<br>`usr/share/bash-completion/completions/gen`、`usr/share/fish/vendor_completions.d/gen.fish`、`usr/share/zsh/vendor-completions/_gen`，逐一校验存在性与内容 | ✅ PASS |
| 2 | `tests/run.sh composite` | composite 模式：`debian/shell-completions` 文件列表（`bash foo.bash` / `fish foo.fish` / `zsh _foo`）按行安装为 `composite` / `composite.fish` / `_composite`，校验路径与内容 | ✅ PASS |
| 3 | `tests/run.sh separate` | separate 模式：`debian/bash-completions`（文件列表 `foo.bash`）→ `separate`；`debian/fish-completions`（完整脚本）→ `separate.fish`；`debian/zsh-completions`（文件列表 `_foo separate`）→ `_separate`，校验路径与内容 | ✅ PASS |

每组用例结束后由 `run.sh` 调用上游 `dh clean` 清理，三组用例全程走通上游脚本的
`run_comp` → 断言 → `clean` 全流程。

### 3.2 test_package 包产物断言（test.sh，10 条）

| # | 测试项 | 功能 | 结果 |
|---|--------|------|------|
| 1 | bin 目录有效 | 包内 `bin/` 存在 | ✅ PASS |
| 2 | 包根目录有效 | 包前缀存在 | ✅ PASS |
| 3 | `bin/dh_shell_completions` 存在 | Debian 布局 `/usr/bin` 镜像 | ✅ PASS |
| 4 | `share/perl5/.../shell_completions.pm` 存在 | Debian 布局 `/usr/share/perl5` 镜像 | ✅ PASS |
| 5 | perl shebang（`#!/usr/bin/env perl`） | 解释器可在 OHOS 上解析 | ✅ PASS |
| 6 | `Debian::Debhelper::Dh_Lib` 标记 | 脚本依赖 debhelper | ✅ PASS |
| 7 | bash 补全路径标记 | `bash-completion` | ✅ PASS |
| 8 | fish 补全路径标记 | `vendor_completions.d` | ✅ PASS |
| 9 | zsh 补全路径标记 | `vendor-completions` | ✅ PASS |
| 10 | generation 模式 + 序列注册标记 | `process_gen` / `insert_after` | ✅ PASS |

---

## 四、证据

| 证据 | 位置 |
|------|------|
| W2 `conan create` 日志（含 3 组上游用例 `=> PASS` 与 test_package 断言） | `reports/conan-create.log` |
| W3 本地 CI 日志（L0/L1/L2/L4/L5 + L1e 破坏性反证） | `reports/w3-local-ci.log` |
| W4 配方验证报告 | `reports/conan-verify-report.md` |
| CI 元数据 | `ci-metadata.json` |

---

## 五、测试环境

```
dh-shell-completions 0.1.0（Debian native 源，Apache-2.0）
package_type = application（零编译；build() 执行上游测试，package() 镜像 Debian 布局）
perl 5.42.0 (/data/service/hnp/bin/perl) + debhelper 13.3.4 + dh-autoreconf 20
clang version 15.0.4 (aarch64-unknown-linux-ohos)
Conan 2.29.1
```

---

*报告生成时间: 2026-09-17*
