# nemu 3.5.0 适配笔记

## 编译环境
- 构建系统: CMake
- 编译日期: 2026-09-11（重建：基线 main 8f05a4eb33，USB/OVF 开启）
- 编译器: clang/clang++
- 状态: built
- 目标平台: HarmonyOS PC arm64（OHOS profile）

## 编译步骤
1. 使用 `ci/conan/profiles/ohos-aarch64` 执行 Conan 配方验证。
2. 通过 `PkgConfigDeps` 生成 json-c 的 pkg-config 元数据（上游 `pkg_check_modules(JSONC REQUIRED json-c)`），`CMakeDeps` 对接其余 find_package；`VirtualBuildEnv` 注入 gettext 工具。
3. 使用 CMakeToolchain 配置 `CMAKE_SYSTEM_NAME=OHOS`；**构建矩阵对齐上游 `.github/workflows/tests.yml`：NM_WITH_USB=ON、NM_WITH_OVF_SUPPORT=ON（默认）**；关闭 DBus、network map、remote、embedded QEMU、embedded ncurses。
4. `CMAKE_FIND_PACKAGE_PREFER_CONFIG=ON`：让 find_package(Intl/LibXml2/…) 命中 CMakeDeps 的 CONFIG 文件（内置 FindIntl 的 MODULE 探测会命中 musl 内嵌 gettext，Intl_LIBRARIES 为空）。
5. 使用 `cmake --build <build_folder> -- -j1` 构建，避免 HMDFS jobserver FIFO 限制。
6. 使用 CMake install 生成可执行包，产物包括 `bin/nemu` 和 `bin/ntty`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `pkg-config` 找不到 `json-c` | Conan 依赖未生成 `.pc` 元数据 | 在 `generate()` 中调用 `PkgConfigDeps(self).generate()` |
| 2 | CMake 找不到 `msgmerge/msgfmt` | gettext 运行工具未进入构建 PATH | 增加 `tool_requires("gettext/0.22.5.1")` 并生成 `VirtualBuildEnv` |
| 3 | HMDFS jobserver FIFO 创建失败 | 并行 make 使用 FIFO 被沙箱限制 | 配方和 test_package 均固定 `-j1` |
| 4 | `curses.h`、`json.h` 找不到 | Conan 包头文件布局与上游 include 写法不同 | 显式注入 ncurses include，并加入 json-c/include/json-c |
| 5 | OHOS Linux 网络头文件冲突 | Linux UAPI socket 与 OHOS libc 重复定义 | OHOS 下使用 `net/if.h`，屏蔽冲突的 Linux socket/if 组合，并保留网络类型所需 UAPI |
| 6 | POSIX mqueue、`gethostid` 未链接 | OHOS SDK 不提供对应用户态符号 | OHOS 通过 CMake 定义功能宏，复用项目已有 SysV 消息队列后端，并使用 `getuid()` 作为 NVMe 序列号替代；其他平台继续使用 `gethostid()` |
| 7 | test_package 直接执行 ELF 被拒绝 | OHOS ELF 代码签名校验 | 沙箱内 `binary-sign-tool -selfSign 1` 重签名后实际运行通过（见 test-report） |
| 8 | `sqlite3.h`/`libxml/tree.h`/`libusb.h` 找不到 | 上游用 MODULE 变量式 `include_directories(${SQLITE3_INCLUDE_DIR}…)`，交叉 sysroot 无系统头文件，CMakeDeps 的 CONFIG target 声明不填这些大写前缀 MODULE 变量 | cache_variables 显式提供 `SQLITE3_INCLUDE_DIR/LIBXML2_INCLUDE_DIR/LibArchive_INCLUDE_DIR/UDEV_INCLUDE_DIR/LIBUSB_1_INCLUDE_DIRS` |
| 9 | 链接 undefined `sqlite3_open` 等 | 同 #8：`${SQLITE3_LIBRARIES}` 等 MODULE 变量为空 | 0001 补丁在 find_package 后桥接 CONFIG 驼峰变量（`Sqlite3_LIBRARIES`→`SQLITE3_LIBRARIES` 等，含 LibXml2/LibArchive/libusb-1.0/UDev） |
| 10 | 链接 undefined `libintl_gettext` | gettext/0.22.5.1 配方未声明 cpp_info.libs，`Intl::Intl` 为空 INTERFACE target | 0001 补丁给 `Intl::Intl` 追加 `INTERFACE_LINK_LIBRARIES`（指向包内 libintl.so，路径由 `NEMU_LIBINTL_PATH/NEMU_LIBINTL_INC` cache 变量注入） |
| 11 | `nm_core.h` `_()` 内联报 int→char* 转换错 | musl 内嵌 gettext 无独立 libintl.h（声明不完整） | `Intl_INCLUDE_DIRS` 显式指向 conan gettext 包 |
| 12 | 上游测试 9 用例全灭（前任 #9121 rule4 FAIL 根因） | 5 项宿主前置缺失：只读 /tmp、无 /etc/passwd（getpwuid NULL）、无 qemu、无 tmux、ELF 签名 | `test_files/` 环境适配层（LD_PRELOAD + sitecustomize 双层 + qemu 桩 + 重签名），**9/9 真跑通过**，详见 test-report.md |
| 13 | OVA import `mkdtemp` 失败 | nemu 用 mkdtemp 建 `/tmp/.../extract_XXXXXX`（模板就地改写语义） | preload 拦截 mkdtemp：在重定向目标真建目录，把实际随机后缀写回原模板（保持 /tmp/ 前缀，后续路径操作经同一规则映射一致） |
| 14 | OVA import `chdir` 失败 | nemu 解包期间 chdir 到 /tmp 下的 extract 目录 | preload 拦截 chdir |
| 15 | `nm_hw_disk_free: statvfs` 失败 | nemu 对 vm_dir 做 statvfs（/tmp 只读不存在） | preload 拦截 statvfs |
| 16 | tmux 会话子进程打不开 HMDFS 文件 | 实测 tmux daemonize 后的 pane 进程 open() HMDFS 返回 EACCES（直接子进程正常） | 测试源码与数据复制到 tmpfs 沙箱执行 |
| 17 | HMDFS 上 unix socket bind 被拒 | 文件系统限制 | tmux socket 目录用 tmpfs（`/data/storage/el2/base/temp`） |
| 18 | python 侧 os.mkdir 拦截不到 | python.org 构建的 libpython 为 BIND_NOW，其 os.mkdir 调用不经过可被 LD_PRELOAD 拦截的 PLT 解析路径（实测 libc.mkdir 解析到 /system/lib/ld-musl） | sitecustomize.py（PYTHONPATH 自动加载）包装 os.mkdir/stat/open/builtins.open/PathLike/shutil/subprocess |
| 19 | subprocess 相对命令名失败 | 同 #18 环境下 python posix_spawn 的 PATH 查找异常 | sitecustomize 对 argv[0] 做 shutil.which 预解析（顺带完成 qemu 桩重定向） |

