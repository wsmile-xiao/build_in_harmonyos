# draft-sourceforge-cdn-blocked-use-alpine-distfiles

## 症状

配方按惯例写官方源，结果本地与 CI 预下载都拿不到源码：

```
curl: (22) The requested URL returned error: 522
curl: (6) Could not resolve host: netcologne.dl.sourceforge.net
```

`conan create` 卡在 `source()`，W3 硬门槛无法执行。

## 排查（要「广撒网」，别只试一个镜像）

SF 的文件分发有 20+ 个 `*.dl.sourceforge.net` 主机。逐个带 `-L` 探测：

```
for h in downloads master netcologne phoenixnap deac-fra netix gigenet deac-riga \
         pilotfiber cytranet-dal jaist newcontinuum freefr kumisystems astuteinternet \
         versaweb psychz excellmedia nchc altushost-swe ixpeering sit.sa udomain \
         webwerks vorboss liquidtelecom; do
  curl -s -o /dev/null -w '%{http_code}\n' -L --max-time 25 -r 0-1023 \
    "https://$h.dl.sourceforge.net/project/<proj>/<file>"
done
```

本环境结果：4 个主机返回 **HTTP 522**，其余 **DNS 解析失败** —— 是 CDN 边缘整体不可达，
不是单个镜像抽风，重试无意义。

## 解决方案

1. **不能改用 Debian/Ubuntu 的 `_1.4.1.orig.tar.*`**：preflight PF7 对
   `deb.debian.org` / `snapshot.debian.org` / `+dfsg` 一律硬拦（Debian 下游重打包源）。
2. **可用**：Alpine Linux 官方 distfiles，逐字保留上游 tarball：
   `https://distfiles.alpinelinux.org/distfiles/edge/<pkg>-<ver>.tar.bz2`。
3. **备选（有坑）**：`sources.voidlinux.org/<pkg>-<ver>/` 给的是 **.tar.xz 重打包**，字节与
   官方 `.tar.bz2` 不同，**不能**和官方源共用一个 sha256（Conan 2 的 `get()` 不支持
   per-mirror 校验和，2.29.1 实测无 `mirror_urls`/`mirror_sha256` 参数）。
4. **conandata.yml 用 url 列表**「官方源优先 + 镜像兜底」，Conan 逐个回退：

```yaml
sources:
  "1.4.1":
    url:
      - "https://downloads.sourceforge.net/project/tanidvr/TaniDVR/tanidvr-1.4.1/tanidvr-1.4.1.tar.bz2"
      - "https://distfiles.alpinelinux.org/distfiles/edge/tanidvr-1.4.1.tar.bz2"
    sha256: "149b075a60625ca23a96d71b46db6ed42e1b10d08366d6891f569c558de33c47"
```

5. **共用 sha256 的前提是先验证字节相同**：

```bash
curl -fsSLO https://distfiles.alpinelinux.org/distfiles/edge/tanidvr-1.4.1.tar.bz2
cmp tanidvr-1.4.1.tar.bz2 <上游 orig tarball 副本>   # 逐字节一致
md5sum tanidvr-1.4.1.tar.bz2                        # b0acaaa1...bf8，与 Ubuntu/Debian 公布值一致
```

6. CI 侧 `ci/conan/build_and_test.sh` 的 predownload 会逐个 URL curl（每 URL 重试 3 次），
   把成功的替换为 `file://`；只要有一个镜像可达，`conan create` 就能拿到源码。脚本退出时
   用 trap 还原官方 URL，不会把 `file://` 提交进仓库。

## 验证

tanidvr/1.4.1：SF 侧 24 个主机全部不可达；Alpine distfiles 返回 200/175991 字节，与上游
orig tarball `cmp` 一致；用 url 列表后本地 `conan create` rc=0，62 项断言全绿。
