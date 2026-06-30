# libdaemon 0.14 — 编译进度

> 档案创建时间: 2026-04-26
> 最后更新: 2026-06-02

## 一、基本信息
| 项目 | 值 |
|------|-----|
| 软件 | libdaemon |
| 版本 | 0.14 |
| 状态 | ✅ success |
| 构建系统 | autotools |
| 源码路径 | http://0pointer.de/lennart/projects/libdaemon/libdaemon-0.14.tar.gz |

## 二、编译过程

### Phase 1: 环境准备
- [x] ohc-run.py init-build 完成，源码下载解压

### Phase 2: 编译
- [x] configure --prefix=$DEFAULT_PREFIX 成功（需4个补丁）
- [x] make -j1 编译成功
- [x] make install DESTDIR=$TEST_PREFIX 完成

- [x] make install（不带 DESTDIR）安装到 ~/usr/local 成功

- 已安装: libdaemon.a（38KB 静态库） + libdaemon.so.0.5.0（39KB 动态库） + 7个头文件 + pkgconfig

- 库仅依赖 libc.so（无额外依赖）

- ELF: aarch64, RPATH 正确, 已签名

- testd 示例程序可正常运行（daemon_fork +retval_send 成功退出

返回值0）

- 无自带测试套件（has_tests: false）

### Phase 2.5: 安装验证
- [x] Staging 验证通过（.verify-passed, verdict=PASS）
- [x] G0 clean-verify 通过（补丁自包含性确认）
- [x] 本地安装验证: pkg-config --modversion libdaemon 正常

  可查询到版本 0.14

- 无二进制可执行文件（库-only 产物）

- 已安装文件清单:
  - ~/usr/local/lib/libdaemon.a（38482 字节）
  - ~/usr/local/lib/libdaemon.so → libdaemon.so.0.5.0
  - ~/usr/local/lib/libdaemon.so.0 -> libdaemon.so.0.5.0
  - ~/usr/local/lib/libdaemon.so.0.5.0（39232 字节）
  - ~/usr/local/lib/libdaemon.la
  - ~/usr/local/include/libdaemon/*.h（7个头文件）
  - ~/usr/local/lib/pkgconfig/libdaemon.pc
  - ~/usr/local/var/run/*.pid 目录（运行时创建）

### Phase 4: 预编译包制作
- [x] 打包完成:
  - libdaemon-0.14-ohos-aarch64.tar.gz（336KB）
  - libdaemon-0.14-ohos-aarch64-debug.tar.gz（95KB）

### Phase 5: 功能测试（2026-06-02）
- [x] 编写覆盖 libdaemon 全核心 API 的 C 测试程序（48 项测试）
- [x] 动态链接测试: 48 PASS, 0 WARN, 0 FAIL
- [x] 静态链接测试: 48 PASS, 0 WARN, 0 FAIL
- [x] 自带示例 testd: daemon_fork/retval 正常运行

**功能测试覆盖明细**:

| 模块 | 测试项 | 结果 |
|------|--------|------|
| daemon_ident | ident_from_argv0（路径/无路径） | ✅ PASS |
| daemon_log | log(stderr, LOG_INFO/LOG_WARNING) | ✅ PASS |
| daemon_log | set_verbosity | ✅ PASS |
| daemon_pid_file | create / is_running / remove / after-remove | ✅ PASS |
| daemon_signal | init / done / reset_sigs / unblock_sigs | ✅ PASS |
| daemon_close_all | close_allv / close_all | ✅ PASS |
| daemon_nonblock | set ON / read EAGAIN / set OFF | ✅ PASS |
| daemon_fork+retval | fork+retval_wait(42) | ✅ PASS |
| daemon_exec | exec(/bin/sh) | ✅ PASS |
| API 链接 | 18个函数符号链接完整 | ✅ PASS |
| Feature 宏 | 7个 DAEMON_*_AVAILABLE 官全部为 1 | ✅ PASS |

**结论**: libdaemon 0.14 在 OHOS 上功能完全可用，所有核心 API（fork, pid, signal, log, exec, nonblock, close_all, retval）均正常工作。

## 三、源码修改清单
| 文件 | 原因 | 方式 | 补丁 |
|------|------|------|------|
| config.guess | 添加 HarmonyOS/OHOS 平台识别 | 添加 `*:HarmonyOS:*:*` case | 0001-config.guess.patch |
| config.sub | 添加 linux-ohos 目标支持 | 添加 `linux-ohos*` 和 `-ohos*` | 0002-config.sub.patch |
| configure | 移除 `umask 077`（OHOS SELinux不支持） | 移除 mktemp/mkdir 中的 umask 077 | 0003-configure.patch |
| examples/testd.c | 修复 `sys/unistd.h` → `unistd.h` | OHOS 不提供 sys/unistd.h | 0004-examples-testd.c.patch |

## 四、关键发现与修复

### 2026-06-02 修复

**问题**: G0 clean-verify 失败，报 `/bin/sh: no closing quote`
- **根因**: clean_verify.py 的 regex 解析 YAML 列格式 configure_options 时截取到 `- "--prefix=$DEFAULT_PREFIX"`（缺少闭合引号），拼入 /bin/sh 彽令后导致 toybox sh "no closing quote" 错误
- **修复**: 将 configure_options 从 YAML 列格式改为单行字符串格式 `"--prefix=$DEFAULT_PREFIX"`

**问题**: G4 归档门禁失败，缺少 software/build_system 字段
- **修复**: 在版本级 manifest.yaml 中添加 `software: libdaemon` 和 `build_system: autotools`

## 五、平台适配要点
- PID 文件路径: ~/usr/local/var/run/<ident>.pid（而不是 /var/run，因为 OHOS /var/run 可能受限）
- daemon_log: stderr 模式工作日志正常，syslog 需检查可用性
- daemon_fork: 不会调用 chroot（syscall 未实现），但其他 daemonize 功能正常
- daemon_exec: 可正常 fork+exec 子进程
- SELinux/umask: 移除 umask 077 后 mkdir/mktemp 正常

- `sys/unistd.h` 不存在于 OHOS，需替换为 `unistd.h`

---

**编译结束**: 2026-06-02
**最终状态**: success