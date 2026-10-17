# E547 — 进程内 libcurl 默认 CAINFO 失效致全部 HTTPS 失败:运行时 CA 库探测

## 错误特征
```
SSL certificate problem: unable to get local issuer certificate
CURLE_SSL_CACERT(curl rc=60)
curl: (60) SSL certificate problem
```
应用自身日志常见形式:`failed to fetch ...`、`unable to fetch ...`(上游对
底层 SSL 错误无透传时,如 clib 的 http-get)。

## 触发条件
- 构建系统: 任意(直接链接 libcurl 的程序;与构建系统无关)
- 阶段: runtime(运行期所有 HTTPS 请求;测试期的真实拉包用例同样命中)
- 平台: OHOS(无 `/etc/ssl` 默认 CA;musl);Conan 发行 libcurl 包的消费者
- 前置: 程序直接调用 libcurl 且未显式设置 `CURLOPT_CAINFO/CURLOPT_CAPATH`

## 根因分析
1. OHOS 设备无 `/etc/ssl/certs/ca-certificates.crt` 等常规 CA 路径;
   `/system/etc/security/certificates/` 为 openssl 哈希命名(`<8hex>.0`)证书目录。
2. Conan 发行 libcurl 包(静态链 openssl)的编译期默认 CAINFO 指向打包机路径
   (本例为设备用户 harmonybrew 前缀),在 CI/其他设备上不存在。
3. 关键失效机理(实测):libcurl 在"未显式设置 CAINFO 时使用编译期默认值",
   该默认值存在(哪怕指向不存在的文件)即屏蔽 openssl 的 `SSL_CERT_FILE`/
   `SSL_CERT_DIR` env;`CURL_CA_BUNDLE` 是 curl **工具层**特性,libcurl 不读。
   因此"设环境变量"这条对 curl/wget 有效的路径(E185 方案)在进程内场景全部失效,
   必须代码级显式 `setopt`。
4. 实测对照:同 libcurl 下不设 CAINFO → rc=60;显式
   `CURLOPT_CAINFO=$HOME/usr/local/ssl/cert.pem`(121 证书)或
   `CURLOPT_CAPATH=/system/etc/security/certificates` → status=200。

## 解决方案

### 推荐方案
运行时探测 CA 库并对每个 easy handle 显式 setopt(在应用的 HTTP 封装层做一次,
探测结果缓存):
1. 探测顺序:
   - env `CURL_CA_BUNDLE`、`SSL_CERT_FILE`(可读文件)→ 设 `CURLOPT_CAINFO`
   - 常见 Linux CA 文件:`/etc/ssl/certs/ca-certificates.crt`、
     `/etc/ssl/cert.pem`、`/etc/pki/tls/certs/ca-bundle.crt` → 设 `CURLOPT_CAINFO`
   - env `SSL_CERT_DIR`、设备证书目录 `/system/etc/security/certificates`
     (openssl 哈希命名目录)→ 设 `CURLOPT_CAPATH`
2. 全部未命中时保留 libcurl 默认行为(不静默降级、不跳过验证)。
3. 纯 POSIX(`access`/`getenv`),无平台条件编译;Linux 上命中标准路径,
   与默认行为等价,双环境兼容。
实例:`archives/c/clib/2.8.7/patches/0001-http-get-ca-store-probe.patch`
(vendored http-get 的 buffer 与 file 两条请求路径均生效)。

### 禁止做法
- ❌ `CURLOPT_SSL_VERIFYPEER=0` / `curl -k` / `--insecure`:关闭证书验证,
  拉取的代码可被中间人替换,包产物不可接受(E185 的临时方案仅限手工测试)。

## 验证
```bash
# 1) 最小程序复现:不设 CAINFO → rc=60;显式 CAINFO → rc=0, status=200
# 2) 包级证据(本任务):
#    上游测试 73/73(含真实 GitHub 拉包/安装/搜索/卸载);
#    test_package 14/14(含 clib-search 真实 HTTPS 查询)
conan create archives/c/clib/2.8.7 -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing \
  --user=ohpcd --channel=stable
```

## 关联条目
- 相关: E185(工具层 SSL 证书问题:set-env-var/curl -k;本条目为其进程内场景增量)
- 相关: E085(musl 缺 pthread_cancel,同为 musl 能力缺失族,方案同为运行时/构建期探测)
