# omins 0.2.0 适配笔记

## 上游与源码

- 上游主页：https://www.nongnu.org/om-synth/omins.html
- 官方发布包：https://download.savannah.nongnu.org/releases/om-synth/omins-0.2.0.tar.gz
- SHA-256：`e6402849cab0c60fc745e43ab56c06d53e1b23e9681edcfea02100005b3b9b63`
- 许可证：GPL-2.0-or-later

## 构建与适配

- 构建系统：Autotools；目标平台为 OHOS/aarch64，编译器为 Clang 15。
- 接口依赖：`ladspa-sdk/1.17`；构建工具依赖：`automake/1.18`、`libtool/2.5.4`。三项均已从 `ohpcd` 制品仓实际下载验证。
- 上游发布包生成于 2005 年，且当前 GNU `config.guess` 仍无法从 `uname -s = HarmonyOS` 推断平台。配方先用已发布工具执行 `autoreconf -fi`，再由 Conan `AutotoolsToolchain` 显式传入构建三元组 `aarch64-unknown-linux-gnu` 与目标三元组 `aarch64-unknown-linux-ohos`，避免执行 HMDFS 构建树中的探针程序。
- HarmonyOS PC 的 HMDFS 对 GNU Bash 的深层目录 `getcwd()` 以及 `config.status` 使用 `umask 077` 创建的临时目录存在权限冲突；OHOS 构建使用系统 POSIX shell，并把重新生成的 `configure` 中该临时目录 umask 调整为 `022`。这是 E011 的标准修复，不改变功能探测结果。
- 上游自定义安装规则直接写 `@ladspadir@`、忽略 `DESTDIR`。为保持 Conan 包隔离，`package()` 从已验证的 `src/.libs` 精确复制 18 个模块到 `lib/ladspa`，并对文件名集合做完整性校验；libtool 的裸 `.so` 是版本化目标的符号链接，打包时解引用为自包含的常规文件，避免包内断链。
- 上游 18 个模块使用 ELF 保留函数名 `_init/_fini` 注册和释放描述符。OHOS 动态加载器执行该旧式 `DT_INIT` 入口时崩溃；18 个自动生成并通过 dry-run 的可移植性补丁仅把入口改为 Clang/GCC 通用的 `constructor/destructor` 属性，使相同逻辑通过初始化数组执行。
- 除上述 18 个最小化入口补丁外，其余适配逻辑均位于配方，未注入 `__OHOS__` 到第三方源码。

## 上游测试清点与执行

- 发行包共 39 个文件，其中 C 源文件 18 个；没有 `test/`、`tests/`、测试源、`TESTS` 或 `check_PROGRAMS` 注册项。
- 顶层与 `src/` 的 `make check` 均为 Automake 自动生成的空目标，因此上游测试用例总数为 **0**。
- 配方仍在每次构建中实际执行 `make -j1 check`，确认官方测试入口返回成功。

## 补充消费者与 HarmonyOS 特有测试

- `test_package/src/test_omins_host.c` 编译为真实 LADSPA 宿主，逐一 `dlopen()` 18 个模块，解析 `ladspa_descriptor()`，验证 28 个描述符的元数据，实例化、连接全部端口并执行 64 帧 DSP，再清理实例。
- HarmonyOS 特有检查：测试源码要求 `__OHOS__`，运行时通过 `uname()` 验证 `aarch64/arm64`，防止用其他平台结果冒充真机验证。
- 测试断言账本：上游 `0/0`；适配消费者与 HarmonyOS 检查共 **170/170**（详见 `test_package/MANIFEST.yml`）。

## 交付物

- `lib/ladspa/*.so`：18 个 LADSPA 插件模块，共 28 个插件描述符。
- `licenses/COPYING`：GPL-2.0 许可证文本。

## 已知边界

- 该包提供无 GUI 的 LADSPA DSP 插件，不包含音频宿主；运行时由消费者选择 LADSPA 宿主加载。
- `package_info()` 不声明链接库，仅通过 `resdirs` 和 `LADSPA_PATH` 暴露插件目录。
