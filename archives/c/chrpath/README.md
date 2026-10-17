# chrpath

chrpath 是一个用于查看、修改或删除 ELF 二进制文件 RPATH/RUNPATH 的命令行工具。
它适合在发布前修正可执行文件的动态库搜索路径。

## OHOS 适配

- 使用 Conan 提供的 HarmonyOS AArch64 编译器和 lld 链接器。
- 优先使用上游 Autotools 构建；当构建 worker 缺少 Automake/aclocal 时回退到直接 C 编译。
- OHOS libc 不提供完整 `getopt_long` 时，通过兼容补丁支持 `--version`、`--help`、`--list`、`--replace` 等长选项。
- 测试使用 `/data/local/tmp/` 形式的目标路径验证 HarmonyOS ELF 的 RPATH 修改行为。

## 依赖

无 Conan 运行时依赖。

## 功能验证

```bash
chrpath --version
chrpath --list <elf-file>
chrpath --replace /data/local/tmp/new-rpath <elf-file>
chrpath --delete <elf-file>
```

## 参考

- [上游项目](https://codeberg.org/pere/chrpath)
- [Debian 源码归档](https://deb.debian.org/debian/pool/main/c/chrpath/)
