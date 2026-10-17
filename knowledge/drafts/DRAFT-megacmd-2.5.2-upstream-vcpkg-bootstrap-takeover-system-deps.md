# 上游 CMake 把 vcpkg 当默认依赖通道：空 `VCPKG_ROOT` 仍在线 clone，离线/OHOS configure 直接 FATAL

- **形态**：knowledge/drafts 条目草稿（最终编号由知识库主编确认）
- **配套 kv**：`knowledge/drafts/DRAFT-megacmd-2.5.2-upstream-vcpkg-bootstrap-takeover-system-deps.kv`
- **申报路径**：B【知识库扩展】
- **来源 run**：megacmd/2.5.2 HarmonyOS PC 首次适配（平台任务 8773，A 机构建机，主理-22，2026-09-24）
- **使用知识库**：`hit(E150 manual-download)`（本包同时命中，写在 PR「使用知识库」行；本条 B 只承载 vcpkg 机制）

## 1. 一句规则

上游 CMake 把 vcpkg 当默认依赖通道（顶层仅按「目录不存在」触发在线 `git clone`）时，
**传 `-DVCPKG_ROOT=` 空串并不能关掉它**——空串让 `NOT EXISTS ${VCPKG_ROOT}` 为真，
clone 块照旧执行；离线 worker 上 `curl -s`（无 `-f`）静默返回空串 ⇒ `git clone
--shallow-since` 实参错位 ⇒ 脚本 RC=128 ⇒ 上游 `FATAL_ERROR` ⇒ configure 终止。
正解是用补丁在 clone 条件前置 `VCPKG_ROOT` 真值判断并给 vcpkg 产物安装块加守卫，
配方侧传空串走上游自带的 `Using system dependencies` 分支，依赖全部由 Conan 注入。

## 2. 机理链（每环可复现）

1. **触发点**：`CMakeLists.txt:42-56`

   ```cmake
   set(VCPKG_ROOT "${CMAKE_CURRENT_LIST_DIR}/../vcpkg" CACHE PATH "...")
   ...
   if((NOT WIN32 OR BASH_VERSION_RESULT EQUAL 0) AND NOT EXISTS ${VCPKG_ROOT})
       message(STATUS "vcpkg will be cloned into ${VCPKG_ROOT}")
       execute_process(COMMAND "bash" "-x" ".../build/clone_vcpkg_from_baseline.sh" "${VCPKG_ROOT}" ...)
       if(NOT status EQUAL "0")
           message(FATAL_ERROR "Failed to run the clone_vcpkg_from_baseline. ${status} ${result} ${resulte} ")
       endif()
   endif()
   ```

2. **脚本**：`build/clone_vcpkg_from_baseline.sh`

   ```bash
   commit=$(grep '."builtin-baseline"' vcpkg.json | awk -F '"' '{print $(NF-1)}')
   commit_date=$(curl -s "https://api.github.com/repos/microsoft/vcpkg/commits/$commit" | grep '"date"' | head -n 1 | awk -F '"' '{print $(NF-1)}')
   git clone --shallow-since $commit_date https://github.com/microsoft/vcpkg $@
   ```

   `curl` 带 `-s` 不带 `-f`：网络不可达时**不报错、只返回空**，于是
   `commit_date` 为空，`git clone --shallow-since` 之后直接跟 URL ⇒ 仓库实参缺失。

3. **陷阱一：空 `VCPKG_ROOT` 挡不住**。`cmake -P` 语言级探测（把顶层条件抄进脚本，
   `set(VCPKG_ROOT "" CACHE PATH "")`）实测：`EXISTS <空>` 为假 ⇒ `NOT EXISTS` 为真
   ⇒ 进入 clone 分支。证据 `~/tmp/uc2/megacmd/vcpkg-branch-probe.txt`（主理-11）。

4. **陷阱二：给个已存在目录也是死路**。`VCPKG_ROOT` 指向已存在目录时不 clone，但
   `if(VCPKG_ROOT)` 为真 ⇒ 走 `process_vcpkg_libraries`，缺 `vcpkg.cmake` 时同样 FATAL。

5. **陷阱三：vcpkg 产物安装块会打包宿主 `/lib`**。`install(DIRECTORY
   ${vcpkg_lib_folder})` 中 `vcpkg_lib_folder` 由 `VCPKG_INSTALLED_DIR` 拼出，
   该变量为空时路径退化为 `/lib/`。短路 clone 时必须同时给这一块加 `if(VCPKG_INSTALLED_DIR)`。

