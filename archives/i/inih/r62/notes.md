# inih r62 鸿蒙 PC 升级记录

## 范围与来源

从已存在的 inih/r58 升级纯 C 静态库至 r62。提交配方仍使用官方
`https://github.com/benhoyt/inih/archive/refs/tags/r62.tar.gz`，
归档 SHA-256 为
`9c15fa751bb8093d042dae1b9f125eb45198c32c6704cd5481ccde460d4f8151`。
无第三方编译依赖、无上游补丁；直接以目标 Clang 编译 `ini.c`，
以同工具链目录中的 `llvm-ar` 生成 `libinih.a`，安装 `ini.h` 与许可证。

## r58→r62 差异与测试

r62 新增 `ini_parse_string_length()`，并调整过长行、堆分配/重分配和
行尾处理。配方按 r62 的 `tests/meson.build` 编译 15 种配置，
在可运行的原生目标上逐项执行，将标准输出与归档内相应
`baseline_*.txt` **逐字节比较**；交叉模式只编译测试程序，不宣称已执行。
安装包消费者单独验证长度限定输入、传统 NUL 终止输入与畸形 section，
弥补上游 `unittest_string.c` 未直接调用新长度 API 的覆盖缺口。

## 私有真机证据和边界

2026-10-06 在 `授权 HarmonyOS PC 真机` 的全新私有 a679 根，
五个配方/消费者输入、官方归档、profile 与 Conan 配置均经上传后的
独立 SSH 会话完整回读逐字节相等。使用目标私有 `CONAN_HOME`、
`TMPDIR` 和预装相同 SHA-256 归档的 Conan 下载缓存；目标无法直连
GitHub，本次日志是缓存命中，不能写成设备 HTTPS 下载成功。
原生 `conan create` RC0、上游 15/15、安装包消费者 3/3。
包引用：
`inih/r62#0641920c66f341d9205efcd474ceaff6:b82a1bbf67052c8879d9482427b66672b105bed6#791fd37903ff286880e9e86766d02e58`。
原始日志保存于任务 D 盘 `a679-create.log`，20,619 字节，SHA-256
`b98068b71b2d70eae5d33c16b9b6886e4eced4972ab165ae70604d02efc48939`。
首次 a677 因设备默认临时目录只读，在链接测试程序时失败；未在原根重放，
于全新 a678 根设置可写 `TMPDIR` 后重验成功；随后仅优化消费者的
Windows 可执行文件后缀，又在全新 a679 根完整复验通过。

此记录仅证明私有真机 Conan 运行，不是正式 W3 回执、平台 CI、
知识审核、PR 提审或积分到账。正式流程须以当时官方 main 和真实工具
输出为准，不得手写 `.ci-result.json`。
