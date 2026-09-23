# datefudge 1.27 HarmonyOS PC 适配笔记

## 范围

datefudge 通过 `LD_PRELOAD` 拦截 `time()`、`gettimeofday()` 和
`clock_gettime(CLOCK_REALTIME)`，让单个进程观察到指定的系统时间。本适配同时打包
`bin/datefudge` 启动脚本和私有的 `lib/datefudge/datefudge.so`。

## 上游与构建

- 官方仓库：`https://salsa.debian.org/debian/datefudge`
- 上游版本：1.27，提交 `99a1e817b95b68cd8fa6f9a141cda05d37db3c91`
- 构建系统：简单 Makefile
- 运行时依赖：musl libc、动态加载接口与 `coreutils/9.10`（GNU `date`）
- 测试依赖：`perl/5.42.2`
- 构建命令：`make -j1 CC=<Conan profile compiler> VERSION=1.27 prefix=/usr`

OHOS Clang 15 编译出的 `datefudge.so` 为 AArch64 ELF64，共导出 `time`、
`gettimeofday`、`clock_gettime` 三个拦截符号，动态依赖仅为 `libc.so`。OHOS musl
已提供所需的 `dlsym(RTLD_NEXT, ...)` 能力，因此不需要平台宏或源码功能降级。

## 适配修改

上游生成脚本原本把构建时的 `libdir` 写成绝对路径。Conan 二进制包下载到另一台机器后，
该路径会指向构建机缓存。补丁 `0001-datefudge.sh.patch` 改为根据启动脚本自身位置解析
`../lib/datefudge/datefudge.so`，同时保留 `DATEFUDGE_LIBDIR` 覆盖入口。该修改是通用的
可重定位修复，不引入平台宏，也不修改任何上游测试文件。

datefudge 的启动器和官方 `make test` 都使用 GNU `date --date` 解析输入时间。OHOS
系统自带的 `date` 不支持该选项，因此配方声明 `coreutils/9.10` 为运行时依赖；在可直接
运行 OHOS AArch64 程序的环境中，上游测试的 `PATH` 会显式优先使用该包中的 GNU
`date`。交叉构建时仍使用构建机的 GNU `date` 执行同一组原始上游测试，不跳过或改写
测试用例。

OHOS worker 的系统 Perl 执行 `localtime(time)` 时不会被该预加载库的 `time()` 符号拦截。
配方因此使用 `test_requires` 引入仓库已发布、动态链接到 `time` 的 `perl/5.42.2`。补丁为
上游 Makefile 增加默认仍为 `perl` 的 `PERL` 变量；可原生运行 OHOS AArch64 程序时，配方
通过该变量传入 Conan 测试依赖中的绝对路径并验证文件存在，防止 shell 静默回退到 worker
自带解释器。测试命令和断言保持不变，Perl 也不会传播给消费者或成为运行时依赖。

## 上游测试清点与结果

上游共有 9 个测试：Makefile `test` 目标包含 2 个 LD_PRELOAD 功能测试，
`debian/tests/control` 注册 7 个 autopkgtest。清点命令与执行结果如下：

```text
make test
Running a simple date test... OK
Running a simple perl localtime() test... OK

debian/tests/control: 7 个 Test-Command
执行结果: 7/7 PASS
```

适配后的消费者测试复现动态时间、静态时间、sleep 时间推进、静态纳秒清零、闰日、默认
`LD_PRELOAD` 和追加预加载库等行为，并直接调用三个被拦截的 libc 时间 API。

## HarmonyOS 特有验证

测试配方在 `os=OHOS` 时执行两项强制检查：测试程序必须由定义 `__OHOS__` 且不定义
glibc 专用 `__GLIBC__` 宏的工具链编译；打包后的预加载库必须是 little-endian ELF64
AArch64（机器号 183）。musl 没有可移植的官方识别宏，因此测试不依赖非标准的
`__MUSL__`。验证结果为 1/1 通过。

## 安全与打包

- `datefudge.so` 必须保持共享库形态，静态化会破坏 `LD_PRELOAD` 的核心功能。
- OHOS 包阶段使用项目工具链的 `llvm-objcopy` 与 `binary-sign-tool` 对共享库签名。
- 包中不包含预编译产物、构建日志或本地状态文件，所有 ELF 均由 `conan create` 重建。
---

**编译结束**: 2026-09-10 10:20
**最终状态**: built
