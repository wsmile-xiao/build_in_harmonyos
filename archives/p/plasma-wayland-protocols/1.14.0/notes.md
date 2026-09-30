# plasma-wayland-protocols 1.14.0 适配笔记

## 编译环境
- 构建系统: cmake（data-only，无 C/C++ 编译产物）
- 编译日期: 2026-09-27
- 编译器: clang / clang++（未实际编译任何目标）
- 目标平台: OHOS / armv8 (aarch64)
- 状态: built（conan create 本地验证通过；未 upload）

## 为什么适配此包

`kwayland5/5.116.0` 构建时执行
`find_package(PlasmaWaylandProtocols 1.9.0 CONFIG REQUIRED)`，并读取
`${PLASMA_WAYLAND_PROTOCOLS_DIR}/<proto>.xml`（约 22 个协议）。该目录此前无人提供，
`libkscreen/6.7.2` 只能把上游 tarball 当第二源码内联并把路径硬编码绕开。
本包把 plasma-wayland-protocols 正式做成 conan 包，下游可正常 `self.requires()`。

## W0 依赖发布检查（先查依赖再动手）

```
$ conan download ecm/6.26.0 -r=ohpcd --only-recipe
Downloading recipe 'ecm/6.26.0#0768b8c9ea392be14e346eca1d1ec6dd'
  ...
Local Cache
  ecm
    ecm/6.26.0
      revisions
        0768b8c9ea392be14e346eca1d1ec6dd (2026-08-13 07:15:30 UTC)
exit 0
```
除 `ecm/6.26.0`（构建期 tool_requires）外无需其他依赖，均已发布。

## 编译步骤

```bash
cd "$REPO_ROOT"
conan create archives/p/plasma-wayland-protocols/1.14.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

配方只做三件事：解包源码 → `cmake.configure()/build()` → `cmake.install()`。
上游 `CMakeLists.txt` + `src/CMakeLists.txt` 的 install 规则完整覆盖产物：
30 个协议 XML + 2 个向后兼容重命名 → `${KDE_INSTALL_DATADIR}/plasma-wayland-protocols`；
`PlasmaWaylandProtocolsConfig.cmake` + `ConfigVersion.cmake` →
`${KDE_INSTALL_CMAKEPACKAGEDIR}/PlasmaWaylandProtocols`。

## 关键设计：消费者侧 `find_package` 必须命中原生 config

上游自带 CMake 包配置。若 `package_info()` 不做处理，CMakeDeps 会在 generators 目录
生成同名的 `PlasmaWaylandProtocolsConfig.cmake`；由于 CMakeToolchain 把 generators
目录 prepend 到 `CMAKE_PREFIX_PATH` 最前面，它会**遮蔽**包内原生 config，而生成的
那个 config 并不定义 `PLASMA_WAYLAND_PROTOCOLS_DIR`——下游会拿到空变量。

处理（libkscreen/6.7.2 先例）：

```python
self.cpp_info.set_property("cmake_find_mode", "none")   # 不生成遮蔽 config
self.cpp_info.builddirs = [os.path.join("lib", "cmake")]  # 原生 config 所在父目录入 PREFIX_PATH
```

实测（W3 日志）：

```
-- FIND_PACKAGE_OK PLASMA_WAYLAND_PROTOCOLS_DIR=/storage/Users/.../p/share/plasma-wayland-protocols
-- FIND_PACKAGE_OK all required protocol XML files present in the package tree
```

包内生成的 config 内容（`<pkg>/lib/cmake/PlasmaWaylandProtocols/PlasmaWaylandProtocolsConfig.cmake`）：

```cmake
get_filename_component(PACKAGE_PREFIX_DIR "${CMAKE_CURRENT_LIST_DIR}/../../../" ABSOLUTE)
...
set(PLASMA_WAYLAND_PROTOCOLS_DIR "${PACKAGE_PREFIX_DIR}/share/plasma-wayland-protocols")
```

`CMAKE_CURRENT_LIST_DIR` = `.../lib/cmake/PlasmaWaylandProtocols`，`../../../` = 包根，
故 `PLASMA_WAYLAND_PROTOCOLS_DIR` **恒指向本 conan 包内**，不依赖任何共享 `/usr/local`
前缀（R49）。此点已通过实际读取生成文件 + 运行 `cmake -P` 求值双重确认（非推断）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `cmake -P resolve_pwp_dir.cmake` 取得的目录为空 | CMake **脚本模式**下 `message()` 写入 stderr，脚本用 `sed` 读 stdout 取不到值 | 改为 `file(WRITE "${PWP_OUT}" "${PLASMA_WAYLAND_PROTOCOLS_DIR}")` 落盘再读；`resolve_pwp_dir.cmake` 保留 `message()` 回退 |
| 2 | 本地 CI L0g 报 `hardcoded_remote` | conanfile.py 注释里出现字面量 `conan download ecm/6.26.0 -r=ohpcd`，命中 L0g 正则 `conan\s+(install\|download\|...).*\s-r[= ]`（注释也扫） | 改写注释为“…confirmed published to the ohpcd registry”，不出现 `-r=`/`-r ` |
| 3 | 消费者侧 `PLASMA_WAYLAND_PROTOCOLS_DIR` 为空风险 | CMakeDeps 同名 config 遮蔽原生 config（见上节） | `cmake_find_mode="none"` + `builddirs=["lib/cmake"]` |

## 源码修改

无补丁（`patches: []`）。上游源码/安装规则原样使用。

## 依赖版本

| 依赖 | 版本 | 类型 |
|------|------|------|
| ecm (extra-cmake-modules) | 6.26.0 | tool_requires（构建期） |

运行时无依赖（纯数据包）。

## 验证结果

### W3 本地编译验证（conan create）

命令与退出码：

```
conan create archives/p/plasma-wayland-protocols/1.14.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
EXIT=0
```

关键行：

```
======== Launching test_package ========
plasma-wayland-protocols/1.14.0 (test package): Running CMake.configure()
-- FIND_PACKAGE_OK PLASMA_WAYLAND_PROTOCOLS_DIR=.../p/share/plasma-wayland-protocols
-- FIND_PACKAGE_OK all required protocol XML files present in the package tree
plasma-wayland-protocols/1.14.0 (test package): Running test()
...
  - PLASMA_WAYLAND_PROTOCOLS_DIR inside package: .../p/share/plasma-wayland-protocols
  - screencast.xml -> protocol name=zkde_screencast_unstable_v1 interfaces=2
