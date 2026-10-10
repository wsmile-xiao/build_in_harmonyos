# libpinyin 2.10.3 适配记录

状态：真机 W3 已通过，上游 CTest 6/6、安装后消费者断言 7/7；尚未提交 PR。通过证据绑定 `libpinyin-w3-20261007T042115Z`，不能挪用前几次失败事务的结果。

## 上游与依赖

- 上游标签：`2.10.3`；源码 SHA-256 `a49286721fb2b0234d86c095db9226246b0aa4a0bb6a885d0902da2743c56476`。
- `model20.text.tar.gz`（20,283,243 字节）从 SourceForge 的 `/project/libpinyin/models/` 路径取得；SHA-256 `59c68e89d43ff85f5a309489499cbcde282d2b04bd91888734884b7defcb1155`。旧式下载 URL 在本机曾返回 HTML，已用 gzip 头和 tar 成员验证实际包。
- W0 `conan install --build=never` 在隔离缓存成功：`glib/2.88.3`、`berkeley-db/4.8.30` 的 OHOS/armv8/Clang 15/Release 精确二进制均可下载。真机 W3 也成功下载二者。

## 配方变更

- 2.10.3 引入标点候选；上游 Autotools 已纳入 `punct_table` 实现、`--gen-punct-table`、`punct.bin` 和标点测试，同标签 CMake 清单未同步。补丁把 CMake 源码、模型生成、安装数据和两项原先未注册的测试对齐；构建期 CTest 实测分母为 6。
- 对注册测试中写 `/tmp` 的路径改为构建目录相对路径，避免目标机 `/tmp` 限制及测试互相覆盖。
- 模型包在 Conan 构建前按 SHA-256 校验并预置；CMake 不再直接调用 `wget`。离线真机可通过 `LIBPINYIN_SOURCE_ARCHIVE` 与 `LIBPINYIN_MODEL20_ARCHIVE` 传入同哈希副本。
- 当前 CMake 对 `ADDITIONAL_MAKE_CLEAN_FILES` 的列表展开会报 `Wrong number of arguments`；补丁将变量作为单个带引号参数传入。最终真机配置、构建与测试均通过。
- 消费者需要显式链接 Berkeley DB 静态包；测试配方将其设为直接依赖以取得已安装包的绝对路径。拼音输入改为上游解析器支持的 `ni'hao`，不把空格误认作音节分隔符。

## 真机尝试（均为独立、已释放事务）

| run_id 后缀 | 首个真实失败点 |
| --- | --- |
| 025831Z | 标点测试补丁第二处 hunk 行号偏移，Conan 补丁器拒绝；已修正并用同一 Conan 补丁器对原始源码逐个验证。 |
| 030603Z | 设备现有 profile 的 `/data/service/hnp/bin/clang` 不存在；本机真机 profile 已改用设备上的 `/storage/Users/currentUser/usr/local/bin/clang` 包装器，仓库配方不写死工具路径。 |
| 031713Z | `data/CMakeLists.txt` 的清理文件列表被拆成多个参数；精确补丁后 CMake 配置通过。 |
| 032444Z | W3 传输清单漏装新增补丁，Conan 导出即失败；随后已校对声明与包内补丁数量一致。 |
| 032722Z | CMake 配置成功；设备默认 `make -j20` 引发 `Out of memory` / `can't fork`，尚未完成编译。 |
| 033046Z | 真机 profile 限为 2 线程后，CMake 的单个编译器探测仍出现 `can't fork`；设备当前资源/执行环境不稳定，尚未执行上游及消费者测试。 |
| 040200Z | 重启后的单线程构建与 CTest 6/6 通过；消费者链接器收到错误的相对参数 `-llib/libdb.a`。 |
| 040833Z | 将路径拼为绝对路径后，Conan 因 Berkeley DB 只是跳过二进制的传递依赖而给出 `package_folder=None`；改为测试包直接依赖。 |
| 041444Z | 构建、链接和消费者运行通过，但空格分隔的 `ni hao` 仅解析前缀；改用上游支持的撇号分隔。 |
| 042115Z | `conan create` 成功；CTest 6/6、消费者 7/7、`punct.bin` 安装检查、W3 12/12 回执与释放均通过。 |

每次真机 run 均使用当前设备清单、主机指纹核对、唯一 `run_id`、精确字节传输和独立回读，单次 launch；失败后记录 `RELEASED` / `POSTRELEASE_PASS`。设备恢复后，所有失败事务和最终通过事务的完整日志、12 份回执及终态记录已回读并校验。最终日志 SHA-256 为 `e21131a6c166851675c034f2db19f65ea2895b053eb86a9fe7d5666957a0b4f1`，目标共享库 SHA-256 为 `0461c1f335a7a7efb27e0d94e512718cc438a873a49e3704100ffa210eb21458`。本地 `w3-*` 与 `evidence/` 不纳入 PR。

## 待完成

1. 完成知识查重、高难四项重判及比赛 Pre-PR 合同。
2. 按赛事模板创建唯一 Issue/PR，完成 POST_CREATE 关联后处理平台 Review 与 CI。
