# libfilezilla

libfilezilla 是一个跨平台的 C++ 库，提供一系列基础功能模块，用于构建网络应用程序。

## 描述

libfilezilla 提供以下核心功能：
- 时间处理（datetime）
- 字符串编码/解码
- 缓冲区管理
- 文件系统操作
- 事件循环和异步 IO
- HTTP 客户端
- TLS/SSL 支持（通过 gnutls）
- JSON 解析
- IP 地址工具
- 哈希计算
- 进程管理
- 线程和线程池

## 版本索引

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|----------|------|
| 0.49.0 | published | 2026-06-05 | 首次在 HarmonyOS 上编译 |

## 依赖关系

### 外部依赖

| 库 | 版本 | 用途 |
|----|------|------|
| gnutls | >= 3.7.0 | TLS/SSL 支持 |
| nettle | >= 3.3 | 加密算法 |
| hogweed | >= 3.3 | 公钥加密 |
| gmp | >= 6.2 | 数学运算 |
| iconv | - | 字符编码转换 |

### 构建依赖

- clang / clang++
- GNU autoconf >= 2.71
- GNU automake >= 1.16
- GNU libtool >= 2.4
- pkg-config >= 0.29

## 平台兼容性

### HarmonyOS (aarch64-linux-ohos)

✅ 已验证可用（2026-06-05）

**注意事项**：
- musl libc 不支持 shadow 密码线程安全函数
- HMDFS 临时目录需设置为可写路径
- 需设置 TMPDIR 环境变量

**环境配置**：
```bash
export TMPDIR=/storage/Users/currentUser/tmp
export LD_LIBRARY_PATH=/storage/Users/currentUser/usr/local/lib:$LD_LIBRARY_PATH
```

## 上游信息

- **官方网站**: https://lib.filezilla-project.org/
- **源码仓库**: https://download.savannah.nongnu.org/releases/libfilezilla/
- **许可证**: GPL-2.0+

## 相关软件

- FileZilla（FTP 客户端）
- FileZilla Server（FTP 服务器）

---

*最后更新: 2026-06-05*