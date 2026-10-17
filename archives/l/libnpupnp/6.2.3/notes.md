# libnpupnp 6.2.3 适配笔记

## 编译环境
- 构建系统: meson
- 上游仓库: https://framagit.org/medoc92/npupnp (tag libnpupnp-v6.2.3)
- 源码包: https://www.lesbonscomptes.com/upmpdcli/downloads/libnpupnp-6.2.3.tar.gz
  (作者官方发布页，与 Gentoo/Alpine/Void/Arch 同源；sha512 与 Gentoo Manifest 一致；
  原 framagit 自动归档包在真机侧持续 ConnectTimeout，无法下载，已弃用)
- 编译日期: 2026-09-16
- 编译器: clang/clang++ (HarmonyOS PC, conan profile ohos-aarch64)
- 状态: built (待真机预检确认后由 HMBS 更新)

## 上游分析
- libnpupnp 是 upmpdcli 使用的 UPnP SDK 分支，C++17，Meson 构建。
- 必需依赖: `threads`、`libcurl`、`libmicrohttpd`;可选 `expat` (feature 选项，配方显式 `-Dexpat=disabled`，不引入额外依赖)。
- 上游测试: `test/meson.build` 在 `-Dtestmains=true` 时注册 4 个测试程序
  (`test_description`、`test_init`、`test_netif`、`test_url`)，通过 `meson test` 运行。
  默认 `testmains=false`，配方显式打开以便在 `conan create` 的 build 阶段真实执行。
- 公共头安装到 `include/npupnp` (见 `inc/meson.build` 的 `install_headers(..., subdir: 'npupnp')`)，
  库文件名为 `libnpupnp` (`name_prefix: ''`)，soversion 13。

## 配方设计
- `requirements()`: `curl/8.15.0` + `libmicrohttpd/1.0.1` (均带 transitive_headers/libs)，
  平台判断使用 `in ("Linux", "OHOS")` (R32)。
- `build_requirements()`: `tool_requires("meson/1.11.0")`，与仓库内其他 Meson 配方一致。
- `generate()`: `PkgConfigDeps` 供 Meson 的 `dependency('libcurl')` /
  `dependency('libmicrohttpd')` 查找;`MesonToolchain` 设置 `default_library`、
  `expat=disabled`、`testmains=true`。
- `build()`: `meson.configure()` + `meson.build()` 后运行 `_run_upstream_tests()`:
  用 subprocess 执行 `meson test --print-errorlogs`，解析 `Ok:/Fail:` 汇总与逐项 `OK/FAIL` 行，
  据此输出 `HMBS_UPSTREAM_TEST_RESULT` (数字全部来自框架真实输出;无输出时判失败，绝不报通过)。
  `LD_LIBRARY_PATH` 补入依赖的 libdirs，保证测试二进制能加载 `libcurl`/`libmicrohttpd`。
- 无补丁:源码为纯 POSIX C++，不引入 `__OHOS__` 分支 (R8)，也不改生成文件 (R6)。
- 非系统同名库，默认 `shared=True`;OHOS 下安装后将版本化 `.so` 软链接物化为真实拷贝并用
  `binary-sign-tool` 自签名 (参照 `archives/l/libavtp/0.2.0` 做法，HMFS 上软链接不可靠)。
- `package_info()`: `libs=["npupnp"]` (meson `library('libnpupnp', name_prefix: '')` 产物为 `libnpupnp.so`，`-lnpupnp` 解析；写 `["libnpupnp"]` 会找 `liblibnpupnp.so` 导致 CMakeDeps 报 Library not found)，`includedirs=["include", "include/npupnp"]`，
  `cmake_file_name=libnpupnp` / `cmake_target_name=libnpupnp::libnpupnp` /
  `pkg_config_name=libnpupnp`，Linux/OHOS 下 `system_libs=["m", "pthread"]`。

## test_package 设计 (R34)
- `test_npupnp.cpp` 实质调用公共 API，共 18 个 CHECK:
  - 4 个版本一致性检查 (等价于上游 `test_init.cpp` 的版本段);
  - 10 个 `UpnpResolveURL2` 用例，直接取自上游 `test_url.cpp` 的 RFC 3986 正/异常例与错误路径
    (`UPNP_E_INVALID_PARAM` / `UPNP_E_INVALID_URL`);
  - 4 个 `UpnpInit(NULL, 0)` / `UpnpGetServerIpAddress` / `UpnpGetServerPort` / `UpnpFinish`
    检查 (等价于上游 `test_init.cpp` 的初始化段)。
