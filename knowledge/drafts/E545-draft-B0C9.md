# E545（草稿）头内 inline function-local static 插件注册表被各 DSO 私享，跨 DSO 查找恒失败

- **现象**：共享构建下 127 个格式插件 dlopen 全部成功，但 `SetInFormat()/SetOutFormat()` 恒返回 false，日志报 `Open Babel Error in LoadAllPlugins` / 格式查不到；上游 ctest 大量格式转换用例失败。
- **根因**：`include/openbabel/plugin.h` 的 `MAKE_PLUGIN` 在默认分支把注册表 `Map()` 定义为头内 inline 的 function-local static。C++ 语义下每个 DSO（主库 libopenbabel.so、各格式插件 .so、消费者 exe）各持一份私有注册表实例：插件在自己的 DSO 里注册进自己的表，调用方在另一个 DSO 里查自己的表，`FindType()` 恒 null。
- **为何 Linux 常见构建不触发**：静态构建或所有插件链入同一二进制时注册与查表同 DSO；上游 Cygwin/MinGW 分支早已针对同一问题准备了外置定义路径（`PLUGIN_CPP_FILE` 在库内单点定义）。
- **解法**（可移植，无平台宏）：删除 plugin.h 的平台条件编译，无条件采用外置定义路径；7 个带 `PLUGIN_CPP_FILE` 守卫的 .cpp（chargemodel/descriptor/fingerprint/forcefield/format/op/ops-loader）解除守卫，使每个插件族的 `Map()` 在 libopenbabel 内恰有一个强定义。
- **验证**：`nm --defined-only` 确认单一强定义；openbabel 3.2.1 共享构建上游 ctest 348/348 全过（含全部格式转换组）。
- **关联**：E546（同为多 DSO 语义问题，typeinfo 面）。
- **来源**：openbabel 3.2.1 OHOS aarch64 适配，PR #14369。
