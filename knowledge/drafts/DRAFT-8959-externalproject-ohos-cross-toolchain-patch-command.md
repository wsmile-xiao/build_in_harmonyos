# DRAFT-8959：canopenterm 2.03 适配 OHOS——CMake ExternalProject vendored 依赖交叉编译链

> Contributor: xiao921924 | Status: Draft | Updated: 2026-09-18
> Source: PR #10213 feat(canopenterm): 2.03 OHOS 适配（8 依赖交叉编译 + 171/171 上游单元测试）

## 背景

canopenterm 2.03 是 C/CMake 的 CANopen 设备分析与配置工具（SDL3 终端 UI）。
其 CMake 构建用 `ExternalProject_Add` **自带全部 8 个依赖源码**（cJSON 1.7.19 /
CANvenient 1.02 / pocketpy 2.1.8 / inih r58 / isocline 1.0.9 / Lua 5.5.0 /
SDL3 3.4.12 / cmocka 1.1.7）并构建，无一来自 Conan registry。这种
"vendored 依赖 + 子构建"结构在 OHOS 交叉编译下有一整条特有的坑链：
子构建不继承 toolchain → 平台判定落空 → 依赖源码无补丁 → bionic 头冲突 →
soname 链缺失。本文沉淀这条链的完整适配范式。

## 坑 1：ExternalProject 子构建不继承 toolchain 文件

### 现象

主工程 OHOS 交叉编译配置正常，进入依赖子构建后按 host 架构编译，
链接期报架构不匹配或 `undefined reference`，各依赖 ELF machine 与主程序不一致。

### 根因

`ExternalProject_Add` 生成的是**独立的 CMake 调用**（子构
建有自己的 cache），`CMAKE_TOOLCHAIN_FILE` 不在自动传递范围内。
主工程的 OHOS toolchain（来自 CMakeToolchain）只作用于主工程。

### 修复

每个 `ExternalProject_Add` 的 `CMAKE_ARGS` 显式追加
`-DCMAKE_TOOLCHAIN_FILE=${CMAKE_TOOLCHAIN_FILE}`。canopenterm 中 8 个子构建
逐个补齐（0003 补丁），可封装成 `OHOS_TOOLCHAIN_ARGS` 变量集中维护。

## 坑 2：conan 补丁只作用于主源码，依赖补丁须走 PATCH_COMMAND

`apply_conandata_patches` 只改主源码根目录。vendored 依赖（SDL3/CANvenient/
cmocka）的源码补丁必须经 `ExternalProject_Add(... PATCH_COMMAND ...)` 注入。

范式（0004/0005/0006 补丁新增 3 个脚本）：

```cmake
# cmake/patch_sdl3.cmake（由 SDL3 子构建 PATCH_COMMAND 调用）
find_package(Git QUIET)
execute_process(
    COMMAND ${Git_EXECUTABLE} apply --allow-empty
            -p1 ${CMAKE_SOURCE_DIR}/patches/sdl3-3.4.12/0001-CMakeLists.txt.patch
    WORKING_DIRECTORY <sdl3 子构建源码目录>
)
```

要点：补丁文件随归档存放于 `patches/<dep>-<ver>/`（不被 conan 应用，
仅供脚本引用）；`--allow-empty` 保证幂等（重跑 conan create 时子构建
重新展开源码，首次 apply 生效）。

## 坑 3：OHOS profile 使 CMake UNIX 为 OFF

OHOS Conan profile 设 `CMAKE_SYSTEM_NAME=HarmonyOS`，CMake 据此把 `UNIX`
置 OFF。上游所有 `if(UNIX)` 平台分支（选 linux 源文件集、链接 POSIX 库）
在 OHOS 上**静默落空**——配置期不报错，构建/链接期才失败，极易误判。

适配范式：

```cmake
if(WIN32)
    set(OS_ICON icon.rc)
    set(OS_SOURCES ...)
elseif(UNIX OR OHOS)        # OHOS 复用 linux 平台分支
    set(OS_SOURCES ...)
endif()
```

Windows-only 资源（icon.rc）在 OHOS 置空（`CONSOLE_ICON` 变量，
codb2json/CANopenTerm 两个 target 统一引用）。

