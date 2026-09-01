# log4c 1.2.4 编译笔记（HarmonyOS PC · 标准 Conan autotools）

## 定位
- C 日志库（log4j 风格），产出 `liblog4c.so`，无 CLI（纯 library package，不需要 commands.json）。
- 上游最后一次发布即 1.2.4（2013-10），SourceForge 官方 tarball。

## 上游构建系统
- autotools（configure + make）。
- `--enable-test` 打开 `tests/` 子目录编译；`make check` 走 `tests/log4c/check-local`：
  顺序执行 test_category → test_layout_r → test_rc → test_big，
  每个程序 `LOG4C_PRIORITY=notice` 运行后 sed 归一化 udata 指针，与 `.ref` 基准 diff。
- expat：configure 默认 `--without-expat`（1.2.4 上游把默认值改成了 no），用内置 yacc/lex 解析 log4crc，无外部依赖。

## 上游正式测试（OHOS AArch64 实测）
在 OHOS AArch64 构建结果上真实执行 `make check`：
- Total 16 / Pass 16 / Fail 0 / Skip 0
  - test_category: 8 个用例（test0..test5 + test00 + test_restore）
  - test_layout_r: 4 个用例
  - test_rc: 3 个用例
  - test_big: 1 个用例
（数量以 .ref 文件中 `=> test #N : passed` 计数为准）

## 关键适配
- 同 lame 3.100 的两处环境适配（本仓已验证模式）：
  1. `configure` 内 `umask 077` → `umask 022`（HMDFS 上 config.status 临时文件 0600 权限问题）；
  2. uname-shim 让 config.guess 返回 Linux/aarch64（设备 uname -s 为 HarmonyOS）。
- `--host/--build` 用 `aarch64-linux-gnu` 名义三元组 + OHOS clang 交叉编译。
- `--enable-test` 必须开，否则 tests/ 不编、`make check` 无测试可跑（L1 要求上游正式测试真实执行）。

## test_package
- 直链 `-llog4c`（非 dlopen），覆盖 init/category/appender/layout/优先级过滤/内容断言/fini，
  24 个确定性断言，详见 `test_package/MANIFEST.yml`。

## 状态
built（CI conan create + make check + test_package 通过）
