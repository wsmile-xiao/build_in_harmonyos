# libtorrent 0.16.17 HarmonyOS 适配记录

## 状态

- issue: 2045
- 分支: `feat/libtorrent-0.16.17-2045`
- 结果: 配方构建、上游测试、打包、消费者测试和 L0/L1/L4/L5 门禁均通过
- 产物: `libtorrent.so.47.0.0`、兼容名称副本、79 个头文件和 `libtorrent.pc`
- 剩余阻塞: 无

## 源码与依赖

本任务适配 Rakshasa/rTorrent 使用的 libtorrent，不是
`arvidn/libtorrent`（libtorrent-rasterbar）。源码使用官方 `v0.16.17` tag archive：

- URL: `https://github.com/rakshasa/libtorrent/archive/refs/tags/v0.16.17.tar.gz`
- SHA-256: `14b502a00f0eeebee9293f7c6cf0d3ec356a5a3792c0d320290edd19c7a65d0b`

W0 已确认以下 Conan recipe 可从 `ohpcd` 获取，无需拆分新的依赖适配：

- 运行依赖: `curl/8.15.0`、`openssl/3.5.6.1`、`zlib/1.3.1.1`
- 测试依赖: `cppunit/1.15.1`
- 构建依赖: `automake/1.18`、`libtool/2.5.4`、`m4/1.4.19`

上游 Autotools 配置强制 C++20，配方将 `compiler.cppstd` 设为 20。依赖包可按
Conan cppstd 兼容规则复用仓库中的 C++17 二进制，libtorrent 自身仍使用 C++20。

## 构建适配

- tag archive 仅包含 `configure.ac`/`Makefile.am`，构建前运行 `autoreconf`。
- 在 OHOS 上显式传入 `aarch64-unknown-linux-ohos` build/host triplet。
- 启用 pthread 8 MiB 栈，关闭不可稳定探测的可选 execinfo。
- 为 HMDFS 上不能直接执行的 Automake/Libtool 脚本显式调用 bash。
- configure 阶段通过 C/C++ 编译器 wrapper 为 `conftest` ELF 注入依赖 RPATH 并自签，
  兼容要求目标可执行文件签名的 CI Worker；配置结束后校验签名事件，缺失时失败闭合。
- 为上游测试注入 Conan 依赖的 `LD_LIBRARY_PATH`。
- 使用 `-j1` 规避 HMDFS 不支持 GNU Make jobserver FIFO。

补丁职责：

1. `0001-clang15-structured-binding-capture.patch`：避免设备 Clang 15 捕获结构化绑定。
2. `0002-libcxx15-heap-algorithms.patch`：改用 libc++ 15 支持的迭代器 heap API。
3. `0003-cppunit-chrono-assertion.patch`：避免 CppUnit 1.15.1 格式化 chrono duration。
4. `0004-writable-test-directory.patch`：使用可写测试目录，并仅豁免 HMDFS 无法执行的
   symlink 专用用例；其他目录事件用例仍正常执行。

## 验证结果

最终验证环境：HarmonyOS aarch64、clang 15.0.4、Python 3.12.9、Conan 2.29.1。
正式任务通过 `device1-shadow-runner.zsh` 的单包设备锁排队执行。

- 验证提交: `75dd31c780e00f2e48e7245c031ea75fa8d7c30b`
- shadow run: `/storage/Users/currentUser/ohpc-ci-shadow/runs/75dd31c780e0-20260812T092655Z-run-38715`
- 输入归档 SHA-256: `795774e0259a1fd6c502e80617d8f118a55a1f62284340cd16f01fe0f3cdf98d`
- 完成状态: `status=pass`、`setup_rc=0`、`build_rc=0`
- 构建日志 SHA-256: `9d3042ba2769d8b2a08f06105829a51a281a49272dadf6ab4c02e0a1f5f5587f`
- configure 探测: 24 个 `conftest` ELF 在最终链接后完成 RPATH 注入、自签和执行权限恢复
- `make check`: 7/7 测试程序通过；151 个 CppUnit 用例实际通过，1 个用例按平台能力豁免
- 消费者测试: 构建并执行，验证 bencode map/list 往返、值读取和 SHA-1
- 负向测试: 移走 `lib/` 和 `include/` 后消费者测试按预期失败
- 构建汇总: Total 1，Success 1，Failed 0，Pass rate 100.0%
- 门禁: L0 pass，L1 pass，L2 skip（库包无 `bin/`），L4 pass，L5 pass

设备 HMDFS 不支持 symlink。唯一专门验证 symlink 回调路径的上游用例按能力宏返回；
同一测试程序内其余 27 个用例仍执行并通过。该限制不影响打包的共享库，因为 libtool
安装阶段使用文件副本生成 `libtorrent.so` 和 `libtorrent.so.47` 兼容名称。

## 知识库使用与草稿

- `E011`：用于识别 HMDFS 临时目录权限和 Autotools 生成阶段限制。
- `E064`：用于识别 Autotools `conftest` 在 HarmonyOS 上无法执行导致的配置误判。
- `E077`：用于保证 `conftest` ELF 在最终链接/RPATH 修改后完成签名并恢复执行权限。
- `E274`：用于检查共享库开发名称、SONAME 名称与真实版本化 ELF 的打包闭包。
- `E316`：用于选择普通文件副本补齐 SONAME 实体，避免依赖 HMDFS 不支持的 symlink。
- `knowledge/drafts/DRAFT-2045.{kv,md}`：记录 `E274` 的
  symlink-first 建议在 HMDFS 上的适用边界，并以 libtorrent 真机结果补充能力感知的
  SONAME 兼容名实体化方案。该草稿与本库直接相关，不修改正式图谱或 `index.tsv`。

## Runner 基础设施处理

首次 shadow 执行虽然构建和门禁通过，但 runner 返回 125。根因位于真机共享脚本
`$HOME/ohpc-ci-shadow/device1-shadow-runner.zsh` 的成功返回码记录逻辑：

```sh
BUILD_RC=125
run_ci_script "$BUILD_FILE" > "$BUILD_LOG" 2>&1 || BUILD_RC=$?
```

当 `build_and_test.sh` 成功返回 0 时，`||` 右侧不执行，`BUILD_RC` 保持 125。
经授权后在真机共享基础设施中改为成功分支显式赋值：

```sh
if run_ci_script "$BUILD_FILE" > "$BUILD_LOG" 2>&1; then
    BUILD_RC=0
else
    BUILD_RC=$?
fi
```

修复前 runner 已备份为
`device1-shadow-runner.zsh.bak-20260812T1400-buildrc`，修复后 runner SHA-256 为
`81ef3da1f250a3cbd8af501686ddcfb00de6e3eefd9f781118b962ef2f42d2f6`。随后重新执行
preflight 和正式 shadow CI，最终获得退出码 0 及 `complete status=pass`。共享 runner
修改未加入本库提交或 PR。
