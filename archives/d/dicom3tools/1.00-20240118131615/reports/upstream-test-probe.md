# 上游测试夹具缺失 — 原始网络探测留档

> 采集时间：2026-09-11（设备本地时间）
> 结论：夹具归档在官方站点上**不存在**。下面每一节都给出**可复跑的 curl 命令行**、
> **逐字原始输出**（状态行 + 全部响应头 + body）以及**该输出的 sha256**。
>
> **哈希口径**：`sha256` 一律对**下方 `BEGIN/END VERBATIM CAPTURE` 标记之间的逐字节内容**计算。
> 复核者可直接复算（以第 1 节为例；**锚点必须写成整行**，否则本说明文字自身也会命中）：
>
> ```sh
> sed -n '/^<!-- BEGIN VERBATIM CAPTURE urls.txt -->$/,/^<!-- END VERBATIM CAPTURE urls.txt -->$/p' \
>   reports/upstream-test-probe.md | sed '1d;$d' | sha256sum
> ```
>
> 脚本 `gen_probe_evidence.py` 生成本文件；属性表的字节数/行数/sha256 由该脚本对**入库块本身**计算，
>
> **内容变换**：仅一处，且是显式的——curl 捕获的 HTTP 响应头原生为 CRLF，
> 已在**写入捕获文件时**统一归一为 LF（`raw1.txt`/`raw2.txt` 各 11 处 CRLF、
> 拼接后的 `raw-both.txt` 22 处；其余 5 个捕获文件本就没有 CRLF）。
> 因此下方各块内 **CRLF 计数恒为 0**，不存在任何未记录的隐式变换：
> 「入库转录的字节 == 被哈希的字节」严格成立。
>
> 判定依据：响应码 404 且 body 为 S3 的 `NoSuchKey` XML——源站（AmazonS3 源 + CloudFront 分发）
> **明确答复该对象不存在**。权限问题会返回 `AccessDenied`，故 `NoSuchKey` 是键级不存在的
> 确定性答复，比单独的「404」更强。

## 1. 归档 URL 穷举探测（当前版本 `1.00.snapshot.20240118131615`）

命令（4 个路径基 × {images,test} × {tar.bz2,tar.gz} = 16 个 URL；URL 由循环里的 `printf`
写入输出，`size_download` 取自同一次 GET）：

```sh
V=1.00.snapshot.20240118131615
for base in \
  "https://www.dclunie.com/dicom3tools/workinprogress" \
  "https://www.dclunie.com/dicom3tools/dicom3tools" \
  "https://www.dclunie.com/dicom3tools/images" \
  "https://www.dclunie.com/dicom3tools/test"; do
  for kind in images test; do
    for ext in tar.bz2 tar.gz; do
      u="$base/dicom3tools_${kind}_${V}.${ext}"
      code=$(curl -s -o /dev/null -w '%{http_code} %{size_download} %{content_type}' --max-time 45 "$u")
      printf '%s | %s\n' "$u" "$code"
    done
  done
done
```