## 3. 实测症状（megacmd/2.5.2，A 机，2026-09-24）

未打补丁、断网代理（`https_proxy=http://127.0.0.1:9`）、`cmake -DVCPKG_ROOT=`：

```
-- vcpkg will be cloned into 
CMake Error at CMakeLists.txt:53 (message):
  Failed to run the clone_vcpkg_from_baseline.  128 + set -e
  + commit=c6d3ab273572019ea0d6f6688e1163143190d326
  ++ curl -s https://api.github.com/repos/microsoft/vcpkg/commits/c6d3ab273572019ea0d6f6688e1163143190d326
  + commit_date=
  + git clone --shallow-since https://github.com/microsoft/vcpkg
  fatal: You must specify a repository to clone.
-- Configuring incomplete, errors occurred!
```

完整日志：`~/tmp/uc2/主理-22/probe-symptom/UNPATCHED-configure.log`（RC=1）。
同一棵树里 `include(detect_host_architecture)` 还报了 `could not find requested file`
——那是 sdk 子模块空目录（E150）的另一条独立症状，本条目不含。

## 4. 修法（megacmd 配方落地）

补丁 `patches/0001-skip-vcpkg-online-clone.patch`：

1. clone 条件前置真值判断：
   `if((NOT WIN32 OR BASH_VERSION_RESULT EQUAL 0) AND NOT EXISTS ${VCPKG_ROOT})`
   → `if(VCPKG_ROOT AND (NOT WIN32 OR BASH_VERSION_RESULT EQUAL 0) AND NOT EXISTS ${VCPKG_ROOT})`
2. vcpkg 产物安装块加守卫：`install(DIRECTORY ${vcpkg_lib_folder} ...)` 整块包进
   `if(VCPKG_INSTALLED_DIR)` / `endif()`。

配方侧：`generate()` 里 `tc.cache_variables["VCPKG_ROOT"] = ""`（**必须走命令行 `-D`**，
理由见陷阱四），并显式给 `CMAKE_INSTALL_PREFIX`、`WITH_FUSE=OFF`、`FULL_REQS=OFF` 等开关。
打补丁后 configure 日志出现 `Using system dependencies`，`vcpkg will be cloned`
零命中，依赖由 CMakeDeps + pkg-config 注入。

### 4.1 六个次生陷阱（全部在真机构建段实测踩到并已修）

| # | 陷阱 | 判定信号 | 修法 |
|---|---|---|---|
| 四 | 空 `VCPKG_ROOT` 必须走**命令行 `-D`**：上游第 29 行在 `project()` **之前**就 `set(... CACHE PATH)` 钉死默认值，`tc.variables` 写进 `conan_toolchain.cmake` 而被 `set(...CACHE...)` 吃掉 | configure 日志仍打印 `vcpkg will be cloned into <build>/../vcpkg` | `tc.cache_variables`（conan 展开成命令行 `-D`，在任何 CMakeLists 之前写入 cache） |
| 五 | 同一时序陷阱的普适形态：上游 `project()` 之前 `include(megacmd_options)`/`include(sdklib_options)`，里面 `option()` 定义了 `FULL_REQS`/`USE_FFMPEG`/`USE_PDFIUM`/`USE_MEDIAINFO`/`ENABLE_MEDIA_FILE_METADATA` 等 ⇒ **所有 `tc.variables` 选项静默失效** | 实测 `FULL_REQS` 仍为默认 ON ⇒ `ENABLE_MEDIA_FILE_METADATA=ON` ⇒ 紧接着 `pkg_check_modules(libmediainfo)` FATAL | 12 个开关统一走 `tc.cache_variables` |
| 六 | 进了 system-deps 分支也可能照样炸：该分支只用 **pkg-config**（`libcrypto++`/`libsodium`/`sqlite3`/`libcurl`/`libuv`/`readline`/`libpcre`），而 Conan 的 CMakeDeps **只产 CMake config 包、不产 `.pc`**；cryptopp 上游更是根本没有 `libcrypto++.pc` | `pkg_check_modules(libpcre)`/`(libcrypto++)` 等 `NOT FOUND` | 补丁 `0002` 双文件改为「有 CMake config 包就用它（`cryptopp::cryptopp`/`pcre::pcre`/`sqlite3::sqlite3`/`CURL::libcurl`/`libuv::libuv`/`readline::readline`），否则回退 pkg-config」；ICU/OpenSSL 按 target 是否存在二选一。同时把 8 处依赖 `PRIVATE`→`PUBLIC`（上游公共头 `<curl/curl.h>`/`<pcrecpp.h>` 泄漏到消费者编译单元） |
| 七 | OHOS triplet 令 CMake 把系统名推成 `HarmonyOS`，CMake 无该 platform module ⇒ **`UNIX` 为假** ⇒ 上游 `#ifdef UNIX` 的公共头包含链整段失效 | 编译期 `sdk/include/mega/gfx.h:32: fatal error: 'megawaiter.h' file not found`（14 处） | `tc.cache_variables["CMAKE_SYSTEM_NAME"]="Linux"` + `CMAKE_SYSTEM_PROCESSOR="aarch64"`（仓库先例 E092，407 处） |
| 八 | `apply_conandata_patches` **只能调一次**：`source()` 与 `build()` 同调时，conan create 会把 source_folder 整体拷进 build folder，二次打补丁必炸；平时被 source 缓存掩盖，改 `conanfile.py` 使 recipe revision 变化后立刻暴露 | `Failed to apply patch … source file is different` | 补丁只打一次，固定在 `source()` |
| 九 | GTest 目标名不一致：Conan 的 gtest 包只声明 `gtest::gtest`（`cmake_target_name`），而按 vcpkg 习惯写的是 `GTest::gtest`/`GTest::gmock` | `find_package(GTest CONFIG)` 找不到目标 / 链接期 gmock 未定义 | 显式钉 `GTest_DIR=<gtest.package_folder>/lib/cmake/GTest` 命中**包内自带的上游 `GTestConfig.cmake`**（该包确实装了它） |

