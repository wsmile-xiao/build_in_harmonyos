# blupimania 1.6.3 适配笔记

## 编译环境
- 构建系统: CMake（上游唯一构建入口 `CMakeLists.txt`，cmake_minimum_required 3.2）
- 编译日期: 2026-09-07
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos)
- 状态: built（设备本地 W3 验证）

## 软件形态
- 上游 `blupi-games/blupimania` tag `v1.6.3`，纯 C（10 个 .c，lang-preflight 判 c，与任务声明 cpp 属兼容族）。
- 产物为**单个可执行文件** `blupimania`（GUI 游戏，SDL2 抽象平台层），无任何库目标。
- 源码自带 argtable3 捆绑副本与 SDL_image webp 加载 shim（`src/sdl/SDL3_IMG_webp.c`，直接链接 libwebp/libwebpdemux 符号，非 dlopen）。
- `main()` 位于 `src/play.c:5817`；`PlayInit`→`OpenMachine` 先经 argtable3 解析参数再 `SDL_Init`，故 `--version`/`--help` 在无显示环境可真实执行并以 0 退出（`OpenMachine` 返回 -1 时 `PlayInit` 返回 0）。

## 依赖（W0 全部已在 ohpcd 发布，conan download --only-recipe 逐个解析通过）
- sdl2/2.30.10（sdl2_mixer/2.8.2 与 sdl2-image/2.8.12 均硬锁此版本，避免版本冲突）
- sdl2-image/2.8.12（cmake 包名 SDL2_image）
- sdl2_mixer/2.8.2（无 cmake_file_name 属性，需注入 SDL2_mixer）
- libwebp/1.6.0（cmake 包名 WebP，仅暴露 WebP::webp）

## OHOS 适配要点

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 4.x 拒绝 cmake_minimum_required(3.2) | CMake 4 移除 <3.5 兼容 | CMAKE_POLICY_VERSION_MINIMUM=3.5（ballerburg/cdogs-sdl 先例） |
| 2 | E092：CMake 不识别 HarmonyOS | CMake 无 OHOS 平台模块 | CMAKE_SYSTEM_NAME=Linux + CMAKE_SYSTEM_PROCESSOR=aarch64（sdl2-image 先例） |
| 3 | 上游动态分支链接 `WebP::webpdemux`，conan libwebp 只暴露 `WebP::webp` | libwebp 配方 cmake_target_name 单一 | generate() 注入 `WebP::webpdemux` imported target 的 CMake build module（sdl2-image/2.8.12 同法，指向包内 libwebpdemux.so） |
| 4 | `find_package(SDL2_mixer)` 找不到 | CMakeDeps 配置文件名默认取 conan 包名 sdl2_mixer（大小写/命名不符） | CMakeDeps `set_property("sdl2_mixer", "cmake_file_name", "SDL2_mixer")` |
| 5 | libwebp.so/libtiff.so 等共享依赖传递 NEEDED | 链接期需要 -L/-rpath-link | 汇总全部依赖 libdirs 注入 CMAKE_EXE_LINKER_FLAGS（sdl2-image 同法） |
| 6 | OHOS 未签名 ELF 不可执行 | 平台签名要求 | package() 对 bin/blupimania 用 binary-sign-tool 自签（libwebp 配方 _sign_shared_libs 同法） |

## 上游测试清点（R51 三步法，第 1 步）

- v1.6.3 源码树无 `tests/` 目录；`CMakeLists.txt` 无 `enable_testing`/`add_test`/CTest 入口；无 `make check` 目标；GitHub Actions（`.github/workflows/build-linux-dynamic.yml`）仅做 configure+build，不跑测试。
- **上游静态测试总数 N_static = 0**（如实申报，无任何测试入口可执行）。
- 补救：新增消费者测试（见下），并在 build() 保留 `ctest --output-on-failure || true` 执行痕迹（"No tests found" 如实记录，sdl2_mixer/2.8.2 先例）。

