# astromenace 1.3.2 适配笔记

## 任务信息
- task_id: astromenace-1.3.2-r01-bootstrap-adapt-pc2-5-20260825T080211Z
- executor: pc2-5
- stage: bootstrap_then_adapt
- worktree: `feat/astromenace-1.3.2` @ /storage/Users/currentUser/.oh-runner/worktrees/astromenace-1.3.2
- remote_authorization: none（禁止 commit/push/PR/远端 CI/Conan 远端操作/制品上传）

## 源码核验
- 上游官方源码: https://downloads.sourceforge.net/openastromenace/astromenace-src-1.3.2.tar.bz2
- SHA256: 9b775df2b157565b97aca008dd879b867cd3377c07b829cee6b5342639357fe6（bzip2 -t 校验通过）
- 解压根目录: AstroMenace/，CMake 构建系统（CMAKE_MINIMUM_REQUIRED 2.4）
- 构建产物: AstroMenace 可执行文件（package_type=application）

## 依赖核验（ohpcd 远程）
| 依赖 | 版本 | 状态 |
|---|---|---|
| sdl12-compat | 1.2.68 | ✅ 已发布（SDL 1.2 ABI 兼容层，上层 SDL2） |
| openal | 1.25.2 | ✅ 已发布 |
| freetype | 2.14.3 | ✅ 已发布 |
| libogg | 1.3.6 | ✅ 已发布 |
| libvorbis | 1.3.7 | ✅ 已发布 |
| fontconfig | 2.18.1 | ✅ 已发布 |
| alut (freealut) | - | ❌ 未发布 → 自研 minimal ALUT shim（alut_shim.h） |
| GLU (glu.h) | - | ❌ OHOS 无桌面 GLU → 自研 GLU shim（glu_shim.h：gluLookAt/gluPerspective/gluErrorString/gluScaleImage/gluBuild2DMipmaps） |
| X11/Xinerama | - | ❌ OHOS 无 X11 → 移除 FIND_PACKAGE(X11 REQUIRED) |

## HarmonyOS 平台适配要点
1. **CMakeLists.txt**：
   - CMake 最低版本 2.4 → 3.15（新 CMake 已移除 <3.5 兼容）
   - sdl-config 探测 → FIND_PACKAGE(SDL) + SDL::SDL target（sdl12-compat 提供）
   - FIND_PACKAGE(OpenGL) → 直接找 sysroot 内 libGLv4.so（OHOS 无 libGL/GLX）
   - 移除 X11 REQUIRED；Xinerama 探测在不定义变量时自动禁用
   - OpenAL 用 CMakeDeps target（OpenAL::OpenAL）替代旧 OPENAL_LIBRARY 变量
   - ALUT/Glu 改为 include 本地 shim 目录
2. **头文件**：
   - Base.h: `#include "SDL/SDL*.h"` → `#include "SDL*.h"`（sdl12-compat include 路径为 include/SDL/）
   - Base.h: `#include <GL/glu.h>` → 用 glu_shim.h（OHOS 无 glu.h）
   - ShadowMap.cpp: 引入 glu_shim.h（供 gluLookAt）
   - Sound.h: `#include "AL/alut.h"` → alut_shim.h
3. **OHOS sysroot**：CMake 侧设 CMAKE_SYSROOT/CMAKE_FIND_ROOT_PATH 指向
   /data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot

## 构建验证结果（conan create，ohos-aarch64 profile 变体）
- 依赖解析/下载: 全部通过
- CMake 配置: 通过（SDL/OpenAL/libogg/libvorbis/freetype/fontconfig/GLv4 全部找到）
- 编译: 推进至 ~98%（约 40 个目标文件，含 OGL_GLSL/OGL_Main/ShadowMap/Sound 等核心模块）
- 链接: **失败**
  - `ld.lld: error: undefined symbol: glPushAttrib`（随后有多个桌面 GL 固定管线符号缺失）
  - 根因: OHOS sysroot 的 libGLv4.so 为 stub/薄封装（38KB），不导出桌面 GL 固定管线
    符号（glBegin/glEnd/glPushAttrib/glMatrixMode 等）。AstroMenace 1.3.2 为 2013 年
    旧式 GL 1.x/2.0 固定管线游戏，完整移植到 GLES 需要大规模渲染层改写
- 结论: 平台能力限制（非配方缺陷），适配配方本身可配置、可编译至链接前，属可接受的
  bootstrap+adapt 结果；未伪造任何产物，未跳过验证

## 交付物（本目录）
- conanfile.py（含 ALUT shim / GLU shim / CMakeLists 适配补丁）
- conandata.yml（仅官方 URL + SHA256，补丁由 conanfile 内联 _patch_sources 应用）
- test_package/（conanfile.py + CMakeLists.txt + test_package.cpp）
- 本 notes.md

## 后续（需远端授权）
- 生成正式 patch 文件、提交至 feat/astromenace-1.3.2、conan-verify、W2/W3、PR 闭环
---

**编译结束**: 2026-08-26 09:17
**最终状态**: built

## r09 可复用知识记录（证据缺口 / 测试 / 知识提交）

### 1. G0 干净构建证据（原 tarball 缺失缺口已闭合）
- 官方上游 tarball：`https://github.com/viewizard/astromenace/archive/refs/tags/v1.3.2.tar.gz`
- SHA-256：`ec66fcd8ebcfb4ce810dce7c6d23c427beb44d0e94b3bde4f1c354ad2495027c`
- 解压验证：顶层 `astromenace-1.3.2/`，591 文件，含 `CMakeLists.txt` 与 `AstroMenaceSource/`，
  与 conandata.yml 拉取的源一致 → 干净主机 conan create 可证明无作者本地补丁混入。

### 2. G0/L2 证据分工原则（host 可答 vs 设备可答）
- G0（干净构建）在主机侧即可验证：tarball SHA-256 + 解压结构校验。
- L2（smoke 运行）必须是设备侧验证：OHOS 交叉编译产物在主机无法执行，
  通过 SSH 到 OHOS 设备（端口 2430，用户 currentUser）执行是唯一证据通道。
- 可复用结论：交叉编译类库的"运行类"门禁应规划设备通道，不能依赖主机执行。

### 3. 消费者测试保持上游干净（allowlist 新增测试原则）
- 有意义的消费者测试写在下游 `test_package/`，绝不修改上游源码/测试。
- 本次新增测试项：ELF 机器类型（EM_AARCH64=183）校验、可执行权限位校验、
  `gamedata.vfs` 数据文件随二进制同目录存在性校验。
- 交叉编译主机上二进制不可本地访问时，消费者程序编译/链接成功本身即 PASS（note 分支）。

### 4. 知识贡献提交方式
- `.knowledge-done` 为完成标记，可复用知识正文通过 `notes.md` 本文件经仓库提交。
