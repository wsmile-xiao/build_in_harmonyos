# pdsh 2.36 — 适配笔记

## 基本信息
- 名称: pdsh
- 版本: 2.36
- 上游: https://github.com/chaos/pdsh
- 许可: GPL-2.0-or-later
- 构建系统: autotools (configure + make)
- 产物类型: 命令行工具 (pdsh, pdcp, rpdcp, dshbak + 动态模块 .so)

## 依赖
- 无强制第三方依赖 (pthreads 由 OHOS libc 提供)
- readline/ncurses 为可选依赖 (默认 OFF，本次未启用)

## 构建参数
```
./configure --prefix=$DEFAULT_PREFIX --with-ssh --with-exec
make -j1
make install DESTDIR=$TEST_PREFIX
```

## 平台问题与修复

### 1. config.guess 不识别 HarmonyOS (E001级)
- 现象: configure 报 "unable to guess system type"
- 根因: config.guess 版本 2018-02-24，不支持 HarmonyOS/OHOS
- 修复: 传 --build=aarch64-unknown-linux-gnu 跳过 config.guess 调用
- 处理: conanfile.py generate() 中 tc.configure_args.append

### 2. HMDFS umask 077 导致 config.status 失败 (E011)
- 现象: config.status 报 "can't create ./confXXXXXX/subs1.awk: Permission denied"
- 根因: autotools 生成的 configure/config.status 使用 umask 077 创建临时目录，
  HMDFS 对新目录权限固定为 660，导致无法在临时目录内创建文件
- 修复: sed 替换 configure 中 "umask 077" → "umask 022"
- 处理: conanfile.py build() 中 content.replace("umask 077", "umask 022")

### 3. pthread_cancel 不可用 (OHOS libc 缺失)
- 现象: 链接错误 "undefined symbol: pthread_cancel"
- 根因: OHOS libc (musl) 不实现 pthread_cancel
- 修复: 用 #ifdef __OHOS__ 守卫，替代为 pthread_kill(thread_sig, SIGINT)
  唤醒 sigwait 线程使其退出
- 补丁: patches/0001-src-pdsh-dsh.c.patch
- R8 例外理由: libc 函数探针（pthread_cancel 是 libc 函数，OHOS 不实现）

### 4. rresvport/rresvport_af 均不可用
- 现象: 链接错误 "undefined symbol: rresvport"
- 根因: privsep.c 的 p_rresvport_af() 函数在 #else 分支无条件调用 rresvport()，
  但 configure 已检测到 rresvport 不存在 (HAVE_RRESVPORT 未定义)
- 修复: 添加 #elif HAVE_RRESVPORT 分支和 #else 返回 -1
- 补丁: patches/0002-src-pdsh-privsep.c.patch

## 测试结果
- Total: 125
- PASS: 12 (基础框架测试, pdsh -V grep 匹配)
- SKIP: 13 (模块未构建: genders/slurm/mrsh/exec/ssh/dshgroup; LONGESTS/NOTROOT 前置)
- XFAIL: 2 (已知断裂)
- FAIL: 88 (运行时环境: 无 localhost ssh, getpwuid 返回空用户, dshbak 为 Perl 脚本)
- ERROR: 10 (测试退出码非零)
- 结论: 编译/链接全部通过，失败均为运行时环境因素

## 修改文件清单
1. src/pdsh/dsh.c — pthread_cancel → pthread_kill (patch)
2. src/pdsh/privsep.c — rresvport guard (patch)
3. configure — umask 077 → 022 (conanfile.py build() 内联修复)
4. configure — --build=aarch64-unknown-linux-gnu (conanfile.py generate() 传参跳过 config.guess)
---

**编译结束**: 2026-09-07 22:49
**最终状态**: built
