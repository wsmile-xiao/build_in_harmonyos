# afpfs-ng 0.8.1 适配笔记

## 构建系统
- autotools (configure + make)
- 源码: https://downloads.sourceforge.net/project/afpfs-ng/afpfs-ng/0.8.1/afpfs-ng-0.8.1.tar.bz2

## 平台适配修改

### 1. config.guess / config.sub (E007)
- 使用 patch-autotools-ohos.pl 脚本打补丁
- config.guess: 添加 HarmonyOS 系统识别 (echo+exit 模式，非 GUESS 模式)
- config.sub: 添加 linux-ohos 到 OS 列表和 case 分支

### 2. configure/config.status 临时目录权限 (E002/HMDFS)
- config.guess 和 config.status 使用 `umask 077 && mktemp -d` 创建临时目录
- HMDFS 上 umask 077 创建的目录无法写入文件
- 修复: 将 umask 改为 022 并在创建后 chmod 755

### 3. lib/afp.c:264 - 指针类型修复
- `afp_closedt(server, volume->dtrefnum)` → `afp_closedt(server, &volume->dtrefnum)`
- 原因: afp_closedt 参数为 `unsigned short *`，需传地址

### 4. include/libafpclient.h - 缺少 sys/select.h
- 添加 `#include <sys/select.h>`，解决 `fd_set` 未定义错误

### 5. lib/loop.c:90 - void* 函数返回值
- `if (ending) return;` → `if (ending) return NULL;`
- 函数末尾添加 `return NULL;`

### 6. lib/proto_desktop.c:183 - 指针解引用
- `htons(refnum)` → `htons(*refnum)`
- 原因: refnum 参数为 `unsigned short *`，htons 需要 uint16_t 值

### 7. cmdline/cmdline_afp.c - getpass 替代
- HarmonyOS 无 getpass() 和 termios.h
- 添加 getpass 替代函数 (fgets-based, 无 echo 控制)

### 8. cmdline/cmdline_main.c - readline/termios 替代
- HarmonyOS 无 readline 和 termios
- 移除 readline/readline.h, readline/history.h, termios.h 头文件
- 添加 readline 函数 stub: readline(), add_history(), rl_set_signals() 等
- 移除依赖 readline 的函数: filename_completion(), initialize_readline(), command_generator()
- 添加 termios 结构体 stub

### 9. cmdline/cmdline_afp.h - extern 声明修复
- `int full_url;` → `extern int full_url;`
- 原因: 头文件中定义变量导致重复符号

### 10. cmdline/Makefile.am + Makefile.in - 移除 readline/ncurses 链接
- `afpcmd_LDADD = -lreadline -lncurses ...` → `afpcmd_LDADD = ...`
- 原因: HarmonyOS 无 readline 和 ncurses 库

## configure 参数
- `--prefix=$DEFAULT_PREFIX --disable-fuse`
- --disable-fuse 是必需的，因为 HarmonyOS 无 FUSE 支持
- gcrypt 和 gmp 可选依赖未找到，configure 自动禁用

## 构建产物
- libafpclient.so.0.0.0 (共享库)
- libafpclient.a (静态库)
- afpcmd (命令行客户端工具)
- afpgetstatus (状态查询工具)

## 测试结果
- make: 成功
- make install: 成功
- make check: 无测试套件 (Nothing to be done for 'check')
- afpgetstatus: 正常显示用法信息
---

**编译结束**: 2026-07-17 12:46
**最终状态**: published

## 段错误修复（2026-08-07）

### 问题
afpcmd 和 afpgetstatus（带参数）运行时段错误（exit 139），原因：
1. HarmonyOS 用户 UID（如 20001006）不在 /etc/passwd 中，getpwuid() 返回 NULL
2. 代码未判空直接解引用 passwd->pw_name / memcpy from NULL
3. afpgetstatus 调用 libafpclient_register(NULL)，循环线程访问 libafpclient->loop_started 时空指针解引用

### 修复
- 0013: lib/afp.c — afp_server_init() 中 getpwuid 返回 NULL 时跳过 memcpy（s 已 memset 清零）
- 0014: cmdline/cmdline_afp.c — cmdline_afp_setup() 中 getpwuid 返回 NULL 时跳过 strncpy（url.username 默认空）
- 0015: cmdline/getstatus.c — libafpclient_register(NULL) 替换为注册最小 struct（函数指针全 NULL，log_for_client 指向 stdout_log_for_client）

### 验证
- conan create 构建成功（15 个 patch 全部应用）
- afpcmd: exit 0（修复前 exit 139）
- afpgetstatus 127.0.0.1: exit 255 连接拒绝（修复前 exit 139）
- CI build_and_test.sh 全流程通过（L0/L1/L1e/L2/L5）
