# DRAFT-10767-puredata-config-guess-hmdfs-tmp-permission

## 摘要

OHOS worker 上 autotools `configure` 未显式传 `--build/--host` 时会执行 `config.guess`
探测构建平台，该探测在 HarmonyOS PC CI 上**双重失败**，最终报：

```
./m4/config/config.guess: line 1613: .../dummy.c: Permission denied
./m4/config/config.guess: unable to guess system type
configure: error: cannot guess build type; you must specify one
```

## 失败点（CI #56266，puredata/0.54.1 实测）

1. **uname 不识别**：`uname -s = "HarmonyOS"`、`uname -r = "HongMeng Kernel 1.12.0"`，
   config.guess（含 2024-07-27 新版）均无法映射为已知三元组。
2. **HMDFS tmp 编译探测失败**：config.guess 向 TMPDIR（HMDFS 挂载路径）写入 `dummy.c`
   并编译验证，HMDFS 对该写入返回 Permission denied（E114 同类），即使 uname 映射可绕过
   探测仍失败。

纯环境问题，与包源码无关——任何走 config.guess 探测的 autotools 包都会复现。

## 推荐解法（rec_approach: explicit-build-host-triplet）

configure 显式传三元组，**完全跳过 config.guess**：

```
./configure --build=aarch64-unknown-linux-ohos --host=aarch64-unknown-linux-ohos ...
```

Conan `AutotoolsToolchain` 用法：

```python
tc.configure_args.append("--build=aarch64-unknown-linux-ohos")
tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
```

仓库内已验证先例：argp-standalone、abiword-plugin-clarisworks/pdb、a52dec、aalib。
若上游 config.sub 过旧不认 `*-linux-ohos` 后缀，可退化用 `aarch64-unknown-linux-gnu`
或 `aarch64-linux`（abiword-plugin-docbook / a52dec 用法）。

## 兜底解法（fallback: patch-config-guess-ohos）

构建树多处硬编码调用 config.guess、无法逐一传三元组时，用
`scripts/patch-autotools-ohos.pl`（R15）为 config.guess/config.sub 增加 HarmonyOS
识别分支；**同时**必须把 TMPDIR 指向构建目录内可写普通路径（E114/HMDFS 修复），
否则编译探测仍会 Permission denied。

## 禁止做法

- `./configure` 不带 `--build/--host`（forbid_1）：必然触发探测失败。
- `sed`/`rm` 盲改 config.guess（forbid_2）：新版同样不识别 HarmonyOS，且破坏
  autoreconf 再生成一致性，掩盖真实失败点。

## 验证

```
conan create archives/p/puredata/0.54.1 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --user=ohpcd --channel=stable
```

修复后本地全绿：configure 通过（无 config.guess 探测）、make、test_package 3/3 PASS。
