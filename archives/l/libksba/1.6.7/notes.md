# libksba 1.6.7 HarmonyOS 适配记录

## 构建信息

- 上游源码：`https://gnupg.org/ftp/gcrypt/libksba/libksba-1.6.7.tar.bz2`
- 构建系统：Autotools
- Conan 依赖：`libgpg-error/1.55`
- 目标平台：HarmonyOS PC arm64
- 当前状态：built（本地 Conan 验证通过，尚未由 CI 发布）

## 平台适配

1. `config.guess` 和 `config.sub` 增加 HarmonyOS 三元组识别。
2. 当前仓库 CI 的 build/host profile 均为 OHOS arm64。Autoconf 参数使用 `--build=aarch64-unknown-linux-gnu` 与 `--host=aarch64-unknown-linux-ohos` 的差异进入交叉编译模式；配方通过 `validate()` 明确限制为 OHOS armv8。
3. 从当前 Conan profile 的 `tools.build:compiler_executables` 获取可在该 OHOS arm64 worker 上运行的 `CC_FOR_BUILD`，用于构建并执行 `asn1-gentables` 等构建期工具。
4. 使用 Conan 依赖包中的 `gpgrt-config`、头文件和库，不依赖共享 `/usr/local` 前缀。
5. 将构建临时目录放在 Conan `build_folder`，并将生成的 `configure` 中 `umask 077` 改为 `umask 022`，规避 HMDFS 权限限制。

## 测试

- 上游 `make -j1 check`：执行 7 个上游测试程序，全部通过。
- 消费者测试：调用 `ksba_check_version`、`ksba_cert_new` 和 `ksba_cert_release`，通过。
- 未修改或削弱上游测试用例。

## 验证记录

- `ohc-run.py conan-verify libksba 1.6.7`：G0–G4、L2、L4、L5 全部通过。
- `clean-verify` 的独立工作目录检查出现 `getcwd` 失效，属于校验临时目录/HMDFS 环境问题；Conan 干净构建不受影响。
---

**编译结束**: 2026-09-08 18:27
**最终状态**: built
