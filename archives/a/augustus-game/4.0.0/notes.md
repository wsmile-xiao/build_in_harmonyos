# augustus-game 4.0.0 适配笔记

## 当前状态

- 分支：`feat/augustus-game-4.0.0`
- issue：不单独创建；本任务按用户指令以路径 B（知识库扩展）提交。历史
  issue #2462 对应基因预测软件 `augustus`，不能复用于本游戏包。
- 2026-09-05：从已关闭未合并的 PR #6662 移植完整配方、4 个补丁、真实
  `--version` 冒烟测试和 SDK lld/libxml2 环境守卫到当前 `origin/main` 基线。
- 历史状态：PR #6662 曾完成 OHOS/aarch64 构建与测试；该 PR 已关闭且未合并，
  历史通过记录不能替代当前 main 基线复验。
- 当前状态：2026-09-05 真机低内存 direct `conan create` 与
  `test_package` 通过；已按 R38 在软件级目录声明 `commands.json`，
  CI 结果以后续 PR #8388 构建为准。
- 本轮 rebase 后的基线提交 `d1c90bb03a` 已推送 fork；expat 修复已随最新
  同名分支再次推送。

## 源码与构建系统

- 上游：`https://github.com/Keriew/augustus/archive/refs/tags/v4.0.0.tar.gz`
- SHA256：`d95957ccf7b66cec80d787692ff857a7a1558eccfa1927e22f717891b2dfb4a2`
- 语言与构建：C + CMake，要求 CMake 3.1 至 3.27。
- 产物：`bin/augustus` 与 `share/augustus-game/assets`；Conan 包类型为 application。
- 上游没有集成进 CMake 的自动化测试；`test/` 主要为游戏数据而非单元测试。

## W0 依赖

- `sdl2/2.30.10`：当前 main 存在静态库配方。
- `sdl2_mixer/2.8.1`：当前 main 存在静态库配方，依赖 SDL2。
- 隔离 Conan home 的 `ohpcd` recipe download 复验通过，revision 分别为
  `9a6fd1dbbc0ac1eef2a42639df48e3b4` 与
  `1e536fb289a65d493119ed5286413696`；graph info 显示二者对应 OHOS
  二进制包均可在 `ohpcd` 下载。
- 若制品仓复验发现依赖缺失，先为依赖库单独建立 issue、分支和 PR，不把依赖
  适配混入本包。

## 补丁说明

- `0001-CMakeLists.txt.patch`：静态链接时把 `SDL2_MIXER_LIBRARY` 放在
  `SDL2_LIBRARY` 前，保证符号按依赖顺序解析。
- `0002-src-platform-arguments.c.patch`：解析 `--version` 并写入
  `augustus_args.print_version`。
- `0003-src-platform-arguments.h.patch`：为 `augustus_args` 增加
  `print_version` 字段。
- `0004-src-platform-augustus.c.patch`：在 SDL/音频初始化前打印版本并退出，
  用于无显示、无 OSS/dsp 音频设备环境下的冒烟验证。
- `0005-CMakeLists.txt-use-bundled-expat-safely.patch`：仅当
  `EXPAT_FOUND` 且上游读取的大写 `EXPAT_INCLUDE_DIRS` 与
  `EXPAT_LIBRARIES` 完整时使用外部 expat；否则回退到上游内置 expat，
  并将内置 include 固定为 `${PROJECT_SOURCE_DIR}/ext/expat`。

## 配方要点

- 上游自带 MODULE 模式 `FindSDL2.cmake` 与 `FindSDL2_mixer.cmake`，不消费
  `CMAKE_PREFIX_PATH`；配方通过 `CMakeToolchain.variables` 注入
  `SDL2_INCLUDE_DIR`、`SDL2_LIBRARY`、`SDL2_LIBRARY_TEMP`、
  `SDL2_MIXER_INCLUDE_DIR` 与 `SDL2_MIXER_LIBRARY`。
- `SDL2_LIBRARY_TEMP` 必须一并注入，防止 MODULE 模块的 `FIND_LIBRARY`
  用系统库覆盖 Conan 依赖路径。
- CI 环境的 `LD_LIBRARY_PATH` 可能遮蔽 SDK lld 的 RUNPATH，导致 lld 加载
  ABI 不匹配的 `libxml2.so.16`；配方从实际 C 编译器路径推导 SDK `llvm/lib`，
  校验存在后前置到构建与安装环境的 `LD_LIBRARY_PATH`。
- `test_package/test.sh` 为 POSIX shell 脚本，执行包内 `bin/augustus --version`，
  断言退出码为 0 且输出包含 `augustus` 与 `4.0.0`。
- 设备用户前缀存在 `expat-config.cmake` 时，CMake 会设置 `EXPAT_FOUND`，但该
  Config 只导出小写变量；补丁 0005 要求上游读取的大写 include/library 变量
  完整后才消费外部 expat，否则使用上游内置源码，避免设备环境泄漏进包图。