<!-- BEGIN VERBATIM CAPTURE urls.txt -->
https://www.dclunie.com/dicom3tools/workinprogress/dicom3tools_images_1.00.snapshot.20240118131615.tar.bz2 | 404 373 application/xml
https://www.dclunie.com/dicom3tools/workinprogress/dicom3tools_images_1.00.snapshot.20240118131615.tar.gz | 404 372 application/xml
https://www.dclunie.com/dicom3tools/workinprogress/dicom3tools_test_1.00.snapshot.20240118131615.tar.bz2 | 404 351 application/xml
https://www.dclunie.com/dicom3tools/workinprogress/dicom3tools_test_1.00.snapshot.20240118131615.tar.gz | 404 350 application/xml
https://www.dclunie.com/dicom3tools/dicom3tools/dicom3tools_images_1.00.snapshot.20240118131615.tar.bz2 | 404 370 application/xml
https://www.dclunie.com/dicom3tools/dicom3tools/dicom3tools_images_1.00.snapshot.20240118131615.tar.gz | 404 349 application/xml
https://www.dclunie.com/dicom3tools/dicom3tools/dicom3tools_test_1.00.snapshot.20240118131615.tar.bz2 | 404 368 application/xml
https://www.dclunie.com/dicom3tools/dicom3tools/dicom3tools_test_1.00.snapshot.20240118131615.tar.gz | 404 367 application/xml
https://www.dclunie.com/dicom3tools/images/dicom3tools_images_1.00.snapshot.20240118131615.tar.bz2 | 404 365 application/xml
https://www.dclunie.com/dicom3tools/images/dicom3tools_images_1.00.snapshot.20240118131615.tar.gz | 404 344 application/xml
https://www.dclunie.com/dicom3tools/images/dicom3tools_test_1.00.snapshot.20240118131615.tar.bz2 | 404 343 application/xml
https://www.dclunie.com/dicom3tools/images/dicom3tools_test_1.00.snapshot.20240118131615.tar.gz | 404 342 application/xml
https://www.dclunie.com/dicom3tools/test/dicom3tools_images_1.00.snapshot.20240118131615.tar.bz2 | 404 343 application/xml
https://www.dclunie.com/dicom3tools/test/dicom3tools_images_1.00.snapshot.20240118131615.tar.gz | 404 342 application/xml
https://www.dclunie.com/dicom3tools/test/dicom3tools_test_1.00.snapshot.20240118131615.tar.bz2 | 404 361 application/xml
https://www.dclunie.com/dicom3tools/test/dicom3tools_test_1.00.snapshot.20240118131615.tar.gz | 404 340 application/xml
<!-- END VERBATIM CAPTURE urls.txt -->

| 属性 | 值 |
| --- | --- |
| 原始文件 | `urls.txt` |
| 字节数 | 2020 |
| 行数 | 16 |
| sha256 | `4171afb742079f3ab542474fab094d69e38e0d413595c7dcdb1cc33341cdea9f` |
| 采集命令 | `见上方循环（16 个 URL）` |
| 采集时间 | 2026-09-11（设备本地时间） |

16 行全部 `404`、`content_type` 全部 `application/xml`、`size_download` 340–373 字节
（正是 `NoSuchKey` XML 的长度，与第 2 节的完整响应一致）。

## 2. 完整原始响应（两份代表样本，含响应头与 body）

```sh
curl -sS -i --max-time 45 \
  'https://www.dclunie.com/dicom3tools/workinprogress/dicom3tools_images_1.00.snapshot.20240118131615.tar.bz2'
curl -sS -i --max-time 45 \
  'https://www.dclunie.com/dicom3tools/test/dicom3tools_test_1.00.snapshot.20240118131615.tar.gz'
```

<!-- BEGIN VERBATIM CAPTURE raw-both.txt -->
HTTP/1.1 404 Not Found
Content-Type: application/xml
Transfer-Encoding: chunked
Connection: keep-alive
Server: AmazonS3
Date: Fri, 11 Sep 2026 14:55:17 GMT
X-Cache: Error from cloudfront
Via: 1.1 38842c146ccd8f527d2de72671759d96.cloudfront.net (CloudFront)
X-Amz-Cf-Pop: SEA900-P9
X-Amz-Cf-Id: fL_JLNtNmk8VqXWmcakmafV2Up4xDC2MNyOf9puAD2_Fck_3c_A0fQ==

<?xml version="1.0" encoding="UTF-8"?>
<Error><Code>NoSuchKey</Code><Message>The specified key does not exist.</Message><Key>dicom3tools/workinprogress/dicom3tools_images_1.00.snapshot.20240118131615.tar.bz2</Key><RequestId>MDEHBCPG0CVNAEW5</RequestId><HostId>iXuKTCdHrFyXyGnSPFNR7JhWqxHv1aUzMxHkFYXyl8scv9bj0mOEXlJvauvzpjRE3kYpzAoGCUA=</HostId></Error>
HTTP/1.1 404 Not Found
Content-Type: application/xml
Transfer-Encoding: chunked
Connection: keep-alive
Server: AmazonS3
Date: Fri, 11 Sep 2026 14:55:18 GMT
X-Cache: Error from cloudfront
Via: 1.1 6ebf93cd3baadad602a5fd706f0df16e.cloudfront.net (CloudFront)
X-Amz-Cf-Pop: SEA900-P9
X-Amz-Cf-Id: tKmZRbfAwyJ37fCqKN0QoVOBUw-WYBlUif5TOqFFrcgESUSaH2Y2RQ==

