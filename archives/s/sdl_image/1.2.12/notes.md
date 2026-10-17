# sdl_image 1.2.12 适配笔记

## W0/W0b/W1 与来源

- 官方源：`https://www.libsdl.org/projects/SDL_image/release/SDL_image-1.2.12.tar.gz`
- SHA256：`0b90722984561004de84847744d566809dbb9daf732a9e503b91a1b5a84e5699`
- W0：精确依赖探针通过：sdl12-compat/1.2.68、libpng/1.6.39、libjpeg-turbo/3.2.0、libtiff/4.7.2、libwebp/1.6.0。
- W0b：upstream/main 无 sdl_image 1.2.12 历史归档或 notes.md。
- W1：worktree 基于 upstream/main `5dff0c6a5c`，分支 `feat/sdl_image-1.2.12`。

## 构建与配方

- 构建系统：Autotools；包类型：静态库。
- `sdl12-compat` 的已发布包提供 SDL 1.2 ABI，但没有 legacy `sdl-config` 命令；recipe 在 Conan build folder 生成可复现的 sdl-config wrapper，并显式传入 `SDL_CONFIG`。
- 老版本 configure 使用 `aarch64-unknown-linux-gnu` build/host tuple；设备 clang 的实际 target 仍为 `aarch64-unknown-linux-ohos`。直接传 OHOS tuple 会被上游 config.sub 拒绝。
- `configure` 中两处 `umask 077` 改为 `022`，通过 `refresh-patch --auto` 生成 `0001-configure.patch`，避免 HMDFS 的 confXXXXXX 不可写。
- JPEG、PNG、TIFF、WebP 依赖均使用已发布 Conan 配方；zlib 通过 `override=True` 统一到 `zlib/1.3.1.1`，消除 libpng/libtiff 传递版本冲突。
- `cpp_info.requires` 声明 SDL 兼容层和 codec 依赖；消费者测试额外显式补入已发布 sdl12-compat 的 `include/SDL` 根目录，因为该已发布包的 CMake metadata 未传出该 include 路径。

## 测试四维账本

| 维度 | 数量 | 证据 |
|---|---:|---|
| 上游静态声明 | 0 | 上游 Makefile.am 无测试目录、测试注册宏或 check 目标 |
| 构建系统注册 | 0 | `make -n check` 无上游测试注册 |
| 实际执行 | 0 | 上游无测试入口 |
| 通过/失败/跳过 | 0 / 0 / 0 | 无上游测试 |
| 新增消费者程序 | 1 | `test_package/test.c` |
| 消费者断言 | 2 | `IMG_Linked_Version` 版本断言、`IMG_Init(0)` 行为断言 |

## 验证结果

- Conan G1/G2/G3/G4/L2/L4/L5：通过。
- 真实 `test_package`：CMake 编译并运行 SDL_image API，2/2 断言通过。
- W3 本地 CI：finish 阶段通过；finish 的通用 G0 clean-verify 受 HMDFS shell/临时目录限制产生非阻塞警告，配方级 Conan 验证和 W3 已通过。

## 路径判断

- 三项 legacy SDL 组件共同验证了 `sdl-config` wrapper、旧 `config.sub`/`umask` 处理和已发布 `sdl12-compat` CMake include 缺口，但这些证据都来自同一仓库内的相关归档，尚无跨仓库触发与知识库新增证据。因此本任务按路径 A 交付，不把单库补丁或同仓库复用冒充路径 B。

---

**编译结束**: 2026-09-15 22:35
**最终状态**: built
**finish/W3**: 设备 finish 与 current-HEAD W3 通过；L0/L1/L4/L5 通过，L2 因无 bin 目录跳过；当前结果见任务临时目录。
