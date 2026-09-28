# mbrola 3.3 HarmonyOS adaptation notes

## Status

- Branch: `feat/mbrola-3.3`
- Task: 智能任务平台 #8725
- Current state: 本机 W3（conan-verify）与本地 CI 门禁（build_and_test.sh）
  均已通过，W4 独立审计通过；等待平台 CI（/rebuild）与 AI 检视（/ai review）闭环。

## W0 Dependency Check

- Runtime/build dependencies: 无第三方依赖，仅 C 工具链、libc、libm。
- Conan dependencies: 无（`resolve-deps` 报告 "所有依赖已就绪"）。
- 语音库（mbrola-* 数据包）是运行时可选数据，不是构建依赖；
  消费者测试使用已发布的 `mbrola-gr2/0.0.20010521` 作为测试数据。

## Source and Build Analysis

- Source: https://codeload.github.com/numediart/MBROLA/tar.gz/refs/tags/3.3
  （GitHub 官方下载端点；与 `github.com/.../archive/refs/tags/3.3.tar.gz`
  经 302 同一实体，字节级 SHA256 一致）
- SHA256: `c01ded2c0a05667e6df2439c1c02b011a5df2bfdf49e24a524630686aea2b558`
- 说明：仓库内 204 个配方使用 codeload 官方端点；设备侧 `conan-verify`
  的 E017 镜像注入（ghfast.top）在当前网络不可达，codeload 直连正常，
  且平台 CI 侧会自行追加镜像回退。
- Build system: plain Makefile（`VERSION=3.3`）。
- Main binary: `Bin/mbrola`（`Standalone/synth.c` + Engine/Parser/Database/Misc）。
- 上游 Makefile 自带 `-DLITTLE_ENDIAN`、`-DROMDATABASE_STORE`、
  `-DROMDATABASE_INIT`、`-DSIGNAL`、include 路径等可移植性设置；
  `CC` 默认 `gcc -ansi -pedantic`。
- OHOS 适配点：仅把 `CC` 换成 Conan profile 提供的 OHOS clang
  （`make -j1 SHELL=sh CC=<c compiler>`），无源码补丁。
- 上游测试：发布包内无 tests/ 目录、无 ctest/pytest 注册；
  Makefile `check/checkold` 依赖私有 `UTILITY_TCTS` 语料（发布包中不存在），
  因此不可运行（`find . -name 'UTILITY_TCTS*'` 为空）。

## Recipe Notes

- `source()` 中 codeload URL 以 tag 名结尾（无扩展名），必须显式传
  `filename="mbrola-3.3.tar.gz"`，否则 Conan `get()` 会退回 zip 解码器
  并抛 `BadZipFile`（同仓库 abcmidi 先例注释一致）。
- `build()` 从 `tools.build:compiler_executables` 取 C 编译器（R33），
  以 `make -j1 SHELL=sh CC="..."` 构建，`-j1` 按 R9。
- 上游以 C89 编写，clang 15 直接编译通过，仅提示 `-O6` 不受支持
  （自动回退 `-O3`）与少量 unused/tautological 警告。
- 产物安装为 `bin/mbrola` + `licenses/LICENSE` + `share/doc/mbrola/README.md`。
- OHOS CI worker 上如存在 `/data/service/hnp/bin/binary-sign-tool`，
  配方对产物执行自签名（设备本地无该工具时自动跳过）。
- 无补丁、无 `__OHOS__` 宏、无绝对前缀注入（PF5/PF6 干净）。

## Consumer Validation

`test_package/test_mbrola_consumer.py`（由 `test_mbrola_consumer.sh` 包装）
以已发布的 `mbrola-gr2` 语音库真实驱动被测二进制，覆盖：

1. CLI 契约：裸执行 banner、`-h` 用法、非法选项/缺失数据库/缺失 pho/
   `-v 0` 的退出码与错误消息；
2. `-i` 数据库信息（GR2 身份、SAMPA 音素表、静音音素行）；
3. 上游 211 条音素示例的真实合成：WAV 头/采样率/位深、时长与乐谱
   17264ms 对齐、极性波形、峰值/RMS、二次渲染字节级一致；
4. 运行选项：`-t 2.0` 时长×2、`-v 0.5` RMS×0.5、`-f 2.0` 波形变化而
   时长不变、`-l 14000` 时长≈14000/22050；
5. 输出格式：`.au`（`.snd` 头/编码 3/数据大小与 WAV 一致）、`.raw`；
6. `-W` ROM 转储 + `-w` ROM 渲染与直渲染字节级一致（复刻上游 check 逻辑）；
7. `-e` 错误恢复：未知音素默认报错退出，`-e` 下用静音替代并成功输出。

## Local Preflight Results

- 官方 tarball 下载并校验 SHA256 通过。
- 设备（HarmonyOS aarch64, clang 15.0.4）试用构建：
  `make CC=clang` 一次通过，产物 `Bin/mbrola` 为
  `ELF 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1)`。
- 试用二进制行为实验确认退出码/消息/时长/音量比例/ROM 往返等测试基准。

## OHOS Device CI Results

- 日期：2026-09-26（设备本地 W3，profile `ohos-aarch64-device`）。
- 命令：`python3 scripts/ohc-run.py conan-verify mbrola 3.3 --profile ohos-aarch64-device`。
- 结果：G0–G4 PASS（G2 干净 `conan create` 成功）；L2/L4/L5 在本地因
  cache 路径解析跳过（工具报告记 PASS，平台 CI 流水线将复核）。
- 构建：OHOS clang 15.0.4；产物包
  `mbrola/3.3@ohpcd/stable#c3e7e5ee666eb7f328ddd0f6b35b0cb1:6b129b068851896169fae42d399fa922d239ce8a`
  （`bin/mbrola` + `licenses/LICENSE` + `share/doc/mbrola/README.md`）。
- 消费者测试：`conan create` 内 test_package 真实执行，
  `mbrola consumer validation: 66/66 assertions passed`（8 场景）。
- conan create 日志：`reports/conan-create.log`；verify 报告：
  `reports/conan-verify-report.md`。
- 本地 CI 门禁（`ci/conan/build_and_test.sh`，profile `ohos-aarch64-device`）：
  L0/L1/L1e/L4/L5 PASS，L2 非阻塞告警（上游 CLI 无 --version/--help），
  `Total: 1, Success: 1, Failed: 0`；日志 `reports/w3-local-ci.log`。

## PR/CI Verification Commands

```sh
conan create archives/m/mbrola/3.3 -pr:h=$HOME/.conan2/profiles/ohos-aarch64-device \
  --build=missing
CI_PACKAGES="archives/m/mbrola/3.3" CONAN_PROFILE=ohos-aarch64-device \
  zsh ci/conan/build_and_test.sh archives/m/mbrola/3.3
```

## Blocking Points

- 无源码级阻塞；等待平台 CI（/rebuild）与 AI 检视（/ai review）闭环。

**编译结束**: 2026-09-26
