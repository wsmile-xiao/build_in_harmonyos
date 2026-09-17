# cxxtools

cxxtools is a collection of general purpose C++ classes (serialization,
binary/JSON/XML RPC, threading, networking, command-line parsing).

## OHOS 适配

- 构建系统为 Autotools；GitHub 标签归档不含生成的 `configure`，需 `autoreconf -fi`
 （tool_requires automake + libtool）。
- `config.guess` 无法识别 HarmonyOS，需显式传递
  `--build=aarch64-unknown-linux-ohos --host=aarch64-unknown-linux-ohos`。
- 默认关闭 demos，仅构建 6 个库与单元测试 runner `test/alltests`。
- SSL 支持来自 Conan 的 openssl/3.5.6.1（AutotoolsDeps 注入）。

## 依赖关系

- 编译依赖：openssl/3.5.6.1
- 构建期依赖：automake/1.18、libtool/2.5.4.1

## 参考资料

- 上游仓库：https://github.com/maekitalo/cxxtools
- 上游主页：http://www.tntnet.org/cxxtools.html
