# DRAFT-6050-libnxml-0.18.5-upstream-test-dead-domain — 上游测试硬编码已被注册局下线的域名：以本地 HTTP 等价数据源替代，测试逻辑零改动

- 触发事件：libnxml 0.18.5 适配，make check 的 easy 用例失败
- 路径：Path B（知识库扩展）
- 编号：DRAFT-6050

## 现象

上游正式测试 easy（test/easy.c）调用
`nxmle_new_data_from_url("http://www.autistici.org/bakunin/index.php", ...)`
返回 NULL → exit(1)，报 "New data from url... Download error"。库本体解析
（new / test_base）全部正常。

## 根因（排除法实证）

1. 本地 curl 取 http://127.0.0.1:18080/ 正常 → curl 链路与 libnxml 下载
   逻辑本身无恙；
2. `www.autistici.org` 在 114.114.114.114 与 8.8.8.8 直连 DNS 查询均返回
   rcode=3（NXDOMAIN，权威否定，非劫持/超时）；`autistici.org` 同样
   NXDOMAIN；对照组 `example.com` rcode=0 正常；
3. 该域名 2026-08-28 起被注册局 serverHold 全球下线（公开报道与制裁事件
   相关），任何网络环境下测试都必然失败。

结论：外部依赖（硬编码 URL）永久失效，非移植缺陷，非 OHOS 兼容性问题。

## 可复用处置模式（配方内做，四步）

1. **定性**：先证明失败点在网络源而非被测逻辑（本地服务对照 + 权威 DNS
   rcode=3）；
2. **等价替代**：`replace_in_file` 把测试源里的 URL 换成
   `http://127.0.0.1:<port>/<原路径>`，端口号自选；测试代码逻辑一行不动；
3. **同构数据**：配方内起本地 HTTP 服务提供与原 URL 同构的内容（原是
   HTML 页面 → 供给等价 HTML）。python http.server + threading 即可：
   ```python
   import http.server, socketserver, threading
   httpd = socketserver.TCPServer(("127.0.0.1", PORT), Handler)
   threading.Thread(target=httpd.serve_forever, daemon=True).start()
   # finally: httpd.shutdown()
   ```
   daemon 线程随 conan create 进程退出，不留残留；
4. **证据留痕**：HMBS_UPSTREAM_TEST_RESULT 机器证据行如实记录处置方式
   （"easy 因上游硬编码域名已被注册局 serverHold 下线，替换为 127.0.0.1
   本地 HTTP 数据源，测试逻辑不变"），不冒充"原样通过"。

## 边界与判断

- 只适用于"数据源失效、测试逻辑仍有效"的场景；若测试断言依赖原站点的
  特定内容结构，需提供结构等价的夹具；
- 域名被墙/被墙DNS污染（rcode 非 3、或换网络可解析）≠ 域名下线；前者应在
  notes 记录环境限制，不能动测试；
- 不适用于"测试本来就设计成需要真实外网"的集成冒烟（如 httperf 基准），
  那类按仓库惯例走本地 http.server fixture（httperf/0.9.1 先例）。

## 实证

- 本处置后 libnxml 上游 3/3 正式测试（new/easy/test_base）全部真实运行
  通过（make check, # PASS: 3）；
- 日志：tmp/libnxml-adapt/final-check3.log（替代后）、final-check2.log
  （替代前，FAIL: easy）；
- 配方：archives/l/libnxml/0.18.5/conanfile.py `_patch_easy_test_url()` +
  `_start_local_http()`。

## 跨项目适用

任何 autotools/meson/cmake 上游测试套件里硬编码 `http(s)://<固定域名>`
取数据的用例（RSS 解析库、sitemap 工具、网页解析库等），域名下线时套用
同模式：定性 → 本地等价数据源 → 逻辑零改动 → 证据行如实记录。
