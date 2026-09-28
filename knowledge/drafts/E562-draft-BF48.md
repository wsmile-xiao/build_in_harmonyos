# E562 — ibiblio 按 Accept-Encoding 切换 Content-Encoding，conan 静默落解压后 tar 导致 sha256 mismatch

## 错误特征

```
ERROR: lbrate/1.1@ohpcd/stable: Error in source() method, line 51
	get(self, **self.conan_data["sources"][self.version], strip_root=True)
	ConanException: sha256 hash failed for 'lbrate-1.1.tar.gz' file.
 Provided hash: ec73e07fa6c38752e0665fe00105b3c6c84bbac06654bb192651bf29a8577dd9
 Computed hash: 66f8e87c9245f275b6e47e85bb7235deb1e0fe2c022fc084ad9853ae7e87ddb5
```

`Provided` 是用 curl 下载、落盘的发布字节（29907 B gzip）；`Computed` 恰好等于
`gunzip -c` 解出的 102400 B 裸 tar。日志里**没有** `Transfer interrupted`。

## 触发条件
- 源站：ibiblio.org（Apache，`.gz` 附加 Content-Encoding，取值随 Accept-Encoding 协商）
- 构建系统：任意（问题出在 `source()` 的 `get()`）
- 阶段：source / download；本地 W3（无 CI 预下载）必现

## 根因分析

| 客户端 | 请求头 Accept-Encoding | 响应 Content-Encoding | 落盘字节 |
|---|---|---|---|
| curl（含 CI 预下载 `curl -sL`） | 无 | `x-gzip` | 发布字节 ec73e07f… |
| urllib.request | 无（`identity`） | `x-gzip` | 发布字节 ec73e07f… |
| requests（conan 下载器） | `gzip, deflate` | `gzip` | 解码后 tar 66f8e87c… |

requests 的 `iter_content` 按 Content-Encoding 透明解码。conan
`file_downloader.py` 只对 `content-encoding == "gzip"` 豁免 Content-Length 尺寸校验——
正好是 ibiblio 回给 requests 的值，于是不报"传输中断"，直接把裸 tar 以 `.tar.gz`
名字落盘，到 `check_sha256` 才失败。与 `DRAFT-conan-downloader-xgzip-content-encoding`
（服务器给 conan 的是 `x-gzip`，报 Transfer interrupted）是同一课题的另一种症状。

发布字节才是 tarball 的身份：CI `build_and_test.sh` 预下载用 curl 取发布字节并把 URL
改写成 `file://`，conan 校验的正是这一层。

## 解决方案

### 推荐方案
1. `conandata.yml` 登记**发布字节**（curl 所得）的 sha256，并在注释里说明两层 hash。
2. `source()`：先 `get()`；捕获 `ConanException` 后用 `urllib.request.urlopen` 重新下载
   （不发送 Accept-Encoding，也不解码），`check_sha256` → `unzip(strip_root=True)` → 删除归档。
3. 两条路径（CI 预下载 file:// / conan 自行下载后回退 urllib）校验同一个 hash。

参考实现：`archives/l/lbrate/1.1/conanfile.py`。

### 回退方案
上游在其它官方位置有无 Content-Encoding 的同版本归档时，按 E561-draft-4FE2 三层字节核验后切换 URL。

### 禁止做法
- ❌ 把 conan 算出的解码后 hash 直接写进 conandata：与 CI 预下载字节层相反。
- ❌ 因为没有 `Transfer interrupted` 就排除 Content-Encoding，转而怀疑上游被篡改、改用非官方镜像。
- ❌ 在配方里调 curl/wget（L0o）或把 URL 写成 file://。

## 验证
```bash
curl -sSI https://ibiblio.org/pub/Linux/utils/compress/lbrate-1.1.tar.gz | grep -i content-encoding   # x-gzip
python3 -c "import requests;print(requests.get('https://ibiblio.org/pub/Linux/utils/compress/lbrate-1.1.tar.gz',stream=True).headers.get('content-encoding'))"   # gzip
curl -sL -o r.tgz https://ibiblio.org/pub/Linux/utils/compress/lbrate-1.1.tar.gz && sha256sum r.tgz && gunzip -c r.tgz | sha256sum
conan create archives/l/lbrate/1.1 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
# 期望日志: "retrying with urllib to keep the published bytes"，随后 Package created
```

## 附：仓库存量风险（请主编复核）
已合入的 ibiblio 源 bsdgames-nonfree 2.17、fortune 9708、mp3info 0.8.5a 的 conandata
登记的均为解码后 hash（实测 raw/decoded：912a9253…/9afcb4f9…、1a98a6fd…/b288b71f…、
0438ac68…/6b600a42…，登记值均为后者），与 CI 预下载（curl 发布字节）的字节层相反。

## 关联条目
- 相似：DRAFT-conan-downloader-xgzip-content-encoding（x-gzip → Transfer interrupted）
- 相似：E561-draft-4FE2（Content-Encoding 两层 hash 的诊断框架）
- 相关：E299（源码获取失败分层诊断）
