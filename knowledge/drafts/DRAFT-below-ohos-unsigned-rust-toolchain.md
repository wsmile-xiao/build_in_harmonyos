# DRAFT-below-ohos-unsigned-rust-toolchain：HarmonyOS 拒绝执行未签名 ELF——预编译工具链经 tool_requires 落地 conan 构建的完整可执行化

> Contributor: akajhsbnz | Status: Draft | Updated: 2026-09-10
> Source: PR #8596 feat(below): 0.11.0 适配 HarmonyOS PC（CI build #43653/#43689）
> Related: E105, E154, E318, E509

## 背景

`below` 0.11.0 是 Rust 项目（124 个源文件，98% Rust），上游用 cargo 构建。
HarmonyOS PC 无系统 cargo/rustc，标准 rustup 又无法识别 HarmonyOS 宿主
（`uname -s` 返回 `HarmonyOS`，rustup 直接 fatal：`error: unrecognized OS type:
HarmonyOS`，见 E105/E154）。仓库已有基础设施包 `rust-toolchain/1.97.1`
（rust-lang 官方 dist 预编译，宿主与目标均为 `aarch64-unknown-linux-ohos`），
以 `tool_requires` 引入后，构建在工具链引导阶段依次暴露**四类**失败。

四类失败必须全部解决才能跑通；任何一类单独看都是"换一个错误继续失败"。

## 错误 1：未签名 ELF 无法 execve（Permission denied，errno 13）

### 现象

```text
below/0.11.0: Error in build() method, line 76
	self._fetch_cargo_deps(env)
while calling '_fetch_cargo_deps', line 84
	result = subprocess.run(
	PermissionError: [Errno 13] Permission denied:
	'/storage/Users/.../p/rust-1b22ad19431ff/p/bin/cargo'
```

### 根因

HarmonyOS 拒绝执行**未签名**的 ELF；rust-lang 官方 dist tarball 内的
`cargo`/`rustc` 不带 OHOS code signature。**与路径无关**——实测同一二进制在
conan 包目录、`$HOME/tmp`、build_folder 表现完全一致；POSIX mode 位已是 0755
仍被拒（失败根因不是权限位）。知识库 E046/hmmac 记录过同类现象但结论模糊，
E318 记录的是 go test 临时 ELF 场景，本条是**预编译第三方工具链**场景。

### 诊断（一行判据）

失败信息里带 `Permission denied` 且平台为 OHOS、目标又是个从 tarball 解包出来的
二进制 → **先怀疑未签名**，不要再花时间查挂载 noexec / LD_LIBRARY_PATH / mode 位。
签名前后各跑一次即可定案。

### 修复

copy 必须执行的二进制到 `build_folder`，逐个自签名（先写 `.signed` 临时文件再
`os.replace`，避免就地签名截断）：

```python
subprocess.run([signer, "sign", "-inFile", path, "-outFile", tmp,
                "-selfSign", "1"], check=True)
os.replace(tmp, path)
os.chmod(path, 0o755)
```

`rustc` 还需额外签它 **dlopen** 的 `librustc_driver-*.so`。其余只读负载
（`lib/rustlib` 等 ~500MB）用软链避免复制；marker 文件保证幂等。

## 错误 2：cargo 运行期缺 OpenSSL/libz（DT_RUNPATH 被忽略 + 系统库缺符号）

### 现象

```text
Error loading shared library libssl.so: No such file or directory
Error relocating .../cargo: SSL_get0_group_name: symbol not found
```

### 根因

`cargo` 动态链接 `libssl.so`/`libcrypto.so`/`libz.so`（`readelf -d` 可见），而
OHOS loader **忽略 DT_RUNPATH**，必须把 lib 目录显式放进 `LD_LIBRARY_PATH`；
且系统 `/usr/lib` 的 OpenSSL 3.0 **缺** `SSL_get0_group_name`（cargo 1.97 需
OpenSSL ≥3.5）。指向系统库会从"库找不到"变成"符号找不到"，仍旧失败。

### 修复

用 Harmonybrew 的 OHOS 预编译 bottle（**已预签名**，仓库既有 Rust 配方先例：
argc/1.24.0、bottom/0.12.3），sha256 固化后解包，把含 `libssl/libcrypto/libz`
的 lib 目录前置进 `LD_LIBRARY_PATH`：

```python
RUST_RUNTIME_BOTTLES = (
    ("openssl3", ".../openssl%403-3.6.4.arm64_ohos.bottle.tar.gz",
     "e1be73c6c68e29c33ff43761045e43e23e7c369f0fb1a24f40e226ec5cb28f98"),
    ("zlib", ".../zlib-ng-compat-2.3.3_1.arm64_ohos.bottle.tar.gz",
     "1c17a31f8104701bce6b471af8dbbd14bb67d16a504eec087018feb05493a430"),
)
```