- 失败即非零退出;二进制自身打印 `HMBS_TEST_PACKAGE_RESULT` (计数器与结果行同源)。
- `test_package/conanfile.py` 用 `self.run(可执行文件, env="conanrun")` 直接运行
  (不用裸 `ctest`，避免通过用例的输出被隐藏导致标记丢失)。
- 上游 `test_netif` / `test_description` 依赖内部头 (`src/inc`)，未安装到包中，
  其功能由 build 阶段真实执行的 `meson test` 覆盖，不在 consumer 侧重复。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 首轮未经过真机验证 | 本轮只允许准备未提交工作树 | 结束本轮，由 HMBS 后台做完整真机验证；失败按反馈继续修复 |
| 2 | 真机 source() 下载 framagit 包持续 ConnectTimeout (3/3 尝试失败) | framagit.org 在真机网络不可达；CI 镜像映射无同字节镜像 | 改用作者官方发布包 lesbonscomptes.com/upmpdcli/downloads/libnpupnp-6.2.3.tar.gz，sha256 更新为实测值 563d2a9e…，sha512 与 Gentoo Manifest 一致，单顶层目录/COPYING/meson 布局不变，配方其余逻辑不动 |
| 3 | 真机 meson setup 报 Unknown compiler /data/service/hnp/bin/clang++ 不存在 | 预检机未提供 profile pin 的 DevBox 绝对路径；MesonToolchain 原样写入 machine file 导致探针失败 | generate() 新增存在性校验的编译器解析：profile 值优先，缺失时按 PATH 与 DevBox 常规路径探测并用 --version 验证可执行性，回写 cross/native machine file 的 c/cpp（c_ld/cpp_ld 仅在原绝对路径缺失时重定位）；_meson_environment 透传 HMBS 注入的 TMPDIR/TMP/TEMP |
| 4 | 上一轮修复后 meson 认出 harmonybrew clang++，但卡在 Unknown linker /data/service/hnp/bin/llvm-ar 不存在 | 同一机理：machine file 的 ar 也是 profile 绝对路径，在该预检机缺失；真机实际工具链位于 harmonybrew/bin | 把 machine file 重定位键从 c/cpp/c_ld/cpp_ld 扩展到 ar/ranlib/strip（仅改写不存在的绝对路径，健康机无影响） |
| 5 | 上一轮扩展键后仍报 Unknown linker [['/data/service/hnp/bin/llvm-ar']]，且伴随 /tmp 只读报错 | 上一方案无效的原因：旧正则只匹配 `ar = 'path'` 字符串写法，而 MesonToolchain 写出的是列表写法 `ar = ['/path/llvm-ar']`（meson 报错的双层列表即证据），导致 ar 行从未被改写；且 ar 只试了 bindir/basename 单候选、未按 llvm-ar/ar 双别名做 PATH 探测；TMPDIR 只在 build() 期透传，generate() 期 meson 仍可能碰只读 /tmp | 换路线：generate() 入口先选定可写 TMPDIR 并同步到 os.environ；删除旧 _fixup/_inject，改用单函数 _repair_meson_machine_files：整行取值后对其中每个引号路径做替换，同时覆盖字符串与列表写法，c/cpp 只换首个可执行位、ar/ranlib/strip 按 llvm-*/通用名做 --version 探测并在缺失时插入 [binaries] 条目；manifest.yaml 与 test_package/MANIFEST.yml 的源地址/sha 同步为 lesbonscomptes 官方包 |

## 验证结果

```bash
# 待 HMBS 真机预检 (conan create) 返回后如实填写:
# - meson test 4/4
# - test_package 18/18
```

## 注意事项
- `curl/8.15.0` 与 `libmicrohttpd/1.0.1` 在归档中状态为 `built`，W0 依赖发布状态待 HMBS/CI 复核;
  若制品仓缺失对应二进制，预检会明确报错，届时再按依赖拓扑处理。
- test_package 的 `UpnpInit` 需要回环/组播可用的网络栈;若真机沙箱受限导致初始化失败，
  下一轮按实际日志处理 (不伪造通过)。
