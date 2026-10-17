# 双构建系统的功能、数据和测试对齐

## 适用情形

上游同时维护 Autotools 与 CMake，但新功能只更新了其中一套构建描述。旧的 CMake 配方在新版本可能“编译成功”，却漏掉新源文件、运行期数据或上游测试。这不是仅靠升级版本号能发现的问题。

## 检查顺序

1. 对照两套构建系统的源文件清单、条件后端、生成器参数、安装数据清单和测试注册；不要只比较顶层 `configure.ac` 与 `CMakeLists.txt`。
2. 从新增公开 API 追到实现，再追到条件编译后端和运行时模型文件。若使用静态中间库，还要确认实现对象最终被链接进共享库。
3. 对照实际注册的测试与 `test_package/MANIFEST.yml`，声明数以本配方真实执行的测试为准；不能拿源码树里未注册的文件充数，也不能少报。
4. 对下载型模型先确认返回体确为压缩包，再固定原始字节的 SHA-256。构建配方在联网时校验哈希，在离线真机环境仅接受同一哈希的预置副本；不能把镜像返回的 HTML 错当数据包。
5. 最后用消费者程序从安装目录加载新增运行期数据，验证构建和安装都覆盖了新功能。

## libpinyin 2.10.3 实例

2.10.3 的 Autotools 清单新增 `punct_table.cpp`、Berkeley DB/Kyoto 后端、`--gen-punct-table`、`punct.bin` 和 `test_punct_table`，而同一标签内的 CMake 清单仍停留在旧功能。CMake 只执行 `gen_binary_files --table-dir` 会生成旧模型；新 API 在 `pinyin_init()` 后读取 `SYSTEM_PUNCT_TABLE`，缺失 `punct.bin` 会让包功能不完整。适配补丁同步 CMake 源码、生成参数、产物安装和测试注册，并额外注册 Autotools 已执行而 CMake 未注册的 `test_table_info`。原有 CMake 四项加这两项，构建期应执行六项真实测试。

同一版本还把文本模型从 `model19` 升为 `model20`。SourceForge 的旧式 `/libpinyin/models/...` URL 在某些客户端会返回 HTML；`/project/libpinyin/models/model20.text.tar.gz` 可返回 gzip。配方固定 model20 原始 SHA-256 `59c68e89d43ff85f5a309489499cbcde282d2b04bd91888734884b7defcb1155`，在 `cmake.build()` 前预置到构建目录，使上游数据生成步骤不依赖 worker 上是否安装 `wget`。

这套检查可复用于任何存在多套构建系统、生成数据和新增 API 的 C/C++ 库；具体文件名、后端及测试数须以各库当前标签重新核对。

若在 CMake `set_directory_properties(PROPERTIES ...)` 中传入由变量展开的分号列表，应给整个变量加引号；否则新版本 CMake 会把它当成多个属性名/值，报 `Wrong number of arguments`。这与编译器或依赖缺失无关，应依据配置阶段的首个错误定位。
