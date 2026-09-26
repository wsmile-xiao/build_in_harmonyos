# curl --data-urlencode 大文件内存上限（OHOS 发行版 curl）

> r02 更新：恢复方案已实测闭环（python 预编码 + --data-binary 使 iwnet server2/proxy1 由失败转通过）。

## 概述
OHOS 发行版 curl（`curl 8.8.0-DEV (aarch64-linux-ohos)`）对
`--data-urlencode @file` 的 URL 编码缓冲存在内存上限：**1MB 文件可编码、5MB 起直接
`out of memory`**。`--data-binary` 流式上传不受此限（24MB 实测可用）。
这是**客户端 curl 构建限制**，不是被测库缺陷。

## 错误特征
```
curl: option --data-urlencode: out of memory
curl: try 'curl --help' or 'curl --manual' for more information
```
（在 `set -e` 的测试 harness 中导致整段脚本 rc=1 中止）

## 根因
1. `--data-urlencode @file` 需将整个文件读入并做百分号 URL 编码，编码缓冲
   分配在 OHOS curl 构建中存在上限（实测阈值介于 1MB 与 5MB 之间）。
2. 命令 `--data-binary` 走流式上传，无此限制。
3. 该现象与目标服务器无关：服务器对到达的请求均正常返回（本库 HTTP 200 全绿）。

## 方案（r02 实测闭环的首选恢复）
服务器按 `form_params["bigparam"]` 原样回写（iwnet `_handle_post_bigparam`），
因此客户端可**用 python3 预计算 URL 编码表单体**，再以 **`--data-binary`** 原样发送，
请求体与服务器解码语义完全一致，同时绕过 curl 内部编码缓冲：
```sh
python3 -c "import urllib.parse;open('bigparam-enc.dat','wb').write(b'bigparam='+urllib.parse.quote(open('test.dat','rb').read(),safe='').encode('utf-8'))"
curl -sk -XPOST -H'Expect:' --data-binary @bigparam-enc.dat -o r1.dat ${BASE}/post/bigparam
```
- 备选：提供标准 curl（命令包安装 / Conan `tool_requires` 普通 curl）。
- 无法替换时：如实记录为工具限制，不得把直接失败的 `ls` 类错误写成退出码 0 或伪造通过。

## 验证
- iwnet 1.3.1 `server2-tests-run.sh` / `proxy1-tests-run.sh`：
  `--data-urlencode bigparam@test.dat`（15MB）→ `out of memory`，rc=1。
- 1MB 文件 `--data-urlencode`：参数解析成功（连接被拒也证明选项有效）。
- `--data-binary` 24MB：通过（server1 large body 用例）。
- **r02 实测闭环**：python3 预编码 + `--data-binary` 后，server2 plain/ssl 与 proxy1
  复跑均 rc=0；全量 11/11 可执行集通过率 100%
  （evidence-r02/server2-plain.log、server2-ssl.log、proxy1.log、full-11-executed.log）。
- 服务端全部端点 200 OK（结论：库无缺陷，客户端工具限制）。

## 适用边界
- 适用于任何在 OHOS 设备用 curl `--data-urlencode` 上传大文件的脚本/测试。
- 不适用于小负载（1MB 内正常）；不适用于标准 curl 构建的环境。
- 反例：CI 标准 Linux 环境 curl 无此限制，本条目仅 OHOS 发行版 curl 生效。

## 关联条目
- similar_to：E017（网络工具镜像/下载失败——同属客户端工具层）
- similar_to：E010（toybox sed 与 GNU 行为差异——同属 OHOS 发行版工具差异域）