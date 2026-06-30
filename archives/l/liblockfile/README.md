# liblockfile

## 简介
liblockfile 是一个 POSIX 文件锁定库，提供安全的文件锁定机制，防止多进程并发访问冲突。

## 主要组件
- **liblockfile**: 文件锁定库（静态库）
- **dotlockfile**: 命令行锁定工具

## 版本
- 当前版本: 1.17

## 依赖
- 无外部依赖（基础系统库）

## 特性
- 支持 NFS 安全锁定
- 提供 C 语言 API
- 命令行工具支持邮件锁定

## 编译说明
- 构建系统: autotools
- 平台适配: 需修复 HMDFS 文件系统限制
  - HMDFS 不支持硬链接，需用 `open(O_CREAT|O_EXCL)` 替代 `link()`
  - HMDFS SELinux 限制 umask 077 文件权限
  - 鸿蒙用户 ID 可能无用户名映射

## 关键补丁
1. `0001-configure.patch` - HMDFS umask 权限修复
2. `0002-dotlockfile.c.patch` - 处理 getpwuid 返回 NULL
3. `0003-lockfile.c.patch` - HMDFS 硬链接不支持，使用原子 open(O_EXCL)

## 测试验证
- 测试套通过："tests OK"
- 本地安装验证成功

## 归档位置
`archives/l/liblockfile/1.17/`

## 知识沉淀
- HMDFS 不支持硬链接，link() 操作返回 EPERM
- HMDFS hmmac 强制访问控制限制 umask 077 创建的文件
- 鸿蒙系统用户 ID 可能没有用户名映射
- 原子锁创建应使用 open(O_CREAT|O_EXCL) 替代 link()