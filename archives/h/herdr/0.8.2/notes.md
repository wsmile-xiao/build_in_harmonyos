# herdr 0.8.2 适配笔记

## 编译环境
- 构建系统: cargo (Rust) + zig 0.15.2 (vendored libghostty-vt)
- 编译日期: 2026-08-23
- 编译器: rustc 1.98.0 + clang 15.0.4 (linker) + zig 0.15.2
- 目标: aarch64-unknown-linux-ohos
- 状态: built

## 编译步骤

```bash
# 1. 构建 vendored libghostty-vt.a（zig 0.15.2，aarch64-linux-musl target）
cd vendor/libghostty-vt
zig build -Demit-lib-vt -Doptimize=ReleaseFast -Dsimd=true \
  -Dtarget=aarch64-linux-musl -Dversion-string=1.3.2-HEAD \
  -Demit-xcframework=false
# 鸿蒙上需要"签名循环"：zig 生成的 build runner/中间工具是未签名 ELF，
# 内核拒绝执行（AccessDenied），对 .zig-cache/o/*/ 下每个 ELF 执行
# binary-sign-tool sign -selfSign 1 后重试，直至构建完成。

# 2. 编译 herdr（cargo 配置 rsproxy 源 + clang linker + OHOS target）
cargo build --release --locked --target aarch64-unknown-linux-ohos
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 解压后 work 目录是 Ghostty 源码而非 herdr | `_BUILD_MARKERS` 不含 `Cargo.toml`，`_promote_nested_source` 误把 `vendor/libghostty-vt`（含 CMakeLists.txt）提升为源码 | 手动用 tar `--strip-components=1` 重建 orig/work 目录（框架问题已绕过，未改框架） |
| 2 | zig build runner 无法执行: AccessDenied | 鸿蒙 SELinux 要求 ELF 带 codesign 签名，zig 生成的中间 ELF 未签名 | 签名循环：每轮失败后对 `.zig-cache/o/*/` 下所有 ELF 执行 `binary-sign-tool sign -selfSign 1`，重试至成功 |
| 3 | zig 0.15.2 不支持 aarch64-linux-ohos target（stdio.h not found） | zig 官方 0.15/0.16 均无 OpenHarmony libc headers | 用 `aarch64-linux-musl` target 编译 libghostty-vt（OHOS libc 为 musl 系，二进制兼容）；patch build.rs 将 `aarch64-unknown-linux-ohos` 映射到 `aarch64-linux-musl` |
| 4 | zig build 每次重编译（签名改变产物内容 → 缓存 hash 失效） | zig 缓存对输出内容校验 | 不用签名循环重跑 zig build，而是 pre-build libghostty-vt.a 后由 patch 后的 build.rs 跳过 zig 调用 |
| 5 | curl SSL 证书验证失败 | 鸿蒙 CA 证书缺失 | 用 python requests（certifi CA）下载；conanfile.py 内 `_set_ca_bundle` 自动定位 CA bundle |
| 6 | zig 0.16.0 与 libghostty-vt build.zig 不兼容 | libghostty-vt 强制要求 zig 0.15.2（build.zig 版本检查） | 锁定 zig 0.15.2（Homebrew 同款） |

## 源码修改

- `build.rs`（补丁 0001-build.rs.patch）：
  1. `zig_target()` 增加 `"aarch64-unknown-linux-ohos" => "aarch64-linux-musl"` 映射
  2. `zig-out/lib/libghostty-vt.a` 已存在时跳过 zig build 步骤（鸿蒙上 zig build runner 需签名循环，由 conanfile.py 预构建）

## 依赖版本

- rust/cargo 1.98.0（harmonybrew，OHOS target 已内置）
- clang 15.0.4（linker）
- zig 0.15.2（官方 aarch64-linux 二进制，SHA256 958ed7d1...）
- libghostty-vt 1.3.2-HEAD（herdr vendored）

## 验证结果

```bash
# 本地功能验证（鸿蒙 arm64 设备）
herdr --version                    # → herdr 0.8.2
herdr server &                     # → 后台启动成功
herdr status server                # → status: running, version: 0.8.2
herdr workspace create --label test-ws --no-focus   # → workspace_created
herdr workspace list               # → 列出 test-ws
```

- **XDG_CONFIG_HOME 是鸿蒙上 herdr server 正常运行的必要条件**：默认 `~/.config/herdr` 位于 file_manager 挂载点（hmdfs），**无法创建 Unix socket**（server 报 `Permission denied / Operation not permitted`）。必须设置 `XDG_CONFIG_HOME`/`XDG_STATE_HOME` 指向支持 socket 的目录（如 BitFun 应用数据区 `/data/storage/el2/base/files/...`）：
  ```bash
  export XDG_CONFIG_HOME=/data/storage/el2/base/files/home_dir/.config
  export XDG_STATE_HOME=/data/storage/el2/base/files/home_dir/.state
  ```
  实测：默认路径 server 启动失败；设置后 `status: running`、socket 正常创建。harmonybrew formula 的 caveats 应提示此配置。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bin/herdr | 23MB | aarch64 OHOS ELF，musl 动态链接，未签名（CI sign.sh 处理） |

## 注意事项

- **zig 依赖是核心难点**：herdr 的 vendored libghostty-vt 必须用 zig 0.15.2 构建（build.zig 版本检查），且鸿蒙上 zig 生成的中间 ELF 全部需要签名。conanfile.py 的 `_build_libghostty_vt()` 内置了"构建失败→签名→重试"循环（最多 20 轮）。
- **CI 兼容**：CI（Linux）上 zig build runner 无签名限制，conanfile.py 按宿主架构下载 zig（aarch64/x86_64），build.rs 在 Linux 上正常执行 zig build；OHOS 上由 conanfile.py 预构建后 build.rs 跳过。
- **R38**：herdr 是 CLI 工具，已创建软件级 `commands.json`。
- 上游测试为 `cargo test`（just test），本次 test_package 以 Homebrew formula 的 test 为蓝本（version + server + workspace API），未修改上游测试源码。

## harmonybrew formula caveats 建议（brew install herdr 后提示）

鸿蒙上 herdr server 依赖 XDG 目录重定向（见上文 E337/XDG 说明），formula 应在 `caveats` 中提示：

```ruby
def caveats
  <<~EOS
    On HarmonyOS, herdr's default config dir (~/.config/herdr) is on the
    file_manager mount which cannot create Unix sockets — `herdr server`
    fails with "Operation not permitted".

    Set XDG_CONFIG_HOME/XDG_STATE_HOME to a socket-capable directory
    (e.g. an app data dir) before starting the server:

      export XDG_CONFIG_HOME=/data/storage/el2/base/files/home_dir/.config
      export XDG_STATE_HOME=/data/storage/el2/base/files/home_dir/.state
      herdr server

    If `herdr --remote` reports "muxclient: master hello exchange failed",
    the HarmonyOS OpenSSH connection multiplexing (ControlMaster) is
    unavailable — add to ~/.config/herdr/config.toml:

      [remote]
      manage_ssh_config = false
  EOS
end

service do
  run [opt_bin/"herdr", "server"]
  keep_alive true
  log_path var/"log/herdr.log"
  error_log_path var/"log/herdr.log"
end
```

> 注：`brew services start herdr` 使用同一环境，若 systemd/launchd 未继承 XDG 变量，需在 plist/service 环境里显式注入上述 export。

建议同步提示 shell 持久化（写入 ~/.zshrc）：

```bash
export XDG_CONFIG_HOME=/data/storage/el2/base/files/home_dir/.config
export XDG_STATE_HOME=/data/storage/el2/base/files/home_dir/.state
```
---

**编译结束**: 2026-08-23 19:36
**最终状态**: built