assertions=143 failures=0
```

日志：`$HOME/tmp/pwp-create-fix.log`（PR 修订版实测：`conan create` exit 0，
`assertions=143 failures=0`）。

### 本地 CI 模拟（ci/conan/build_and_test.sh）

```bash
cd "$REPO_ROOT"
CI_PACKAGES="archives/p/plasma-wayland-protocols/1.14.0" \
  zsh ci/conan/build_and_test.sh "archives/p/plasma-wayland-protocols/1.14.0"
```

结果行（断言提交后运行，JC 走 incremental 模式仅扫本 PR 12 个文件）：

```
G0_RESULT=pass
KC_RESULT=pass
JC_RESULT=pass                 # incremental (12 个文件)
L0_RESULT=pass: all checks passed
L1_RESULT=pass: upstream tests + test_package executed
L2_RESULT=skip: no bin/ dir
L4_RESULT=pass: no patches
L5_RESULT=pass: lib/ has content
```

其中 L1e 破坏性反向验证：`[sabotage] lib/ moved away` →
`[ok] L1e: Negative test confirmed — test genuinely depends on plasma-wayland-protocols`。
最终 `Success: 1  Failed: 0  Pass rate: 100.0% (1/1)`。

> 注：首次在**提交前**运行 CI 时 JC 因工作树存在其他任务遗留的
> `archives/{c/cloog,k/kics,t/thc}/.staging-verified`（均已在 origin/main 上跟踪）
> 而落入 full 整仓扫描并报 junk；提交后 JC 自动切回 incremental 模式，
> 仅检查本 PR 的 12 个文件 → pass。本包目录内无任何 junk 文件。

## 上游测试计数（R51 三步法，证据）

**第一步：清点** —— 上游 **确无测试套件**。

```
# ① tarball 中 tests/ 目录计数（0 = 无）
$ tar tf plasma-wayland-protocols-1.14.0.tar.xz | grep -cE '/tests?/'
0

