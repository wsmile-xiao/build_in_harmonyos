# SoundTouch homebrew — 编译笔记

## 软件信息

- **名称**: SoundTouch — 音频处理库，用于独立调整音频的节奏(tempo)、音高(pitch)和播放速率(rate)
- **版本**: homebrew (上游 2.4.1, Homebrew 公式版本)
- **许可证**: LGPL v2.1
- **构建系统**: cmake (上游源码包同时支持 CMake 和 Autotools；使用 CMake 避免 automake 依赖)
- **目标平台**: OHOS aarch64 (鸿蒙系统)
- **上游仓库**: https://codeberg.org/soundtouch/soundtouch
- **Homebrew 公式**: https://github.com/Homebrew/homebrew-core/blob/master/Formula/s/sound-touch.rb

## 编译步骤

1. **Apply patches**: `apply_conandata_patches(self)` (soundtouch_config.h)
2. **Configure**: `cmake.configure()` (with `-DNEON=OFF` to disable NEON)
3. **编译**: `cmake.build()`
4. **安装**: `cmake.install()`

## 关键问题与解决方案

### 问题 1: __powidf2 运行时符号未找到

**现象**: 运行 soundstretch 或加载 libSoundTouch.so 时报错:
```
Error relocating: __powidf2: symbol not found
```

**根因**: OHOS aarch64 的 clang 编译器在 C++ 代码中调用 `pow()` 时，
会生成对 `__powidf2` (软浮点双精度幂函数) 的调用。该符号存在于
OHOS SDK 的 `libclang_rt.builtins.a` 中，而非 libc 或 libm。
默认链接标志 `-lm` 不包含此库。

**解决方案**: 在 CMakeToolchain 中设置 `CMAKE_EXE_LINKER_FLAGS` 和
`CMAKE_SHARED_LINKER_FLAGS` 添加 `-lclang_rt.builtins`，将所需
运行时符号静态吸收到共享库和二进制文件中。

**验证**:
```
llvm-nm libSoundTouch.so.1.0.0 | grep powidf
→ 0000000000012338 t __powidf2  (本地符号，已在库内部)
```

**影响范围**: 所有在 OHOS aarch64 上使用 `pow()` 或 `sqrt()` 的 C++ 软件
都可能遇到此问题，需要链接 `-lclang_rt.builtins`。

**知识条目**: E098 (ref: E098)

### 问题 2: automake 缺失导致 bootstrap 失败 (CI 修复)

**现象**: CI worker 缺少 `automake`(aclocal)，导致 `./bootstrap` (autoreconf) 失败。

**根因**: 上游源码包不含 `configure` 和 `Makefile.in`，需先运行 bootstrap；
但 CI worker 只安装了 `autoconf`，未安装 `automake`。

**解决方案**: 将构建系统从 Autotools 切换为 CMake。上游源码包含完整的
`CMakeLists.txt`，CMake 在 CI worker 上可用（设置了 `CMAKE_PREFIX_PATH`）。
无需 bootstrap，无需 automake 依赖。

### 问题 3: NEON 优化不兼容

**现象**: SoundTouch 的 NEON 汇编优化代码与 OHOS aarch64 工具链不兼容。

**解决方案**: CMake 配置时设置 `-DNEON=OFF`。

**知识条目**: E099 (ref: E099)

### 问题 4: 源码包不含 configure 脚本

**现象**: soundtouch-2.4.1.tar.gz 中没有 configure 脚本。

**解决方案**: 不再使用 Autotools，改用上游提供的 `CMakeLists.txt` 构建。

## 测试结果

项目上游无自动化测试套件 (`make check` 无实际测试)。
功能测试通过 test_package 中的消费者测试验证。

## CI 修复记录

### 问题 5: codeberg.org 源码下载 429 限流（第 1 轮）

**现象**: CI 构建时 `conan create` 在 `source()` 步骤失败:
```
Error 429 downloading file https://codeberg.org/soundtouch/soundtouch/archive/2.4.1.tar.gz
```

