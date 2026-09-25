# infgen 3.5 适配笔记

## 上游信息

| 项 | 值 |
|---|---|
| 上游仓库 | https://github.com/madler/infgen |
| 版本 | 3.5（无 git tag，对应 commit `c6fe0c3` "Update version to 3.5."，2024-12-26） |
| 许可证 | zlib（SPDX: Zlib） |
| 语言 | 纯 C（单文件 `infgen.c`，另有辅助工具 `infstats.c`） |
| 构建系统 | 无（README：`Simply compile infgen.c`，直接 clang 编译） |
| 运行时依赖 | zlib（`crc32()`/`get_crc_table()`，仅 PNG 输入 CRC 校验用） |

## 编译环境

- 本机（Windows）环境：Python 3.12.10、DevEco OHOS LLVM clang 可用；**无 conan、无 make、无 gzip**。
- 因此本机无法执行完整 `conan create` 交叉编译与上游冒烟测试，只完成配方编写 + 本机静态验证（SHA256 复核、Python 语法、YAML 结构、diff --check）。
- 目标真机/CI 环境：OpenHarmony aarch64（musl libc），clang + GNU make + conan 2.29.1。

## 构建方式

infgen 上游不提供 Makefile/configure。build() 直接用从 Conan conf 取得的 clang 编译：

```bash
clang -O2 -Wall -I<zlib_include> -L<zlib_lib> -o infgen infgen.c -lz
```

- zlib 静态链接（`zlib/1.3.1`，非 PIC 静态归档），`crc32` 等符号内嵌进可执行文件，运行期不依赖 `libz.so`。
- R32：`validate()` 用 `settings.os in ("Linux", "OHOS")`。
- R33：编译器从 `tools.build:compiler_executables` 取得，不用裸 `${CC}`/`${CFLAGS}`。
- E077：OHOS 平台可执行文件需 `binary-sign-tool -selfSign 1` 签名，`package()`/`build()` 内联 `_sign_elf`，Linux 构建宿主上签名工具不存在时为 no-op，最终签名由 CI release 的 sign.sh 兜底。

## 上游测试

- 上游无正式测试套件（无 `make check`）。README 的冒烟测试是 `gzip < infgen.c | ./infgen`，依赖设备端 gzip。
- 本配方 test_package 改为**确定性输入**：直接向 stdin 喂 20 字节空 gzip 流（mtime=0），断言输出首行 `! infgen 3.5 output`，不依赖设备端 gzip/压缩器。

## 遇到的问题与解决

| # | 问题 | 根因 | 解决 |
|---|------|------|------|
| 1 | `git worktree add` 在 Windows 上失败：`unable to create file archives/g/gama/2.29/patches/0002-dataparser-ungated.patch??: Invalid argument` | origin/main 里存在文件名被污染（尾部含 `\r\r`）的 gama 补丁文件，Windows 文件系统不允许 `\r` 控制字符 | 用 `git worktree add --no-checkout` + `git sparse-checkout set archives/i/infgen` 只检出目标目录，规避该非法文件 |
| 2 | 上游无 git tag，master 已是 3.6 | 上游只维护 master 分支，不发布 tag | 用 commit `c6fe0c3` 的 GitHub archive（带 `.tar.gz` 后缀，避免 Conan 误判为 zip），SHA256 已复核 |
| 3 | 本机无 conan/make/gzip，无法 conan create | Windows 开发机未装 Conan 与 OHOS 交叉工具链 | 如实记录为前置适配；完整 `conan create` 在真机 shadow CI 执行 |
| 4 | shadow CI 首次失败：`zlib/1.3.1: Error in build() ... cmake: inaccessible or not found` | 隔离 job 的 `conan-home/remotes.json` 只有 conancenter（无 ohpcd），依赖解析走了 conancenter 的 zlib CMake 配方，真机无 cmake | 给 job 的 conan-home 添加 `ohpcd` remote（`conan remote add ohpcd https://conan.cnb.cool/OpenHarmonyPCDeveloper/Conan/-/packages/`）并禁用 conancenter；之后 zlib 命中 ohpcd 预编译包（revision `2ee7c0ee`，Makefile 配方），不再源码构建 |
| 5 | shadow CI 二次失败：test() 里 `bash` 不可用（`/system/bin/sh: bash: inaccessible or not found`） | 真机 run 环境 PATH 无 bash（profile 的 `CONFIG_SHELL` 只在 build 阶段生效） | test() 改为 OHOS 下用绝对路径 `/data/service/hnp/bin/bash`（非 OHOS 用 `bash`，参考 rgbds 先例），并显式声明 `generators = "VirtualRunEnv"` |

## 依赖版本

- `zlib/1.3.1`（非 PIC 静态归档，用于可执行文件静态链接；仓库已适配并发布，W0 无需拆分适配）

## 验证结果

### 本机前置

- 源码归档 SHA256 复核通过：`3AEEFCFA93B33529D2DA9FA9FCF37116BF485F87C0723356AFF7AAB616813CB4`
- `conanfile.py`/`test_package/conanfile.py` Python 语法检查通过
- `conandata.yml`/`manifest.yaml`/`test_package/MANIFEST.yml` YAML 结构检查通过
- `git diff --check` 通过

### 真机 shadow CI（2026-09-20，exit code 0 ✅）

隔离 job：`infgen-3.5-shadow-20260920`（真机 `10.62.178.77`，`~ohos-users/codex/`）。

| 门禁 | 结果 | 说明 |
|---|---|---|
| L0 | pass | zlib/1.3.1 已发布、infgen/3.5 首次发布、commands.json 有效、目录结构合规 |
| L1 | pass | L1a test_package 已执行、L1b 测试证据、L1e 破坏性验证确认真测试（移走 bin/ 后 test 失败） |
| L2 | skip | infgen 仅支持 `-h`（不支持 `--version`/`--help`），non-blocking |
| L4 | pass | 无 patches |
| L5 | pass | bin/ 有 infgen 产物 |

- `conan create`：clang 编译 `infgen.c` + 静态链接 zlib 成功；`binary-sign-tool -selfSign 1` 签名成功；打包 `infgen` + `LICENSE` + `README.md`。
- test_package：`infgen -h` 输出 `infgen 3.5`/`Usage`，空 gzip 流反汇编输出 `! infgen 3.5 output`，3/3 断言通过。
- 上游测试：无正式测试套件（上游 README 冒烟依赖 gzip，本配方用确定性输入替代）。
- 构建产物：aarch64 OHOS 可执行文件，静态内嵌 zlib（crc32），无运行期 libz.so 依赖。

## 下一步

shadow CI 已通过，后续为提交流程（需 issue 编号 + PR 描述）：

1. 提交本目录改动到 `feat/infgen-3.5-codex` 分支并 push；
2. 创建 PR（PR 描述含上游 3.5 与 Conan 3.5 一致、test_package 3 断言、L0-L5 结果、issue 待补说明）；
3. CI 走正式 release 流水线发布 `infgen/3.5` 到制品仓。
