# libyuv 0.0.1949.20260706 适配记录

## W0 / issue

- 在项目归档、适配建议和当前会话上下文中未找到明确 issue 编号，交接时标记为“issue 待补”。
- 无必需 Conan 依赖。JPEG 是上游可选能力；本配方关闭 `LIBYUV_DISABLE_JPEG`，避免把未确认发布的 JPEG 依赖混入本 PR。

## 源码与构建

- 构建系统：上游 CMake，最低 CMake 3.16。
- 源码固定到官方 Chromium Gitiles 的 libyuv commit `2dd4257364d39c38d79465c4ddc4b93137fe729b`，官方归档 sha256 记录在 `conandata.yml`；该归档解压后的 191 个源码文件与此前真机验证快照逐一 SHA256 一致。
- 上游 CMake 定义静态/共享库、`cpuid`、`yuvconvert`、`yuvconstants`；配方通过 CMakeToolchain 安装库、头文件和工具。
- `UNIT_TEST=OFF`：上游单元测试依赖 GoogleTest，且本轮没有可发布的 gtest 依赖；消费者测试改为直接调用 `I420ToARGB`。

## 本机验证与下一步

- 已完成源码下载、SHA256 校验、CMakeLists 构建系统和头文件/API 静态分析。
- Windows 主机没有可用的 CMake 命令；已在 HarmonyOS aarch64 真机完成实际 `conan create` 和单包 CI 验证。
- 真机/shadow CI 单包命令：`CI_PACKAGES="archives/l/libyuv/0.0.1949.20260706" zsh ci/conan/build_and_test.sh`
- 真机前需确认隔离 Conan profile 含 `OHOS` setting、`TMPDIR=$RUN_DIR/tmp`，并按单包队列运行；再补 issue 编号和最终 CI 结果。
- 首次真机编译发现 OHOS Conan toolchain 未设置 `CMAKE_SYSTEM_PROCESSOR`，导致 NEON/SVE2 符号未定义；配方已显式设置为 `aarch64`，需重跑验证。
- 第二次验证仍未生成 AArch64 专用对象，追加官方支持的 `LIBYUV_DISABLE_NEON/SVE/SVE2` 宏，优先验证通用实现链路。
- 第三次真机验证成功：run `codex-0.0.1949.20260706-libyuv-0.0.1949.20260706-conan-20260916-092639-48593`；Conan create、test_package、`yuvconvert --version` 和 L1e 反向依赖测试均通过（Build Summary: Total 1, Success 1）。
- GoogleTest 通过 `tool_requires("gtest/1.17.0")` 补齐，只参与真机原生构建期，不进入 libyuv 运行时依赖。最终 run `codex-0.0.1949.20260706-libyuv-0.0.1949.20260706-conan-20260916-095030-64960` 执行上游 18 个测试源文件生成的 3541 个用例（8 suites），3541/3541 通过；单包 L0/L1/L2/L4/L5 全部通过。

## 平台 CI 阻塞与依赖版本修正

- 平台 CI 三次失败（build `#48566` / `#48571` / `#49081`）均停在 L0，报 `registry_unreachable`，未进入编译。2026-09-26 复核确认不是 worker 网络故障：同一时段其它 PR（如 `#12947`，build `#61987`）CI 全绿。
- 真实原因：配方此前声明的 `gtest/1.14.0` 在 `ohpcd` 制品仓中不存在。`conan list "gtest/*" -r=ohpcd` 只有 `1.17.0`、`1.17.0.1`、`1.17.0.2`；`conan download gtest/1.17.0 -r=ohpcd --only-recipe` 成功，而 `gtest/1.14.0` 返回 `ERROR: error:system acceleration policy not enabled. [Remote: ohpcd]`（cnb.cool 对不存在包的通用应答），CI 的 L0i 依赖门禁把它归类成 `registry_unreachable`，掩盖了真实原因。
- 修正：`tool_requires` 由 `gtest/1.14.0` 改为 `gtest/1.17.0`（仓库内其余 8 个使用 gtest 的配方统一使用该版本）。gtest 1.17.0 的已发布二进制（package_id `21b17f8b2bc0e9511e276e3d57a23893067cefe5`，OHOS 6.0 / armv8 / clang 15 / libc++ / cppstd 17 / Release）包含 `lib/libgtest.a` 与 `include/gtest/`，与配方 `GTEST_LIBRARY`、`-I<gtest>/include` 的既有假设一致；上游 `unit_test/unit_test.cc` 自带 `main()`，不需要 `gtest_main`；CI profile 已固定 `compiler.cppstd=17`，满足 gtest 1.17 头文件的 C++17 下限。日志与布局证据见 `reports/knowledge-evidence.md` EVID-04 / EVID-05。
- 影响面：gtest 只用于原生构建期启用 `libyuv_unittest`，不进入 libyuv 产物或运行时依赖；SIMD 回退标志、源码、`test_package` 均未改动。
- 待办：按 `reports/knowledge-evidence.md` 的约定，依赖版本变更须重新执行真机验证；本机（Windows，无 OHOS 工具链）无法复现，改由 PR CI 在真机重新验证构建与上游 3541 个用例。

