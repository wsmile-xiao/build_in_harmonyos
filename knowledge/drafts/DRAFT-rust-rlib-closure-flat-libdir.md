# DRAFT-rust-rlib-closure-flat-libdir

## 症状

Rust 库包（首个！此前仓内 Rust 包全是 application）真机 test_package 阶段，
消费者 probe 报（两轮不同的错误面）：

```
FAIL: rlib closure incomplete under /storage/Users/currentUser/.conan2/p/b/.../p/lib
```

或 rustc 直链时（use 式代码，错误被掩蔽成顶层 crate 名）：

```
error[E0463]: can't find crate for `libsignal_core`
```

用 `extern crate` 改写后真凶现形：

```
error[E0463]: can't find crate for `zerocopy_derive` which `libsignal_core` depends on
```

实例：libsignal-core/0.103.1 适配真机第 6/7 轮（2026-09-28）。

## 根因

- cargo 构建库产出的 rlib 分两层：目标 crate 的 `lib<crate>.rlib` 在
  `target/<profile>/` 顶层；**全部传递依赖 rlib 在 `deps/` 子目录**，且带
  哈希后缀名（如 `librand-39d9d4e268a0c61a.rlib`，防 crate 重名冲突）。
- rustc 的 `-L dependency` 只在参数给定的**单一目录**内按 crate 名解析
  哈希后缀 rlib，**不递归搜索子目录**。
- conan `copy()` 按相对路径保序拷贝：src 设 target 目录递归收集 `*.rlib`
  时，`deps/` 子目录结构原样带进 package 的 lib/ → 哈希 rlib 落在
  `lib/deps/` 而非 `lib/` 顶层 → 消费者 glob 找不到、rustc 解析不到。
- **第二层坑**：deps/ 里还有 proc-macro crate（zerocopy_derive /
  derive_more_derive / thiserror_impl）的哈希后缀 **.so**——
  `--crate-type proc-macro` 只产 .so、元数据嵌在 .so 内。消费者 rustc
  解析 rlib 闭包时对**每个传递依赖**（含 proc-macro）做全图元数据加载：
  只拷 `*.rlib` 时必报 can't find crate for `zerocopy_derive`。
- **排障陷阱**：`use` 式代码里该错误被掩蔽成顶层 crate 名（E0463 指向
  use 首段），须改用 `extern crate` 声明 + `RUSTC_LOG=rustc_metadata=info`
  看 "resolving dep X->Y" 链逐层定位真正的缺失 crate。
- application 包只交付 bin/ 可执行文件，从未暴露此坑；库包交付是首次
  走入此路径。

## 修复

package() 三段拷贝，把 deps/ 平铺进 lib/：

```python
# 顶层：liblibsignal_core.rlib（+ 同 profile 顶层其他产物）
copy(self, "*.rlib", src=target_dir, dst=os.path.join(self.package_folder, "lib"))
# deps/：哈希后缀依赖 rlib 平铺进同一 libdir（-L dependency 不搜子目录）
copy(self, "*.rlib", src=os.path.join(target_dir, "deps"),
     dst=os.path.join(self.package_folder, "lib"))
# deps/：proc-macro crate 的 .so 一并平铺（消费者全图元数据加载必需）
copy(self, "*.so", src=os.path.join(target_dir, "deps"),
     dst=os.path.join(self.package_folder, "lib"))
```

消费者 probe：

```
rustc --edition 2024 \
  --extern libsignal_core=$pkg/lib/liblibsignal_core.rlib \
  -C linker=${CC:-clang} \
  -L dependency=$pkg/lib probe.rs
```

**链接器必须显式传 `-C linker`**：裸 rustc 不读 RUSTFLAGS（那是 cargo 的
变量），无 `-C linker` 时回退默认 `cc`——OHOS 无 cc 符号/cc 不可执行
（EACCES，真机第 8 轮实证）。CC 由 test_package 环境解析为 clang。

C/C++ 消费者不能直接链 rlib（需 Rust 运行时/panic 处理）——package_info
仅声明 libdirs。

## 适用范围

- 一切以 rlib 形态交付的 Rust 库包（cargo 构建、crate 类型 rlib）；
- 消费者为 rustc 直链或任何 -L dependency 集成（含 hmbs 预检的
  test_package probe）。

## 反例/边界

- 交付布局已固化无法平铺时，fallback = 消费者对每个传递依赖（含
  proc-macro .so）逐一 `--extern <crate>=<path>` 枚举（脆弱，随依赖版本
  漂移），仅应急；
- cdylib/staticlib 交付无此问题（单一 .so/.a 产出，不涉及 deps/ 闭包）；
- 非本机理的 can't find crate：--extern 拼写/版本/feature 差异——先查
  lib/ 布局与 .so 闭包，再用 extern crate 改写 + RUSTC_LOG 定位。

## 触发实例

- libsignal-core/0.103.1（2026-09-28）：第 6 轮 probe 报 rlib closure
  incomplete（deps/ 子目录坑）→ 第 7 轮平铺 rlib 后报 can't find crate
  for `zerocopy_derive`（proc-macro .so 坑）→ 第 8 轮 *.so 随档平铺后全过。

## 相关

- wagyu-0.6.1-rust-legacy-lockfile-ohos-port：Rust 包锁文件迁移；
- DRAFT-rust-toolchain-no-rustdoc-skip-doctests：库包测试目标限定（--lib）。