# ② CMake 测试目标（enable_testing/add_test/ctest）命中数（0 = 无）
$ grep -rniE 'enable_testing|add_test|ctest' <src>/ | wc -l
0

# ③ 完整源码树文件清单（无任何 test* 文件、无 tests/ 目录）
$ find <src> -type f | sort
./CMakeLists.txt
./PlasmaWaylandProtocolsConfig.cmake.in
./cmake/Modules/FindWaylandProtocols.cmake
./metainfo.yaml
./README.md
./COPYING.LIB
./LICENSES/{BSD-3-Clause,CC0-1.0,LGPL-2.1-or-later,MIT-CMU,MIT}.txt
./src/CMakeLists.txt
./src/protocols/*.xml  (30 个)
./src/protocols/TODOKF6.md
./.gitignore  .gitlab-ci.yml  .kde-ci.yml
```

上游 `CMakeLists.txt` 仅做 `install()`，无 `ctest` 目标 → `upstream_tests = 0`。

**第二步：可运行环境运行** —— 无上游测试可运行（N=0）。

**第三步：如实回填** —— `test_package/MANIFEST.yml` 记 `upstream_tests: []`、
`upstream_test_in_build: false`；本包全部实质测试落在 test_package。

## test_package 自建测试（R34：实质依赖被测包）

| 文件 | 作用 |
|------|------|
| `CMakeLists.txt` | 真实消费者工程：`find_package(PlasmaWaylandProtocols 1.9.0 CONFIG REQUIRED)`，断言 `PLASMA_WAYLAND_PROTOCOLS_DIR` 存在且 22 个协议 XML 全在（`build()` 中执行）；并构建端到端用例 `plasma_e2e`（其协议绑定在构建期由包内 XML 生成） |
| `resolve_pwp_dir.cmake` | `cmake -P` 求值原生 config 得到 `PLASMA_WAYLAND_PROTOCOLS_DIR` |
| `test_protocols.sh` | 定位包内原生 config → 求值目录 → 调 validate（并传入包目录）；`set -o pipefail`，以 `find -print -quit` 取代 `find \| head -1`；打印 `assertions=N failures=0`，失败非零退出 |
| `validate_protocols.py` | 143 项断言（目录存在 + 位于包内 + 目录名正确；22 个消费协议逐文件 存在/非空/合式 XML/根元素 `<protocol>`/name 非空/有 interface/interface 均有 name+version；两处重命名协议名正确，其中 screencast.xml 走独立第二遍） |
| `e2e/plasma_e2e.c` | **鸿蒙特有测试 / 完整消费者用例（rule 12）**：见下节 |
| `e2e/gen_protocol.py` | 构建期协议生成器：由包内 `keystate.xml` 产出 `keystate-protocol.h/.c`（枚举、opcode、listener、客户端包装、服务端 handler 结构、事件发送器、`wl_interface` 表）；严格失败（XML 缺失/非合式/根元素不对/接口数或版本不符/参数类型无法精确翻译/产出空文件） |

实测 `assertions=143 failures=0`（exit 0）。破坏性反向验证（L1e）：包内 `lib/`
被移走后 `find_package` 失败 → 测试失败，证明测试真实依赖被测包。
另有失败注入复核（本轮 PR 修订）：把 `screencast.xml` 或
`plasma-virtual-desktop.xml` 的 `<protocol name>` 改错，各自精确红 1 条断言
（`failures=1`）并 `rc=1`；此前版本对 screencast 的改动**不会**被发现
（`RENAMES["screencast"]` 因 screencast 不在 `PROTOCOLS` 中而从不触发），
本轮已修复。

## 鸿蒙特有测试：端到端消费者用例（rule 12）

数据包的真实消费方式是「把协议描述变成代码、再说这个协议」（kwayland5 / kwin /
libkscreen 都是如此）。`e2e/plasma_e2e.c` 完整走通这条链路，而不是列断言：

```
构建期（CMakeLists.txt 的 add_custom_command + e2e/gen_protocol.py）
  ${PLASMA_WAYLAND_PROTOCOLS_DIR}/keystate.xml   ← 包内实际安装的文件，
     经包内原生 PlasmaWaylandProtocolsConfig.cmake 解析出的路径
        └─ gen_protocol.py ─→ generated/keystate-protocol.h + .c
                                  （wl_interface 表 + 客户端/服务端调用包装）

运行期（ctest 用例 plasma_keystate_e2e）
  socketpair(AF_UNIX, SOCK_STREAM)
    ├─ server 端：wl_display_create + wl_client_create(fd)
    │             + wl_global_create(org_kde_kwin_keystate, v4)
    └─ client 端：wl_display_connect_to_fd → wl_display_get_registry
                  → 看到全局 → wl_registry_bind → 生成的 fetchStates()
  服务端 handler 被解出 → 生成的 stateChanged(key=1, state=2) 回发
  客户端 listener 收到 → 载荷逐字节比对（numlock=1 / locked=2）
  生成的 destructor 请求 → 服务端 handler 亦被解出
```

实测输出（`conan create` 全流程，退出码 0）：

```
E2E CHECK the package's protocol XML is readable                     OK
E2E STEP installed XML fingerprint=0xc9754fd4fb39165d, bindings built from 0xc9754fd4fb39165d
E2E CHECK the installed XML is the bindings' source                  OK
E2E CHECK generated interface name / version / request / event count  OK
CLI: global org_kde_kwin_keystate name=1 version=4
SRV: global bound (version 4)
SRV: fetchStates() decoded from the generated protocol
CLI: stateChanged(key=1, state=2) received
SRV: destroy() decoded from the generated protocol
E2E STEP client events=1 key=1 state=2; server binds=1 fetchStates=1 destroys=1
assertions=22 failures=0
hongmeng_e2e_flow=PASS
```

要点：

- **不使用文件系统 socket**：本沙箱禁止文件系统 AF_UNIX `bind()`（EPERM），故用
  `wl_client_create(fd)` 直接接管 socketpair 一端，未调用 `wl_display_add_socket*()`。
- **为何测试自带生成器**：本机 `wayland/1.22.0` 包内的 `wayland-scanner` 是
  可执行性被 OHOS 加载器拒绝的 ELF（#13500 修复），测试构建期无法调用上游 scanner。
  为确证生成规则与上游一致，用**真实 wayland-scanner 1.22.0**（配齐 expat/libxml2
  依赖后在本机可执行）对同一 `keystate.xml` 生成参考实现逐项对齐：
  `{"fetchStates",""}` / `{"destroy","4"}` / `{"stateChanged","uu"}`、
  接口名 `org_kde_kwin_keystate` v4、2 requests / 1 event —— 完全一致。
- **签名约定**：`since` 版本号是**前置**数字（`destroy` since 4 → `"4"`），
  与上游 scanner 一致（`wl_surface.damage_buffer` since 4 → `"4iiii"`）。
- **只链接 client + server**：已发布的 `wayland/1.22.0` 同时装了
  `libwayland-cursor.so.0` / `libwayland-egl.so.1`，其 ELF 被加载器拒绝
  （`dlopen` 实测 `Permission denied`），故用例按显式路径只链接
  `libwayland-client.so` / `libwayland-server.so`，避免二进制起不来。
- **wayland 是仅测试用依赖**：被测包本身是纯数据包，运行期不依赖 wayland；
  该依赖只为让生成的协议代码在真实传输上跑通。

## 交付物

| 文件 | 说明 |
|------|------|
| `conanfile.py` | 配方（data-only，cmake） |
| `conandata.yml` | URL 列表（镜像优先 + 官方源兜底）+ sha256 |
| `test_package/` | 消费者视角验证（CMake 工程 + sh + py 断言） |
| `manifest.yaml` / `notes.md` | 元数据 |

## 注意事项

- 版本 1.14.0 与 kwayland5 5.116.0 的 `find_package(... 1.9.0 ...)` 版本约束兼容
  （`ecm_setup_version` 生成 `PACKAGE_VERSION 1.14.0`，向下兼容 1.9.0）。
- `plasma-virtual-desktop.xml` 与 `screencast.xml` 是上游 install 规则的 RENAME 产物，
  kwayland 5.116 实际消费前者，故不可省略。