## 已知风险：官方归档 SHA256 不可复现（已通过更换取源主机解决）

- `conandata.yml` 原本使用 Chromium Gitiles 的 `+archive/<commit>.tar.gz`。该接口是现打 tar，条目 mtime 取打包时刻而非 commit 时间，因此同一 URL 两次下载得到不同 SHA256：2026-09-26 两次下载分别为 `00f32902375f2c89b346c134c7763a0b3bcd8d81b18a252181bc5151a0102f7f`（607756 B）与 `2d1bd81c69148c6163056a2545d73cfb3b9131ac7885512d7c5264125977c8c8`（607799 B），字节差异仅出现在 tar 头的 mtime 字段，两次解压出的 191 个源码文件逐一字节相同。
- 该 commit `2dd4257364d39c38d79465c4ddc4b93137fe729b` 只存在于官方 Gitiles：官方 GitHub 镜像仓库 `libyuv/libyuv` 已返回 404，GitCode 镜像 `gh_mirrors/li/libyuv` 的 `main` 停在 `a09d909f63888d6513c47886d00eb37f28205983`。
- 平台 CI 实测（build `#61999`，2026-09-26）确认 worker 无法访问 `chromium.googlesource.com`：`conan create` 在 `get()` 阶段报 `ConnectTimeoutError ... Connection to chromium.googlesource.com timed out. (connect timeout=30)`，L1 失败并提示"源码下载失败，请检查 conandata.yml 中 URL 是否可访问"。
- 处理：改用同一 commit 的 GitLab 镜像工程归档接口。`https://gitlab.com/api/v4/projects/11344580/repository/archive.tar.gz?sha=2dd4257364d39c38d79465c4ddc4b93137fe729b` 两次下载字节完全一致（600397 B，SHA256 `69c3de784395ee5e527aa67e421beadbeb72beb60a55ffed70f93c8357e83040`）；另外两个独立 GitLab 镜像（project `86586703`、`32947410`）对同一 commit 返回的归档字节与哈希完全相同，可作为哈希独立复核。解压出的 191 个文件与此前真机验证快照逐一 SHA256 一致，因此配方、SIMD 标志、测试源与已验证行为均未改变。
- `conandata.yml` 内已用注释记录上游工程地址、钉定 commit 与更换取源主机的原因。GitLab 网页版 `/-/archive/` 路径被 Cloudflare 拦截（403），故使用 API 归档路径。
- 平台 CI 实测（build `#62006`，2026-09-26）确认 GitLab 归档 URL 在 worker 上可用，但暴露出第二个配方级问题：`get()` 无法从该 URL 推导文件名（URL 以 `?sha=...` 查询串结尾），报 `Cannot deduce file name from the url ... Use 'filename' parameter.`。已补 `sources.filename: libyuv-<commit>.tar.gz`（仓库内另有 169 个配方使用同一 `filename` 字段）。本机用 `conan source` 实测：下载 + SHA256 校验通过，解压出的 191 个源码文件与此前真机验证快照逐一 SHA256 一致。
- 同时把注释里的上游 URL 改写为非 URL 文本：CI 的预下载步骤用宽松正则扫描 `conandata.yml` 全文（注释也算），会把注释里的裸 URL 当成第二个源码地址去下载，产生无意义的失败重试噪音。