<?xml version="1.0" encoding="UTF-8"?>
<Error><Code>NoSuchKey</Code><Message>The specified key does not exist.</Message><Key>dicom3tools/test/dicom3tools_test_1.00.snapshot.20240118131615.tar.gz</Key><RequestId>KEY41E23WG8AZK3Z</RequestId><HostId>NIfP6ozSf+8469IDI29pilpID9JSRelYPZ+419o6yEwa9YGZm+zHVQDbLh/mj0HC0TpIs6ThdOE=</HostId></Error>
<!-- END VERBATIM CAPTURE raw-both.txt -->

| 属性 | 值 |
| --- | --- |
| 原始文件 | `raw-both.txt（两份响应的拼接）` |
| 字节数 | 1399 |
| 行数 | 26 |
| sha256 | `da2fbfd276b59afa20f6be45f9ee90d6a2d2642fe8c6ddc26329e1f2af5db65a` |
| 采集命令 | `cat raw1.txt raw2.txt > raw-both.txt（对**已归一化**的两份文件做拼接，故该命令字面可复现本块）` |
| 采集时间 | 2026-09-11（设备本地时间） |

`Server: AmazonS3` + `X-Cache: Error from cloudfront` + body `<Code>NoSuchKey</Code>`：
源站确定性地答复该键不存在。单条响应另存为 `raw1.txt`（706 字节，sha256 `b0837bc32e1d1dfcf57104e58ce22ab2230f56b7994d13b014fd06ce56528748`）与
`raw2.txt`（693 字节，sha256 `f3f2df6b5dcf9b12aa47741fd60db2b3bea2379f495e07a069966de8ee3f7ede`）。

## 3. 历史日期探测（同样 404）

4 个日期取自索引页里**真实存在**的源码快照版本号，因此不是凭空构造的路径：

<!-- BEGIN VERBATIM CAPTURE hist.txt -->
https://www.dclunie.com/dicom3tools/workinprogress/dicom3tools_images_1.00.snapshot.20231221101722.tar.bz2 | 404 353 application/xml
https://www.dclunie.com/dicom3tools/workinprogress/dicom3tools_test_1.00.snapshot.20231221101722.tar.bz2 | 404 351 application/xml
https://www.dclunie.com/dicom3tools/workinprogress/dicom3tools_images_1.00.snapshot.20220120135102.tar.bz2 | 404 353 application/xml
https://www.dclunie.com/dicom3tools/workinprogress/dicom3tools_test_1.00.snapshot.20220120135102.tar.bz2 | 404 371 application/xml
https://www.dclunie.com/dicom3tools/workinprogress/dicom3tools_images_1.00.snapshot.20200418151316.tar.bz2 | 404 373 application/xml
https://www.dclunie.com/dicom3tools/workinprogress/dicom3tools_test_1.00.snapshot.20200418151316.tar.bz2 | 404 371 application/xml
https://www.dclunie.com/dicom3tools/workinprogress/dicom3tools_images_1.00.snapshot.20200101000000.tar.bz2 | 404 353 application/xml
https://www.dclunie.com/dicom3tools/workinprogress/dicom3tools_test_1.00.snapshot.20200101000000.tar.bz2 | 404 371 application/xml
<!-- END VERBATIM CAPTURE hist.txt -->

| 属性 | 值 |
| --- | --- |
| 原始文件 | `hist.txt` |
| 字节数 | 1056 |
| 行数 | 8 |
| sha256 | `4e0538b444d70669b7f9452b005f4ef592c2ee192a167a3a8e566db561886dd2` |
| 采集命令 | `对 workinprogress 基址、tar.bz2 扩展名，逐个替换为下面 4 个历史日期版本号执行同一 curl 探测（共 8 个 URL）` |
| 采集时间 | 2026-09-11（设备本地时间） |

## 4. 目录索引原始内容

<!-- BEGIN VERBATIM CAPTURE index-stats.txt -->
$ curl -sS --max-time 45 "https://www.dclunie.com/dicom3tools/workinprogress/index.html" > wip-index.html
页面字节数: 14394
sha256: 9cc24a9fb570608f9d84e255d6b30585cf70a90a04605a0b1611d62585b1a740
快照条目数: 68
匹配 image|test 的行数: 0
macexe: 1   winexe: 1
<!-- END VERBATIM CAPTURE index-stats.txt -->

