# 原生真机验证

OHOS 6 arm64；Clang 15.0.4；10.62.201.39:2222；UID 20020084。

| 类别 | 原始分母 | 结果 |
| --- | --- | --- |
| 上游注册测试 | 0 | 原始 make check 已执行；无注册测试，不写成 6/6 |
| 安装包消费者 | 非上游 | 6/6：版本、帮助、FTP 登录/list、binary get、binary put、delete |

FTP 服务仅绑定 127.0.0.1 随机端口，测试凭据仅该临时 fixture 使用；所有文件和配置在本任务自己的消费者目录。
上传与下载均核对完整 65792 字节内容，上传服务端保存实际收到的字节后核对，删除验证真实 DELE 和状态。
SFTP 和 IPv6 只有构建/探测证据，未宣称业务消费者通过；NLS/Kerberos 当前自动探测未找到。

run_id yafc-w3-r4-20261011T080600Z；tree 9f006ebc1b1941c9687be1c1f1630c0284f9f736；Conan create RC0。
日志 SHA256 a2cdb83c1889589b2a624e0a7ff7e930a07a68f2d8c2dc7c2a9a7f179a2addd8。
terminal SHA256 06a070553f094eda09f555547d42fc7465854fbb7e8781d6a39d1a224f0ecd79。
生产 ELF SHA256 67581271002e6da0015bf590dc881b76917c53e554814212d78c536447eae869。
完整 12 receipts，W3_PASS，release/postrelease PASS；日志只收集一次。
以上是历史 r4，不是比赛 worker CI；当前正式验证如下。

## 当前完整正式验证

run_id yafc-full-finish-r2-20261011T104500Z；输入 tree f996e77886427f35ae9f2ad1aaba43d8cd8b5635。
endpoint 10.62.201.39:2222；boot_id c54c7831-20b9-452b-ada4-c221a56df139；UID 20020084。
正式 ConanVerifier PASS、官方 finish step35 PASS、独立 W3_PASS，N=0、消费者 6/6。
log SHA256 22b32ac8ccc13019be073387d072e3c1da048f80acb7a47b396356a67b60230c；
terminal SHA256 f46199ee36ae640ec96b2126edde80a8b0e79f7081ad92b9c7c3f2b4eaeac2f3；
ELF SHA256 67581271002e6da0015bf590dc881b76917c53e554814212d78c536447eae869。
RREV 57c0b500bec290d230a3d616fe389662；PID a2b9c52bd29bfe0b183c9810e1cb1ee41efb94d1；PREV b9ce9fee91012a19dabe0b2917f55059。
原始 .ci-result SHA256 3ca504b4de5c3841ab31226af982211175cb59655524fbebb8704cfb890e2a6b；
timestamp 2026-10-11T18:48:47.728674；integrity_hash 7cbe8e0415fcd0a9；未手工改写。
完整 finish RC1/PARTIAL_POST_W3：step5b/step8 为既有后置检查失败，不称整个 finish PASS。
ConanVerifier L2/L4/L5 cache ID 查找 SKIP，不冒充执行；官方消费者实际运行并通过。
12 回执完整；runner PID25504/start221483 已退出，logs/release 各消费一次，release/postrelease PASS。
旧事务因开机身份变化且无远端任务资源，仅保留诊断，不与新事务拼接计数；未重放旧 launch。
此结果仍不是比赛 worker CI 成功、PR 检视、审核或制品发布结论。
