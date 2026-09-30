# lite (lite-xl) 2.1.8 适配笔记

## 上游信息

| 项 | 值 |
|----|-----|
| 软件 | Lite XL —— 用 Lua + C 编写的轻量级文本编辑器 |
| 上游仓库 | https://github.com/lite-xl/lite-xl |
| 版本 | 2.1.8（Git tag: `v2.1.8`） |
| 官网 | https://lite-xl.com/ |
| 许可证 | MIT |
| 构建系统 | meson |
| 源码 URL（R39 官方源） | https://github.com/lite-xl/lite-xl/archive/refs/tags/v2.1.8.tar.gz |
| sha256 | `fcaffb946bc60583369cb040d533a4ac18075a6d474d49a2a5ff4bf87e2e9a10`（**已实测**，见下） |

### sha256 核实（非占位符）

- 源码已解压于 `/storage/Users/currentUser/builds/lite-2.1.8.work`（及同源 `.orig`）。
- 本地 tarball `/storage/Users/currentUser/builds/lite-2.1.8.tar.gz` 的
  `sha256sum` = `fcaffb946bc60583369cb040d533a4ac18075a6d474d49a2a5ff4bf87e2e9a10`，
  与 `.orig/.tarball-sha256` 内记录一致；`.orig` 与 tarball 解压内容逐字节一致
  （diff -rq 无差异）。
- 网络可达但 GitHub 下载偶发超时；sha256 由本地官方 tarball 计算得出，
  与 conandata.yml / manifest.yaml 回填值一致。**不是占位符。**

## 本次配方修正内容（与旧配方对比）

| 项 | 旧配方（缺陷） | 修正后（本版本） | 依据 |
|----|--------------|-----------------|------|
| SDL | `requires("sdl2/2.30.10")` | `requires("sdl3/3.4.8")` | 源码 `src/meson.build:62` **硬编码** `sdl_dep = dependency('sdl3', static: true)`，**无 sdl2 回退**（已核实） |
| agg | 注释/阻塞描述为依赖，需先发布 agg | **移除**所有 agg 相关 requires/注释/补丁占位 | 源码 `subprojects/` 仅 freetype2.wrap/lua.wrap/pcre2.wrap；全树 grep 无 `dependency('agg')` 或 agg.wrap（已核实） |
| Lua | 未设 use_system_lua（默认 false → lua.wrap 需下载） | `tc.project_options["use_system_lua"] = True` | 源码 `meson_options.txt` 的 `use_system_lua`（默认 false→wrap）；wrap_mode=nodownload 下走 wrap 必失败，置 true 后走 pkg-config |
| Lua 别名 | lua.pc/lua5.4.pc | 覆盖 lua_names 全列表 `lua5.4`/`lua-5.4`/`lua` | 源码 `src/meson.build:25-29` lua_names 三个探测名，conan lua/5.4.8 .pc 名是 `lua-5.4`，别名补全 |
| pcre2 | `requires("pcre2/10.45.1")` | 保留 | 源码 `dependency('libpcre2-8', ...)`，本仓配方组件化输出 `libpcre2-8.pc`（已核实） |
| freetype | `requires("freetype/2.14.3")` | 保留 | 源码 `dependency('freetype2', ...)`，本仓配方 pkg_config_name=freetype2（已核实） |
| system_libs | dl/m/pthread | 保留 | 源码 `cc.find_library('m'|'dl')` + dlopen（已核实） |
| sha256 | 标注"待环境计算" | 已实测回填 | 见上 |

## 构建系统与产物

- Meson 项目，C 语言（上游默认 `c_std=gnu11`），本配方显式钉死 `-Dc_std=gnu11`（musl 上避免 POSIX 检测误判，dav1d 教训）。
- 产物：`bin/lite-xl`（可执行文件，GUI 应用）+ `share/lite-xl/`（运行时数据/字体/插件）。
- 应用包 → **R38**：软件级 `commands.json` 已生成（`binary: false` 未发布）。

## 依赖（W0 依赖检查）

lite-xl 2.1.8 的 meson 依赖（经 pkg-config 查找）：

| 依赖 | 本仓配方 | pkg-config 名 | 状态 |
|------|---------|--------------|------|
| SDL3（硬编码，无 sdl2 回退） | sdl3/3.4.8（conan 配方由协作者并行补全） | sdl3 | ⚠️ 归档在（archives/s/sdl3/3.4.8/，status built、G0-G4 pass、4 个 OHOS 补丁），conan 配方若未就绪需 W0 复核 |
| FreeType2 | freetype/2.14.3 ✅ | freetype2 | ✅ |
| Lua 5.4 | lua/5.4.8 ✅ | lua-5.4（+ lua5.4/lua 别名） | ✅ |
| PCRE2（8 位码元） | pcre2/10.45.1 ✅ | libpcre2-8 | ✅ |
| agg | **无**（不是依赖） | — | ✅ 已核实移除 |