### 对话 #1（2026-09-07，设备本地）

- 任务: #6028 blupimania 1.6.3（活动: 开源鸿蒙PC专项积分赛），分支 feat/blupimania-1.6.3，基线 upstream/main d142b34656。
- W0: 依赖 sdl2/2.30.10、sdl2-image/2.8.12、sdl2_mixer/2.8.2、libwebp/1.6.0 经 `conan download --only-recipe` 逐个解析通过。
- W0b: 仓库无同软件历史归档；lang-preflight 判 c（任务声明 cpp，兼容族），CMake 构建，无语言/工具链缺口。
- 构建（conan create，profile ci/conan/profiles/ohos-aarch64）:
  - 第 1 次失败: CMake generate 阶段 `SDL2::SDL2` target 不存在（sdl2 配方无 cmake 属性，CMakeDeps 默认小写 `sdl2::sdl2`）→ CMakeDeps `set_property("sdl2", "cmake_target_name", "SDL2::SDL2")`；`MATH_LIBRARY` NOTFOUND（musl 无独立 libm）→ 置空缓存变量（ballerburg 先例）。
  - 第 2 次失败: `SDL2_mixer::SDL2_mixer` 同理 → `set_property("sdl2_mixer", "cmake_file_name", "SDL2_mixer")` + `cmake_target_name`；注意 cmake_target_name 必须写完整 `X::Y` 形态（CMakeDeps 不自动补命名空间）。
  - 第 3 次成功: configure + build + package 全绿，test_package 消费者测试 1/1（`blupimania --version` 输出 1.6.3，退出码 0）。
- conan-verify 首跑 G2 失败: conan-verify 经 /usr/local/bin/conan wrapper 启动，注入 SDK `LD_LIBRARY_PATH`（llvm/lib/aarch64-linux-ohos），与 `binary-sign-tool` 链接的 OHOS 系统 libc++ ABI 冲突 → 配方签名步骤改 `env -u LD_LIBRARY_PATH`；重跑 conan-verify 全门禁（G0-G4/L2/L4/L5）PASS。
- W3: 首跑 JC6 假失败（fork 过期基线扫出上游 37 个既有包）→ 先精确提交 8 个交付文件，`git diff upstream/main...HEAD > ~/tmp/uc2/blupimania/pr.diff`，`JUNK_PR_DIFF` 指向该文件重跑，W3 PASS。
- verify-build PASS；PackageBuilder 打包 `blupimania-1.6.3-ohos-aarch64.tar.gz`（19407KB）+ debug 包；`.staging-verified` 创建。

### 对话 #2（2026-09-07）

- finalize 补齐软件级 README.md；notes.md 补对话记录章节；重跑 finish 确认 step10 就绪。

## 消费者测试（test_package）

- `test.sh` 在 conanrun 环境中运行打包产物 `blupimania --version`：
  - argtable3 在 `SDL_Init` **之前**解析 `-V/--version`，打印 `BLUPIMANIA_VERSION_STR`（即 `1.6.3`）并经 `main` 以退出码 0 返回——不依赖显示/音频设备，可无头执行；
  - 断言输出包含 `1.6.3` 且退出码为 0（验证参数解析、版本宏编译与动态链接全链路真实可用）。
- 可执行文件已由 package() 自签，test_package 运行的是**打包产物本身**（非重新编译的测试程序），删除产物即测试失败（L1e 反向验证有效）。

## 已知限制

- GUI 主循环需要真实显示（OHOS 图形栈），无法在无头 CI 中完整启动游戏；消费者测试覆盖 `--version` 真实行为路径（argtable 解析→版本宏→退出码），主循环逻辑未执行，如实申报。
- 上游无测试套件，无跳过/失败用例可报；通过率按"静态全量 0，执行 0；消费者测试 1/1"口径申报。
---

**编译结束**: 2026-09-07 10:18
**最终状态**: built
