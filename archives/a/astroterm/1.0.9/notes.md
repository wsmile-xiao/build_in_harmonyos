# astroterm 1.0.9 — 适配笔记

## 基本信息

- **适配状态**: `ready` / `built` / `verified` / `released`
- **适配版本**: 1.0.9
- **对应 Issue**: #49
- **用户名**: gyccc
- **队伍**: NebulaAGI
- **构建系统**: Meson
- **语言**: C

## 编译步骤与关键注意事项

### 1. 依赖说明

astroterm 依赖以下库：
- `argtable3` (>= 3.0) — 命令行参数解析
- `ncurses` (>= 6.0) — 终端 UI
- `math` — 标准 C 数学库（libc 的一部分）

Conan 配方下载并静态编译 argtable3 3.3.1 源码，ncurses 由 OHOS 构建环境提供。

### 2. 构建步骤

```bash
conan create . --profile:host <OHOS-profile> --profile:build <native-profile>
```

Meson 构建流程：
1. `source()`: 下载 `v1.0.9.tar.gz`
2. `generate()`: 生成 MesonToolchain（注入 ar/ranlib 路径）
3. `build()`: 应用补丁，执行 `meson setup` + `meson compile`
4. `package()`: `meson install`，并清理 `.so`/`.la` 文件（R26）

### 3. OHOS 适配补丁

#### 补丁 1: `0001-add-stddef.h-before-string.h.patch`

在 `include/parse_BSC5.h` 中 `string.h` 前添加 `#include <stddef.h>`，解决部分目标平台 `size_t` 未定义的问题。

#### 补丁 2: `0002-fix-embed-sh-for-toybox.patch`

OHOS 使用 toybox 工具链，其 `xxd` 不支持 `-i` 选项。补丁在 `scripts/embed.sh` 中检测 `xxd -i` 是否可用，不可用时自动回退到项目自带的 `scripts/embed.py`（CLI 接口一致），确保 `meson.build` 中的 `custom_target('bsc5_embed')` 能正常生成 `bsc5_embed.h`。

#### 补丁 3: `0003-fix-curses-for-ohos.patch`

OHOS CI worker 在 `/storage/Users/currentUser/usr/local/{include,lib}` 预装了 ncurses 静态库（`libncursesw.a`）和头文件，但未安装 `curses.pc` pkg-config 文件。meson 的 `dependency('curses')` 走 pkg-config 查找必然失败。

**第一版方案（已废弃）**：用 `cc.find_library('ncursesw', dirs: [...])` 替代。但 meson 1.11.1 的 `compiler.find_library` 会编译链接测试程序验证库可用，而 Conan MesonToolchain 隔离环境下 OHOS clang 默认搜索路径不含 `/storage/Users/currentUser/usr/local/{include,lib}`，导致 probe 失败（`-I`/`-L` 均缺失），报错：

```
../meson.build:150:21: ERROR: C shared or static library 'ncursesw' not found
```

**最终方案（条件应用补丁）**：补丁 0003 仅在 `self.settings.os == "OHOS"` 时应用。`conanfile.py` 的 `build()` 手动遍历 `conan_data["patches"]`，对 `0003` 补丁加 OS 判断：OHOS 应用 `declare_dependency(link_args: [...], include_directories: [...])` 直接注入 `-I`/`-L`/`-l`；Linux/macOS 跳过补丁，保留原始 `dependency('curses', required: true)` 走 pkg-config。

- 这与 `conanfile.py` 的 `validate()` 允许 `os in ("Linux", "OHOS")` 契约一致：Linux 走 pkg-config 原可移植路径，OHOS 走硬编码路径。
- 不再使用 fallback 模式（`required: false` + `if not curses.found()`），因为补丁只在 OHOS 上应用，不需要运行时判断。
- `declare_dependency()` 返回 `found() == true`，后续 `if curses.found()` 头文件检测块在 OHOS 上继续执行。
- `cc.has_header()` 不带 args 时在 OHOS 上找不到 ncurses 头文件，所有 `HAVE_NCURSES*` 宏不定义。
- 但源代码（`src/*.c`、`include/*.h`）不引用任何 `HAVE_NCURSES*` / `HAVE_CURSES*` 宏，仅 meson.build 内部 `if` 块用，缺失仅触发 warning，不阻塞 configure/compile。
- 实际编译时 `static_library(..., dependencies: [curses, math])` 会自动应用 `curses` 的 include_directories，`#include <curses.h>` 能找到。

