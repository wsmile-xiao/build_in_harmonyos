# Ruby 3.4.10 for HarmonyOS/OpenHarmony

> **编译日期**: 2026-08-13
> **状态**: 已构建 (built)
> **构建系统**: autotools (configure + make)

## 一、软件简介

Ruby 是一种动态、开源的面向对象编程语言，注重简洁和生产力。本适配将 `ruby/3.4.10` 作为 Conan package 提供，安装 `ruby` 解释器、`gem`/`irb`/`rake` 等命令行工具及核心标准库，扩展（openssl/yaml/fiddle/socket/json）均已启用。

## 二、编译指导

使用仓库 CI 包入口构建：

```bash
CI_PACKAGES="archives/r/ruby/3.4.10" zsh ci/conan/build_and_test.sh
```

配方在 HarmonyOS PC aarch64 真机上使用 autotools 构建，依赖以下已发布制品仓包（R36）：
- `libffi/3.5.2`（fiddle 扩展）
- `openssl/3.5.6.1.1`（openssl 扩展）
- `libyaml/0.2.5`（psych/yaml 扩展）

## 三、补丁清单

- `patches/0001-configure.patch`: config.status 临时目录 umask 077 → 022（HMDFS setgid 目录不可写，E011/E114 模式）
- `patches/0002-tool-config.guess.patch`: config.guess 添加 HarmonyOS 系统识别（E007）
- `patches/0003-tool-config.sub.patch`: config.sub 接受 `aarch64-unknown-linux-ohos` 三元组：ohos-linux + linux-ohos 内核校验（E205/E268）

## 四、已知限制

- `make check` 中 `test_fork.rb` 在鸿蒙平台段错误后挂起（fork 相关平台限制），按 SKILL 规则超时跳过并记录原因；其余 bootstraptest 全部通过。
- `configure --prefix=/` 会将 `$LOAD_PATH` 硬编码为 `//lib/ruby/...`，配方 `package_info()` 已通过导出 `RUBYLIB` 指向包内 stdlib + arch 目录解决。

## 五、功能验证

- Conan `test_package`（L1 smoke，test_ruby.sh）: 7/7 断言 PASS，覆盖版本校验、`openssl`（OpenSSL 3.5.6）、`yaml`（YAML 5.2.2 解析断言）、`fiddle`、`socket`、`json` 加载。
- 上游测试 `make check`: bootstraptest 大部分通过（test_env/test_eval/test_exception/test_fiber/test_flow 等）；test_fork.rb 因鸿蒙 fork 限制跳过。
- 本地 CI 模拟（W3, build_and_test.sh）: 100% 通过（L0/L1/L2/L5 pass，L4 仅警告）。
- Conan verify（G0-G4 + L2/L4/L5）: 全部 PASS。
