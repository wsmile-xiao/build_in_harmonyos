# 编译笔记 — libcoro 6.513

## 软件概述
libcoro 是 Marc Lehmann 开发的轻量级 C 协程库，提供协程上下文切换功能。
版本 6.513 来自 Perl Coro 模块的 CPAN BackPan 历史归档（当前 CPAN 仅有 Coro-6.57）。

## 编译过程

### 1. 下载源码
- URL: https://backpan.cpan.org/modules/by-authors/id/M/ML/MLEHMANN/Coro-6.513.tar.gz
- SHA256: 3448b99c62142d1b204bf87269600d53328daf9de5a68cc995bd056a04f2696d
- 来源: CPAN BackPan（当前 CPAN 镜像已无此版本，需从历史归档下载）
- SSL: 需禁用 SSL 证书验证（本地 SSL 证书不完整）

### 2. 构建系统识别
- init-build 自动识别为 "perl"（实际应为 makefile）
- Coro 是 Perl 模块分布，包含 Makefile.PL
- 独立 C 库 libcoro 无 autotools/configure 脚本
- 采用手动编译（模式 B），创建自定义 Makefile

### 3. 后端选择
- CORO_ASM: aarch64 汇编支持不完整（上游标注 experimental）
- CORO_UCONTEXT: ❌ 不可用（musl/OHOS 缺少 getcontext/makecontext/swapcontext）
- CORO_PTHREAD: ❌ 不可用（musl/OHOS 缺少 pthread_cancel）
- CORO_SJLJ: ✅ 可用（sigsetjmp/siglongjmp + sigaltstack 正常工作）
- **最终选择: CORO_SJLJ**（最可靠且平台兼容性好）

### 4. 源码修改（PSCAN-MUSL-001 修复）
- 文件: Coro/libcoro/coro.c (line 598)
- 修改: pthread_cancel → #ifdef __OHOS__ 使用 cancel_flag + pthread_join
- 文件: Coro/libcoro/coro.h (CORO_PTHREAD coro_context struct)
- 修改: 增加 cancel_flag 字段（__OHOS__ 下）
- 两者均在 CORO_PTHREAD 条件块内，CORO_SJLJ 编译不受影响

### 5. 编译命令
```bash
cd $BUILD_SRC_DIR
make CC=clang CFLAGS="-fPIC -O2 -DCORO_SJLJ -DHAVE_SETJMP_H -DHAVE_SIGALTSTACK"
make install DESTDIR=$TEST_PREFIX PREFIX=$DEFAULT_PREFIX
make install-local PREFIX=$DEFAULT_PREFIX
```

### 6. 测试验证
- 自编写 test_libcoro.c 验证协程切换功能
- 测试结果: PASSED（5 次协程切换均正确完成）
- 上游 Perl 模块测试套件: 跳过（需要 Perl + 众多 Perl 依赖）

### 7. 安装产物
- libcoro.a (静态库, 5638 bytes)
- libcoro.so.6.513 (动态库, 22848 bytes)
- libcoro.so → libcoro.so.6.513
- libcoro.so.6 → libcoro.so.6.513
- coro.h (头文件, 15562 bytes)
- libcoro.pc (pkg-config 文件)

## 编译结束
**最终状态**: published
**日期**: 2026-06-01
---

**编译结束**: 2026-06-01 11:27
**最终状态**: published

## 综合功能测试 (2026-06-01)

### 测试结果: 16项全部通过 ✅

| # | 测试名称 | 结果 | 说明 |
|---|---------|------|------|
| 1 | 基本协程切换 | ✅ | 5次 ping-pong, counter=5 |
| 2 | 参数传递 | ✅ | 字符串参数正确传递 |
| 3 | 多协程交替 | ✅ | A→B→main 3协程序列正确 |
| 4 | 栈分配/释放 | ✅ | 多种栈大小正常分配/释放/重分配 |
| 5 | 嵌套切换链 | ✅ | 4协程深度切换链, result=630 |
| 6 | 状态保持 | ✅ | 局部变量跨切换持久保持 |
| 7 | 生产者-消费者 | ✅ | 10轮数据传递正确 |
| 8 | 大栈深递归 | ✅ | 65536栈单位, 50层递归 |
| 9 | 空 context | ✅ | 全零参数创建成功 |
| 10 | 资源回收 | ✅ | 200次循环无崩溃 |
| 11 | 信号兼容 | ✅ | sigaltstack 与协程共存 |
| 12 | API符号 | ✅ | 核心函数地址有效 |
| 13 | 栈错误处理 | ✅ | 极大请求优雅处理 |
| 14 | pkg-config | ✅ | 关键字段正确 |
| 15 | 多独立协程 | ✅ | 5个隔离协程独立运行 |
| 16 | 高频切换 | ✅ | 1000次切换正确完成 |

### 发现的问题（全部已修复 ✅）

1. **pkg-config 路径参数缺失** (🟡 中): Makefile 中 `${libdir}` 被 Make 解释为空变量 → 修复为 `$${libdir}` 转义， → 重新安装和打包 → pkg-config 现正确输出 `Libs: -L${libdir} -lcoro` 和 `Cflags: -I${includedir} -DCORO_SJLJ` ✅
2. **manifest.yaml guard 标记** (🟢 低): `guard: 'pending'` → 已更新为 `guard: '__OHOS__'` ✅
3. **预编译包 .so strip 羅澄清): `.symtab` 保留是 `--strip-debug` 标准行为（仅移除 DWARF debug sections），`--strip-all` 会额外移除 .symtab 但需要保留 .dynsym 用于动态链接。 当前 `--strip-debug` 方式对库文件是合理的 ✅

4. 预编译包已重新打包（ohc-run.py package），包含修复后的 pkg-config 和正确的 strip/sign 流程 ✅

### 上库评估
**✅ 符合上库要求**: 编译状态 published, 16项功能测试全部通过, pkg-config 修复完毕, 预编译包重新打包完成, ELF签名和代码签名完整。 所有已知问题均已修复。
