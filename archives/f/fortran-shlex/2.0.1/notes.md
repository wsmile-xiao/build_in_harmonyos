# fortran-shlex 2.0.1 HarmonyOS PC adaptation

status: partial

### 对话 #1：源码、依赖与构建方案

- 官方版本标签为 `2.0.1`，对应提交 `e20b6f86c82e33fae78b54b074bab5369efde6a3`。
- 官方标签归档 SHA256 为 `660d1ca12ee8213d7c6061732a48d7fc29a13dd408afc334af26090ea842bfad`。
- 上游 `fpm.toml` 的版本字段仍为 `2.0.0`，但本配方以正式 Git 标签和 Conan 版本 `2.0.1` 为准。
- 软件没有外部运行时库依赖；HarmonyOS 原生构建使用已发布的 `flang-ohos/20.1.0` 工具包。
- 配方直接编译唯一模块 `src/shlex_module.f90`，安装静态库和 `shlex_module.mod`，不修改上游源码。

### 测试证据

- `build()` 编译并运行官方 `test/shlex_test.f90`，覆盖 10 项 POSIX 测试、224 项 MSVCRT 测试、110 项 UCRT 测试、12 项 cmd quoting 测试和 7 项非 cmd quoting 测试，共 363 项。
- 独立主机验证分别使用 LLVM Flang 20.1.8 和 GCC 15 编译官方源码与原始测试，两次均输出 `SUCCESS! all 363 tests passed.`。
- LLVM Flang 20.1.8 还按 `test_driver.sh` 的相同路径编译并运行消费者测试，23 项公共 API 检查全部通过。
- `test_package` 从消费者视角链接已安装的 `libfortran-shlex.a` 并读取已安装的 `shlex_module.mod`，执行 23 项公共 API 检查。
- R34 破坏性反向验证会移走 `lib/` 与 `include/`；此时消费者测试无法编译或链接，因此测试实质依赖被测包。
- 隔离 W3 执行中 L0 全部通过，Conan 成功解析并下载 `flang-ohos/20.1.0` 与官方源码；随后因本机为 x86_64、工具包中的 `flang` 为 HarmonyOS AArch64 原生 ELF 而以 `Exec format error` 停止。
- 另以 rootless QEMU 10.2.1 和 SDK 链接期 sysroot 尝试运行该 AArch64 `flang`；SDK 中的 `libc.so` 不是可替代真机运行时的完整根文件系统，加载阶段即 `SIGSEGV`，因此该尝试不计作 HarmonyOS 构建通过。
- 本机 `hdc list targets` 返回 `[Empty]`，HarmonyOS 真机 W3 结果只接受真实设备或设备 CI 的后续输出，不以主机测试替代。

### 构建命令

```sh
conan create archives/f/fortran-shlex/2.0.1 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=fortran-shlex/*
```