| 属性 | 值 |
| --- | --- |
| 原始文件 | `index-stats.txt` |
| 字节数 | 275 |
| 行数 | 6 |
| sha256 | `008479df66811d8b263d2abdfbc0eb9104984056e49f5d7bc54b0f532644dbcd` |
| 采集命令 | `见该文件首行记录的 curl 命令` |
| 采集时间 | 2026-09-11（设备本地时间） |

即索引中只有 **68 个源码快照**与 `macexe/`、`winexe/` 两个可执行归档目录，
**`image`/`test` 匹配 0 行**——与第 1 节的 404 结论一致（索引里根本没有该归档的链接）。
页面本体 `wip-index.html` 为 14394 字节、
sha256 `9cc24a9fb570608f9d84e255d6b30585cf70a90a04605a0b1611d62585b1a740`
（该页无 CRLF，可逐字节复算）。

### dicom3tools/old/index.html（旧版归档）

<!-- BEGIN VERBATIM CAPTURE old-index.txt -->
href="."
href="./dicom3tools_0.15.tar.gz"
<!-- END VERBATIM CAPTURE old-index.txt -->

| 属性 | 值 |
| --- | --- |
| 原始文件 | `old-index.txt` |
| 字节数 | 42 |
| 行数 | 2 |
| sha256 | `bb8b88eca9b5ec246cb9560c9c788c814c7a39f1647731be90a346f13ccb0104` |
| 采集命令 | `curl -sS --max-time 45 'https://www.dclunie.com/dicom3tools/old/index.html' | grep -o 'href="[^"]*"'` |
| 采集时间 | 2026-09-11（设备本地时间） |

旧版索引中同样没有夹具归档。

## 5. 第三方镜像：fedorov/dicom3tools

该 GitHub 仓库**已改名**，`curl -L` 后落到 `ImagingDataCommons/dicom3tools`。
其 REST API 有速率限制（本次采集时命中 `API rate limit exceeded`），
故改用不受该限制的 **HTML 页面**取顶层条目：

<!-- BEGIN VERBATIM CAPTURE fedorov.txt -->
$ curl -sSL --max-time 60 "https://github.com/fedorov/dicom3tools" -o fedorov.html
# 该仓库已改名，curl -L 后的最终 URL: https://github.com/ImagingDataCommons/dicom3tools
# HTML 字节数: 300408
条目数: 20
.github appsrc config libsrc support BUGS CHANGES COPYRIGHT Configure Doxyfile INSTALL Imakefile Makefile NotAMakefile README README.md TODO VERSION VERSION.txt WARNINGS
含 images/test 的条目: 无
<!-- END VERBATIM CAPTURE fedorov.txt -->

| 属性 | 值 |
| --- | --- |
| 原始文件 | `fedorov.txt` |
| 字节数 | 422 |
| 行数 | 6 |
| sha256 | `d74bfd77755f315d684735eebad5c9194b34759aa127bc3bdbd0a3268fac6af0` |
| 采集命令 | `见该文件首行的 curl 命令（解析脚本用括号配平取出页面内嵌的 tree.items）` |
| 采集时间 | 2026-09-11（设备本地时间） |

顶层只有 `appsrc` / `config` / `libsrc` / `support` 与若干文档文件，
**没有 `images/` 或 `test/` 目录**（与该镜像的 2004 年快照年代一致）。

## 6. 上游 INSTALL 原文（夹具单独分发的依据）

来自上游 tarball 内的 `INSTALL`（sha256 见 `conandata.yml`）：

```
104: 		make install
105:
106: 	4. To test the conversion routines, and some of the dicom and
107: 	   miscellaneous utilities, if you have the sample images, which
108: 	   are distributed separately, having set the PATH, correctly, do:
109:
110: 		make test
```

上游自己写明夹具「**are distributed separately**」（单独分发），因此官方 tarball 里没有
`images/`、`test/` 是设计如此；而第 1–4 节证明该「单独分发」的归档在官方站点上找不到。
