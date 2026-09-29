# passenger 6.1.8 适配笔记

## 上游与源码

- 上游仓库：https://github.com/phusion/passenger
- 版本：`release-6.1.8`
- 源码：`https://github.com/phusion/passenger/archive/refs/tags/release-6.1.8.tar.gz`
- SHA256：`a812771f9d3278519cd0c75f556732cdf4199c12ae972cf9bc172b06c55421cc`
- 许可：MIT

这里没有使用 GitHub release 页面上的二进制/发布包。该资产缺少约 169 个上游
`test/` 文件，无法用来复现上游测试；tag archive 才包含完整的测试树。

## 交付形态

`passenger` 是应用型包，交付的是上游 native-packaging 源码树和六个用户命令：

- `passenger`
- `passenger-config`
- `passenger-install-apache2-module`
- `passenger-install-nginx-module`
- `passenger-memory-stats`
- `passenger-status`

包内布局如下：

- `package/bin/`：命令转发脚本，保持命令名和可执行权限。
- `package/libexec/passenger/`：上游 `bin/`、`src/`、`resources/`、`doc/` 等运行所需目录。
- `package/libexec/passenger/src/ruby_supportlib/phusion_passenger/locations.ini`：
  由配方生成，所有路径都指向当前包实例，避免把构建机路径写进包。
- `package/licenses/LICENSE`：上游 MIT 许可证。

配方不把 `test/`、`buildout/`、下载缓存或编译中间产物放进最终包，只保留运行时需要的目录和空占位目录。这样既能让 Ruby 命令找到支持库，也不会把测试源码和构建缓存带到消费者侧。

## 测试情况

上游测试入口是 `rake test`，包含 OXT、C++、Ruby、Node 和 Integration 五类。按上游测试文件中的声明计数，当前树共有：

| 套件 | 声明数 |
|---|---:|
| OXT | 12 |
| C++ | 846 |
| Ruby | 145 |
| Node | 33 |
| Integration | 85 |
| **合计** | **1121** |

配方在 `build()` 中执行 `rake test:oxt`，真实结果为 `ok:12`、退出码 0。OXT 是当前 HarmonyOS PC 受限环境里可离线运行且不依赖外部服务的套件。

其余套件没有写成通过：

- C++：需要 OpenSSL 和 libcurl 开发头文件/库；已定位真机 Conan 缓存中的依赖并继续验证，结果以队列日志为准。
- Ruby：需要 `cgi`、`logger`、`json`、`rspec`、`rack`、`webrick` 等 gems，当前 Ruby 3.4.5 环境未安装完整 bundle。
- Node：需要 `node_modules`、mocha、should、sinon 等依赖，当前源码树未安装。
- Integration：需要 Apache/NGINX、可写多进程运行环境和端口监听能力，当前受限设备环境未满足。

未执行的上游测试不计入通过数。`test_package/check_passenger.py` 还从消费者角度检查命令转发、包内路径、locations.ini 字段和 Ruby CLI 版本/库路径；最终通过率以真机 `conan create` 日志为准。
2026-09-29 的真机 `conan create` 复核通过：补丁成功应用，OXT 输出
`tests summary: ok:12`，消费者检查输出
`PASSENGER_TEST_RESULT checks=47 passed=47 failed=0`，整体 `exit_code: 0`。

## 需要注意的 OHOS 差异

- 上游命令是 Ruby 程序，系统里必须有可执行的 Ruby；配方在构建时检查 `ruby` 和 `rake`，缺少时明确报错。
- `locations.ini` 不能沿用构建机的临时路径，否则包被缓存或导出后会变成失效路径。
- 六个命令必须同时保留包内原始脚本和 `bin/` 转发脚本，二者缺一都会导致命令找不到支持库。
- 当前只声明已知的 OXT 结果，不把“构建成功”当作“全部测试通过”。

## 平台补丁

| 补丁 | 目标 | 原因 |
|---|---|---|
| `patches/0001-IOUtils-avoid-ohos-linux-net-header-conflict.patch` | `src/cxx_supportlib/IOTools/IOUtils.cpp` | OHOS SDK 的 `<linux/net.h>` 会带入 `<linux/socket.h>`，其中 `struct sockaddr_storage` 与 `<sys/socket.h>` 的重定义冲突；OHOS 上 `accept4()` 所需声明和常量已经由 `<sys/socket.h>` 提供，因此仅在 `__OHOS__` 下跳过该 UAPI 头 |
