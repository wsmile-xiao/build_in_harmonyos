# GPGME (GnuPG Made Easy)

## 软件简介

GPGME（GnuPG Made Easy）是一个库，提供对GnuPG加密操作的简便访问接口。它简化了在应用程序中使用GnuPG进行加密、解密、签名、验证等操作的过程。

## 主要功能

- 加密和解密操作
- 签名和验证
- 密钥管理
- 支持OpenPGP和CMS（Cryptographic Message Syntax）
- 提供C、C++、Python、Qt等语言绑定

## 依赖关系

### 构建依赖
- **libgpg-error** (>= 1.55): 错误处理库
- **libassuan** (>= 3.0.2): IPC库，用于与GnuPG进程通信
- **gettext** (>= 0.22): 国际化支持

### 运行依赖
- **GnuPG**: 实际执行加密操作的守护进程

## OHOS适配要点

### 1. 平台识别问题（E007）
**问题**: autotools的config.guess不识别HarmonyOS平台
**解决**: 修改config.sub，添加`linux-ohos*`模式识别：
```bash
# 在config.sub中添加ohos支持
| linux-ohos* \
```

### 2. HMDFS文件系统权限（E011）
**问题**: HMDFS默认umask为077，导致临时目录权限问题
**解决**: 在configure脚本中修改umask设置：
```bash
# configure第33036行
umask 000  # 替换 umask 077
```

### 3. libtool archive路径问题（E012）
**问题**: libgpg-error.la包含硬编码的安装路径
**解决**: 修改dependency_libs中的路径：
```bash
dependency_libs=' /storage/Users/currentUser/usr/local/lib/libgpg-error.la ...'
```

### 4. libintl链接问题（E074）
**问题**: libgpg-error静态库依赖libintl，但链接顺序错误
**解决**: 添加LDFLAGS="-lintl"，跳过工具程序编译

## 编译状态

| 版本 | 状态 | 日期 | 备注 |
|------|------|------|------|
| 1.24.0 | built | 2026-05-21 | 核心库可用，工具程序跳过 |

## 使用建议

1. **推荐动态链接**: 编译libgpg-error时使用动态链接gettext，避免后续链接问题
2. **工具程序**: gpgme-tool和gpgme-json因链接问题暂未编译，但不影响核心库使用
3. **测试**: 建议在实际应用中测试加密、解密、签名功能

## 知识提取

- **E007**: autotools项目需要修改config.sub添加linux-ohos*模式识别
- **E011**: HMDFS文件系统umask问题解决方案
- **E012**: libtool archive硬编码路径问题
- **E074**: 静态库依赖libintl的链接顺序问题

## 参考链接

- 官方网站: https://gnupg.org/software/gpgme/
- API文档: https://gnupg.org/software/gpgme/manual.html
- 源码下载: https://gnupg.org/ftp/gcrypt/gpgme/