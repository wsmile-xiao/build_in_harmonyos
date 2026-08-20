# perl-socket6 0.29 编译笔记

## 编译环境
- 构建系统: Perl ExtUtils::MakeMaker (Makefile.PL) + autotools configure
- 编译日期: 2026-07-01
- 编译器: clang/clang++
- 状态: built

## 软件简介

Socket6 是 Perl 的 IPv6 socket 支持模块（XS/C 模块），提供以下函数：
- `inet_pton` / `inet_ntop`: IPv6 地址转换
- `getaddrinfo` / `getnameinfo`: 地址解析
- `pack_sockaddr_in6` / `unpack_sockaddr_in6`: sockaddr_in6 结构操作
- `gethostbyname2`: 按 family 解析主机名
- 各种 IPv6 常量（AF_INET6, PF_INET6, NI_NUMERICHOST 等）

## 编译步骤

1. 从 CPAN 下载 Socket6-0.29.tar.gz
2. 初始化编译环境：ohc-run.py init-build perl-socket6 0.29
3. 运行 autotools configure（在 HMDFS 上 config.status 失败，需手动创建配置文件）
4. 手动创建 config.pl 和 config.h（绕过 config.status HMDFS 问题）
5. 修改 Makefile.PL 跳过 configure 调用并添加 XS 链接参数
6. 运行 perl Makefile.PL 配置
7. 运行 make 编译
8. 运行 make install DESTDIR=$TEST_PREFIX 安装到 staging
9. 生成 Conan 配方并验证

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | autotools configure 失败 | config.status 在 HMDFS 上无法创建临时文件 | 手动创建 config.pl（`$cc='clang'; $libs='';`）和 config.h（定义所有 HAVE_* 宏） |
| 2 | 链接错误：缺少 crti.o, crtn.o | 鸿蒙系统缺少 CRT 文件 | 在 Makefile.PL 中添加 `dynamic_lib => { OTHERLDFLAGS => '-nostartfiles -nodefaultlibs -lc' }` |
| 3 | configure 脚本无执行权限 | 源码包解压后权限丢失 | conanfile.py 中 `chmod(configure_path, 0o755)` |
| 4 | 模块加载测试跳过 | SELinux HMDFS 限制：.so 只能从 hnp_file 上下文路径加载 | 模块需安装到 `/data/service/hnp/perl.org/...` 才能运行时加载 |

## 与 perl-dbd-pg 的经验对照

| 经验 | perl-dbd-pg | perl-socket6 |
|------|------------|--------------|
| CRT 文件缺失 | ✅ -nostartfiles -nodefaultlibs -lc | ✅ 相同方案 |
| HMDFS 限制 | ✅ 需安装到 /data/service/hnp | ✅ 相同限制 |
| Makefile.PL 修改 | ✅ dynamic_lib => OTHERLDFLAGS | ✅ 相同方案 |
| autotools configure | ❌ 不涉及 | ✅ 需手动创建 config 文件 |

## 依赖版本

### 已存在
- Perl 5.42.0: /data/service/hnp/perl.org/perl_5.42.0/
- clang 21.1.5 (Harmonybrew ohos-llvm)

### 编译依赖
- Perl（提供 ExtUtils::MakeMaker、xsubpp 等）

## 编译产物

- **Socket6.so**: 25,728 字节，ELF 64-bit ARM64 共享对象
  - 依赖: libc.so
  - 导出: boot_Socket6 (XS bootstrap 函数)
  - 安全特性: NX=enabled, PIE=enabled, RELRO=full, Stack Canary=enabled
- **Socket6.pm**: 9,783 字节，Perl 模块文件

## config.h 手动配置

由于 autotools configure 在 HMDFS 上失败，手动创建 config.h 定义以下宏：
```c
#define CAN_INET_NTOP 1
#define HAVE_GETADDRINFO 1
#define HAVE_GETHOSTBYNAME2 1
#define HAVE_GETNAMEINFO 1
#define HAVE_INET_NTOP 1
#define HAVE_INET_PTON 1
#define HAVE_PL_SV_UNDEF 1
#define HAVE_SOCKADDR_IN6_SIN6_SCOPE_ID 1
#define HAVE_SOCKLEN_T 1
```

## 知识沉淀

### 平台发现
- 鸿蒙系统缺少 CRT 文件（crti.o, crtn.o 等）
- autotools config.status 在 HMDFS 上失败（无法创建临时文件）
- SELinux HMDFS 限制动态库加载：只有 `hnp_file` 上下文的文件可被 dlopen 加载
- /dev/shm 虽可写文件但不可创建目录，且 .so 加载同样被 MAC 策略阻止

### 编译建议
- Perl XS 模块编译需要 `-nostartfiles -nodefaultlibs -lc` 链接参数
- autotools configure 失败时可手动创建配置文件绕过
- 功能测试需在模块安装到系统路径后进行

---
**编译结束**: 2026-07-01 10:23
**conan-verify 全部通过**: 2026-07-02 (G0-G4 + L2/L4/L5 共 8 道门禁全部 PASS)
**最终状态**: built (编译成功，conan-verify 全部通过，运行时测试因平台限制跳过，待 CI 部署后补充)