> **sdl3 配方协作约定**：本配方 `requirements()` 已写为 `sdl3/3.4.8`。
> 协作者正在补全 `archives/s/sdl3/3.4.8/` 的 conanfile.py/conandata.yml（复用归档 4 个 OHOS
> 补丁：定义 `SDL_PLATFORM_OHOS` 并取消 `SDL_PLATFORM_LINUX`、禁用 `pthread_setcanceltype`、
> 禁用 `SDL_TRAY` 并排除 `SDL_Gtk_Quit`）。若该配方尚未生成/发布，conan create 前需 **W0 复核**
> （R35：`conan download sdl3/3.4.8 --only-recipe`）。

## test_package 修正（R34 实质测试）

**旧测试缺陷**：旧 `test_litexl.c` 用 `lite-xl --command "core.log(...); os.exit(0)"`。
已核实 **lite-xl 2.1.8 没有 `--command` CLI 参数**（`src/main.c` 不解析任何 CLI flag，
argv 全部进入 ARGS 表当作文件路径），且 `core.log()` 只写入内部 log_items / status view，
**不写 stdout**。旧测试要么超时（事件循环挂死）要么断言标记永远不出现 → 必然 FAIL。

**新测试方式**（`test_package/test_litexl.c`，真实启动链路）：
1. 构造临时目录 `litexl_test_user_<pid>`，写入 `init.lua`：
   ```lua
   print("LITE_XL_TEST_OK")
   os.exit(0)
   ```
2. fork/exec 被测 `lite-xl` 二进制，环境变量：
   - `LITE_USERDIR=<临时目录>`（`data/core/start.lua` 用该 env 定位用户配置目录，
     `core.load_user_directory()` 在启动时 `dofile` 该 `init.lua`）
   - `SDL_VIDEODRIVER=dummy`、`SDL_AUDIODRIVER=dummy`（无头运行）
3. 断言：退出码 0 **且** stdout 含 `LITE_XL_TEST_OK` 标记。

该路径覆盖 lite-xl 真实启动全链路：SDL 初始化 → 窗口/渲染器创建 → 内嵌 Lua VM 启动 →
core 模块加载 → 用户配置加载 → 干净退出。60s 超时防事件循环挂死；非 0 退出/标记缺失 → FAIL。
（test_package conanfile.py 通过 `LITE_XL_BIN` + `env="conanrun"` 提供二进制路径与
依赖库 LD_LIBRARY_PATH。）

## 已执行步骤

1. 读取 SKILL.md 与 references/compile-guide.md、knowledge/ARCHIVE-SPEC.md、
   templates/conanfile-meson.py.tmpl、ci/conan/profiles/ohos-aarch64。
2. 源码核实（`/storage/Users/currentUser/builds/lite-2.1.8.work`，只读）：
   - `src/meson.build:62` `sdl_dep = dependency('sdl3', static: true)` —— 硬编码 SDL3。
   - `subprojects/` 只有 freetype2.wrap / lua.wrap / pcre2.wrap；全树 grep 无 agg。
   - `meson_options.txt`：`use_system_lua`（boolean，默认 false）。
   - `src/meson.build` lua_names = {lua5.4, lua-5.4, lua}；pcre2 → libpcre2-8；
     freetype2；libm/libdl 用 cc.find_library。
3. 核对依赖配方 pkg-config 名：lua/5.4.8 → lua-5.4；freetype/2.14.3 → freetype2；
   pcre2/10.45.1 组件 → libpcre2-8。
4. 修正 conanfile.py / conandata.yml / manifest.yaml / notes.md / README.md /
   软件级 manifest / test_package（test_litexl.c + MANIFEST.yml）。
5. 计算并回填 sha256（本地官方 tarball）。

## W3 真实验证记录（2026-08-17，本机工具链 /data/service/hnp/bin）

**环境事实（纠正上轮误判）**：工具链真实存在于 `/data/service/hnp/bin`（clang 15.0.4，
target aarch64-unknown-linux-ohos；make/ninja/cmake/llvm-ar/llvm-ranlib/binary-sign-tool 齐全）。
conan 2.29.1 + profile `ohos-aarch64`（已 cp 到 `~/.conan2/profiles/`）可用；ohpcd remote 已配。

**验证命令**（实际执行，全量构建）：
```bash
cd archives/l/lite/2.1.8
export PATH=/data/service/hnp/bin:$PATH
conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
# → EXIT=0
```

**结果**：
- 主包：从源码全量编译（14 个编译目标 + 链接 `src/lite-xl`）+ meson install →
  `bin/lite-xl`（ELF arm64, ~2.8MB）+ `share/lite-xl/` 运行时数据；`.codesign` 段已写入
  （binary-sign-tool 签名，R40 深度适配检查通过）。
