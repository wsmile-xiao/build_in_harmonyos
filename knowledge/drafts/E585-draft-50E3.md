# E585（草稿）— CMake 项目在初始化阶段被误判为 Autotools

## 错误特征与证据

ttylog/0.31 官方压缩包根目录含 `CMakeLists.txt`、`ttylog.c`，无 `configure`、`configure.ac`。`init-build` 输出 `BUILD_SYSTEM="autotools"`，`conan-init` 随之生成调用 `AutotoolsToolchain`、`autotools.configure()` 的配方；同一源码的 `lang-preflight` 则报告 `build_system: "cmake"`。若直接运行生成的配方，会对不存在的 `configure` 发起配置。

## 根因

两个阶段使用不同判型依据；初始化的启发式结果在配方生成时覆盖了顶层源码的真实构建入口。不是 OHOS 编译器问题，也不能通过额外安装 autoconf 消除。

## 处置与验证

1. 下载后检查顶层 `CMakeLists.txt`/`configure` 并运行 `lang-preflight`；发现冲突时以实际源码构建入口为准。
2. 保持源码官方 URL 和 SHA256，人工把生成的配方改为 `CMakeToolchain`、`CMake`；同步改版本 manifest / notes 的 build_system，不修改框架文件。
3. 在本机执行 `python3 scripts/ohc-run.py conan-verify ttylog 0.31`：本次 G1、G2 及 G3 均通过，交付的静态 AArch64 CLI 经 qemu 完成 4/4 项实际测试。

## 查重

已有 E483 解释 SourceForge `/download` 被误判 ZIP、已有 E429 草稿解释 G1 对无补丁配方仍要求补丁导出/应用钩子，均不覆盖“CMake 根目录被误判 Autotools 后生成错误配方”。只提交草稿，建议主编复审后决定是否 promote。