**最终态**：`conan create` 全绿——上游 tests/unit 全量真实执行（`SUITES=8 TOTAL=70 PASS=47 FAIL=23`，
23 例平台受限逐条申报）；包内 5 个 ELF 完成重新自签名、68 个包装脚本完成 shebang 归一化（两项「包内落地」已实证：签名汇总行 w3-local-ci.log:5635、shebang 动作行 5604，且包内 bin/mega-ls 文件头实测已是 env bash 形态）；其**运行时可执行性本轮仅 `mega-cmd` 一个目标在 conanrun 下被真实执行并产出 banner**（5692-5699），其余 4 个 ELF 与 68 个包装脚本未测、不作强结论（W3 的 L2 冒烟步不带 runenv，全判失败不具证据力）；功能级可执行性另受 libcurl 无 TLS 与 path-form AF_UNIX 两项平台限制阻塞；
W3 本地 CI（`setup.sh` + `build_and_test.sh`）通过。

## 5. 适用边界

- **命中**：CMake 顶层把 vcpkg 当默认依赖通道、且仅按「目录不存在」触发 clone/bootstrap
  的工程（vcpkg manifest 模式项目常见）；对离线/受限网络 worker 与 OHOS 交叉构建必然 FATAL。
- **不命中**：把 vcpkg 放在可选分支（有开关关掉）、或依赖获取全在 configure 之后
  （build/install 期）的工程。
- **与 E342 的分界**：E342 = 测试期 bootstrap 下载（`BUILD_TESTING` 门内）；本条 =
  toolchain 级依赖通道接管，发生在 configure 最早期、与测试开关无关，组合型不判重。
- **与 E150 的关系**：本包同时命中 E150（tag 归档子模块 `sdk/` 为空，须单独取源拷入）；
  两条机制独立，`similar_to` 已互指。

## 6. 证据索引

| 文件 | 内容 |
|---|---|
| `~/tmp/uc2/megacmd/vcpkg-branch-probe.txt` | `cmake -P` 分支探测（空 VCPKG_ROOT 仍 clone；指向已存在目录进 vcpkg 管理分支） |
| `~/tmp/uc2/megacmd/patchwork/0001-skip-vcpkg-online-clone.patch` | 补丁母本（dry-run RC=0） |
| `~/tmp/uc2/主理-22/probe-symptom/UNPATCHED-configure.log` | 未打补丁 + 断网的真实首错（本条目核心证据） |
| `archives/m/megacmd/2.5.2/reports/w3-local-ci.log` | 打补丁后本地 CI（W3）实跑日志 |
