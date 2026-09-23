# cpipe

cpipe（Counting Pipe）是一个轻量命令行工具：它把标准输入原样复制到标准输出，并可在标准错误中显示吞吐率，适合放在管道中观察数据传输速度。

- 上游：https://sourceforge.net/projects/cpipe.berlios/
- 版本：3.0.1
- 许可证：GPL-2.0-or-later
- Conan 引用：`cpipe/3.0.1`
- HarmonyOS 目标：6.0、AArch64（Conan `arch=armv8`）

## 使用示例

```sh
printf 'payload' | cpipe -ngr > output
tar cf - source | cpipe -vt | tar xf - -C destination
```

`-ngr` 启用非贪婪读取；`-vt` 把吞吐统计写到标准错误，不改变标准输出的数据。

## HarmonyOS 构建要点

- 保留上游原始 Makefile，由 Conan 的 `tools.build:compiler_executables` 提供 C 编译器，并以 `-j1` 构建。
- 配方只接受 `os=OHOS`、`os.version=6.0`、`arch=armv8`，并在 Conan 的独立构建目录内编译和取出打包文件。
- 上游已随源码包提供 `cmdline.c`、`cmdline.h` 和 `cpipe.1`，配方只调整其时间戳，避免构建时错误调用未提供的 `clig`。
- 补丁 `0001-fix-size-t-format.patch` 将 `size_t` 的 `%u` 格式改为 C99 `%zu`，消除 64 位 AArch64 上的格式类型不匹配。
- 打包内容为 `bin/cpipe`、`share/man/man1/cpipe.1` 和许可证；配方明确把 `bin/cpipe` 权限设为 `0755`。

## 测试

- 官方源码包没有上游测试目录或 Makefile `check`/`test` 目标，配方和测试包均输出规范的 `HMBS_UPSTREAM_TEST_RESULT` `no_tests` 证据。
- 一次性宿主源码构建执行四项真实行为测试：二进制透传、1 KiB 缓冲透传、吞吐统计与标准输出分离、非法参数拒绝。
- Conan `test_package` 使用 HarmonyOS 工具链编译专属探针，编译期要求 `__OHOS__`、`__aarch64__`、64 位和小端 ABI。
- 测试包先确认 `bin/cpipe` 具有执行权限，再以独立 ELF64 解析同时确认 `cpipe` 与专属探针的 `e_machine=183`（AArch64），并确认加载器为 `/lib/ld-musl-aarch64.so.1`。

当前本地 HarmonyOS 6.0 虚拟机为 x86_64 且没有 AArch64 模拟器，不能运行发布产物。因此没有生成 x86_64 替代包，也没有宣称完成 AArch64 HDC 运行测试；发布产物始终只面向 AArch64。
