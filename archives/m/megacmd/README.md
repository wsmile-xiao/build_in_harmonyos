# megacmd — MEGA 云存储命令行客户端

## 一句话

MEGAcmd 提供对 MEGA 云服务的非 UI 访问：交互式 shell（`mega-cmd`）、常驻服务（`mega-cmd-server`）与脚本化客户端（`mega-exec`），以及安装到 `bin/` 的 `mega-*` 命令包装脚本（mega-ls/mega-get/mega-put/mega-sync/mega-webdav 等 60+ 个）。

## 功能概述

- 同步（sync）与本地目录备份（backup）到 MEGA
- WebDAV / 流媒体服务
- 文件上传/下载/分享/挂载（FUSE，可选）等文件操作命令
- `mega-cmd` 交互 shell + `mega-exec` 脚本化调用两种模式

## OHOS 适配要点

- **上游默认 vcpkg 全托管依赖**（README：“All dependencies are downloaded and installed automatically by vcpkg”），构建期会在线 `git clone` vcpkg —— OHOS/离线 CI 必须以补丁短路该路径，改走 `else` 的 system-deps 分支（pkg-config/find_package），依赖由 Conan CMakeDeps 注入。
- **子模块形态分发**：仓库只有 `.gitmodules`（子模块 `sdk` → meganz/sdk），tag 归档中 `sdk/` 为空目录；按 E150 manual-download 单独取子模块 commit 源。
- **fuse3 可选且默认开**：`-DWITH_FUSE=OFF` 关闭（OHOS 无 fuse 运行时；`fuse3` 命名的 recipe 在制品仓不存在，`libfuse/3.18.2` 存在）。
- 依赖面可通过 `-DFULL_REQS=OFF` + 关闭 USE_FFMPEG/USE_PDFIUM/USE_FREEIMAGE/USE_MEDIAINFO 裁剪到核心集。

## 依赖关系

- 编译（核心，已 W0 核验 recipe 在制品仓，本轮 L0i 逐个 `dependency in registry`）：pcre、cryptopp、libsodium、sqlite3、libcurl、icu、openssl、libuv、readline、zlib（经 libcurl 传递亦显式声明）
- 可选（recipe 均在制品仓，本配方默认关）：ffmpeg、pdfium、freeimage、libmediainfo（其 zenlib 传递依赖在制品仓**缺失**，故默认裁剪）、gtest（测试，走 `test_requires`）
- 运行：包内 ELF **动态链接** `libcurl.so` 与 `libuv.so.1`（实测 `bin/mega-cmd` 内嵌的 `NEEDED` 串），且包内**没有** `lib/` 目录、RUNPATH 指向不存在的 `opt/megacmd/lib` ⇒ 必须由 Conan 的 `conanrun` 环境注入 `LD_LIBRARY_PATH` 才能加载（旧写法"默认静态链接 Conan 依赖"与证据不符，已更正）。68 个 `mega-*` 包装脚本还需 `PATH` 指向包 `bin/`（脚本以**裸命令名**调用 `mega-exec`）。
- 运行期功能面：`mega-cmd-server` 因平台 `libcurl/8.5.0` 未启用 TLS 而初始化中止；CLI↔server 的 path-form AF_UNIX 套接字在本平台无法 bind ⇒ 登录/传输等功能不可用（逐条申报见 `2.5.2/notes.md` §8.4，W3 冒烟步 `L2=skip` 的定性见 §8.5）。

## 参考资料

- 上游仓库：meganz/MEGAcmd（tag `2.5.2_Linux`）
- 子模块仓库：meganz/sdk（pin `fae76a36d60484657fbdf442b7b917ccc4fbad77`）
- 官网：https://mega.nz/cmd

## 版本索引

见 `manifest.yaml`。
