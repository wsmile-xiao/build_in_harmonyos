# Yafc

Yafc 是具有书签、补全、批量传输等功能的交互式 FTP/SFTP 客户端。

原生配方保留 readline 和 libssh，使用发布的 OpenSSL 完成口令/Base64 相关功能；不据此声称支持或测试了 FTPS/TLS。
平台适配处理无 passwd 条目的用户身份，以及 libc tmpfile 不遵守应用可写临时目录的问题，不修改系统账户、SSH 或 libc。

依赖：libssh、readline（间接 OpenSSL、zlib、ncurses）；构建 shell 为发布的 Bash。
FTP 回环消费者已验证上传/下载字节和删除。SFTP 业务测试、正式 finish 与赛事 PR 合同仍待完成。

上游：[sebastinas/yafc](https://github.com/sebastinas/yafc)。
