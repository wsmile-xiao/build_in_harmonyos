# coeurl 0.3.2 适配笔记

## 编译环境
- 构建系统: meson（上游 `.gitlab-ci.yml` 以 meson 为主构建；根 CMakeLists.txt 是消费者/测试用的平行构建，不采用）
- 编译日期: 2026-09-08/09
- 编译器: clang/clang++ 15.0.4（aarch64-unknown-linux-ohos，OHOS NDK sysroot）
- meson 1.12.0 / ninja 1.13.1 / Conan 2.29.1 / python3 3.12.8
- 状态: built（设备验证完成，release upload 未确认）

## 上游与源码
- 上游为 Nheko-Reborn `coeurl`（https://nheko.im/nheko-reborn/coeurl），MIT 许可的 C++17 异步 HTTP 客户端库（libcurl + libevent）。GitHub 上 Nheko-Reborn/coeurl 已 404，官方源为 nheko.im 自建 GitLab。
- 源码 URL：`https://nheko.im/nheko-reborn/coeurl/-/archive/v0.3.2/coeurl-v0.3.2.tar.gz`，SHA-256 `84c1d76116bd118ee2c3a1c7913e2f2f7b20fff34628d09bd86eb349bfdaf1a7`。下载后做过 gzip magic（1f 8b）、tar 顶层目录（`coeurl-v0.3.2/`）、41 文件零字节比对三重校验。
- nheko.im 实测偶发抖动：同 URL 三次尝试 = 2×SSL timeout + 1×HTTP 500 后第 4 次成功（200）；工具内置下载器另观测到一次瞬时 404。conandata sources 以官方直链为唯一锚点，CI 下载类失败按 workflow §5.3/§11.1 `/rebuild` 换 worker 处置。

## 编译步骤
1. `ohc-run.py init-build`（本地 tarball 复用 + EXPECTED_SHA256）建立 .orig/.work 双轨与 `.build-context-coeurl-0.3.2`。注意工具在 registry 缺条目时把 BUILD_SYSTEM 猜成 autotools，实际为 meson（上下文字段仅提示用途）。
2. `ohc-run.py lang-preflight` → cpp 匹配（build_system 识别为 cmake，主体语言 91% cpp，无碍）。`prescan` 零命中（无 musl 风险函数）。
3. W0：libcurl/8.5.0、spdlog/1.17.0、libevent/2.1.13、fmt/11.1.3、doctest/2.5.2 逐个 `conan install --build=never` 全部 OHOS binary 可取。实测 spdlog/1.17.0 配方硬性要求 fmt/12.2.0（与显式 fmt/11.1.3 冲突），故配方不锁 fmt，由 spdlog 解析传递依赖。（该中间结论后被问题 #5 修正：最终配方显式锁 fmt/12.2.0，理由见下文问题表。）
4. 原生探索（`$TASK_DIR/builds/coeurl-0.3.2.work`，out-of-source build）：
   - 依赖探测走 pkg-config：`conan install -g PkgConfigDeps` 生成消费方 .pc（prefix 指向本机包目录，规避发行包自带 .pc/curl-config 的 prefix 固化坑——实测发行 curl 包 `curl-config --prefix` 指向已不存在的 `p/b/libcu8e3caef60472e/p`）。
   - `meson setup build-native -Dtests=true -Dexamples=true --wrap-mode=nofallback`：threads/spdlog/libcurl/libevent_core/libevent_pthreads/doctest 全部命中，libevent CMake 子项目 fallback 未触发。`ninja -j1` 零错误（仅 examples 对 fmt 12.2 deprecated 运算符告警）。
   - 产物：`libcoeurl.so.0.3`（soversion 0.3，meson 另建 `libcoeurl.so` symlink）、头文件 4 个、`coeurl.pc`、tests/requests、tests/requests_tls、examples/coeurl_example。`meson install --destdir` 验证安装树完整。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 TLS 测试套件 16/17 失败，第一条错误 `error_code()==1`（CURLE_UNSUPPORTED_PROTOCOL），https 请求全部空响应 | ohpcd 发行 libcurl/8.5.0 为无 TLS 后端变体：`.so` 无 OpenSSL 版本串、`nm -D` 无 SSL 符号、DT_NEEDED 仅 libc.so；`-o "libcurl/*:with_openssl=True"` package_id 不变（该变体 options 无此开关），remote 仅此一个 binary。设备系统 curl 是静态链接自带的 TLS 版，无共享 libcurl/头文件可复用 | 按 workflow §7.3「测试依赖自建私有 prefix」路径：curl-8.5.0 源码 + CMake（`-DCURL_USE_OPENSSL=ON`、`-DOPENSSL_ROOT_DIR=$HOME/.harmonybrew` 的 OpenSSL 3.6.4、`-DHAVE_LINUX_TCP_H=OFF`）构建到 `$TASK_DIR/test-prefix`，仅测试用、不进包依赖链。重建后 TLS 套件 17/17 通过 |