### 4. 静态链接（R26）

astroterm 是终端工具，通过 `MesonToolchain` 默认关闭共享库构建，并在 `package()` 阶段删除任何意外生成的 `.so` / `.la` 文件，确保 DevBox 部署兼容性。

### 5. 已知问题与待办

- **系统依赖**: ncurses 由 OHOS 构建环境提供；argtable3 3.3.1 随配方下载并静态编译。
- **ncurses 宽字符**: 确保 ncurses 启用了 wide-char 支持（`ncursesw`），否则中文字符或特殊符号可能显示异常。
- **上游测试**: 上游包含 7 个 Unity 测试程序，当前配方未在 CI 中执行；test_package 执行二进制烟雾测试（`--version` / `--help`）。

### 6. 文件清单

- `conanfile.py` — Conan 配方
- `conandata.yml` — 源码与补丁元数据
- `manifest.yaml` — 软件包元数据
- `test_package/conanfile.py` — 测试入口
- `test_package/MANIFEST.yml` — 测试清单
- `patches/0001-*.patch` — stddef.h 修复
- `patches/0002-*.patch` — embed.sh toybox 兼容
- `patches/0003-*.patch` — curses pkg-config 绕过（OHOS 专用）

## 真机预检记录

- 2026-08-16（连续多轮）: 预检在 compile 阶段前失败，stderr 仅含
  `ohos@113.25.148.239: Permission denied (publickey,keyboard-interactive).`，
  stdout 为空，上游测试 0/0/0。属 SSH 传输层 publickey 认证被拒的真机连接
  环境故障，发生在任何编译/测试开始之前，与配方代码无关。按守则停止修改
  代码、等待环境恢复，工作树未做配方改动。
- 2026-08-16（第 3 策略周期）: 证据与前三轮逐字一致——stderr 仅
  `ohos@113.25.148.239: Permission denied (publickey,keyboard-interactive).`、
  stdout 为空、compile 阶段在任何编译前失败、上游测试 0/0/0。SSH 公钥认证
  由 HMBS 宿主侧发起，工作树内容不可能影响其到真机的认证；确认仍为真机
  连接环境故障，本轮不做配方改动、不伪造修复，等待环境恢复。
- 配方已具备全部 HMBS 硬门禁标记：
  `HMBS_UPSTREAM_TEST_RESULT`（conanfile.py build() 内 meson test 后输出）、
  `HMBS_TEST_PACKAGE_RESULT`（test_package/conanfile.py 内 test_astroterm 后输出），
  SSH 环境恢复后可直接复跑预检。
- 2026-08-16（compile 阶段失败）: 预检进入 compile 阶段即失败，stdout 明确报
  `/system/bin/sh: meson: inaccessible or not found`，随后
  `ConanException: Error 127 while executing`（conanfile.py 的 meson.configure()）。
  HMBS_BUILD_TOOLS 只探测到 cmake/make/ninja/python3 四件套，未提供 meson；
  HMBS_PLATFORM_CAPABILITIES 显示 chmod=0/hardlink=0（与 meson 无关）。
  **根因**：OHOS 真机（与官方 CI 同源）的构建环境 PATH 上没有 meson，配方
  build() 直接调 `meson setup` 必然 127。仓库已发布 meson 工具包
  `archives/m/meson/1.11.0`（_index.yaml status: uploaded；commands.json
  binary: false 即 recipe-only，首次消费时在真机现场构建，build() 内含
  OHOS 专用测试环境注入，不适配 Linux）。
  **修复**：conanfile.py 新增 build_requirements()，`if self.settings.os ==
  "OHOS": self.tool_requires("meson/1.11.0")`——Conan 2 自动把 tool_requires
  的 cpp_info.bindirs（bin/）前置到构建环境 PATH，`meson setup`/`meson
  test` 均可解析；Linux 分支保持系统 meson。manifest.yaml 的
  build.dependencies 补充 meson/1.11.0（CI L0i 的 AST 扫描会校验该依赖在
  ohpcd registry 中存在，已确认 uploaded）。
