# E430 — 上游站点停服（OSDN）后的权威源码获取：FreeBSD distcache

> 状态：草稿（待知识库主编审核）｜来源：playumidi 0.8.3 适配（PR 待提交）

## 错误特征

```
$ curl -sS https://ja.osdn.net/projects/playumidi/
curl: (6) Could not resolve host: ja.osdn.net
$ curl -sS https://osdn.net/dl/playumidi/playumidi-0.8.3.tar.gz
curl: (6) Could not resolve host: osdn.net
$ curl -sS https://distcache.FreeBSD.org/ports-distfiles/playumidi-0.8.3.tar.gz
curl: (28) Connection timed out after 25001 milliseconds
```

同时：GitHub/Debian/Ubuntu/AUR/pkgsrc/Gentoo/MacPorts 等主流索引**均无此包**
（`api.github.com/search/repositories?q=<name>` → total_count 0）。

## 触发条件

- 目标软件的 `MASTER_SITES` 指向 **OSDN**（`https://osdn.net/dl/%SUBDIR%/`），
  典型为 FreeBSD ports 里 `MASTER_SITES= OSDN/${PORTNAME}` 的条目
- 阶段：源码获取（init-build / source()）
- 背景：OSDN（原 SourceForge.JP）已于 2024 年终止服务，域名 DNS 不再解析

## 根因分析

1. **上游站点永久消失**，不是网络抖动：`ja.osdn.net` / `osdn.net` 均 NXDOMAIN
   （对照：同环境 `github.com` / `mirrors.tuna.tsinghua.edu.cn` 均可解析可达）。
2. **FreeBSD 官方 distcache 主站走 Fastly**（`distcache.FreeBSD.org` → 151.101.65.241），
   在受限网络中整段不可达（同段 `pypi.org` 亦超时）；但**区域站点不是 Fastly**：
   `distcache.{eu,us-east,us-west}.FreeBSD.org` 直连可达。
3. 区域站点 HTTPS 证书为 `*.freebsd.org` 通配，**不覆盖二级子域**
   （`SSL: no alternative certificate subject name matches 'distcache.us-east.freebsd.org'`），
   因此对这类子域应使用 **HTTP** 或改用主域名。

## 解决方案

### 推荐方案

```bash
# 1) 先读权威打包元数据（sha256 / SIZE），它同时是"上游原件"的指纹
curl -s https://cgit.freebsd.org/ports/plain/audio/<port>/distinfo

# 2) 从区域 distcache 取原始 tarball（HTTP 直连，绕开 Fastly 段与二级域证书问题）
curl -sSL -o <name>-<ver>.tar.gz \
  http://distcache.us-east.FreeBSD.org/ports-distfiles/<name>-<ver>.tar.gz

# 3) 双元数据交叉校验（sha256 + 字节数必须同时一致）
sha256sum <name>-<ver>.tar.gz     # 必须等于 distinfo 的 SHA256
stat -c%s <name>-<ver>.tar.gz     # 必须等于 distinfo 的 SIZE

# 4) 写入 conandata.yml 时使用 https 官方主域 + 区域镜像列表（Conan 支持 url 列表回退）
```

要点：
- **sha256 + SIZE 双校验**可确认取到的是上游原件而非二次打包；
- conandata.yml 中 `url` 用 `https://distcache.FreeBSD.org/...`（官方主域，满足 R39/PF7），
  并附 `https://distcache.{eu,us-east,us-west}.FreeBSD.org/...` 作为回退；
- 判定依据（R39）：FreeBSD distcache 是 **FreeBSD Project 官方基础设施**，
  其 `ports-distfiles/` 缓存就是上游 tarball 原件，属权威镜像源，非个人 fork/网盘。

### 禁止做法

- ❌ 因主站超时就判定"源码不可获取"直接 `dependency_missing` 止损：区域站点可能可达。
- ❌ 用 `file://` 本地路径或未登记镜像域名写进 conandata.yml（PF7 闸会拦）。
- ❌ 不做 sha256 校验就采用来源不明的 tarball。

## 验证

```bash
# DNS 对照（判定"站点消失"而非"网络抖动"）
curl -sS https://ja.osdn.net/ ; echo "rc=$?"        # rc=6 Could not resolve host
curl -sS -o /dev/null -w '%{http_code}\n' https://github.com   # 200 => 网络本身正常

# 区域站点可达性 + 权威校验
curl -sSL -o t.tar.gz http://distcache.us-east.FreeBSD.org/ports-distfiles/<file>
sha256sum t.tar.gz
```

## 实证（真实执行）

playumidi 0.8.3：
```
http://distcache.us-east.FreeBSD.org/ports-distfiles/playumidi-0.8.3.tar.gz -> http=200 size=22160
sha256sum  -> 518e6cefc77d057ab7a802041c4d250a208f93d1bd054fed42a76d6a387dfb1e
FreeBSD ports audio/playumidi distinfo -> SHA256 同上，SIZE(22160) 一致   ✅ 双元数据吻合
```

## 关联条目

- 相关：R39 源码 URL 必须官方/权威源；PF7 源 URL 闸
- 互补：E 类"依赖未发布/registry 不可达"的 R41 止损判定口径（先排除"源可见但主 CDN 不可达"）
