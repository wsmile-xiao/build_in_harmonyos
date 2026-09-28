# glbinding 3.5.0 适配笔记（executor pc7-24，task glbinding-3.5.0-r01-pc7-24）

## 环境
- OHOS PC aarch64（aarch64-linux-ohos），Clang 15.0.4（OHOS NDK 26.0.0.18）
- Conan 2.29.1 + ohpcd remote；profile: ci/conan/profiles/ohos-aarch64

## 适配过程
1. **官方源**：GitHub cginternals/glbinding tag v3.5.0，SHA-256
   `bb39a97d5d94f70fe6e9c2152e0d8d760758bb031b352e1707fa90f00a43fc69`
   （GitHub 直连不可达，经 codeload 官方 tarball 下载核验；conandata 保持官方 URL）。
2. **构建系统**：CMake。产物 libglbinding.a + libglbinding-aux.a（静态），
   无第三方 requires（核心库仅需 KHR 头，OPTION_BUILD_OWN_KHR_HEADERS=ON 自带）。
3. **OHOS 要点**：
   - Conan CMakeToolchain 把 os=OHOS 映射为 CMAKE_SYSTEM_NAME=HarmonyOS（CMake 不识别），
     且上游根 CMakeLists 的 `option(BUILD_SHARED_LIBS ... ON)` 会覆盖 toolchain 注入的
     cache 变量（实测产物 .so 而非 .a）。解决方案：仿 glfw 3.5.1 既有配方，OHOS 分支
     直接自发现 ohos.toolchain.cmake 驱动 cmake，并显式 `-D` 传全部 OPTION_*。
   - OHOS SDK llvm/bin 有 llvm-ar 但无 llvm-ranlib；用 `/data/service/hnp/bin/llvm-ranlib`
     （指向 llvm-ar 的符号链接）作 -DCMAKE_RANLIB。
   - OPTION_BUILD_TOOLS=OFF/EXAMPLES=OFF：上游 tools（glinfo 等）依赖 glfw + GL 上下文，
     非库交付物；纯库包不需要 commands.json（R38）。
4. **测试**：
   - 上游 glbinding-test（gtest）：source_declared_total=18（16 注册 + 2 未注册文件），
     configured=16，executed_passed=16 → 16/18 (88.9%)，可执行集合 16/16 (100%)。
     registry gtest/1.17.0 包名 gtest vs 上游 find_package(googletest)：用测试专用
     googletest-config.cmake shim 桥接（详见知识草稿），另需显式链接 libgmock.a。
   - test_package：test_glbinding（消费者公开 API）+ test_glbinding_ohos（鸿蒙专项：
     dlopen libGLESv3.so/libEGL.so 解析 eglGetError/glGetString）2/2 通过。
5. **门禁**：conan-verify G2-G4 通过；finish W2/W3 通过（W3 本地 CI 模拟 exit 0）。
   W3 的 JC 全量扫描命中 3 个其他库（cloog/kics）既有基线状态文件（origin/main 已跟踪），
   按基线隔离规程：记录 pre_sha256（e3b0c44…，空文件）→ git rm --cached 临时隔离 →
   复跑 JC/finish 通过 → git add -f 原样恢复 → post_sha256 一致。基线文件未进本库 diff/PR。

## 知识路径
- 路径 B（知识库扩展）：候选 C3（registry gtest 包名 vs 上游 find_package(googletest) 桥接）
  验证通过、可跨库复用、查重部分覆盖 → new_draft
  `knowledge/drafts/DRAFT-glbinding-3.5.0-cmakedeps-googletest-name-bridge.{kv,md}`。
- 候选 C1（llvm-ranlib 缺失）与 C2（option() 覆盖 toolchain 变量）登记观察，
  与既有 E012/E288 重叠，不重复建草稿。

## 未完成项
- 无真实外部阻塞；上游 2 个未注册测试文件（MultiContext/MultiThreading）保持
  uninstantiated（上游排除 + 补丁实测编译失败，原因已记录）。
