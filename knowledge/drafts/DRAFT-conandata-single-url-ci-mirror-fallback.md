# E549：conandata.yml 多 URL 列表形态导致 CI mirror fallback 静默跳过

## 错误特征

CI 上 `conan create` 失败于 source() 阶段，日志形态三选一：

```
ERROR: boost1.84-program_options/1.84.0: Error in source() method, line 48
	get(self, **self.conan_data["sources"], strip_root=True)
	ConanException: Error downloading file https://archives.boost.io/release/1.84.0/source/boost_1_84_0.tar.gz: 'Can't connect to HTTPS URL because the SSL module is not available'
```

```
boost1.84-program_options/1.84.0: WARN: network: Error downloading file https://downloads.sourceforge.net/project/boost/boost/1.84.0/boost_1_84_0.tar.gz: ...
boost1.84-program_options/1.84.0: WARN: Could not download from the URL ...: Error
boost1.84-program_options/1.84.0: Trying another mirror.
（列表内所有 URL 依次失败后 ERROR: Error in source() method）
```

CI 失败诊断自动归类为"网络问题/源码下载超时"，提示"已知可达: zlib.net; 已知不可达: ftp.gnu.org"——**具有极强误导性**：会把注意力引向"换个可达的源"，而真实根因是 URL **形态**而非源本身。

## 根因

CI 的 Mirror fallback（`ci/conan/build_and_test.sh` L1019-1027）负责把已知域名（sourceforge.net / archives.boost.io / github.com / ftp.gnu.org 等）的源码 URL 自动改写为镜像列表（官方 + `https://gh-proxy.com/` + 官方）。

**入口条件是单行正则**：

```bash
grep -qE 'url:.*https://(archives\.boost\.io|github\.com|...|sourceforge\.net)/' "$CONANDATA"
```

它要求 `url:` 与 `https://已知域名/` 出现在**同一行**——即 conandata.yml 的 `sources.url` 是**单值字符串**形态：

```yaml
# ✅ 单值形态：正则命中，CI 注入镜像
sources:
  url: "https://archives.boost.io/release/1.84.0/source/boost_1_84_0.tar.gz"
```

而写成多 URL 列表（`url:` 后换行、URL 以 `- ` 为条目前缀）时正则不匹配：

```yaml
# ❌ 列表形态：正则不命中，CI 静默跳过镜像注入
sources:
  url:
    - "https://downloads.sourceforge.net/project/boost/boost/1.84.0/boost_1_84_0.tar.gz"
    - "https://archives.boost.io/release/1.84.0/source/boost_1_84_0.tar.gz"
```

CI 不改写、不提示，配方作者完全无感知。

**后果分两种**，第一种掩盖了坑：

| 场景 | 结果 |
|---|---|
| Worker 的 `DOWNLOAD_CACHE`（/data/cache）已有该 tarball | 构建正常（**假阴性**——写法有雷但被缓存掩盖） |
| cache miss（新包/缓存被清理/换 Worker 池） | conan 按列表顺序裸连官方源：sourceforge 下载超时，archives.boost.io 报 `SSL module is not available`，source() 失败 → CI 红 |

## 解法

**conandata.yml 的 sources.url 写单条官方 URL 字符串**（非列表）。CI 会自动改写为 `[官方, gh-proxy.com/官方]`，gh-proxy 在 CI Worker 上实测可达（build_and_test.sh 注释：2026-08-06 实测仅 gh-proxy.com 可用 412KB/s）。

```yaml
sources:
  # 单值 url 触发 CI mirror fallback 自动注入 gh-proxy 镜像。写多 URL 列表会被
  # CI 静默跳过镜像注入，Worker cache miss 时裸连官方源失败。
  url: "https://archives.boost.io/release/1.84.0/source/boost_1_84_0.tar.gz"
  sha256: "a5800f405508f5df8114558ca9855d2640a2de8f0445f051fa1c7c3383045724"
```

**提交前自检**（判定形态）：

```bash
grep -E 'url:.*https://' conandata.yml
# 有输出 = 单值形态（镜像注入会触发）
# 无输出 = 列表形态，改回单条官方 URL
```

## 降级方案

官方 URL 已失效、必须直连镜像站时：仍保持**单值**形态，URL 直接写镜像地址。先例：

- chmlib 0.40：`https://gitee.com/src-openeuler/chmlib/repository/archive/master.tar.gz`（openEuler 仓库）
- folly v2024.11.18.00：`https://gitee.com/mirrors/folly/repository/archive/v2024.11.18.00.tar.gz`（Gitee 镜像）
- grpc 1.49.2：`https://gitee.com/mirrors/grpc/repository/archive/v1.49.2.tar.gz`

注意：gitee/gitcode 的 repository archive 是 **git 快照**，sha256 与官方 release tarball 不同，须对实际下载内容重算后填入。

切勿把镜像写成第二个列表项——那会同时关掉 CI 镜像注入，且 conan 按序尝试时镜像排在官方源之后，救不了官方源失败。

## 实证

| 构建 | 形态 | 结果 |
|---|---|---|
| CI #40758（Worker CI-026） | 双 URL 列表 | 🔴 source() 失败（sourceforge 超时 → boost.io SSL 错误） |
| CI #40774（Worker CI-037） | 双 URL 列表 | 🔴 同上 |
| CI #40781（Worker CI-031） | 单 URL | 🟢 通过 |

修复 commit：fb5ddf09e1（PR !8512 boost1.84-program_options 1.84.0，calbee21）

**波及面**：同仓库 boost1.84 系列 15 个组件包 PR 同为双 URL 列表写法，构建全绿是因为命中 DOWNLOAD_CACHE——写法本身有雷，cache 失效即复现。

## 红线

- conandata.yml 的 `sources.url` 一律单值字符串（官方 URL）
- 不要为"保险"加多 URL 列表——CI 的镜像机制比手写列表可靠
- 镜像站 URL 也保持单值，sha256 对镜像内容重算
