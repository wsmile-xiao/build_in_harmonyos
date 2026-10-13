# phyx 1.3.2 适配笔记

## 编译环境

- 构建系统：Autotools + Make
- 编译日期：2026-10-12
- 编译器：HarmonyOS clang/clang++ 15
- 状态：built

## 编译步骤

Conan 下载并校验上游 `v1.3.2` 标签源码，应用单一数学后端补丁，仅向
Autoconf 注入 Armadillo 与 NLopt 的搜索目录，依次执行 `autoreconf -fi`、
`configure`、单线程 `make` 和上游完整 `make check`。最后打包 47 个 CLI、
man pages 与官方测试数据。配置前从固定的 `automake/1.18` 构建依赖刷新
`config.sub`/`config.guess`，使历史快照正确识别 `aarch64-unknown-linux-ohos`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 原始链接命令缺少 `_FortranA*` 符号 | Makefile 硬编码 reference `-llapack -lblas`，该静态实现需要 Flang 运行时 | 不引入无关的 reference 实现，改用 configure 已确认的 Armadillo 提供者 |
| 2 | 追加 FortranRuntime 后虽能链接，程序却同时携带静态 BLAS/LAPACK 符号并依赖 Armadillo→OpenBLAS | 两套数学后端混入同一进程，符号解析与数值实现取决于链接/装载顺序 | `CPP_LIBS=@LIBS@ -lpthread` 并保留已探测的 NLopt；构建期检查 NEEDED 和已定义符号，阻止双提供者回归 |
| 3 | 上游测试遗漏两个已安装 CLI | `run_tests.py` 报告 `pxtcol`、`pxtcomb` 为无测试程序 | 在 `test_package` 中加入真实树文件的确定性功能测试 |
| 4 | GNU `config.guess` 不识别 `uname -s=HarmonyOS` | 上游与 Automake 1.18 的辅助脚本都没有 HarmonyOS 分支 | 从固定 Automake 构建依赖刷新辅助脚本，再为 `config.guess` 注入 HarmonyOS→`aarch64-unknown-linux-ohos` 原生识别；不传 `--host/--build`，保留 configure 的运行探针 |
| 5 | CI 的 `config.status` 无法创建 `conf*/subs1.awk` | Autoconf `AS_TMPDIR` 以 `umask 077` 创建临时目录，HMDFS 沙箱映射属主后当前构建身份失去写权限（E011） | 仅在 OHOS 构建中、`autoreconf` 生成 `configure` 后把 `umask 077` 调整为 `umask 002`；真机同入口 W3 验证 `config.status`、构建、上游测试与消费者测试全部通过 |

## 源码修改

- `0001-use-configured-math-provider.patch`：以 Autoconf 的 `@LIBS@` 替代硬编码
  reference BLAS/LAPACK 链接列表，保留条件式 NLopt，确保数学后端唯一。

## 依赖版本

- `armadillo/12.8.4`（传递提供 OpenBLAS 后端）
- `nlopt/2.11.0`
- `automake/1.18`（构建工具）

## 验证结果

```text
上游：执行 100 项；95 项精确匹配，5 项随机比较由上游 runner 标记为 anticipated failures，命令成功退出
消费者：pxlssq、pxtcol、pxtcomb 与 HarmonyOS pxseqgen 运行时闭包全部通过
结构：ELF 无 reference BLAS/LAPACK/FortranRuntime 动态依赖，且未定义嵌入 dgemm_/dgesv_/dgetrf_
```

路径 B 三臂链接实验还在同一组真机目标文件上验证：原始 `-llapack -lblas`
链接线以 `_FortranA*` 未定义失败；追加 `FortranRuntime/FortranDecimal` 后虽链接成功，
但程序静态定义 `dgemm_`、`dgesv_`、`dgetrf_`，且 Armadillo 动态依赖
`libopenblas.so.0`；仅消费 `@LIBS@` 的修复线同时通过链接、ELF、符号表和运行检查。
脱敏命令与结果见 `reports/path-b-evidence.md`，仓库外原始日志 SHA256 为
`5a20094e3977b9726db529253af8f11453e6dfc859ce833f15da5bf9e5a5c5c5`。

针对远端 CI 的 HMDFS 权限回归，最终配方又以完整 `build_and_test.sh` 在真机执行；
W3 退出码为 0，日志 SHA256 为
`eccdf65e1d44cdd84b320d1238cb876928661eab3bb387a1901de10b9b5ecf05`，Conan
recipe revision 为 `8c3f7476b102ca2185ea9a09dfbde65d`。

## 注意事项

`phyx` 是应用包，`commands.json` 位于软件级目录。运行期共享库路径由 Conan
`VirtualRunEnv` 和配方的 `runenv_info` 从实际依赖包导出，未写死 Conan 缓存路径。
---

**编译结束**: 2026-10-12 12:07
**最终状态**: built
