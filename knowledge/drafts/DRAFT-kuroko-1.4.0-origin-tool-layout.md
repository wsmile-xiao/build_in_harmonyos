# `$ORIGIN` 只指向工具目录，不会自动搜索兄弟 `lib/`

状态：知识库扩展候选；是否独立入库、计分与等级由维护者判断。此条解决的是 ELF 工具移动后的运行时路径问题，不是 Kuroko 的语言兼容性问题。

## 现象与根因

Kuroko 1.4.0 的 `make all` 和 148/148 项上游测试在 HarmonyOS PC AArch64 上通过。Conan 安装包将 `krk-demo` 放在 `bin/`，将 `libkuroko.so` 放在 `lib/`。直接以空 `LD_LIBRARY_PATH` 运行安装包中的工具，目标机报 `Error loading shared library libkuroko.so` 和符号未定义，退出码 127；将包的 `lib/` 加入该环境变量后，输出 `Kuroko 1.4.0`，退出码 0。

`readelf -d bin/krk-demo` 显示 `NEEDED libkuroko.so` 与 `RUNPATH [$ORIGIN]`。`$ORIGIN` 是工具自身所在的 `bin/`，不是包根目录，也不会自动搜索兄弟 `lib/`。上游 Makefile 的安装目标同样把工具和库分置这两个目录；在可运行 `ldconfig` 的传统发行版中可能由系统库缓存补足，但当前私有 Conan 包不应依赖全局安装。

## 可复用处理

1. 区分构建树运行与最终包运行；记录 `readelf -d` 的 `NEEDED`/`RUNPATH` 和最终 `bin/`、`lib/` 位置。
2. 若使用 Conan，`package_info()` 通过 `runenv_info.prepend_path("LD_LIBRARY_PATH", package/lib)` 导出运行环境。其他打包方式可在链接期使用正确的相对 RUNPATH，但必须重测构建工具和安装工具两种位置。
3. 从源码树之外运行包中的实际工具，并测试一个无库路径的负例与一个设置包内库路径的正例；不要以解释器正常启动替代工具动态链接验证，因为本例解释器静态链接 VM 库。

此配方的 `krk-*` 工具需要 Conan run environment 或等效的调用方 `LD_LIBRARY_PATH`。尚未验证无环境变量的独立直接运行；也不声称本方案修复其他场景中的权限拒绝或缓存文件重写。

## 证据与查重

- 官方源码 `v1.4.0` SHA-256：`55c143761da9b3ed0f523b9f7828dc04fc8e02280783274376dbbd335866c95d`；真机目录：`/data/storage/el2/base/haps/entry/files/kuroko-1.4.0-20260926T181400`。
- 真机原样负例：`LD_LIBRARY_PATH= <package>/bin/krk-demo` → 缺 `libkuroko.so`，RC 127。正例：`LD_LIBRARY_PATH=<package>/lib <package>/bin/krk-demo` → `Kuroko 1.4.0`，RC 0。
- 配方消费者脚本从最终安装包执行解释器、语言模块、`krk-demo` 和共享库 C API。最终 `conan create` 的精确日志与哈希记录在版本 `notes.md`。
- 已读现有 `DRAFT-garmintools-0.12.2-conan-cache-runpath-mask-dlopen`（Conan 缓存中 RUNPATH 字符串被改写）和 `DRAFT-E575-libosip-libtool-hardcode-empty-no-runpath`（libtool 注入绝对路径）；本条的失效机制是**未改写的** `$ORIGIN` 与最终目录布局不一致。若维护者发现更早同义条目，应归并而非重复计分。
