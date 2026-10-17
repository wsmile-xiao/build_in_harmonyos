# DRAFT-ohos-cargo-no-http2-sparse-multiplexing

> Draft（待审核 promote）｜对应: `knowledge/drafts/DRAFT-ohos-cargo-no-http2-sparse-multiplexing.kv`
> 说明：该 kv 为文档式条目，本文档为其可读镜像。

---

## 适用场景

OHOS 设备/CI 上 cargo 拉取依赖（rsproxy.cn sparse 镜像方案，argc/libsignal-core 家族）时报：

```
ERROR network: failed to enable HTTP/2, is curl not built right? error: [1] Unsupported protocol
error: failed to get `ahash` as a dependency of package ...
Caused by: failed to query replaced source registry `crates-io`
Caused by: download of config.json failed
```

或换 git 索引协议后报：

```
warning: spurious network error (5 tries remaining): [60] SSL peer certificate
or SSH remote key was not OK (SSL certificate OpenSSL verify result:
self-signed certificate in certificate chain (19))
```

## 根因

- cargo 内置 libcurl 在 OHOS 分发（Harmonybrew bottle / rust-toolchain 包）常未启用 HTTP/2；sparse 注册表协议默认启用 HTTP/2 多路复用 → `[1] Unsupported protocol`，索引更新完全失败。
- 换 git 索引躲开 HTTP/2，但 cargo 的 git 传输（libgit2）证书校验路径不同，报 `[60]`（设备无默认 CA bundle）——死路。

## 解法

`.cargo/config.toml` 的 `[http]` 段双修（保留家族既有的 rsproxy sparse 替换 + retry/timeout/low-speed-limit 容错）：

```toml
[source.crates-io]
replace-with = "rsproxy-sparse"

[source.rsproxy-sparse]
registry = "sparse+https://rsproxy.cn/index/"

[net]
retry = 10

[http]
timeout = 600
low-speed-limit = 1
multiplexing = false
cainfo = "/storage/Users/currentUser/usr/local/ssl/cert.pem"
```

1. `multiplexing = false`：强制 HTTP/1.1，绕开 libcurl 无 HTTP/2 硬伤（alacritty ~300 crate 全量 fetch 实测成功）；
2. `cainfo`：指向系统 CA 存储（usr/local/ssl/cert.pem），设备无默认 CA bundle 时显式喂证书链；仅文件存在时写入（CI 环境路径可能不同）。

**不要改用 git 索引协议**——git 传输证书校验是另一条失败路径，sparse + multiplexing=false 才是正解。

## 实证

alacritty 0.17.0 三轮（2026-10-07 设备）：sparse 默认 FETCH_RC=101（HTTP/2 Unsupported protocol）；git 索引 [60] SSL 失败；sparse+multiplexing=false FETCH_RC=0 全量下载。

## 兜底

个别 crate 慢速卡顿由家族容错覆盖（[net] retry=10 + timeout=600 + low-speed-limit=1，argc 第 12 号坑先例）；彻底无网环境走 cargo vendor 离线路线。