**根因**: codeberg.org 对 CI worker IP 的匿名请求返回 HTTP 429 (Too Many Requests / 限流)。

**解决方案**: 在 conandata.yml 添加 `mirror_url` 指向 `ghproxy.com` 代理源，在 conanfile.py 的 `source()` 方法中添加镜像降级逻辑：主 URL 失败后自动尝试镜像源。

**结果**: ghproxy.com 在 CI worker 上 connect timeout（不可达），修复失败。

**生效范围**: `sound-touch/2.4.1` 和 `sound-touch/homebrew` 两个版本均需同步修改。

### 问题 6: codeberg.org 源码下载 429 限流（第 2 轮）

**现象**: 第 1 轮修复（ghproxy.com 镜像）因 ghproxy.com 在 CI worker 上不可达而失败。
两版本均因 `Source fetch failed` 构建失败（Build #4755, error_signature: source_fetch:d2b1adf23cce）。

**根因**: ghproxy.com 代理服务在 CI worker 网络环境下连接超时。

**解决方案**: 将 `mirror_url` 从 `ghproxy.com` 更换为 `ghfast.top`，该代理在仓库中已有成功使用案例。

**生效范围**: `sound-touch/2.4.1` 和 `sound-touch/homebrew` 两个版本均需同步修改。

### 问题 7: codeberg.org 源码下载 429 限流（第 3 轮）

**现象**: 第 2 轮修复（ghfast.top 镜像）因 ghfast.top 返回 HTTP 403 Forbidden 而失败。
两版本均因 `AuthenticationException: 403: FORBIDDEN` 构建失败（Build #4787, error_signature: code:14c1ff41a8d9）。

**根因**: ghfast.top 代理服务拒绝代理 codeberg.org 的 URL 请求，返回 403 禁止访问。

**解决方案**: 将 `mirror_url` 从 `ghfast.top` 更换为 `gh-proxy.com`。

**生效范围**: `sound-touch/2.4.1` 和 `sound-touch/homebrew` 两个版本均需同步修改。

### 问题 8: 收缩 PR 范围并改用正式发布包

**现象**: Build #4807 同时构建 `2.4.1` 与任务指定的 `homebrew`，且 `gh-proxy.com` 继续超时并返回 403。

**根因**: 首次适配错误地提交了同一软件的两个版本；连续使用未经 CI 验证的临时代理也没有消除源码获取风险。

**解决方案**: PR 仅保留 `homebrew` 版本。源码改为 SoundTouch 官方 2.4.1 发布包，回退地址使用 BLFS 的 OSUOSL 归档镜像；两者使用同一正式发布包，已核验 SHA256 为 `e07abf20ce8f95850c280132e1f61ad400fc1f4011b7fac698a503de6aab6733`。

### 问题 9: automake 缺失（第 4 轮 — 当前修复）

**现象**: Build #4838 的 conan-build-test 步骤失败，错误为 `Can't exec "aclocal": No such file or directory`。
CI worker 安装了 autoconf 但未安装 automake，导致 `./bootstrap` (autoreconf) 失败。

**根因**: CI worker 缺少 `automake` 包（提供 aclocal 命令），autoreconf 无法执行。

**解决方案**: 将构建系统从 Autotools 切换为上游已支持的 CMake，无需 bootstrap 步骤，
无需 automake/aclocal 依赖。CMake 在 CI worker 上可用（配置了 CMAKE_PREFIX_PATH）。
同时移除 autotools 专用补丁 0002 (SoundStretch-Makefile.am) 和 0003 (SoundTouch-Makefile.am)。

## 安装产物

| 产物 | 路径 | 说明 |
|------|------|------|
| libSoundTouch.so.1.0.0 | lib/ | 主共享库 |
| soundstretch | bin/ | 命令行工具 |
| SoundTouch.h 等 | include/soundtouch/ | 开发头文件 |
| soundtouch.pc | lib/pkgconfig/ | pkg-config 文件 |

---

**编译日期**: 2026-07-17
**最终状态**: built