| 6 | 主包 meson 已通过、新卡点在 test_package 的 CMake configure：CMAKE_CXX_COMPILER 仍是缺失的 /data/service/hnp/bin/clang++ | 主配方只修了 Meson machine file，test_package 的 CMakeToolchain 同样原样抄写 profile 绝对路径；且 test_package 无 TMPDIR 兜底、无编译器重绑定 | 改用与 meson 不同的路线：test_package 改为显式 CMakeToolchain.generate() 并在 generate() 内打补丁，仅改写不存在的绝对编译器路径（引号/非引号三式全覆盖，健康机无影响），同时做 --version 验收的 clang/clang++ 探测与可写 TMPDIR 选定 |
| 7 | test_package 报 Imported target includes non-existent .../p/include，上游测试 0 发现 | 上轮 machine-file 重写时误删了 build()/package()/package_info()/_meson_environment() 等方法，包内无 include，导致 CMakeDeps 校验失败；与编译器路径无关 | 恢复 build（configure/build/meson test 并输出 HMBS_UPSTREAM_TEST_RESULT）、package（meson install + COPYING + OHOS 别名物化签名）、package_info（含 include/include-npupnp 与 cmake/pkg-config 属性）、_test_library_dirs 与 _meson_environment（PKG_CONFIG_PATH/TMPDIR 透传），其余修复保持不动 |
| 8 | meson setup Dependency libcurl required but not found, fallbacks disabled | PkgConfigDeps emits libcurl.pc into generators_folder but worker has no pkg-config binary on PATH (HMBS injects only cmake/make/ninja/python3); meson cannot resolve any .pc so both libcurl and libmicrohttpd lookups fail | New route vs cycles 1-2 (compiler/archiver path rewrites): add tool_requires pkgconf/3.0.5 like fcft-3.3.3 and gulkan-0.15.1, keep PkgConfigDeps and PKG_CONFIG_PATH passthrough unchanged |
| 9 | added tool_requires pkgconf/3.0.5 yet meson still reports Dependency libcurl required but not found (pkgconf recipe downloaded ok) | Package alone does not wire the binary: ohpcd pkgconf installs bin/pkgconf only and its package() rejects a bin/pkg-config alias, while workers have no system pkg-config on PATH; MesonToolchain [binaries] therefore still points at bare pkg-config which does not execute | Different route from round 8 (package presence): resolve runnable binary (conf tools.gnu:pkg_config, deps.build pkgconf bin/pkgconf, PATH pkg-config/pkgconf, --version handshake), set tc.binaries[pkg-config] before generate, extend machine-file repair to pkg-config/pkgconf keys with missing-entry insert, prepend pkgconf bindir to PATH in _meson_environment |
| 10 | Malformed machine file: option pkg-config in section binaries already exists (native ini line 24) | Repair regex key class [A-Za-z0-9_]+ excluded hyphen, so tc.binaries-written pkg-config line parsed as key pkg / unmatched and repair inserted a second pkg-config entry | Different route from rounds 8-9 (wiring): keep tc.binaries wiring, widen line_pattern and key_match to [A-Za-z0-9_-]+ so existing pkg-config/pkgconf lines are seen, swapped if dangling, never duplicated; verified with local regex simulation |
| 11 | meson test 阶段 `/bin/sh: meson: inaccessible or not found` (rc=127, executed=0)，伴随 preflight.sh 自身 `/tmp/sh....tmp: Read-only` 噪声 | 自定义 `_run_upstream_tests()` 用 `subprocess.run(cmd, shell=True)` 裸调 `meson`：配方从未生成 VirtualBuildEnv，`_meson_environment()` 只透传 pkgconf/编译器 bindir，从未暴露 meson tool 包 bindir；Meson helper 内部能解析 tool 二进制所以 configure/build 成功，只有裸 shell 调用找不到 meson；shell=True 还会经由只读 /tmp 建临时文件 | 换路线：新增 `_meson_bindir()`/`_resolve_meson()`（tool 包 bin/meson 优先，PATH 兜底，--version 握手），`_meson_environment()` 预置 meson bindir 到 PATH，`_run_upstream_tests()` 改为 `shell=False` 列表调用绝对 meson 路径并把 bindir 注入 test_env PATH（marker 的 command 仍保留人类可读 `meson test -C ...`），彻底绕开裸 PATH 依赖与 /bin/sh 的 /tmp 临时文件；不删测试、不改口径 |
| 12 | 主包 meson test 4/4 通过后 test_package CMake configure 报 `Library 'libnpupnp' not found in package` | `package_info()` 写 `libs=["libnpupnp"]`，而上游 `meson.build` 为 `library('libnpupnp', name_prefix: '')`，产物是 `libnpupnp.so`；Conan `-l<name>` 语义下 `libnpupnp` 会找 `liblibnpupnp.so`，故 CMakeDeps 校验失败；与编译器路径/TMPDIR 无关 | 最小改名：`cpp_info.libs=["npupnp"]`（`-lnpupnp` 解析到 `libnpupnp.so`），cmake_target/pkg-config 名保持 `libnpupnp` 不变；不改 test_package 链接写法 |