- 2026-08-16（依赖图解析失败，tool_requires 方案废弃）: 预检在计算依赖图阶段
  即失败，stderr 明确报
  `ERROR: Package 'meson/1.11.0' not resolved: Unable to find 'meson/1.11.0' in
  remotes. Required by 'astroterm/1.0.9'`——conan create 先在本地缓存找，再
  依次匿名连接 conancenter、ohpcd 两个 remote 均未命中。上一轮"meson/1.11.0
  已发布到 ohpcd"的判断错误：仓库归档有 recipe 不代表 ohpcd registry 已
  发布/可匿名解析，tool_requires 在依赖图阶段即失败，走不到 build()。
  **修复（改用 libdvdnav/7.0.0 已验证的 vendored meson 方案）**：
  - conanfile.py 删除 build_requirements()（不再 tool_requires 任何远端包）；
  - source() 新增 `get(conan_data["meson_source"])`，把官方 meson 1.11.2
    源码解压到 source_folder/meson-vendor/；
  - 新增 `_meson_cmd()`/`_meson_env()`：绕过 PYTHONPATH 传递问题，用
    `python3 -c` 脚本进程内 sys.path.insert(0, meson-vendor) 后调
    mesonmain.main()，sys.argv 前置 "meson" 占位；env 用 list 传
    PYTHONPATH/PYTHONHOME/LD_LIBRARY_PATH 及 HMBS_* 工具路径；
  - build()/测试/package() 全部改经 vendored meson 执行（setup 带
    `--prefix=/ --native-file`，install 带 `--destdir`），ninja 用
    HMBS_NINJA 绝对路径；不再使用 Conan 的 Meson 工具类；
  - manifest.yaml 的 build.dependencies 改为
    "meson/1.11.2 (vendored 源码, source() 下载至 meson-vendor/, 无远端依赖)"。
  conandata.yml 的 meson_source 条目（官方 meson-1.11.2.tar.gz + sha256）与
  libdvdnav 完全一致，已验证可下载。
- 2026-08-16（compile 阶段失败：cities.h 裸十六进制字节）: 预检在编译
  src/city.c 时失败，报 `./cities.h:1:3: error: expected identifier or '('`，
  头文件首行就是 `0x63, 0x69, 0x74, ...`（cities.csv 内容的 hex dump），
  且 `cities`/`cities_len` 未声明。**根因**：OHOS 真机（与官方 CI 同源）
  的 xxd 是 toybox 实现，其 `-i` 只输出裸十六进制字节（每行 12 字节、
  两空格缩进），**不输出** GNU xxd 的 `unsigned char NAME[] = {` /
  `unsigned int NAME_len` 包装行（toybox xxd.c 源码注释明确 "The original
  xxd outputs a header/footer... We don't"）。旧补丁 0002 用
  `xxd -i /dev/null` 的退出码判断"是否支持 -i"，toybox xxd 支持 -i 返回
  0，fallback 不触发，sed 无事可改，cities.h 直接变裸字节。
  **修复**：重写补丁 0002——先照旧走 xxd 管道，随即 `grep -q "unsigned
  char"` 检查生成结果是否含 C 数组包装行；不含（toybox 场景）则回退
  `embed.py --source/--header/--array-name`（CLI 与 embed.sh 一致），
  embed.py 输出 `unsigned int <name>_len = N;` + `unsigned char <name>[] =
  {...};`，与 src/city.c（cities/cities_len）、src/main.c（bsc5*）引用
  契约一致。python 解释器优先用 `$HMBS_PYTHON3`（真机注入绝对路径），
  缺省回退 `python3`。本地用假 toybox xxd + 真 python 端到端验证通过：
  生成的 cities.h 含包装行、可被 C 编译器接受；GNU xxd 场景 grep 命中
  包装行，不回退，行为与上游一致。
