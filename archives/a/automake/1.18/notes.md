# automake 1.18 编译笔记（HarmonyOS PC · Conan autotools · 工具包）

## 定位
`package_type = "application"`，只提供构建期工具（`libdirs` 置空），
供其他配方 `tool_requires` 使用。仓内已有 1.16.5 / 1.17，本次补 1.18。

## 关键适配：三处"把构建期路径烤进产物"

automake 是 perl 脚本，configure 期会把 `@prefix@`/`@datadir@` 写死进产物。
conan 用 `--prefix=/` + DESTDIR 打包，于是烤出来的是 `//share/automake-1.18`
这种空前缀畸形路径——**载体是文本文件，ELF 检查完全看不见**。

1. **perl `@INC`**：automake 主体按烤死的 datadir 找 `Automake/Config.pm`。
   不改脚本（改了换机器同样废），而是用 `PERL5LIB` 把真实位置补进 `@INC`。
2. **aclocal 的宏目录**：同病，`couldn't open '//share/aclocal-1.18'`。
   用 `ACLOCAL_PATH` 指向真实位置。
   > 坑：一度改用 `--system-acdir`，它是**替换**不是追加，
   > 反而遮蔽了 hnp 自带的 `pkg.m4`，导致下游报
   > `'pkgconfig_DATA' is used but 'pkgconfigdir' is undefined`。
3. **hnp 各包的 aclocal 目录**：`package_info` 里 glob 出 hnp 的
   `share/aclocal` 追加进 `ACLOCAL_PATH`——自发现而非写死路径。

## 其他
- `MAKEINFO=true`：设备无 makeinfo，`make install` 会 `Error 127`。
- 显式三元组 `--build/--host=aarch64-unknown-linux-musl`，跳过 `config.guess`
（OHOS 不在 config.sub 里，否则 `cannot guess build type`）。

## 状态
built —— 真机 `conan create` 通过；test_package 实际调用 `automake --version`
与 `aclocal --version`，并验证 aclocal 能找到宏目录。
