# libbf 2021.03.27 — OpenHarmony 编译记录

## 基本信息
- 软件: libbf (Fabrice Bellard 任意精度浮点小库)
- 版本: 2021.03.27
- 构建系统: makefile (库本体直接编译 + quickjs Makefile 构建测试运行器)
- 目标: ohos-aarch64
- 上游: https://bellard.org/libbf/
- 许可: MIT
- 依赖: 无
- 产物: 静态库 libbf.a + 公开头文件 libbf.h (libbf.h 自包含, 仅依赖 stddef.h/stdint.h)

## 源码来源说明
- 独立发布包 `libbf-2021-03-27.tar.gz` / `libbf-2021.03.27.tar.gz` 已从
  bellard.org 下架 (2026-09-16 实测均 HTTP 404, 站内仅保留最新版)。
- 采用同作者、同日期的 `quickjs-2021-03-27.tar.xz` (HTTP 200, 实测下载,
  sha256 `a45bface...fe7fe1a`), 其内 `libbf.c` / `libbf.h` / `cutils.c` /
  `cutils.h` / `list.h` 即该日期的 libbf (包内 `VERSION=2021-03-27`;
  GaloisInc/libBF-hs 亦以 `libbf-quickjs-2021-03-27` 为该版本快照名)。

## 编译指导
- 库本体不走上游 Makefile (无 install 目标): 以 Conan 配置的 CC 直接编译
  `libbf.c` + `cutils.c` (`-O2 -fPIC`), `llvm-ar rcs` 生成 `libbf.a`。
- 测试运行器 `qjs` 以上游 Makefile 构建 (`make -j1 qjs CC=.. AR=..
  HOST_CC=.. CONFIG_BIGNUM=y`), 产物仅用于 build() 内上游测试, 不打包。
- CC/AR/HOST_CC 取自 Conan `tools.build:compiler_executables`, OHOS 下缺失直接报错。
- make -j1 (R9)。

## 补丁清单
- `0001-qjsc-use-tmpdir.patch`: qjsc 生成可执行文件时优先使用 TMPDIR,
  回退当前目录, 不再硬编码 `/tmp` (OHOS 下 /tmp 不可写; 与已合入的
  quickjs 2024-01-13 同名补丁同源同构, 2021 版 qjsc.c 上下文逐字一致)。

## 上游测试
- `tests/test_bignum.js`: 上游 BigFloat/BigDecimal 回归测试, 底层由 libbf
  实现 (exp/log/pow/sin/cos/tan/asin/acos/atan/atan2、进制转换、舍入模式)。
- 静态断言点: 126 处 `assert()` + 8 处 `assertThrows()` = 134。
- 执行: `./qjs --bignum tests/test_bignum.js`; 任一断言失败即抛异常,
  qjs 非零退出; 期望值均为文件内字面常量 (如
  `BigFloat.exp(0.2l) === 1.2214027581601698339210719946396742l`), 非空文件
  比对, 不存在静默跳过。
- build() 内真实运行并输出 `HMBS_UPSTREAM_TEST_RESULT` 标记。

## 功能验证
- test_package 以打包产物编译链接 `test_libbf.c`, 运行加/乘/除/开方/
  十进制解析 5 项真实断言 (TAP 风格输出, 失败非零退出), 输出
  `HMBS_TEST_PACKAGE_RESULT` 标记 (discovered=5)。

## 已知限制
- 仅提供静态库 (上游无共享库构建规则)。
- `bfbench` / `bftest` (需 MPFR/mpdecimal) 未构建, 非库本体功能。

## 真机适配记录 (2026-09-17)
- 预检 runner 上 profile 钉死的 `/data/service/hnp/bin/clang` 不存在
  (`/bin/sh: ... inaccessible or not found`, Error 127)。
- 第一轮修复 (isfile+X_OK 门控 + basename 回退) 未生效: 失败预检仍以
  绝对路径调用 clang, 说明该路径在配方进程视角存在但 shell 无法执行,
  文件存在检查不可靠。
- 第二轮修复 (本轮): 改用真实执行探测 `<cand> --version` (subprocess,
  软失败) 决定是否保留 conf 钉死的绝对路径; 探测通过则零改动直接用,
  失败则丢弃并取 basename (+备选短名) 走 PATH, which 未命中时返回短名
  由 `self.run(env="conanbuild")` 时的 hmbs PATH 解析; make 优先用
  `HMBS_MAKE`, 不可用时回退 `make`; test 侧同理对 `CC` 做执行探测,
  `test_libbf.sh` 内对含 `/` 但不可执行的 `CC` 再做一次 basename
  回退。测试口径不变 (上游 134 + test_package 5)。

## 真机适配记录 (2026-09-17 第二轮)
- 现象: test_package `Signal 11 (core dumped)` + `Error 139`,
  `HMBS_TEST_PACKAGE_RESULT passed:false discovered:5 passedCount:0`,
  伴随 `can't create temporary file /tmp/sh*.tmp: Read-only file system`。
- 根因 1 (段错误): `test_libbf.c` 以 `bf_context_init(&ctx, NULL, NULL)`
  初始化; libbf 的 `bf_context_init` 原样保存指针 (无默认分配器),
  首次 `bf_set_si` -> `bf_resize` -> `bf_realloc` 即调用空函数指针。
  上游 `bftest.c` 均用 `my_bf_realloc` (realloc 包装) 初始化, 从不传 NULL。
- 根因 2 (只读 /tmp): `test_libbf.sh` 含 `$(basename ...)` /
  `$(command -v ...)` 命令替换, 该 shell 每处替换需在 /tmp 建临时文件,
  只读下直接失败; 且 test() 未像 build() 那样注入可写 TMPDIR。
- 修复: test_libbf.c 新增 `libbf_realloc` (realloc 包装, 与上游同构) 并传入
  `bf_context_init`; test_libbf.sh 重写为纯 POSIX sh (`set -eu`,
  无 `$()`/反引号/管道, `${CC_BIN##*/}` 截 basename, TMPDIR/TMP/TEMP
  缺省回退到当前目录并 export); test() 以 `Environment` 注入
  `build_folder/_tmp` 为 TMPDIR/TMP/TEMP, 改用 `/bin/sh test_libbf.sh`,
  测试口径不变 (上游 134 + test_package 5)。
