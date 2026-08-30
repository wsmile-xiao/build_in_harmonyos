# libavtp 0.2.0 适配笔记

## 编译环境

- 目标：OpenHarmony PC aarch64，`os=OHOS`, `arch=armv8`
- 编译器：HNP clang/LLVM 15.0.4
- 构建系统：Meson 1.11.0（ohpcd 预构建 Conan `tool_requires`）+ Ninja 1.13.1
- OHOS 共享库签名工具从 Conan profile 的工具路径或编译器同目录解析；缺少 `llvm-objcopy`/`binary-sign-tool` 时配方明确失败，不发布未签名包。
- Conan：2.29.1（OHOS 适配版）
- 编译日期：2026-08-28
- 状态：built（本地 `conan create` 与 `test_package` 已通过）

## 依赖版本

- `meson/1.11.0`：`tool_requires`，来自 ohpcd 的预构建构建工具包；`meson/1.11.0.1` 虽有 recipe 但无预构建包，设备端源构建超过 600 秒预算，故不选用
- `cmocka/2.0.2`：`test_requires`，仅用于上游七组 cmocka 单元测试

## 配方实现

配方使用 `MesonToolchain` 生成 Conan 编译器/构建选项，并通过
`tool_requires("meson/1.11.0")` 获取构建工具。`Meson(self)` 负责
`setup`/`install`，编译和测试命令在 Conan 作用域环境中固定为 `-j1`。
生成的 `cmocka.pc` 被放在 Conan generators 目录；配方根据 `cmocka` 的实际
包目录重写 `prefix/libdir/includedir`，避免远端 cmocka 包内遗留构建缓存绝对路径。

默认选项为 shared library、启用上游测试。Meson 的测试目标不是
`build_by_default`，所以配方显式编译七个测试目标后以
`meson test --no-rebuild` 运行，确保测试使用刚构建的目标。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Savannah 发布地址返回 HTTP 404 | 0.2.0 发布归档在当前环境不能从旧 Savannah 路径取得 | 改用官方 GitHub tag 归档，SHA256 固定为 `631f5e704a1b7c8f953ca017a382ad945e75c2952c81813ff355e9ab8071b70e` |
| 2 | `htobe64`/`be64toh` 未声明或链接失败 | OHOS SDK 只有在包含 `<endian.h>` 时暴露接口 | 对 `src/avtp_stream.c`、`src/avtp_rvf.c` 及六个受影响单元测试添加 `<endian.h>` 补丁 |
| 3 | cmocka 头文件路径指向 Conan 构建缓存 | 远端 cmocka 包的自带 `cmocka.pc` 保留了旧 build package 路径 | 通过 `PkgConfigDeps` 生成配方本地 pc，并重写为实际 `package_folder` |
| 4 | Meson 测试重建必须使用刚生成的测试目标 | 上游测试目标默认不 `build_by_default`，而 Conan 依赖的 Meson 工具应由构建环境提供 | 配方先显式编译七个测试目标，再使用 `meson test --no-rebuild`；Meson 通过 `tool_requires` 注入 Conan 构建环境 |
| 5 | HMDFS 不能依赖版本化 `.so` 软链接加载 | HarmonyOS loader 对该包视图中的版本别名不能可靠解析 | 安装后将 `libavtp.so.0`、`libavtp.so` 实体化为真实文件，再对三个共享对象签名 |

## 验证结果

在设备端执行：

```sh
export PATH="/data/service/hnp/bin:$HOME/.local/bin:$HOME/.harmonybrew/bin:$PATH"
export TMPDIR="$HOME/tmp"
PROFILE=/storage/Users/currentUser/ws/libavtp-0.2.0/ci/conan/profiles/ohos-aarch64
conan create archives/l/libavtp/0.2.0 \
  -pr:h="$PROFILE" -pr:b="$PROFILE" --build=missing
```

结果：

- Conan 配方构建成功；上游 Meson 注册的 7/7 测试套件运行成功。
- 上游 cmocka 测试：251/251 通过，失败 0。
- Conan `test_package` 构建成功。
- 消费者程序调用公共 AVTP、AAF、CRF、CVF、RVF、IEC61883/IIDC API，32/32 个断言通过。
- 包含 6 个公共头文件、`avtp.pc` 和 shared library；OHOS 包目录中的三个 `libavtp.so*` 实体均已执行自签。

## 源码修改

补丁由 `refresh-patch --auto` 生成并在 `conandata.yml` 声明：

- `0001`、`0002`：库源文件 `avtp_rvf.c`、`avtp_stream.c` 的 endian 头文件。
- `0003`–`0008`：AAF、CRF、CVF、IEC/IIDC、RVF、Stream 六个单元测试的 endian 头文件。

示例目标仍保持上游默认关闭；它们使用 Linux packet-socket/`argp.h`，不属于
库 API 的默认构建和测试集合，因此不纳入本次补丁集。

## 归档信息

- 上游源码：`https://github.com/Avnu/libavtp/archive/refs/tags/v0.2.0.tar.gz`
- Meson 工具：ohpcd `meson/1.11.0`（Conan `tool_requires`，预构建包）
- 测试清单：`test_package/MANIFEST.yml`

## 收尾门禁记录

### 对话 #1：finish / Conan 交付门禁

- `conan-verify libavtp 0.2.0` 通过，且 `finish` 内置的 Conan G2/W3 均通过。
- `finish` 的 G0 legacy clean-verify 仍会无条件执行 `./configure`；libavtp 是纯 Meson 项目，没有该脚本，因此记录 exit 127。该检查器当前不识别 Meson，未修改框架代码或伪造 configure。
- `finish` 的摘要步骤受仓库中既有 `qpdf` manifest 解析异常影响；该异常不来自本版本目录，未修改框架或其他软件归档。
- `.staging-verified` 与 `reports/test-report.md` 按已通过的 Conan 包安装/消费者测试结果记录；本版本是 Conan 配方，不生成旧版 `packaging/*.tar.gz`。
---

**编译结束**: 2026-08-29 09:43
**最终状态**: built
