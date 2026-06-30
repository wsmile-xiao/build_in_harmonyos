# psqlodbc 16.00.0000 编译笔记

## 编译状态
状态: partial（部分成功）

## 问题与解决

### 问题1: config.guess/config.sub 不识别 HarmonyOS 平台
- 解决: 从系统已安装的 autoconf 包复制支持 HarmonyOS 的文件

### 问题2: config.status 临时文件创建权限被拒绝
- 解决: 将源码解压到 ~/tmp 目录，修改 config.status 移除 umask 077

### 问题3: tar 包创建失败（ustar 格式不支持大 inode）
- 解决: 使用 zip 格式替代 tar.gz 格式

## 预编译包
- psqlodbc-16.00.0000-ohos-aarch64.zip (1.3M)

---
编译结束: 2026-06-04
最终状态: partial
