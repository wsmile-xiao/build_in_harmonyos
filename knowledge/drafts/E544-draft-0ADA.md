# E544 — 在 x86 runner 上用 QEMU 强制执行静态 AArch64 CLI 功能测试

## 问题

Conan 的包设置可以声明 `os=OHOS`、`arch=armv8`，但执行
`test_package` 的机器仍可能是 x86_64。直接执行 AArch64 ELF 会出现
`Exec format error`。动态目标即使经 `qemu-aarch64` 启动，也可能缺少
OHOS musl loader 或目标动态库。

将这种情况写成“跳过目标执行并返回成功”只验证了二进制文件存在，不能验证
CLI 的真实功能，属于假绿风险。

## 适用条件

- 被测物是面向 AArch64 OHOS 的命令行程序；
- 程序只依赖 libc，能够安全静态链接；
- 功能可以通过命令行输入、输出和退出码验证；
- runner 为 AArch64，或 x86 上可用 `qemu-aarch64`。

不适用于需要动态 OHOS 运行库的程序，也不适用于库 API 的运行时验证。

## 推荐做法

1. 配方从 Conan profile 的 compiler 配置取得 C 编译器，并通过 `CC='<clang> -static'`
   链接 libc-only CLI；不要读取未定义的 shell `CC` 环境变量。
2. 测试先使用包内二进制的绝对路径确认被测包确实被消费；这样破坏性移除
   `bin/` 后测试会失败。
3. AArch64 runner 直接执行该路径；x86 runner 在修改 `PATH` 前解析
   `qemu-aarch64` 的绝对路径，并通过它运行**相同**功能断言。
4. QEMU 不存在时返回失败，而不是 `exit 0` 跳过；若程序不能静态链接，则转为
   真实 AArch64 HarmonyOS runner 验证，并如实记录未覆盖的运行时范围。

## 验证

```bash
make CC='<ohos-clang> -static' -j1
qemu-aarch64 ./whichman -h
bash test_package/test.sh ./whichman ./ftff ./ftwhich
```

`whichman/2.4` 的测试覆盖三个二进制存在性、MANPATH 精确查找与未命中返回、
PATH 可执行文件查找、目录树文件查找，共 7 项断言，均通过。

## 关联条目

- `E423`：交叉工具的包所有权与目标格式验证；该条目覆盖无法在宿主执行的
  非宿主目标工具，而本条处理应当在 AArch64 执行的 CLI。
- `E294`：交叉构建中必须区分测试编译链接与目标端执行；本条提供 libc-only CLI
  的 QEMU 执行路径。
