# detox 3.0.1 HarmonyOS 移植说明

## 来源

- 官方项目：<https://github.com/dharple/detox>
- 官方源码：<https://github.com/dharple/detox/releases/download/v3.0.1/detox-3.0.1.tar.gz>
- SHA-256：`b3dac4f7fcfaa621c6fc5950a2c7e5747cdc9d78aacb9041875fad916b838e60`
- 许可证：BSD-3-Clause

## 构建方案

使用 Release tarball 自带的 `configure` 与生成后的 lexer/parser C 源码，通过
Conan Autotools helper 构建。运行时没有第三方 Conan 依赖；完整单元测试使用
`check/0.15.2`。本次使用 Windows 构建机交叉编译为 HarmonyOS x86_64，并在
HarmonyOS 6.0 PC 虚拟机运行刚生成的 Conan 产物。

包安装两个命令、默认 `detoxrc`、当前及 legacy 转换表、手册和许可证；安装映像
使用根前缀布局，供 HarmonyOS 系统包部署到 `/bin`、`/etc` 与 `/share`。

HarmonyOS CI 的 HMDFS 会给 Autoconf 临时目录附加 setgid 属性；`configure`
默认的 `umask 077` 会使 `config.status` 无法写入 `conf*/subs1.awk`。配方在运行
`configure` 前将脚本及其内嵌 `config.status` 模板中的该值改为 `umask 022`。
该处理只调整构建临时目录权限，不修改 detox 源码或安装产物。

原生 HarmonyOS CI 执行 `make check` 时，测试程序会动态加载仅用于测试的
`libcheck.so`。由于 Check 通过 Conan `test_requires` 提供，配方只在这一步把
Check 包的 `lib` 目录加入 `LD_LIBRARY_PATH`，确保上游测试可以启动，同时不会把
测试依赖泄漏到常规构建、安装产物或 detox 的运行时环境。

上游 `test_table_resize` 使用相对路径读取 `fixtures/test_table_resize.tbl`，但
Automake 的 `EXTRA_DIST` 只负责发布源码包，不会把夹具复制到 out-of-source 构建
目录。配方在构建后将这一只读测试夹具镜像到对应的构建目录，再执行测试；该文件
不进入 Conan 安装产物，也不改变 detox 的产品行为。

## 测试口径

上游测试包含 14 个 Check 测试程序、37 个注册 Check 测试，以及 17 个 legacy
场景。报告采用两种明确口径：31 个套件/场景单元，或 54 个细粒度测试/场景。

交叉构建会编译 14 个 Check 测试程序但不在构建机执行；这些程序与 Conan 包随后
上传到目标机运行。Conan 消费脚本和 HarmonyOS 专项 `TMPDIR` 重命名测试也在目标机
执行；专项测试使用调用方提供的可写临时目录，兼容 CI 的非特权用户权限模型。仓库
W3 的正式 profile 固定为原生 aarch64，不能用 x86_64 虚拟机伪装通过，详情见测试报告。

## 可移植性补丁

上游测试夹具硬编码 `/tmp`。同一通用修复由仓库 `refresh-patch --auto` 按受影响
文件生成 12 个测试补丁，使 shell 与 C 测试优先读取 `TMPDIR`，未设置时仍回退到
`/tmp`。这些测试改动不添加 `__OHOS__`，也不改变 detox 的产品行为。

HarmonyOS 运行 `test_clean_utf_8` 时还稳定暴露出一个上游缓冲区越界：非法的双字节
NUL 会扩展为 `_hidden_null_`，但原实现只按转换表的单字节最大长度分配输出。
第 13 个通用补丁按转换表、NUL 占位串和非法字符占位串三者的最大长度分配缓冲区；
修复后该测试程序的 5 个注册测试以及全部 14 个 C 测试程序均在 HarmonyOS 通过。

另外两个通用构建修复分别纠正上游 `PKG_CHECK_EXISTS` 参数次序错误，并为
out-of-source 单元测试构建补充源码头文件目录。共计 15 个补丁。
