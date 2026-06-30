# libdatachannel 0.24.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-01
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. 下载源码: `v0.24.0.tar.gz` from GitHub (Python urllib绕过SSL)
2. 手动填充git子模块源码（Python urllib下载5个子模块）
3. 替换libsrtp为v2.5.0（原main分支v3.0.0与libdatachannel不兼容）
4. 安装OpenSSL 1.1.1w完整头文件和库到~/usr/local
5. 创建ohos_compat.h兼容性头文件（BSD类型+宏定义）
6. cmake配置（显式指定OpenSSL路径、ohos_compat.h -include）
7. make编译成功

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Git子模块为空 | GitHub SSL+超时 | Python urllib下载源码并手动填充 |
| 2 | OpenSSL头文件不完整 | 安装了3.x但缺少ssl.h | 切换为OpenSSL 1.1.1w完整头文件和库 |
| 3 | BSD类型未定义(u_int/u_long/u_char/caddr_t) | HarmonyOS无BSD类型定义 | 创建ohos_compat.h头文件 |
| 4 | IFNAMSIZ未定义 | HarmonyOS缺少网络常量 | ohos_compat.h中定义IFNAMSIZ=16 |
| 5 | timercmp宏未定义 | HarmonyOS缺少BSD timeval比较宏 | ohos_compat.h中定义timercmp/timeradd/timersub宏 |
| 6 | libsrtp submodule为v3.0.0(srtp3) | 下载了main分支而非v2.x | 替换为libsrtp v2.5.0(srtp2 target) |
| 7 | pkg-config openssl.pc指向错误版本 | 安装了1.1.1w但pc文件指向3.x | cmake显式指定OpenSSL库路径 |

## 源码修改

- 新增文件: ohos_compat.h (BSD兼容性头文件，定义u_int/u_long/u_char/caddr_t/IFNAMSIZ/timercmp等)
- 新增文件: deps/usrsctp/usrsctplib/user_socketvar.h (原为空文件，填充BSD socket结构定义)
- 修复说明: user_socketvar.h中的OHOS兼容类型原被错误放在 `#if defined(__APPLE__)` 内（在OHOS上该块被跳过），已移至独立的平台检测块

## 依赖版本

| 依赖 | 版本 | 备注 |
|------|------|------|
| OpenSSL | 1.1.1w | 需完整头文件和库 |
| nlohmann-json | master分支 | 内嵌子模块 |
| plog | master分支 | 内嵌子模块 |
| libjuice | master分支 | 内嵌子模块 |
| usrsctp | paullouisageneau fork | 内嵌子模块 |
| libsrtp | 2.5.0 | 替换了v3.0.0 |

## 验证结果

```bash
# 库文件
$ file ~/tmp/test-install-libdatachannel-0.24.0/storage/Users/currentUser/usr/local/lib/libdatachannel.so
libdatachannel.so: ELF 64-bit LSB shared object, ARM aarch64, ...

# 头文件
38个rtc/*.hpp头文件已安装
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libdatachannel.so | 3.5MB | 共享库 |

## 注意事项

- 必须使用ohos_compat.h -include编译以解决BSD类型兼容性
- libsrtp必须是v2.x系列（v3.x target名称不匹配）
- OpenSSL需要完整头文件（包含ssl.h）
- user_socketvar.h中OHOS兼容类型不能放在#if defined(__APPLE__)内
## 功能测试结果（2026-06-02）

**9项功能测试全部通过**：

| # | 测试项 | 结果 | 说明 |
|---|--------|------|------|
| T1 | 版本 | PASS | RTC_VERSION = "0.24.0" |
| T2 | InitLogger | PASS | 日志系统正常 |
| T3 | Configuration | PASS | IceServer配置正常 |
| T4 | PeerConnection | PASS | 创建成功，初始状态=New |
| T5 | 回调 | PASS | LocalDescription生成(offer)，状态回调正常 |
| T6 | DataChannel | PASS | 创建成功，label="test-channel" |
| T7 | WebSocket | PASS | 实例创建成功 |
| T8 | Description | PASS | 描述对象正常 |
| T9 | C API | PASS | rtcInitLogger等C接口正常 |

**链接注意事项**：OHOS SDK Scrt1.o 导致 `-ldatachannel` 链接时出现 `undefined symbol: main`，需用完整 .so 路径或 `-nodefaultlibs` 方式链接

---

**编译结束**: 2026-06-02 12:18
**最终状态**: published
