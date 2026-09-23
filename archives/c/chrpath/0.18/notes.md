# chrpath 0.18 适配笔记

## 编译环境

- 构建系统：Autotools，HarmonyOS worker 缺少 Automake 时使用直接 C 编译回退
- 目标平台：HarmonyOS PC AArch64
- 源码校验：`f09c49f0618660ca11fc6d9580ddde904c7224d4c6d0f6f2d1f9bcdc9102c9aa`
- 适配状态：本地 OHOS 交叉构建与打包通过；远程验证采用 HarmonyOS 设备原生 Conan 构建，
  只传源码、配方和测试脚本，不上传预编译目标文件；原生 Conan 构建与测试已通过

## 上游测试清点

上游源码没有独立的 `tests/` 目录；测试入口为 `testsuite/runtest.sh`，由
`testsuite/Makefile.am` 的 `check` 目标执行。脚本包含 10 个独立逻辑场景：帮助、版本、
脚本输入拒绝、缺失文件拒绝、RPATH 列举、短路径替换、长路径尝试、RPATH/RUNPATH 转换、
删除 RPATH/RUNPATH，以及总返回值汇总。

## 适配变更

- `0001-ohos-getopt-long-fallback.patch`：当 `HAVE_GETOPT_LONG` 不成立时，把长选项规范化
  为上游已有的短选项，再继续调用原有业务逻辑；具备完整 `getopt_long` 的平台不改变行为。
- Conan 配方在 OHOS 下提供 lld 参数，并在缺少 Automake 时直接编译四个上游 C 源文件。

## 验证记录

- `conan create`：通过。OHOS AArch64 目标 ELF 已编译并打包，`test_package` 已完成交叉构建；
  因当前主机不是 OHOS，Conan 按预期跳过目标程序执行。
- 目标产物静态检查：通过。ELF64/AArch64、PIE、BIND_NOW，依赖 `libc.so`。
- HarmonyOS 6.1 真机原生 Conan：通过。设备本地构建、上游 testsuite、通用 consumer 和
  HarmonyOS RPATH 测试均通过，Conan 返回码为 0。运行期间 Bash 输出若干非致命的
  `getcwd`/`job-working-directory` 警告，未影响测试结果。
- 语言预检：通过，源码识别为 C，与任务语言族兼容。
- 预扫描：通过，报告识别出上游 Autotools 的 `config.guess/config.sub` 风险；本配方在
  OHOS 下采用不依赖 Autoconf 生成物的直接 C 构建回退。
- 上游 10 个 testsuite 场景：在 HarmonyOS 6.1 真机原生构建中通过。
- HarmonyOS 特有测试：`test_ohos.sh` 在目标设备上的 Conan 工作目录内执行，使用设备本地
  编译生成的 AArch64 ELF，验证 `/data/local/tmp` RPATH 的长选项替换；不上传预编译 ELF。
- 该测试在 HarmonyOS 6.1 真机原生构建中通过。
- 远程原生命令：`conan create 0.18 --name=chrpath --version=0.18 -pr:h=ohos-aarch64.profile
  -pr:b=ohos-aarch64.profile --build=missing`，使用设备本地 `/data/service/hnp/bin/clang`。
- 仓库全量 Python 回归在本地 Windows 受既有环境问题影响：`fcntl` 不可用，以及
  `test_v1220.py`/`test_v1221.py` 的既有测试环境问题；未修改这些无关代码。

本次目标测试均已在设备本地执行；非致命的 shell 工作目录警告不计入失败。真正的 ELF
由 HarmonyOS 设备本地工具链生成，控制端未上传预编译 ELF。
