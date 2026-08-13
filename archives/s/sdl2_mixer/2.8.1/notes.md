# sdl2_mixer 2.8.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-08
- 编译器: clang 15 / clang++
- 状态: published

## 编译步骤

```bash
# 源码获取（GitHub 本地不可达，用 gitcode 镜像）
git clone --depth 1 --branch release-2.8.1 https://gitcode.com/libsdl-org/SDL_mixer.git

# init-build（本地已备源码，--no-download）
python3 scripts/ohc-run.py init-build sdl2_mixer 2.8.1 --no-download --url=...release-2.8.1.tar.gz

# configure（裁剪非必要音频格式，仅保留 WAV + MP3/minimp3）
cmake .. -DCMAKE_BUILD_TYPE=Release -DCMAKE_C_COMPILER=clang \
  -DSDL2_INCLUDE_DIR=<sdl2 包>/include/SDL2 -DSDL2_LIBRARY=<sdl2 包>/lib/libSDL2.a \
  -DSDL2MIXER_OPUS=OFF -DSDL2MIXER_VORBIS=OFF -DSDL2MIXER_FLAC=OFF \
  -DSDL2MIXER_MOD=OFF -DSDL2MIXER_MIDI=OFF -DSDL2MIXER_WAVPACK=OFF \
  -DSDL2MIXER_GME=OFF -DSDL2MIXER_CMD=OFF -DBUILD_SHARED_LIBS=OFF

cmake --build . -j4   # → libSDL2_mixer.a
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `Could NOT find PrivateSDL2 (missing: SDL2_LIBRARY SDL2_INCLUDE_DIR)` | SDL2_mixer 用自带 FindPrivateSDL2.cmake（模块模式）查 SDL2 | 配方 generate() 显式注入 `SDL2_INCLUDE_DIR`/`SDL2_LIBRARY` |
| 2 | `Could NOT find OpusFile`（及后续 FLAC/MOD/MIDI 等） | 可选音频格式默认 ON，OHOS 无对应系统库 | configure 裁剪：OPUS/VORBIS/FLAC/MOD/MIDI/WAVPACK/GME/CMD=OFF，仅留 WAV + MP3（内建 minimp3） |
| 3 | conan-verify G2 `SDL.h/SDL_mixer.h not found` | 头文件装在 `include/SDL2/`，cpp_info.includedirs 默认不含 | package_info() 设 `includedirs=["include/SDL2","include"]` + 补 sdl2 依赖的 include/SDL2 |
| 4 | test_package 运行 `Permission denied` | binary-sign-tool 输出的 .signed 文件丢失可执行位 | 签名后 `os.chmod(path, 0o755)` 恢复 |
| 5 | 本地 conan-verify GitHub 下载超时 | conan-verify 自动注入 ghfast.top 镜像，本机不可达 | 本地验证临时用 file:// 本地 tarball；提交 conandata 恢复官方 URL+SHA256 |

## 源码修改

无源码修改（`patches/0001-no-patch-needed.patch` 为文档性说明）。
适配全部通过配方 generate() 的 CMake 变量完成。

## 依赖版本

| 软件 | 版本 | 来源 | 状态 |
|------|------|------|------|
| sdl2 | 2.30.10 | cnb 制品仓 | ✅ |

## 验证结果

```bash
python3 scripts/ohc-run.py conan-verify sdl2_mixer 2.8.1
# G0/G1/G2/G3/G4 + L2/L4/L5 全 PASS，状态可标记 published
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | CMake 静态库配方：SDL2 路径注入 + 格式裁剪 + cpp_info 修正 |
| conandata.yml | 官方 archive URL + SHA256 `63804b4b...`（haikuports/FreeBSD 双源确认） |
| patches/0001-no-patch-needed.patch | 无源码修改说明（文档性） |
| test_package/ | Mix_Init/Mix_Quit API 验证 + MANIFEST.yml + OHOS 签名 |
| reports/conan-verify-report.md | G0-G4 + L2/L4/L5 全 PASS |

## 注意事项

- SHA256 `63804b4b...` 对应 GitHub archive tarball（SIZE 6041627），
  与 haikuports recipe、FreeBSD ports distinfo 双源交叉确认。
- julius（凯撒3 重制版）硬依赖本库：`find_package(SDL2_mixer REQUIRED)`，
  julius 的【积分赛】PR 需把本【依赖项】PR 配置为前置 PR。

## 结束标记

最终状态: published
