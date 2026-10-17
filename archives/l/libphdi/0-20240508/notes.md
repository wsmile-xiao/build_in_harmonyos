# libphdi 0-20240508 适配笔记

## 当前状态

- 状态：built（OpenDesk OHOS 真机 `ci/conan/build_and_test.sh` 全通过）
- 分支：`feat/libphdi-0-20240508`
- 上游版本：`20240508`
- 上游测试：`make -j1 check`
- 适配路径：路径 A（基础适配）

## 源码闭包

发布包自带以下本地 libyal 组件：

`libbfio, libcdata, libcdirectory, libcerror, libcfile, libclocale, libcnotify, libcpath, libcsplit, libcthreads, libfcache, libfdata, libfguid, libfvalue, libuna`

同时自带 `configure`、`aclocal.m4`、`config.guess`、`config.sub`、
`Makefile.in`。配方在 `build()` 开始时检查这些路径，缺失即终止，不调用
`synclibs.sh`，不把未注册依赖混入当前 PR。

## OHOS 构建处理

- 使用发布包自带 Autotools 生成物，不执行 autoreconf。
- OHOS 下显式传入 `--build=aarch64-unknown-linux-ohos --host=aarch64-unknown-linux-ohos`。
- 发布包自带的 `config.sub` 尚未收录 OHOS；配方在 OHOS 构建前仅追加
  `ohos*` OS 和 `linux-ohos*` kernel-OS 两个识别分支，不改变其他平台。
- 通过 `CONFIG_SHELL` 调用 `configure`，并让 automake 通过
  `LOG_COMPILER` 启动 shell runner。
- 构建期将 Autoconf 的 `umask 077` 改为 `022`，保证 HMDFS 临时目录可写。
- 将 libtool 测试包装脚本解析到 `.libs` 下的真实 ELF，并注入库目录到
  `LD_LIBRARY_PATH`；不修改上游测试源文件和断言。
- 上游测试的 `HOME` 指向构建目录内的临时 HOME。

## 测试

上游 `tests/Makefile.am` 注册：

- `19` 个库级 C 测试程序；
- `0` 个工具级 C 测试程序；
- `1` 个集成 shell runner；
- 总计 `19` 个 `check_PROGRAMS`，runner 为：`test_library.sh, test_phdiinfo.sh`。

新增消费者测试：

- `test_libphdi.c`：版本、签名、codepage、错误路径和对象生命周期；
- `test_ohos.c`：`__OHOS__` 目标、非 `/tmp` 的 `TMPDIR`、临时文件读写清理。

## 待补结果

OpenDesk 真机执行完成后，将上游 PASS/SKIP/FAIL 数量、消费者断言数量和
实际构建命令写入 `manifest.yaml` 与 PR 正文。

## OpenDesk 真机验证结果

- CI 结果：`PASS`
- 上游程序级测试：`19/19` 通过，`0` 失败，`0` 跳过
- 上游 runner 级：`1/2` 通过，`0` 失败，`1` 跳过
- 新增消费者测试：`14/14` 断言通过，`0` 失败
- 真机环境：OpenDesk HarmonyOS aarch64，HongMeng Kernel 1.12.0
- 任务 ID：`8333`
- 构建入口：`ci/conan/build_and_test.sh`