| 2 | curl autotools 构建两连败：`config.sub` 不识别 `ohos` 三元组；改用 gnu 三元组后 `config.status` 写 `$ac_tmp/subs1.awk` 报 Permission denied（HMDFS） | OHOS config.guess/sub 老旧 + HMDFS 对 config.status awk 临时文件的写入怪癖 | 测试专用构建改走 CMake（curl 官方支持），一并绕开两个 autotools 坑 |
| 3 | CMake 首次构建 curl 报 `linux/socket.h: redefinition of 'sockaddr_storage'`（`cf-socket.c` → `linux/tcp.h`） | OHOS musl libc 与内核头的既有冲突（知识 E091/E119 同根因，curl 源自带 `HAVE_LINUX_TCP_H` feature-test） | `-DHAVE_LINUX_TCP_H=OFF` 关闭该头检测，构建通过。属既有知识在 CMake feature-test 场景的应用，非新模式 |
| 4 | `meson install` 报 `No module named 'mesonbuild'` | 命令块提前把 HOME 指向沙箱目录，meson pip 启动器按 user site-packages 解析失败 | install 类非测试命令用真实 HOME 执行；§7.3 沙箱 HOME 仅约束上游测试执行 |
| 5 | conan-verify G2 首轮：test_package 编译 `curl/curl.h not found`；修 include 链后再挂 fmt 符号未解析（`fmt::v12::vformat` 等，来自静态 libcoeurl.a 内联 spdlog 模板代码） | 配方 `package_info()` 未声明依赖链，CMakeDeps 不为传递依赖生成数据（E216）；spdlog.pc 有 `Requires: fmt` 但 CMakeDeps `spdlog::spdlog` 目标不传播 `fmt::fmt` | 双层修复：`cpp_info.requires` 按 dep 配方声明的目标名引用（跨包必须 `pkg::component` 形式，裸包名被 Conan 2.29 判 internal component 报错）；fmt 显式声明为直接依赖（静态变体消费者必须可链接 fmt）。修复后 conan create 全绿 |
| 6 | `meson install` 安装出的 `libcoeurl.so.0.3` 无法加载（`Error loading shared library`），build-tree 同名文件正常 | meson install 在安装副本 `.dynstr` 内原位改写 DT_RUNPATH 字节，hnp clang 内嵌 `.codesign` 哈希失效（知识草稿 E560）；本机 musl 加载器不读 DT_RUNPATH | 配方 `package()` 用 build-tree 原始 `.so` 覆盖安装副本（gupnp 同款）；运行期依赖经 `LD_LIBRARY_PATH` 解析 |
| 7.1 | CI worker（meson 1.11.1）configure 报 `ERROR: Unknown linker(s): [['llvm-ar']]`（设备 meson 1.12.0 + PATH 含 hnp/bin 从未复现） | meson 按编译器（clang）推断静态归档探测名 `llvm-ar` 并用 PATH 裸名解析；worker PATH 短、解析不到 | 配方 `generate()` 用 `tc.binaries["ar"]` 显式钉绝对路径（`which llvm-ar` → hnp bin 同目录 → 兜底 `ar`），与 profile 的 compiler_executables 同构；本地重跑 create 验证 `[binaries] ar` 写入且全绿 |
| 7 | shared 变体 conan create 的 test_package 编译报 `'spdlog/fmt/bundled/format.h' file not found` | ohpcd spdlog 按 external fmt 编译（包内无 bundled 头），但其配方 cpp_info 未声明接口宏，CMakeDeps 生成的 spdlog_DEFINITIONS 为空，消费方 TU 未定义 SPDLOG_FMT_EXTERNAL 落进 bundled 分支 | `package_info()` 在 coeurl 目标上声明消费方接口宏 `SPDLOG_FMT_EXTERNAL/SPDLOG_COMPILED_LIB/SPDLOG_SHARED_LIB`（对齐上游 spdlog config targets 的 INTERFACE_COMPILE_DEFINITIONS）；shared/static 两变体重跑均通过 |

## 源码修改

无补丁（零补丁配方）。上游 meson 原样使用：`tests=false`/`examples=false`（上游默认值，打包只编库本体）、`--wrap-mode=nofallback`（强制依赖走 pkg-config 命中，杜绝 subprojects 网络下载）。`export_conandata_patches`/`apply_conandata_patches` 均保留（无补丁时 no-op）。

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| libcurl | 8.5.0 | ohpcd 发行 binary（无 TLS 后端变体，见问题 #1） |
| spdlog | 1.17.0 | 头文件依赖（公共头 `spdlog/logger.h` 暴露） |
| fmt | 12.2.0 | 直接依赖（静态库内联 spdlog 模板代码的未定义 fmt 符号须可链接；同时是 spdlog 配方硬性传递依赖，显式锁 11.1.3 会版本冲突） |
| libevent | 2.1.13 | 提供 libevent_core + libevent_pthreads |
| doctest | 2.5.2 | 仅上游测试框架（原生探索阶段用），不进包依赖链 |

## 验证结果

- 上游测试（沙箱 HOME、flask testserver 5000/TLS 5443 自签证书，上游 CI 同构）：
  - `tests/requests`：17/17 用例、54/54 断言，Status: SUCCESS!
  - `tests/requests_tls`：17/17 用例、55/55 断言，Status: SUCCESS!
  - junit：http.xml/https.xml 各 `<testcase>` 17，failures=0 errors=0
  - examples/coeurl_example：exit 0
- 上游测试统计：TOTAL=34，PASS=34，FAIL=0，SKIP=0，NOT_RUN=0（统计单位=doctest TEST_CASE；取数命令 `grep "test cases:" <log>` 与 `grep -c "<testcase" <junit>`，已写入 MANIFEST.yml）
- test_package：进程内嵌迷你 HTTP 服务器 + 公开 API 异步 GET 消费者，13/13 断言通过，输出 `COEURL_TEST_PACKAGE_OK`（原生预演与 conan create 内嵌执行均通过）

## 注意事项

- ohpcd 发行 libcurl/8.5.0 无 TLS 后端：本包交付物在默认依赖下的 https 能力取决于该 curl 变体（运行时对 https 返回 CURLE_UNSUPPORTED_PROTOCOL）。上游功能本身不受限（TLS 套件经 TLS-enabled curl 验证 17/17），下游需要 TLS 时应推动带 TLS 后端的 curl 发行变体。
- 库本体以上游 `cpp_std=c++17` 编译；profile cppstd=17，无标准冲突。
- conandata 全文件无 sources 之外的裸 http(s) URL（CI 预下载器边界）。