## 错误 3：cargo 拉 sparse 索引报证书校验失败

### 现象

```text
error: download of config.json failed
Caused by: SSL certificate verify result: self-signed certificate in
certificate chain (19)
```

### 根因

设备**无默认 CA store**，cargo 走 HTTPS（rsproxy.cn sparse 索引）时无根证书。

### 修复

探测 `/etc/ssl/certs/cacert.pem` 等路径，命中后导出 `SSL_CERT_FILE`、
`CURL_CA_BUNDLE`，并在 `$CARGO_HOME/config.toml` 写 `[http] cainfo`。

## 错误 4（连带）：构建期工具与依赖探测缺失

libbpf-sys 的 `make install_headers` 需要 `install` 工具，而 builder 基础 PATH
不含 `/system/bin`（Error 127）；其 `build.rs` 用 pkg-config 探测 libelf/zlib，
需注入 `PKG_CONFIG_PATH`。另 `conan.tools.files.copy` 默认 `keep_path=True`，
`copy("bin/below", dst=pkg/bin)` 会产出 `pkg/bin/bin/below`，test_package 找不到
可执行文件。

## 方案（首选，可直接复用）

```python
# build_requirements
self.tool_requires("rust-toolchain/1.97.1")

# build 阶段
bin_dir = self._prepare_signed_toolchain()      # 签名 cargo/rustc/librustc_driver
lib_dirs = self._prepare_runtime_libs()         # harmonybrew openssl@3 + zlib-ng
env["LD_LIBRARY_PATH"] = os.pathsep.join([toolchain_lib] + lib_dirs + [prev])
env["SSL_CERT_FILE"] = env["CURL_CA_BUNDLE"] = self._ca_bundle()
env["PATH"] = toolchain_bin + ["/system/bin", "/system/sbin", "/vendor/bin"] + PATH
env["PKG_CONFIG_PATH"] = <dep>/lib/pkgconfig:...
```

回退路径：改用 harmonybrew 的 `rust-1.97.1.arm64_ohos.bottle.tar.gz`
（已预签名）。注意 bottle 的 `bin/cargo` 是**指向 Cellar 绝对路径的 sh wrapper**，
解包到 build 目录后 rc=127，须重写为 exec 本地 `cargo.real` 或直接用
`cargo.real`；运行库与 CA 两项仍需照做。

## 禁止（实测踩过的错误方向）

| 禁止 | 原因 |
|------|------|
| `rustup-init.sh --default-toolchain` / `rustup target add` | rustup 不识别 HarmonyOS 宿主，直接 fatal（E105/E154） |
| `chmod 777 cargo` / 反复调权限位 | 失败根因是缺 code signature，mode 0755 实测仍 EACCES |
| `LD_LIBRARY_PATH` 指向 `/usr/lib`、`/system/lib` | 系统 OpenSSL 3.0 缺 `SSL_get0_group_name`，变成 relocating 失败 |

## 验证证据

- 本机对照实验：clang 新编译二进制可执行；同一 rust-toolchain 二进制在
  conan 缓存 / `$HOME/tmp` / build_folder 一律 EACCES；`binary-sign-tool -selfSign 1`
  后立即输出 `cargo 1.97.1`、`rustc 1.97.1`
- 本地 `conan create archives/b/below/0.11.0`：0 错误，Package created，
  test_package 冒烟通过（产物 18.8MB，含 codesign 段）
- CI：PR #8596 构建 #43689 conan-build-test **PASSED**（此前 #43653 在 cargo
  EACCES 处失败）

## 适用边界

- 平台：HarmonyOS（OHOS loader + hmmac 签名门禁）
- 工具：conan 2.x 构建流程中需要 exec 任何**预编译第三方二进制**的配方
  （Rust/cargo、Go/zig/Deno 等自带发行包的语言，或上游 tarball 内含预编译工具）
- 系统自带工具（clang、make）不受影响；harmonybrew bottle 已预签名，仅需补运行库

## Provenance

- PR: #8596（`feat/below-0.11.0`，fork `akajhsbnz/build_in_harmonyos_6303`）
- Commit: `c122a74f0e`
- 关联正式条目：E105（HarmonyOS 不在 rustup 支持列表）、E154、E318（未签名 ELF
  无法执行，go test 场景）、E509（harmonybrew 动态二进制缺 OpenSSL 3.x 符号）
- 增量：上述条目均未覆盖"预编译工具链在 conan build 中完整可执行化"这条链路
  （签名 + 运行库 + CA + 构建期工具四连解）