## 源码修改

所有源码适配均通过 `conandata.yml` 登记的补丁应用：
- `patches/0001-CMakeLists.txt.patch`：OHOS 归入 Linux 实现并跳过 librt 检测；MODULE→CONFIG 变量桥接（Sqlite3/LibXml2/LibArchive/libusb-1.0/UDev）；`Intl::Intl` 空 target 的 libintl 注入。
- `patches/0002-ohos-network-ipc.patch`：处理 OHOS 网络头文件、SysV IPC 后端和主机标识兼容性。

## 依赖版本
- ncurses/6.6
- sqlite/3.53.3
- json-c/0.18
- gettext/0.22.5.1
- libxml2/2.15.3
- libarchive/3.7.7
- openssl/3.5.6.1
- libusb/1.0.27（NM_WITH_USB=ON）
- libudev-zero/1.0.4（NM_WITH_USB=ON，UDev 头文件与静态库）

## 上游测试（rule4 真跑）

一键入口：`bash test_files/run-upstream-tests.sh <pkg-dir> <src-dir>`

```text
Ran 9 tests in 7.620s — OK（vm_test 8 + ova_test 1 全部通过）
```

环境适配层（test_files/，上游零修改）：
- `nemu_test_env.c`：LD_PRELOAD（/tmp 与 /usr/bin/qemu-* 重定向、getpwuid、mkdtemp/chdir/statvfs/openat 等）
- `sitecustomize.py`：python 层路径重定向 + subprocess argv 解析
- `qemu-system-x86_64.stub` / `qemu-img.stub`：QEMU 桩（`-M help` 机型表 / create/convert）
- `dsl.ovf`：OVA 测试数据模板（上游 gdown 不可达，按 OVF 1.0 envelope 构造）
- tmux 3.4：仓内 `archives/t/tmux/3.4` 同源构建

## 验证结果

```text
G0: PASS
G1: PASS
G2: PASS — conan create 干净重建成功（USB/OVF 开启）
G3: PASS — 无系统同名库冲突
G4: PASS
L2: PASS — 设备本机重签名后 nemu --version 实跑
L4: PASS
L5: PASS
test_package: 编译/链接 PASS；运行 PASS（本机重签名实跑）
上游测试: 9/9 PASS（100%，本机真跑）
```

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/nemu` | Nemu 主程序（OVF import + USB Support 开启） |
| `bin/ntty` | Nemu 终端辅助程序 |
| `share/nemu/templates/config/nemu.cfg.sample` | 示例配置 |
| `share/locale/ru/LC_MESSAGES/nemu.mo` | Russian locale |

## 注意事项

- QEMU 本体在 OHOS PC 不可用（上游亦未打包）；测试桩只覆盖命令行生成路径（上游测试的断言对象），VM 实际启动属 QEMU 生态。
- `qemu_bin_path` 等运行时路径由 nemu.cfg 配置，部署侧可指向任意 QEMU 发行版。
---

**编译结束**: 2026-09-11 13:55
**最终状态**: published