## 2026-09-05 本机验证记录

- 官方 tag tarball SHA256 复验为
  `d95957ccf7b66cec80d787692ff857a7a1558eccfa1927e22f717891b2dfb4a2`。
- 5 个补丁均在 pristine v4.0.0 源码上通过 `git apply --check`。
- 主配方与 `test_package/conanfile.py` 通过 `python -m py_compile`。
- 目标目录内 YAML 与 JSON 均通过解析；`test_package/test.sh` 通过 `sh -n`。
- `conan export .` 通过，导出 revision 为
  `08bafe30778b4f56c43f12bd58ebbd07`。
- 使用 CI 同源的 OHOS 适配版 Conan 2.29.1 与项目 profile 完成 `graph info`：
  根包 package_id 为 `1ba600bd6dc3c3341e03f6d77d2093bce84e4d18`，
  依赖图解析成功。stock Conan 2.31.2 因缓存 settings 缺少 `OHOS` 枚举，
  不能直接读取项目 profile；真机/shadow 环境按 `ci/conan/setup.sh` 刷新后可用。
- 仓库 L0 pre-commit 通过；唯一 warning 是保留官方 GitHub 源 URL，符合镜像
  注入机制。
- `scripts/ohc/preflight.py` 通过。R38 所需的软件级 `commands.json` 已加入，
  声明 `4.0.0` 产物为可执行工具；这不改变配方内容，direct OHOS 验证结论
  仍适用。

## 2026-09-05 真机 direct 验证记录

- 真机 SSH：`ssh -T -p 2222 -i ~/.ssh/id_rsa currentUser@10.62.220.52`。
- 因 GitHub 原始 URL 在真机上长时间挂起，临时将远端 sparse checkout 的
  `conandata.yml` 指向已下载的 `file://` tarball；该 tarball SHA256 复验为
  `d95957ccf7b66cec80d787692ff857a7a1558eccfa1927e22f717891b2dfb4a2`。
  本地 PR 文件继续保持官方 GitHub URL。
- 低内存策略：heavy lock、隔离 `CONAN_HOME`、`tools.build:jobs=1`、
  `CMAKE_BUILD_PARALLEL_LEVEL=1`、`MAKEFLAGS=-j1`；watchdog 每 10 秒检查
  `MemAvailable`，阈值 2097152 kB。成功运行未触发 watchdog；运行结束后
  `MemAvailable` 为 15310848 kB。
- 成功 run：
  `/storage/Users/currentUser/ohos-test-runs/codex-augustus-game-augustus-game-augustus-game-4.0.0-r2-sparse-20260905-direct-local-source-20260905-124522-26994`。
  运行时间为 UTC `04:45:23` 至 `04:47:56`，退出码 0。
- Conan 完整引用：
  `augustus-game/4.0.0#7ffcd1a2ad4168ed6307a347c4e347fc:1ba600bd6dc3c3341e03f6d77d2093bce84e4d18#ba2b649bfe803756abd7d069e40c6926`。
- 生成 `flags.make` 包含绝对路径 `ext/expat`；link 命令包含
  `ext/expat/xmlparse.c.obj`、`xmlrole.c.obj`、`xmltok.c.obj`，未链接设备前缀的
  `libexpat.so`。
- `test_package` 实际运行包内二进制，输出
  `augustus 4.0.0 (ARM64 build)`，退出码 0。
- 产物 `bin/augustus` 为 ELF 64-bit arm64、musl 动态链接可执行程序，SHA256 为
  `f080131bf61ee765573a3864bd9fb52996aec9e757b62acf8b98d12e31c33cc8`。
- 单包 shadow CI 曾在
  `/storage/Users/currentUser/ohos-test-runs/codex-augustus-game-augustus-game-augustus-game-4.0.0-r2-sparse-20260905-conan-20260905-122455-15856`
  运行，L0k 因当时缺少 `commands.json` 失败且未进入编译；该失败已由软件级
  声明修复，需以下一轮 CI 复验为准。

## 下一步验证命令

在仓库根目录使用真机或 shadow CI 单包执行：

```bash
CI_PACKAGES="archives/a/augustus-game/4.0.0" zsh ci/conan/build_and_test.sh
```

如需直接 Conan 复验：

```bash
conan create archives/a/augustus-game/4.0.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

## 历史验证归属

以下结果属于 2026-08-26 的已关闭 PR #6662，不代表当前 main 移植后的复验：

- `conan create` 生成 package `1ba600bd6dc3c3341e03f6d77d2093bce84e4d18`。
- `augustus --version` 输出 `augustus 4.0.0 (ARM64 build)`，退出码 0。
- 旧配方曾通过本机 conan-verify；后续 CI 分别暴露 worker 网络与 lld 动态库
  遮蔽问题，最终配方加入 SDK linker 环境守卫并保留官方源 URL。
