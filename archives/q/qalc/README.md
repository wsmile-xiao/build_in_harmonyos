# qalc

`qalc` 是 Qalculate! 的命令行计算器：任意精度与符号计算、单位换算、变量/函数/矩阵运算，支持交互式（readline）与非交互式（单表达式、`-f/--file` 脚本、`--test-file` 批处理）两种用法。上游项目主页为 [qalculate.github.io](https://qalculate.github.io/)，GPL-2.0-or-later。

## 包的构成

qalc CLI 与 libqalculate 库同源：上游唯一 release tarball 就是 `libqalculate-5.11.0.tar.gz`（Debian/Ubuntu 的 `qalculate` 二进制包同样产自该源码包）。本包以任务名 `qalc` 独立交付，一次构建同时打包：

- `bin/qalc` — 命令行计算器
- `lib/libqalculate.so` — 同源构建的计算库（供后续消费者直接链接）
- `share/qalculate/` — units/functions/variables/elements 等运行时定义数据（XML）
- 依赖：`gmp/6.3.0`、`mpfr/4.2.2`、`libxml2/2.15.3`、`readline/8.3`（制品仓均已发布）；`libcurl`/`icu` 为可选项且未发布，configure 传 `--without-libcurl --without-icu` 关闭

## OHOS 适配要点

- **config.guess**：补丁 0001 增加 `aarch64:HarmonyOS` → `aarch64-unknown-linux-gnu` 映射（与已合入的 libqalculate 5.8.2-r0 同法）
- **configure**：补丁 0002 去掉 `umask 077 && mktemp/mkdir` 临时目录守卫（HMDFS 限制）
- **pthread 取消**：补丁 0003 把 `pthread_cancel/pthread_setcancelstate/pthread_setcanceltype` 用 `HAVE_PTHREAD_*` 宏守卫；OHOS musl 不提供该 API，宏由 build() 内 feature-detection 生成（探测加 `-Werror=implicit-function-declaration` 防隐式声明误判）。无 `__OHOS__` 平台宏（R8/PF5）
- **intltool 已消失**：5.11.0 上游改用 GNU gettext `msgfmt --xml` 生成 data XML；不再需要 XML::Parser/intltool-merge shim
- **依赖注入**：不用 AutotoolsDeps/VirtualRunEnv（conftest 污染 + lld 劫持坑），`-I/-L` 经 AutotoolsToolchain 环境手动注入；build() 内显式注入 `LD_LIBRARY_PATH`（SDK llvm/lib 排在 conan 依赖之前）与 `PKG_CONFIG_PATH`
- **.la 修复**：依赖包 `.la` 的 `libdir='//lib'` 跨包全局映射修复（E236 同族）

## 测试

上游测试套件由 `qalc --test-file` 原生执行器驱动：`tests/` 17 个 batch 文件共 688 个 input→expected 用例（`stats.batch` 依赖 `tests/*.csv`）。`test_package` 将上游测试文件逐字节拷贝后在真实鸿蒙 CI worker 全量复跑；另加鸿蒙特有 7 项：A1-A4（ELF64/AArch64、musl interp、DT_NEEDED 自洽、pthread 守卫编入）与 H1-H3（设备端定义加载与单位换算、表达式退出码、musl libm 三角函数）。