- test_package：`test_litexl` 真实 fork/exec `bin/lite-xl`（SDL dummy + `$LITE_USERDIR/init.lua`），
  stdout 输出 `LITE_XL_TEST_OK`，退出码 0，断言 2/2 通过。

**修复记录**：
- test_package 首次 conan create 失败：`meson setup` 报
  `Unknown linker(s): [['llvm-ar-15'], ['llvm-ar'], ['ar'], ['gar']]`
  —— test_package 的 `generate()` 只 `MesonToolchain.generate()`，未注入 ar/ranlib；
  主配方有 `_inject_meson_archiver()` 但 test_package 没有。已把同款 `_inject_meson_archiver`
  补进 test_package/conanfile.py（ar/ranlib 全路径写进 `conan_meson_native.ini`）。修复后重建通过。
- 主包构建未遇到其他错误（sdl3/freetype/lua/pcre2 pkg-config 名、lua 别名、SDL dummy 驱动均按预期命中）。

## 被环境阻塞的步骤（已全部解除）

| # | 步骤 | 状态 |
|---|------|------|
| 1 | `conan create` 编译验证（W3/G2） | ✅ **2026-08-17 真实通过**（EXIT=0，含 test_package） |
| 2 | W0 `conan download` 依赖发布验证（R35） | ✅ freetype/lua/pcre2 在 ohpcd remote 发布（download exit 0）；sdl3/3.4.8 本地缓存已有 recipe+built binary（任务确认算就绪；ohpcd 上 `conan download --only-recipe` 报 remote policy 错，属远端访问策略，非依赖缺失） |
| 3 | conan-verify 8 道门禁（G0-G4/L2/L4/L5） | 由 finish step [3/9]/[4/9] 执行（本次任务范围 = W3 conan create + W0） |
| 4 | `.ci-result.json` 写入 | 禁止手动创建；由 finish step [5/9] 写入（本次**未创建**） |
| 5 | git 提交（feat/lite-2.1.8） | 协作者模式走 PR，见「分支约定」 |

> 本任务未伪造 `.ci-result.json`；conan create 真实执行并记录日志哈希线索于上（日志
> `~/tmp/lite_conan_create3.log`）。

## 质量门禁自评（静态审计 + 真实编译验证）

| 门禁 | 本任务状态 |
|------|-----------|
| W2 结构完整性（L0a-L0e） | ✅ conanfile.py / conandata.yml / test_package(conanfile+源文件+meson.build) / MANIFEST.yml 齐全 |
| R32 settings.os | ✅ `in ("Linux", "OHOS")`（package() 签名守卫、package_info system_libs） |
| R33 无裸 shell 环境变量 | ✅ build() 走 MesonToolchain；test_package build 走 MesonToolchain；无 `${CC}` |
| R34 实质测试 | ✅ test_litexl.c 真实运行 lite-xl 二进制（LITE_USERDIR/init.lua 驱动启动链路），实测 stdout 含 LITE_XL_TEST_OK + 退出码 0 |
| R38 commands.json | ✅ 已生成（应用包，bin/lite-xl；软件级 `archives/l/lite/commands.json` 已核对） |
| R39 官方源 | ✅ github.com/lite-xl/lite-xl release tarball |
| sha256 无占位符 | ✅ 已实测（fcaffb9...9a10） |
| W3 conan create 编译验证 | ✅ **真实通过**（EXIT=0，全量源码构建 + test_package 通过），未伪造 `.ci-result.json` |
| R29 published 判定 | ✅ 标 built（verify 通过未 upload）；published 待 finish/CI release 流水线 |

## 分支约定

- 目标分支：`feat/lite-2.1.8`（当前 git 分支即 feat/lite-2.1.8）。
- 提交时遵守协作者铁律：不推 main，走 GitCode PR；不碰 SKILL/references/templates/scripts/ci/index.tsv/SUMMARY.md。

## 遗留问题

1. **sdl3/3.4.8 未发布到 ohpcd remote**：本地缓存已有 recipe+built binary（本机 conan create 可用），
   但 `conan download sdl3/3.4.8 -r=ohpcd --only-recipe` 报 `error:system acceleration policy not enabled`
   —— 远端访问策略/配方未上传。lite 的 CI release 流水线（--build=missing）前需先确保 sdl3 发布
   到 ohpcd（R36：依赖先发布再构建下游）；本地缓存算就绪（任务确认）。
2. lite-xl 数据目录查找：DATADIR 由 EXEDIR 推断为 `../share/lite-xl`（非 portable 模式）。
   test_package 已实测通过（运行期能定位到包内 share/lite-xl 并完成字体/插件加载），无需额外处理。
3. OHOS SDL dummy video/renderer：本机实测 test_package 中 lite-xl 以 SDL dummy 驱动正常完成
   SDL 初始化→窗口/渲染器→Lua VM 启动→init.lua 退出全链路（未触发平台异常），无退化需求。
