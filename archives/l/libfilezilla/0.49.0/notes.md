# libfilezilla 0.49.0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-05
- 编译器: clang 15.0.4 / clang++ 15.0.4
- 平台: aarch64-unknown-linux-ohos (HarmonyOS)
- 状态: built

## 编译步骤

1. **依赖准备**（耗时最长）
   - 编译 libtasn1 4.19.0
   - 编译 nettle 3.10.2 + hogweed（启用公钥加密，使用 mini-gmp）
   - 编译 gnutls 3.8.9（使用 --without-p11-kit）
   - 编译 brotli 1.2.0（gnutls 的 brotli 压缩支持）

2. **环境设置**
   ```bash
   export TMPDIR=/storage/Users/currentUser/tmp  # HMDFS 临时目录
   export LD_LIBRARY_PATH=/storage/Users/currentUser/usr/local/lib:$LD_LIBRARY_PATH
   export PKG_CONFIG_PATH=/storage/Users/currentUser/usr/local/lib/pkgconfig:$PKG_CONFIG_PATH
   ```

3. **配置与编译**
   ```bash
   cd libfilezilla-0.49.0.work
   sed -i 's/umask 077/umask 022/g' configure  # 修复 HMDFS 权限问题
   ./configure --prefix=/storage/Users/currentUser/usr/local CXX=clang++
   make -j2
   make install
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 缺少 gnutls >= 3.7.0 | 未编译 gnutls | 编译 gnutls 及其依赖链（libtasn1, nettle, hogweed） |
| 2 | gnutls 缺 rsa_sec_decrypt | nettle 未启用公钥加密 | 重编译 nettle 使用 --enable-mini-gmp |
| 3 | /tmp 只读（E002） | HMDFS 系统限制 | 设置 `TMPDIR=/storage/Users/currentUser/tmp` |
| 4 | umask 077 权限失败 | HMDFS 权限问题 | 修改 configure 中 `umask 077 → umask 022` |
| 5 | getspnam_r/crypt_r 未定义 | musl libc 不支持 | 禁用 shadow 密码功能（impersonation.cpp） |
| 6 | sockaddr_storage 重定义 | 内核头文件与 sys/socket.h 冲突 | 使用宏定义绕过重定义（iputils.cpp） |
| 7 | 缺少 brotli 库 | gnutls 启用了 brotli | 编译安装 brotli 1.2.0 |

## 源码修改

### 0001-configure.patch
- 修改 `umask 077` → `umask 022`（修复 HMDFS 权限问题）

### 0003-lib-impersonation.cpp.patch
- musl libc 不支持 shadow 密码的线程安全函数
- 禁用 `getspnam_r` 和 `crypt_r`，使用非线程安全替代或直接禁用

### 0004-lib-iputils.cpp.patch
- 解决 `sockaddr_storage` 重定义冲突
- 使用宏定义隔离 `linux/socket.h` 的定义

## 依赖版本

| 软件 | 版本 | 说明 |
|------|------|------|
| gmp | 6.3.0 | 系统预装 |
| libtasn1 | 4.19.0 | 编译安装 |
| nettle | 3.10.2 | 编译安装，启用公钥加密 |
| hogweed | 3.10.2 | 编译安装（nettle 公钥加密库） |
| gnutls | 3.8.9 | 编译安装，使用 --without-p11-kit |
| brotli | 1.2.0 | 编译安装（gnutls brotli 支持） |
| iconv | 系统 | musl libc 内置 |

## 功能测试结果

### 测试时间: 2026-06-05 14:40
### 测试项: 18项

| 功能模块 | 测试项 | 结果 |
|----------|--------|------|
| Time | datetime::now() | ✅ PASS |
| Time | datetime comparison | ✅ PASS |
| Encode | base64_encode() | ✅ PASS |
| Encode | base64_decode_s() | ✅ PASS |
| Encode | hex_encode() | ✅ PASS |
| Buffer | buffer::get() | ✅ PASS |
| Buffer | buffer read/write | ✅ PASS |
| File | fopen() write | ✅ PASS |
| File | remove() | ✅ PASS |
| JSON | json::parse() | ✅ PASS |
| JSON | json_type check | ✅ PASS |
| IPUtils | get_ipv6_long_form() | ✅ PASS |
| IPUtils | get_address_type() IPv4 | ✅ PASS |
| IPUtils | get_address_type() IPv6 | ✅ PASS |
| IPUtils | is_routable_address() public | ✅ PASS |
| IPUtils | is_routable_address() localhost | ✅ PASS |
| Hash | md5() | ✅ PASS |
| Hash | sha256() | ✅ PASS |

**结论**: libfilezilla 0.49.0 在 HarmonyOS 上功能正常，核心模块全部可用。

## 注意事项

### HMDFS 临时目录问题

**重要**: HarmonyOS 系统中 `/tmp` 目录为只读，configure 和编译过程需要设置临时目录。

**推荐方案**（用户实际部署时）:
```bash
# 方案 1: 使用用户家目录
export TMPDIR=/storage/Users/currentUser/tmp
export TMP=/storage/Users/currentUser/tmp
export TEMP=/storage/Users/currentUser/tmp

# 方案 2: 使用系统缓存目录（如果存在）
# 注: /data/storage/el/base/cache 目录需要提前创建并设置权限
mkdir -p /data/storage/el/base/cache
chmod 1777 /data/storage/el/base/cache
export TMPDIR=/data/storage/el/base/cache
```

### musl libc 限制

1. **shadow 密码不支持**: `getspnam_r` 和 `crypt_r` 函数不存在
   - 影响: 用户认证（impersonation）功能受限
   - 解决: 禁用 shadow 密码验证

2. **__MUSL__ 未定义**: HarmonyOS SDK 的 sys/socket.h 会定义 sockaddr_storage
   - 影响: 与 linux/socket.h 冲突
   - 解决: 使用宏隔离

### 库链接顺序

编译依赖 libfilezilla 的程序时，链接顺序：
```bash
-lfilezilla -lgnutls -lhogweed -lnettle -lgmp -lpthread -liconv
```

---

**编译结束**: 2026-06-05 14:12
**最终状态**: published
**功能测试**: 18项全部通过
**预编译包**: libfilezilla-0.49.0-ohos-aarch64.tar.gz (12M)