# sdl2-ttf 2.24.0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-08-28
- 编译器: clang 15.0.4 / clang++
- 状态: built

## 编译步骤

1. `ohc-run.py init-build sdl2-ttf 2.24.0 --url=https://codeload.github.com/libsdl-org/SDL_ttf/tar.gz/refs/tags/release-2.24.0`
   官方 tag `release-2.24.0`，sha256 `2c45241a...`。GitHub release 直连超时，改用 codeload 官方端点。
2. `ohc-run.py conan-init sdl2-ttf 2.24.0` 生成配方，随后修正：
   - conandata.yml 补 `filename`（codeload URL 无扩展名 → conan get() 按 zip 解压 BadZipFile）
   - requirements(): sdl2/2.30.10, freetype/2.14.3, harfbuzz/14.2.0.1.1.2
   - generate(): 禁用 builtin FreeType/HarfBuzz；注入依赖 env（AutotoolsDeps + LD_LIBRARY_PATH/PKG_CONFIG_PATH/PATH + SDL2 include/SDL2 + HB_CFLAGS/HB_LIBS）
3. `ohc-run.py conan-verify sdl2-ttf 2.24.0` → G0-G4 + L2/L4/L5 全部 PASS
4. `ohc-run.py finish sdl2-ttf 2.24.0 published` → W2/R36/W3 PASS（R03 基线噪音隔离复核后 W3 通过，`baseline_noise_exempted`）
5. `ohc-run.py result` 以同一 task_id 回传

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan get() BadZipFile | codeload URL 无 `.tar.gz` 扩展名，conan 默认按 zip 解压 | conandata.yml 增加 `filename: SDL2_ttf-2.24.0.tar.gz` |
| 2 | configure: cannot guess build type (HarmonyOS) | config.guess/config.sub 不识别 HarmonyOS (E007) | 补丁 0001-config-guess-sub.patch（__OHOS__/ohos-linux triplet） |
| 3 | config.status: subs1.awk Permission denied | HMDFS setgid + umask 077 使临时目录阻塞属主写入 (E129) | 补丁 0002-configure-umask.patch（configure 内 umask 077→022） |
| 4 | configure conftest: cannot run C compiled programs | 依赖共享库不在默认加载路径 | generate() 注入 LD_LIBRARY_PATH（dep libdirs） |
| 5 | make: SDL.h not found | sdl2.pc prefix 解析为空 → `-I//include/SDL2` 无效 | CPPFLAGS 注入 sdl2 include/SDL2 |
| 6 | configure: Unable to find HarfBuzz | harfbuzz.pc Requires.private 引用缺失 glib-2.0.pc，pkg-config 校验失败 | 预置 HB_CFLAGS/HB_LIBS 绕过 pkg-config |
| 7 | make: No rule to make external/freetype/... | release tarball 不含 external/ submodule | --disable-freetype-builtin --disable-harfbuzz-builtin |

## 源码修改

- `patches/0001-config-guess-sub.patch`：config.guess/config.sub 增加 HarmonyOS 识别
- `patches/0002-configure-umask.patch`：configure 临时目录 umask 077→022

## 依赖版本

- sdl2/2.30.10
- freetype/2.14.3
- harfbuzz/14.2.0.1.1.2

## 验证结果

```bash
python3 scripts/ohc-run.py conan-verify sdl2-ttf 2.24.0  # exit 0, G0-G4 + L2/L4/L5 PASS
python3 scripts/ohc-run.py finish sdl2-ttf 2.24.0 published  # W3 local CI PASS (JC pass, 100% 1/1)
# test_package: SDL_Init + TTF_Init + TTF_Linked_Version(==2.24.0) + TTF_GetError + TTF_Quit, PASS
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| conanfile.py | 4.9 KB | Conan 配方（autotools + OHOS 适配） |
| conandata.yml | 827 B | 源码声明 + 补丁 |
| test_package/ | — | 消费者测试（test.c + CMakeLists + MANIFEST.yml） |
| patches/ | — | 2 个 OHOS 适配补丁 |

## 注意事项

- SDL2_ttf 是纯库，无上游独立测试套件；验证依赖 test_package 消费者测试。
- sdl2.pc / harfbuzz.pc 在 conan 包内 prefix 解析异常，已在配方 generate() 中处理。
- W3 整仓 junk-check 受 `archives/g/goaccess/1.10.2/ncurses-headers.tar.gz`（origin/main 基线）干扰，R03 隔离复核已豁免；非本库缺陷。
---

**编译结束**: 2026-08-29 01:28
**最终状态**: built
