# UPSE 1.0.0 HarmonyOS 适配笔记

## 构建配置

- 上游版本：1.0.0
- 构建系统：上游自定义 Makefile/Autoconf；交付配方采用直接 C 源码构建
- 目标：HarmonyOS/OHOS 6.0，AArch64，Clang 15
- 依赖：`zlib/1.3.1.1`
- 产物：`libupse` 共享库（默认）、公共 C 头文件和 `upse123` CLI

官方主页声明 1.0.0 正式版原始下载站为 `distfiles.atheme.org`，该站当前无法完成 TLS 连接。配方固定使用原作者 `kaniini` 官方 GitHub 仓库的提交 `b71b54f315f6f7218c033405d475a2ae31a58dc8`；该提交与 1.0.0 发布源码逐文件一致，差异仅为发布包生成的 `configure`、`aclocal.m4`、`.hg_archival.txt` 与仓库使用的 `autogen.sh`。归档 SHA-256 为 `fa5945a3d49b527f7ae33b2e8d1c5de7d611a02e9a75195e69aa8fa9b2e1c468`。参考源码包只保存在仓库外 `docs/refs`，没有进入归档。

## W0 依赖检查

`conan list zlib/1.3.1.1:* -r=ohpcd` 实测返回 OHOS armv8 Release 配方与二进制修订。该版本是静态 PIC zlib，适合链接进共享版 `libupse`，且不会引入与 HarmonyOS 系统 `libz.so` 同名的运行时库。

## 构建系统处理

上游 `configure --disable-audplugin` 能正确判断 Audacious SDK 不可用，但静态 `src/Makefile` 仍无条件进入 `upse-audacious`，因此标准 `make` 会在缺少 `audacious/plugin.h` 时失败。上游 `buildsys.mk` 声明的核心库源文件清晰且不依赖插件，配方直接用 Conan 配置的 OHOS Clang 编译这些源文件，并保留 `upse123`。这避免修改生成文件、伪造平台三元组或引入已淘汰的 Audacious 1.4 SDK。

`upse123` 在不使用可选 libao 时保留上游 OSS 回退路径；版本和帮助等非播放路径不访问音频设备。Audacious 输入插件和 libao 输出后端均是上游可选集成，不属于 `libupse` 公共 API。

## R47 语言预检

`ohc-run.py lang-preflight upse 1.0.0` 检出 Autotools 构建系统和 20 个 C 源文件，C 主体占比 100%。C 与 C++ 属于赛事兼容语言族，预检通过。

## R51 上游测试三步法

### 1. 清点

对官方 1.0.0 源码树执行测试目录、测试命名文件、Makefile 测试目标与 Autoconf 测试宏检索，结果均为 0。`make -n check` 返回“没有规则可制作目标 check”。因此上游测试基线 N=0。

### 2. 运行

上游不存在可执行测试，配方明确输出结构化结果：发现 0、执行 0、通过 0、失败 0、跳过 0。没有删除、修改或跳过上游测试。

### 3. 回填

新增 5 个消费者测试场景、23 条确定性断言，均必须通过：

1. `upse_strtof` 的正数、负数、小数和非法输入行为。
2. 自定义 BIOS 设置、查询和清除 API。
3. 插值、混响和音频回调公开配置 API 的可调用性。
4. 自定义 I/O 下无效 PSF 输入的拒绝路径。
5. `upse123 -v` 版本行为与 HarmonyOS AArch64 ELF/动态依赖契约。

其中第 5 项包含 HarmonyOS 特有测试：验证产物是 AArch64 ELF，并且 `libupse` 不动态依赖冲突的 `libz.so`。

## 结束标记

UPSE 1.0.0 适配完成，状态：built；上游测试 0/0、新增测试 5/5，全部通过。
