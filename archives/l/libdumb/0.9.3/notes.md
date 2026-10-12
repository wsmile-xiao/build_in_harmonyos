# libdumb 0.9.3 适配记录

## 版本与来源

- 任务要求原始 DUMB 0.9.3，不复用不同 API、许可证和构建系统的 2.0.3 配方。
- 官方 SourceForge tarball，SHA256 为 `8d44fbc9e57f3bac9f761c3b12ce102d47d717f0dd846657fb988e0bb5d1ea33`。
- 使用原始 GNU Make 构建规则；不修改源码，不补入 CMake 构建系统。
- 许可证以该版本 `licence.txt` 为准，为 DUMB 自定义许可证；不沿用历史归档的 Unlicense 声明。

## 范围与依赖

- 核心 IT/XM/S3M/MOD 解码与软件渲染静态库，发布 `libdumb.a`、公开 `dumb.h` 和许可证。
- 无第三方库依赖，只链接 libc/libm。Allegro 集成非必需，不纳入本包。
- 上游 `dumbout`、`dumb2wav` 已随原生探索构建编译成功，作为示例不纳入库制品。
- 未验证 Allegro 音频设备输出；测试检查内存 PCM，不宣称扬声器播放成功。

## 上游测试清点

- 清点官方 tarball 的全部文件名及 Makefile/make/Makefile.inc 目标。
- 无 tests 目录、自动测试源文件、test/check 目标或测试框架注册；上游自动化测试数为 0。
- examples 下 3 个用户示例（dumbplay 依赖 Allegro，dumbout/dumb2wav 无需 Allegro）不计为自动测试。
- 新增 4 个独立消费者检查场景，详见 test_package/MANIFEST.yml。

## 真机验证

- 2026-10-09：HarmonyOS HongMeng Kernel 1.12.0，aarch64。
- 原始 Makefile 的 Release/Debug 库与两个核心示例构建返回 0。
- 第一次 Conan 构建发现 AutotoolsToolchain 未默认设置 CC/AR；配方通过工具链环境声明 clang/llvm-ar，保持编译选项由 Conan 生成。
- Conan create 返回 0；安装后的公开头文件和静态库通过 CMakeDeps 的 `libdumb::libdumb` 被消费者链接。
- 新增场景 4/4 通过：memory_io、mod_decode、stereo_pcm_render、invalid_and_missing_module。
- MOD fixture 包含非零循环样本及音符；渲染返回恰好 4096 帧，验证非静音、立体声和位置前进。
- 本次未增加 IT/XM/S3M 的正向格式 fixture，不宣称这三种格式已取得独立运行验证。
- 原始 Conan 日志 `create-fixed.log` SHA256：`ae26617f7b53fc37de5aaa59846871d903d7e6c1c1f6845a1897c396eac5a9d5`。
- 上游自动测试通过率为 N/A（0 项），不写成 100%。
- 最终配方经官方 `finish` 的 W3 原生构建门禁通过；L0/L1/L4/L5 通过，L1e 移走库和头文件后消费者按预期失败。
- 最终 `w3-local-ci.log` SHA256：`a8a196b16d0a4063b1e6af66b4c041cfcdc460a16cbe841ea4e6d46011ea1b17`；工具生成的 `.ci-result.json` 与日志一致，未手工改写。
- 工具打包模块从已验证的 Conan 安装目录生成静态库制品，返回 0。原始日志和预编译包留作本地证据，不提交到 Git。

## 最终状态

编译结束：built。核心库及消费者场景已在真机验证，积分赛 PR #15157 已提交。

## 2026-10-10 鸿蒙特有测试补全

- 新增独立场景 `ohos_arm64_storage_mod_decode`，鸿蒙特有测试数从 0 增为 1；通用消费者场景仍为 4，新增测试合计 5 项。
- 运行时校验 HarmonyOS、aarch64 和 64 位指针。在 TMPDIR（未设置时使用 HOME）的应用存储路径中创建独立目录及中文文件名的 MOD，调用 `dumb_load_mod` 真实读取，渲染并校验 4096 帧非零立体声 PCM、通道数与播放位置，最后清理夹具。
- 测试由 OHOS Conan 设置启用，失败返回非零；非 OHOS 环境不将其计为已运行的平台测试。
- 真机 W3 本地构建验证通过，原 4 项和新增 1 项均 PASS（5/5），L1e 负向制品验证通过。
- 本次 W3 原始日志 SHA256：`63615745161b913e88678e686ca7fbd79ff52fe8c7d46b79f4816e0c5d5fd854`。
- 此结果是本地真机验证；远端 CI 曾因运行器 fork 失败，不能据此宣称远端 CI 已通过。