## 坑 4：bionic socket 头顺序（CANvenient SocketCAN 驱动）

`<sys/socket.h>` 必须先于 `<linux/can.h>`。bionic 的 `<sys/socket.h>` 会
先引入 `<linux/socket.h>` 定义 `sockaddr_storage`；若 `<linux/can.h>` 先被
包含（经 `<linux/can.h>` → `<linux/types.h>` 链），后续再包含
`<sys/socket.h>` 时重定义冲突：

```text
error: redefinition of 'sockaddr_storage'
```

修复：CANvenient 头与 SocketCAN 驱动源文件的 include 顺序调整
（patches/canvenient-1.02/0001、0003）。

## 坑 5：cmocka __WORDSIZE 启发式不识 aarch64

cmocka 1.1.7 `cmocka.h` 按 `#if defined(__x86_64__) || defined(__sparc__)`
判 64 位，否则把 `uintptr_t` 定义成 32 位。OHOS aarch64 不在其识别范围，
且系统头已定义 `uintptr_t` → 冲突类型错误。

修复：`__OHOS__` 守护跳过重定义（patches/cmocka-1.1.7/0001）。
经 0006 补丁接入 `patch_cmocka.cmake` 的 PATCH_COMMAND。

## 坑 6：交叉构建无 soname 链 + 运行期库路径

ExternalProject 交叉构建产物只有 `libcjson.so` 一个文件（无
`libcjson.so → libcjson.so.1` 符号链接链，HMDFS 亦拒绝 symlink）。

范式：

1. 被依赖库强制 plain `DT_SONAME`（无版本后缀，目标属性 SET_TARGET_PROPERTIES）。
2. 依赖方链接 unversioned `.so` 名（`target_link_libraries(... libcjson.so)`）。
3. 上游 CMake 不生效 `CMAKE_BUILD_RPATH`（canopenterm 实测 RUNPATH 缺失，
   test 环境无 LD_LIBRARY_PATH 时 rc=126/127）：recipe `build()` 用
   patchelf 写 `RUNPATH=$ORIGIN/../lib`。两个坑：conan `self.run` 走 shell
   会展开 `$ORIGIN`（写成 `/../lib`）→ 用 subprocess 列表参数；本机
   文件系统拒 patchelf in-place 重写（Operation not permitted）→
   临时副本 + `os.replace`。package 布局 `bin/ + lib/ +
   share/canopenterm/`（codb/dbc/eds 运行数据 + scripts + tests）。
4. test_package 用包内 `share/canopenterm` 副本作工作目录运行
   `run_unit_tests`——上游 171 例 cmocka 用例（can_read/can_write 经
   `-Wl,--wrap` 打桩，无需真实 CAN 设备）**171/171 通过**。
5. 冒烟测试信号坑：CANopenTerm 安装信号处理器捕获 SIGTERM（/proc 状态
   SigCgt 含 15），`timeout` 默认 TERM 杀不掉 → 冒烟用后台启动+存活
   判定（未崩溃=依赖库加载成功）+ kill -9；其余 timeout 加 `-k` 兜底。

## 可复用结论

- 判定一个 CMake 项目是否需要本文范式：看其 CMake 是否含
  `ExternalProject_Add`/`FetchContent` 且依赖源码随仓库自带。
- 子构建 toolchain 传递 + PATCH_COMMAND 脚本 + `elseif(UNIX OR OHOS)`
  三件套是 vendored 依赖型 CMake 项目 OHOS 适配的通用骨架。
- 测试资产复用：上游自带单元测试套件时，test_package 直接对打包产物
  执行（数据副本作 cwd），比另写冒烟断言覆盖度高一个量级。

## 验证

```text
真机隔离 CONAN_HOME：
conan create archives/c/canopenterm/2.03 -pr:h ohos-aarch64 -pr:b ohos-aarch64 --build=missing
→ exit 0；test_package 19 断言全过；上游 run_unit_tests 171/171。

反证：移除任一 ExternalProject_Add 的 -DCMAKE_TOOLCHAIN_FILE，
子构建按 host 架构编译，链接期必炸。
```
