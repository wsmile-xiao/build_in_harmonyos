# DRAFT-13336-rainfrog-rust-toolchain-relocate-sysroot — 从 conan 工具包供给 OHOS Rust 工具链：**搬移二进制会破 rustc 的 sysroot 推导**（E0463），且**cargo 的动态依赖闭包随构型而变**

> **Contributor**: atomcode | **Status**: DRAFT | **Updated**: 2026-09-27
> **Severity**: 🟡 medium（构建期硬失败，但定位后修法明确） | **Category**: conan / rust / toolchain-provisioning

## 相关既有条目（同族差异化定位）

| 既有条目 | 收录状态 | 问题面 | 本条增量（差异化） |
|---------|---------|--------|--------------------|
| `DRAFT-below-ohos-unsigned-rust-toolchain` | 已收 | rust-lang 官方 dist **未签名**无法 execve（EACCES）→ 逐二进制自签名（含 rustc dlopen 的 `librustc_driver`）+ 补 libssl/libcrypto/libz + CA；**它已确立「用 `tool_requires` 引入 `rust-toolchain` 包」这条路线** | 本条是它的**下一步**：签完名**把二进制搬到别处**会破 sysroot（E0463）；且**不要假设**工具包的运行库闭包固定 |
| `DRAFT-13336-...-probe-exec-not-access`（本 PR 另一份） | 已收 | 探测层：`os.access(X_OK)` 谎报可执行 | 同属工具链供给链，但那条讲"**如何判断可用**"，本条讲"**搬移代价与依赖闭包**" |
| `wagyu-0.6.1-rust-legacy-lockfile-ohos-port` | 已收 | bottle URL 会过期（`openssl@3-3.6.3` 实测 404，pin 须当日实测可达） | 那条讲 **URL 时效**；本条讲**为何应改用仓内 conan 工具包**（轮换风险的结构性解法） |

> **查证记录**（四路检索 `graph/index.tsv` / `graph/*.kv` / `doc/*.md` / `drafts/*`）：
> `E0463` 命中 0；`sysroot` 命中 8 个文件，逐个核过**均属交叉编译 sysroot 语境**（skypat/termutils/trueprint/lgeneral/kqwait/E577/E587 等），**无一处**涉及 "rustc 搬移后 sysroot 失效"；
> `cargo.*(libgit2|libssh2|libcurl|libsqlite3|libzstd)` 与 `动态依赖.*cargo` **命中 0**。
> 即「搬移→sysroot」与「cargo 闭包随构型变化」两个命题在库内均为空白。

## Scope（何时用）

从 conan 工具包（如 `rust-toolchain/1.97.1`）供给 Rust 工具链，且**需要把二进制复制/搬离**原包目录时——典型动因是**为签名**（官方 dist 未签名，须就地或复制后签名）或为构建隔离。

## Symptom

签名后 `cargo`/`rustc` 本身能跑（`--version` 正常），但编译任何代码立即失败：

```text
error[E0463]: can't find crate for `std`
  = note: the `aarch64-unknown-linux-ohos` target may not be installed
  = help: consider downloading the target with `rustup target add ...`
```

对照：`rustc --print sysroot` 输出的是**搬移后的目录**（其中没有 std），而不是原包目录。

## 根因

`rustc` 由**自身可执行文件路径**推导 sysroot（`<bin>/../lib/rustlib/<triple>/lib`）。把 `bin/cargo`、`bin/rustc` 复制到别处后，sysroot 随之变成那个新目录 → 找不到 target 标准库。而只读负载（std rlib、rustlib 等）体积很大（实测该包 **890MB**），全量复制代价高且多数文件无需 exec。

> 注意与 `below` 草稿的边界：它解决"**为何不能执行**"（未签名 → 签名），本条解决"**签名要搬文件，搬完为何编译不了**"（sysroot）。**只签名不处理 sysroot 会从 EACCES 变成 E0463**。

## 修复（rainfrog 0.3.20 实证）

只复制并签名**需要 exec 的少数文件**，再用 `--sysroot` 把标准库指回原包目录：

```python
pkg = self.dependencies.build["rust-toolchain"].package_folder
self._rust_sysroot = pkg          # 记下包目录作为显式 sysroot
# 仅复制 bin/cargo、bin/rustc 与 rustc 会 dlopen 的 librustc_driver-*.so，逐个自签名
...
env["RUSTFLAGS"] = f"--sysroot={self._rust_sysroot} -C linker={cc}"
```

* 实测：加 `--sysroot=<包目录>` 后真实编译正常推进（**372 个 crate 编成，无 E0463**）。
* 省下 ~890MB 复制；`std` 等只读负载不被 exec，无需签名。
* `librustc_driver-*.so` 是 `rustc` **dlopen** 的（不是 NEEDED），仍须复制并签名。

## 附带事实（同批实测，供供给工具链时判断）

1. **cargo 的动态依赖闭包随 rust 构型而变，不要假设"工具包自带其运行库"**：
   | rust 版本 | cargo 的额外 NEEDED（除 libc） |
   |---|---|
   | 1.97.1（harmonybrew bottle） | `libssl.so` `libcrypto.so` `libz.so` |
   | 1.98.1_2（同一 CDN 的当前版） | 上述之外**再加** `libgit2.so.1.9` `libssh2.so.1` `libcurl.so.4` `libsqlite3.so.0`（`librustc_driver` 另需 `libzstd.so.1`） |
   → 升级 rust 版本可能**悄悄引入一串新的运行库依赖**。供给前先 `readelf -d` 看 NEEDED，别沿用旧版本的库清单。
2. **优先用仓库内 conan 工具包（`rust-toolchain/1.97.1`），而非外部 CDN 的 bottle**：CI 实测 harmonybrew 的 `rust-1.97.1` bottle 已被**轮换为 404**（同一 URL 在本机因命中旧缓存边缘仍 200），而当前可取的 `1.98.1_2` 闭包又大；仓内包随制品仓固定，不受 CDN 轮换影响。

## 反例/边界

* 若**不搬移**二进制（就地签名，如 `below` 的做法），sysroot 不受影响，**无需** `--sysroot`。
* `--sysroot` 必须指向**含 `lib/rustlib/<triple>/lib`** 的目录（即包目录本身，不是 `bin/`）。
* 若工具包本就自带全部运行库（闭包为 0），第 1 条附带事实不适用——但仍应实测确认，而非假定。

## 触发实例

rainfrog 0.3.20（PR #13336，2026-09-27）。首版把签名后的 `cargo`/`rustc` 复制到 `build_folder/rust-toolchain`，编译即报 `E0463 can't find crate for std`；改为 `--sysroot=<rust-toolchain 包目录>` 后通过。
