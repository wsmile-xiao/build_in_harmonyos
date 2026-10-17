# 硬编码外部服务端点的工具：本地代理 mock 功能测试法

> **适用范围**：硬编码知名外部服务端点（如 EC2 metadata `169.254.169.254`、IMDSv2
> token 端点）的 Python/shell CLI 工具，在无外网/离线/CI 环境做 test_package 功能验证。
> 典型对象：`ec2metadata`、`cloud-init`、各类 instance-id / region / IAM 查询脚本。

## 问题

`ec2metadata`（cloud-utils 0.34）把元数据服务写死为 `169.254.169.254`：

- IMDSv2 token 端点：`http://169.254.169.254/latest/api/token`（`PUT`，恒为全局常量，
  不受 `-u/--url` 覆盖）；
- 元数据基址：可被 `-u http://host/base` 覆盖，但构造 `EC2Metadata` 时先做**直连
  连通性探测**（6 次 × 1s connect）。

离线环境下直连 `169.254.169.254` 是 SYN 黑洞（约 2 分钟级 connect 超时），导致：
任何一个子进程用例挂起、功能路径（token + meta-data）完全不可验证；只测 `--help`
又不满足 R34/PF3 "test_package 必须实质执行被测功能"（空壳测试在建 PR 前置硬闸被拦）。

本机通常**无 root、无 `ip`、无 `iptables`**，无法绑定 `169.254.169.254` 或做端口重定向。

## 根因

1. 工具的端点常量写死，`-u` 只覆盖元数据基址、不覆盖 token 端点；
2. connect 探测无超时参数，黑洞路由挂起而非快速失败；
3. `usage()` 风格工具对 `--help` 也 `exit 1` 且写 stderr —— 以 rc=0 断言帮助
   输出会把设计行为误判失败（首次实测 `--help` rc=1，按输出文本断言后通过）。

## 方案：本地 http_proxy mock 路由法

利用 urllib/requests 遵循 `http_proxy` 环境变量的行为，起一个**本地 HTTP 服务
同时扮演「正向代理 + IMDS mock」**：

1. `socketserver.TCPServer(("127.0.0.1", 0), Handler)` 分配随机端口，线程化服务；
2. 子进程 env 注入：`http_proxy/https_proxy/HTTP_PROXY/HTTPS_PROXY = http://127.0.0.1:<port>`，
   **`no_proxy` 置空**（否则本地地址被绕过、流量直连黑洞）；
3. 元数据 URL 用 `http://127.0.0.1:<port>/2009-04-04`（必须指向 mock 真实端口，
   供工具的直连连通性探测通过；探测只建连不发字节，mock 不受影响）；
4. mock 按 request-line（代理请求 `self.path` 为**绝对 URL**）处理：
   - `PUT .../latest/api/token` → 200 + mock token；
   - `GET .../meta-data/<key>` → 拆绝对 URL 路径，`meta-data/<key>` 命中预设表 → 200 + 值；
5. 断言：`--instance-id`/`--ami-id` 输出含 mock 值（rc=0）。

实测（cloud-utils-ec2metadata 0.34，OHOS PC）：

```text
[help] rc=1            # 上游 usage() 设计行为：写 stderr、exit 1 → 断言文本
[instance-id] rc=0 → i-ohos-test-001
[ami-id] rc=0        → ami-ohos-0.34
[wmm-help] rc=0       # 同包第二工具
OHOS TEST PASSED (rc=0)
```

测试随 `test_package/` 进入 `conan create` 与 W3 本地 CI，门禁真实消费该路径。

## 验证

```bash
EC2METADATA_BIN=<安装>/bin/ec2metadata python3 test_ohos_ec2metadata.py
# → OHOS TEST PASSED, rc=0
```

## 边界与反例

- 仅适用走 TCP/HTTP 的功能路径；需要真实内核/设备能力的用例（如 growpart 类分区
  用例需 fdisk/sfdisk/qemu-utils/mkfs.ext4/lvm2）无法用代理 mock 替代，应如实标记
  `uninstantiated`（上游 CI 对 growpart-lvm 同样 SKIP）；
- 工具若走 raw socket 直连（不走 urllib/requests），`http_proxy` 不生效，需另想方案；
- `--help` 断言必须以输出文本为准，勿以 rc 为准（`usage()` 常 exit 1）。

## 关系

- `similar_to`：E037（env shebang 修复）、E049（硬编码解释器路径修复）、E201
  （比 /bin/bash 等运行时依赖的 OHOS 测试执行）、E325（test_package 内 shell 发现与
  可写 TMPDIR）、E363（test runner 假绿防护）。
- 与 E037/E049 的差异：本条目属于**测试方法**（如何在离线环境真实执行功能路径），
  而非构建期修复；可与脚本包 shebang/install 修复组合使用。