# CMake 属性值中的分号列表须作为单个实参传递

libpinyin 2.10.3 的 `data/CMakeLists.txt` 把多个待清理文件汇入 `ADDITIONAL_MAKE_CLEAN_FILES`，随后以未加引号的变量传给 `set_directory_properties(PROPERTIES ...)`。CMake 展开分号列表后将其视为多个参数，配置在该行报 `set_directory_properties Wrong number of arguments`。

只给属性值的变量展开加双引号，不改变文件清单或清理属性。独立真机事务 `libpinyin-w3-20261007T031713Z` 记录了原始错误；修复后的最终事务 `libpinyin-w3-20261007T042115Z` 完成 `conan create`、上游 CTest 6/6 和安装后消费者断言 7/7，日志 SHA-256 为 `e21131a6c166851675c034f2db19f65ea2895b053eb86a9fe7d5666957a0b4f1`。中间的 032722Z 曾因设备负载引发 `Out of memory` / `can't fork`，属于独立的环境故障，不能误判为该 CMake 参数修复失败。

可复用判别：若 `set_directory_properties` 报参数数量错误，先核对属性名和值是否成对，再检查传入值是否由分号列表变量展开。保留原清单并将整个值引用为一个参数；重新配置后继续核对构建、清理及测试行为，不能通过删除属性来掩盖错误。

查重边界：现有 E409 处理的是 CMake `list(APPEND)` 中可选值为空、未引用展开导致必要实参消失；本条相反，多个非空路径由分号列表展开为过多实参，作用点是 `set_directory_properties` 的属性值。二者共享“引用变量以保持参数边界”的原则，但错误签名、发生位置和清理行为风险不同。
