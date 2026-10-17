# smu 1.5：HarmonyOS PC Conan 构建记录

日期：2026-09-23（UTC 11:37；北京时间 19:37）。目标设备为 H1 HarmonyOS PC，
`HongMeng Kernel 1.12.0`、aarch64。HiShell 中 Conan 2.29.1、
OHOS Clang 15.0.4，编译器目标 `aarch64-unknown-linux-ohos`。

## 输入

- 上游归档：`https://github.com/Gottox/smu/archive/refs/tags/v1.5.tar.gz`，
  SHA-256 `f3bb18f958962679a7fb48d7f8dcab8b59154d66f23c9aba02e78103106093a4`。
- 配方对应本地提交：`b74b737720429399df35f5302cd5edde2d9ce312`。
- 输入 ZIP SHA-256：`265aa10e37aef5773291f96791c8396ed0300dbf376932ae09449095c3cf7733`。
- 单文件 `ohos-aarch64` profile SHA-256：
  `a390d53a5e8d869d6e0b8dae268a0b42ca75ed1d701e97004c9779571024255a`。
  host/build 均解析为 `os=OHOS`、`os.version=6.0`、`arch=armv8`、
  `compiler=clang`、`compiler.version=15`、`compiler.libcxx=libc++`、
  `compiler.cppstd=17`、`build_type=Release`。

原始输入哈希见 [h1-input-sha256.txt](h1-input-sha256.txt)，环境输出见
[h1-environment.txt](h1-environment.txt)。上游源码没有第三方 Conan 依赖，
也不修改 C 源码；配方通过 Makefile 变量覆盖上游固定编译器与主机路径。

## 命令与结果

在 H1 正常 HiShell 中，解压并核对输入后执行：

```sh
conan create "$RECIPE" -pr:h="$PROFILE" -pr:b="$PROFILE"
```

`RECIPE` 为输入 ZIP 的 `delivery/archives/s/smu/1.5`，`PROFILE` 为上述
单文件 profile。H1 原始 Conan 输出记录
`Forced build from source`、`Building from source`、`CC smu.c`、`LD smu`；
打包 `LICENSE`、`smu` 和 `smu.1`，随后调用 `test_package`。
`conan create` 退出码为 0，包引用为：

```text
smu/1.5#f063e7bae7642fd070859cbc39a70a35:6b129b068851896169fae42d399fa922d239ce8a#50757f989d8f69cfebe3679ec151ea43
```

构建时 CFLAGS 含 `-fPIE`，LDFLAGS 含 `-pie -Wl,-z,relro,-z,now`。
Conan 缓存中的本轮成品二进制未随运行目录回传。之后 H1 在同一包
路径执行 `sha256sum`、`readelf -h/-l/-d`，回传哈希与测试汇总一致；
输出显示 ELF64 AArch64 PIE、GNU_RELRO、不可执行栈、NOW，唯一
`NEEDED` 项为 `libc.so`。原始 Conan/ELF 命令输出保存在赛事实测归档，
可按需提供；本线程仍未在
Windows 拿到该二进制本体，不把 H1 命令输出写成 Windows 独立解析。

这次使用的是从本地提交提取的 **单文件** profile 和配方 ZIP。随后
2026-09-24 在 H1 独立框架检出中，`finish` 内的 G2 和 W3 均另行从源码
建包，包内功能 32/32；W3 本地 CI 标记有效。W3 的 L0/L1/L4/L5 通过，
L2 因上游不支持 `--version`/`--help` 记非阻塞 skip。`finish` 在 W3 后
仍因知识图谱/submit 就绪检查未完整通过而退出 1；`conan-verify` 的 G4
找不到包 ID、L2/L4/L5 无 cache 路径却标 PASS，不可作为实质门禁证据。
官方 CI、上传及 PR 尚未执行。
