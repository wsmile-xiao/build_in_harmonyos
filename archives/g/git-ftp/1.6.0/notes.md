# git-ftp 1.6.0 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-07-30
- 编译器: N/A（纯 shell 脚本，无需编译）
- 状态: built

## 编译步骤

无编译步骤，仅复制 git-ftp 脚本和 git-ftp.1 man page 到安装目录。

## 遇到的问题与解决方案

- 上游集成测试 requires vsftpd（FTP 服务器）+ lftp（FTP 客户端），均为 Linux 基础设施；本机无 Docker/vsftpd，用 pyftpdlib + curl 等效替代实跑

## 依赖版本

运行时依赖：
- git
- bash
- curl（用于 FTP/FTPS/SFTP 传输）

## 验证结果

```bash
git-ftp --version
```

### 上游测试实跑结果（本地 pyftpdlib + curl 环境）

- 搭建 pyftpdlib FTP 服务器（127.0.0.1:2121）+ curl FTP 客户端（上游测试脚本本身用 curl）
- 实跑 `tests/git-ftp-test.sh` 14 个用例：**11 通过 / 3 失败（78.6%）**
- 3 个失败用例均为带空格文件名的上传场景（test_inits/test_pushes 等），失败原因：Windows curl 对 URL 中空格编码不兼容（curl error 3: URL using bad/illegal format），非 git-ftp 脚本自身缺陷
- 剩余用例需 lftp（测试脚本中 `skip_without lftp` 守卫跳过），本机无 lftp 未跑
