# E321 — GitLab 418 拦截 conan/urllib 源码下载（反爬）

## 错误特征

```
ERROR: HTTP Error 418: I'm a teapot
[Remote: gitlab.alpinelinux.org]
```
或 conan create 的 source() 阶段下载 tarball 时被 gitlab 拒绝；curl 手动下载同一 URL 却成功。

## 触发条件

- 构建系统: 任意（发生在 conan source() 阶段，与构建系统无关）
- 阶段: configuration / source 下载
- 场景: conandata.yml 的 sources.url 指向 gitlab.alpinelinux.org（或 gitlab.com）官方归档

## 根因分析

gitlab.alpinelinux.org 对非 curl 的 User-Agent（如 `ohc/1.0`、`Conan/2.x`、`Mozilla/5.0`）启用反爬拦截，返回 HTTP 418。Conan/urllib 使用自己的 UA 即被拒绝；curl 默认 UA 可正常下载。这是服务端策略，不是 URL 或签名问题。

## 解决方案

### 推荐方案

用 curl 预下载 tarball，按 sha256 命名预置到 conan 源码下载缓存（`core.sources:download_cache`），使 conan create 的 source() 直接命中缓存、跳过网络下载：

```bash
CACHE=${CONAN_HOME:-~/.conan2}/s
mkdir -p "$CACHE/<sha256>"
curl -fsSL <上游URL> -o "$CACHE/<sha256>/file"
# 生成含 references 的 .json 元数据（conan 缓存格式）
# 同时可预置 tarball 到 $TMPDIR/builds/ 让 init-build 跳过下载
```

### 禁止做法

- ❌ 不要把 conandata.yml 的 URL 换成个人 fork / 非官方镜像（违反 R39，官方源必须保留）
- ❌ 不要用 `--insecure` / 关闭校验绕过

## 验证

```bash
curl -fsSL <上游URL> -o /dev/null && echo OK   # curl 可下载
conan create ... -pr:h=ci/conan/profiles/ohos-aarch64   # 命中缓存不再报 418
```

## 关联条目

- 相关: E002（/tmp 只读，同为鸿蒙环境网络/文件系统限制类模式）
