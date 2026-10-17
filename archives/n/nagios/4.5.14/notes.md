# nagios 4.5.14 OHOS 适配笔记

## 基本信息
- 上游: https://github.com/NagiosEnterprises/nagioscore (tag nagios-4.5.14)
- 语言: C (主体 88%, perl/bash 辅助脚本)
- 构建系统: autoconf/automake (configure + make)
- 类型: application（daemon + CGI 工具集）

## 依赖
- openssl/3.5.6 (base/netutils.c NSCA 通知 SSL 加密, CGI 也链接)
- gd/2.3.3.1 (statusmap/trends/histogram CGI 的图形渲染; 可选组件)
  - 传递依赖: libpng/libjpeg-turbo/freetype/fontconfig/libwebp/libtiff 等, 全部制品仓有预编译
- zlib: 上游源码实际不引用 (grep 无 zlib.h/gzopen), 不声明依赖

## OHOS 适配点 (补丁清单)

### 1. config.guess / config.sub (0002/0003)
- 上游 2023-08-22 版不识别 HarmonyOS (uname -s = HarmonyOS)
- 加 __OHOS__/HarmonyOS/aarch64-ohos 识别 → aarch64-unknown-linux-ohos
- umask 077 → 000 (HMDFS E012: setgid 构建目录下 0270 权限导致用户不可写)

### 2. tap/ 子目录 config (构建时复制, 无补丁)
- nagios --enable-libtap 时主 configure 会 run tap/configure
- tap/ 自带 2025-10-28 版 config.guess 也不识别 ohos
- conanfile build() 阶段将主目录补丁后的 config.guess/config.sub 复制到 tap/

### 3. cgi/statusmap.c: rindex → strrchr (0001)
- rindex 是 BSD 遗留 API, OHOS libc (musl 系) 未提供
- strrchr 语义完全等价 (POSIX 标准)

### 4. t-tap/Makefile.in: 3 个链接行补 $(LDFLAGS) (0004)
- 上游 bug: test_commands/test_downtime/test_notifications 链接行漏 $(LDFLAGS)
- 依赖在非系统路径 (conan package_folder) 时链接失败 "unable to find library -lssl"
- 上游 Linux 系统路径安装时碰巧不触发

### 5. t/660status-downtimes-comments.t: $^X (0005)
- bin/generate_downtimes shebang 是 #!/usr/bin/perl, OHOS perl 在 /data/service/hnp/bin/perl
- 改用 $^X (当前 perl 解释器) 调用, 与 prove 环境一致, 测试逻辑不变

### 6. t/etc/*.cfg: temp_path 等路径 (0006-0012, 7 个文件)
- 测试配置写死 temp_path=/tmp check_result_path=/tmp log_file=/tmp/nagios.log
- OHOS /tmp 只读 (E002) → 改相对路径 ../var (与主 nagios.cfg 其余路径风格一致)
- 测试逻辑不变, 仅路径环境适配

## configure 参数
```
CC=clang
--with-ssl=$SSL_SHIM --with-ssl-inc=$SSL_SHIM/include --with-ssl-lib=$SSL_LIBDIR
--with-temp-dir=$TMPDIR   # 关键: configure 的 --with-temp-dir 会覆盖 TMPDIR 变量, 默认 /tmp 只读
--with-gd-inc=$GD/include --with-gd-lib=$GD/lib
--enable-libtap           # 启用 C 单元测试 (上游默认 no)
--with-nagios-user=file_manager --with-nagios-group=file_manager  # OHOS 无 nagios 用户
--with-command-user=file_manager --with-command-group=file_manager
LDFLAGS="<gd 依赖链全部 -L>"
```

### SSL shim 方案 (conanfile 内实现)
configure 的 SSL 检测逻辑:
- --with-ssl-inc=$OSSLP/include 时命中 $dir/include/openssl/ssl.h 分支 → CFLAGS 加 -I.../include/openssl
- conftest 用 #include <openssl/ssl.h> → 双 openssl 路径拼接失败
- --with-ssl-inc=$SHIM/include (shim 含 include/ssl.h 转发 + include/openssl 符号链接) → 命中 $dir/include/ssl.h 分支 → SSL_INC_PREFIX="" → #include <ssl.h> 经 shim 转发到真实 openssl 头
- SSL 库: conan 静态 libssl.a, configure 只认 libssl.so → shim lib 目录做 .so 符号链接 (静态链接不受影响)

### make install 用户处理
- INSTALL_OPTS=-o user -g grp 无条件生成, OHOS 无 nagios 用户且无 root
- conanfile 用 make 变量覆盖: `make install INSTALL_OPTS= COMMAND_OPTS=` (GNU make 标准特性, 上游 Makefile 打包目标同款用法)
- daemon 在 OHOS 的服务管理: nagios 的 init 脚本/systemd unit 不安装 (make install 不含 install-init), OHOS 上由使用方通过 hdc shell 启动或自行封装 hilog 服务配置

## 构建产物
- bin/: nagios (daemon), nagiostats (统计工具)
- sbin/: 19 个 CGI (status/tac/extinfo/..., statusmap/trends/histogram 依赖 gd)
- share/: stylesheets, html (web 界面静态资源, 供 web 服务器使用)
- CGI 本身是标准 stdio 程序, 无需 web 服务器即可构建/测试 (t/ 测试直接执行 CGI 解析输出)

## 上游测试
- t/ perl 套件: 14 文件 478 断言 (make test → prove)
- t-tap C 单元测试: 9 个 (test_logging/events/checks/commands/downtime/nagios_config/timeperiods/macros/notifications), 6702 断言 (--enable-libtap)
- 全部通过 (本机 arm64 OHOS 原生运行)
- test_each.t 是包装脚本 (需参数指定单测试), 不计入注册测试数

## 鸿蒙特有测试 (test_package)
- nagios --version 输出验证
- nagios -v 配置校验 (validate config) 真实运行 daemon 核心逻辑
- nagiostats -c 状态文件解析

## 构建验证记录 (W3/submit)
- conan create 全绿（G1-G4 + L2/L4/L5，conan-verify PASS，status=published）
- W3 本地 CI 模拟: L0/L1/L2/L5 pass + L1e 负向验证确认测试真实依赖
- test_package 4/4 消费者断言通过（本机 arm64 OHOS 原生运行）
---

**编译结束**: 2026-09-11 14:06
**最终状态**: published
