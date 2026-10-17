# sdl_ttf 2.0.11 适配笔记

## W0/W0b/W1 与来源

- 官方源：`https://www.libsdl.org/projects/SDL_ttf/release/SDL_ttf-2.0.11.tar.gz`
- SHA256：`724cd895ecf4da319a3ef164892b72078bd92632a5d812111261cde248ebcdb7`
- W0：精确依赖探针通过：`sdl12-compat/1.2.68`、`freetype/2.14.3`。
- W0b：`upstream/main` 无 `sdl_ttf 2.0.11` 历史归档或 `notes.md`。
- W1：worktree 基于 `upstream/main` `5dff0c6a5c`，分支 `feat/sdl_ttf-2.0.11`。

## 构建与配方

- 构建系统：Autotools；包类型：静态库。
- `sdl12-compat` 提供 SDL 1.2 ABI，但没有 legacy `sdl-config` 命令；recipe 在 Conan build folder 生成可复现 wrapper，并显式传入 `SDL_CONFIG`。
- 老版本 `config.sub` 拒绝 `aarch64-unknown-linux-ohos`，因此 configure 使用可被上游接受的 GNU build/host tuple；设备编译器仍按 OHOS profile 产出目标代码。
- 旧版 SDL_ttf 的 configure 还探测 `freetype-config`，recipe 为已发布 `freetype/2.14.3` 生成匹配 wrapper，并通过 `FREETYPE_CONFIG` 显式传入。
- `configure` 中两处 `umask 077` 改为 `022`，通过 `refresh-patch --auto` 生成 `0001-configure.patch`，避免 HMDFS 的 `confXXXXXX` 不可写。
- `cpp_info.requires` 传播 SDL 兼容层和 FreeType；消费者测试额外显式补入已发布 `sdl12-compat` 的 `include/SDL` 根目录，因为其 CMake metadata 未传出该 include 路径。

## 测试四维账本

| 维度 | 数量 | 证据 |
|---|---:|---|
| 上游静态声明 | 0 | 上游 Makefile.am 无测试目录、测试注册宏或 check 目标 |
| 构建系统注册 | 0 | `make -n check` 无上游测试注册 |
| 实际执行 | 0 | 上游无测试入口 |
| 通过/失败/跳过 | 0 / 0 / 0 | 无上游测试 |
| 新增消费者程序 | 1 | `test_package/test.c` |
| 消费者断言 | 2 | `TTF_Linked_Version` 版本断言、`TTF_Init`/`TTF_WasInit` 行为断言 |

## 验证结果

- Conan G1/G2/G3/G4/L2/L4/L5：通过；设备证据见 `reports/conan-verify-report.md`。
- 真实 `test_package`：CMake/CTest 编译并运行 SDL_ttf API，2/2 断言通过。
- W3：finish 在设备当前提交上通过，日志见 `reports/w3-local-ci.log`；L0/L1/L4/L5 通过，L2 因无 `bin/` 跳过。
- W4/CI/AI/PR：待当前提交完成 W4、推送后再执行；在此之前不声称可以提审。

## 路径判断

- 三项 legacy SDL 组件共同验证了 `sdl-config` wrapper、旧 `config.sub`/`umask` 处理和已发布 `sdl12-compat` CMake include 缺口，但这些证据都来自同一仓库内的相关归档，尚无跨仓库触发与知识库新增证据。因此本任务按路径 A 交付，不把单库补丁或同仓库复用冒充路径 B。
---

**编译结束**: 2026-09-15 23:32
**最终状态**: built