- 2026-08-18（compile 阶段失败：argtable3 源码下载超时）: 预检 stdout 明确报
  `ERROR: astroterm/1.0.9: Error in source() method, line 77`——conanfile.py
  source() 内 `get(self, **conan_data["argtable3_source"])` 下载
  `https://github.com/argtable/argtable3/releases/download/v3.3.1/argtable-v3.3.1.tar.gz`
  时 github.com 连接/读取超时（connect timeout=30、read timeout=60，重试两次
  后抛 ConanException）。同一轮 astroterm 主包 v1.0.9.tar.gz 与 bsc5 下载成功，
  仅 GitHub 域不可达。**修复**：按守则「源码包下载超时」例外，把
  conandata.yml 中三个 GitHub 源（sources/argtable3_source/meson_source）的
  url 从单值改为有序列表，复用仓库 ci/conan/build_and_test.sh 已维护的 GitHub
  镜像映射（实测仅 gh-proxy.com 可用）：`https://gh-proxy.com/<原URL>` 置前、
  官方原始 URL 置后兜底；sha256 全部保持官方原值不变（本地缓存
  argtable-v3.3.1.tar.gz sha256 c08bca4b… 与 conandata 一致，佐证镜像内容
  一致）。Conan 2.x get() 支持 url 列表逐个尝试。改动仅工作树，未提交。


- 2026-08-18（upstream_test 阶段失败：drawing_test "Failed to create fake terminal"）:
  预检 build 与其余 6 个测试（coord/astro/city/bit/core/stopwatch）全部通过，仅
  7/7 drawing_test FAIL（exit status 1），stderr 仅一行
  "Failed to create fake terminal"。该消息来自上游 test/drawing_test.c:416——
  setUp() 里 `newterm("xterm", output_file, stdin)` 返回 NULL（上游注释本意是
  用 fake screen 绕过真实终端依赖）。**根因**：newterm 通过 terminfo 数据库查
  找 "xterm" 条目，而 OHOS 系统默认 terminfo 路径不存在该条目；配方自带的
  cmd-pkgs ncurses-6.4-ohos 包（conandata ncurses_ohos，解压到
  deps/ncurses-ohos/）内含 share/terminfo/x/xterm，但测试运行时未设置
  TERMINFO，ncurses 找不到条目直接返回 NULL。
  **修复**：conanfile.py 的 _meson_env() 在 os==OHOS 时把
  deps/ncurses-ohos/share/terminfo 注入 TERMINFO 环境变量（目录存在才注入），
  meson test 子进程继承该环境变量后 newterm 可正确定位 xterm 条目。改动仅工作
  树，未提交。

- 2026-08-18（upstream_test 阶段失败·第 2 轮：drawing_test 仍 FAIL）:
  上一轮在 _meson_env() 里注入 TERMINFO（env=list 形式）后真机复跑仍失败：
  7/7 drawing_test FAIL exit status 1，HMBS_UPSTREAM_TEST_RESULT failed=1。
  **根因修正**：Conan 2 self.run(env=...) 传 KEY=VALUE 列表时变量并不会真正
  传给子进程（本配方 _meson_cmd 注释行 120 已实证 PYTHONPATH 传不到、
  acf-db/0.2.1 notes 同样记载 "Conan 2 run() env= 只接受 env 文件名列表，
  不接受 KEY=VALUE"）。因此上一轮注入的 TERMINFO 从未到达 meson test →
  drawing_test 进程，newterm("xterm",...) 依旧找不到 terminfo 条目返回 NULL。
  **修复（策略变更）**：删除 _meson_env() 里的无效注入，改为在
  _run_upstream_tests() 内用进程级 os.environ["TERMINFO"]=<deps/ncurses-ohos/
  share/terminfo>（OHOS 分支），子进程必然继承；并输出诊断行
  "TERMINFO set: ... (xterm entry exists: True/False)" 供下一轮验证。
  ncurses-ohos 包内 share/terminfo/x/xterm 与 78/xterm 均存在（tar 实证，
  magic 0x011A 合法 terminfo 格式）。改动仅工作树，未提交。
