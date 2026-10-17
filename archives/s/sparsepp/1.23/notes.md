# sparsepp 1.23 适配记录

## 包类型与范围

- 类型：`header-library`，不是动态库、静态库或工具包。
- 依赖：无；只使用 C++ 标准库。
- 上游构建入口：`tests/makefile`。
- 不添加软件级 `commands.json`：包不安装命令行程序。
- 应用补丁：`0001-use-writable-test-temp-path-on-ohos.patch`，通过运行时
  `TMPDIR` 将上游测试的临时目录从固定的 `/tmp/intio` 改为可配置目录。

## 来源校验

- 官方仓库：[greg7mdp/sparsepp](https://github.com/greg7mdp/sparsepp)
- 标签：`1.23`
- 下载 URL：`https://github.com/greg7mdp/sparsepp/archive/refs/tags/1.23.tar.gz`
- SHA256：`3dca5bb8744e86d395f3d58846f4ac1fd9c0a3c261611750324f54a9d5268028`

## 上游测试计数口径

上游 CI 使用 `cd tests && make CXX=$COMPILER && make test`。其中默认
`make` 构建 `spp_test` 和 `spp_relative_include_test`，`make test` 只运行
`spp_test`。`spp_relative_include_test` 是编译检查，不是运行用例；`make all`
中的其他程序也不属于官方测试入口。

`tests/spp_test.cc` 的活动注册为 19 个 `TEST`，以及 264 个类型化实例：
`HashtableIntTest` 为 6×3，`HashtableStringTest` 为 1×3，
`HashtableAllTest` 为 27×9，合计 283 个真实注册 cases。`HashMunging` 位于
禁用的 `#if 0` 区域，不计入统计。

## 验证状态

本地 macOS 基线已执行上游 `make -C tests CXX=clang++ -j1` 和
`make -C tests test -j1`，结果为 `PASS`；直接以源码头文件编译并运行
`test_package/test.cpp` 也输出 `sparsepp consumer test passed`。这些结果只证明
macOS 基线，不能替代 HarmonyOS PC 设备验证。

最终代码提交：`f2e1ad1cbdcee7202409d2bbfe4dcf0176c75e3b`，设备远端
worktree 已核对为同一 SHA。设备执行的 Conan create 完成包构建、上游测试、
relative-include 编译检查和 test_package：

- 上游活动注册：283 个真实 cases（19 个普通 TEST 加 264 个类型化实例），
  `make test` 实际 283/283 PASS；
- `spp_relative_include_test`：1 个 compile-only 检查，PASS，不计入运行 cases；
- Conan consumer：1/1 PASS，程序内 12 个显式检查；
- 设备日志：`$HOME/tmp/import-deps-100-odd-sparsepp-create-r7.log`。

首次上游测试曾因固定路径 `/tmp/intio` 报权限错误；设备 `/tmp` 只读是已验证
的环境限制，补丁改用运行时 `TMPDIR` 后通过。构建仍打印 `jobserver mkfifo ...
Operation not permitted` 警告，但退出码为 0，未将警告写成失败。
