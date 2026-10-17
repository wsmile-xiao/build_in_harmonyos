# libsvg-cairo 0.1.6 适配笔记

## 编译环境
- 构建系统: autotools（上游 `configure` + `Makefile`，未重写）
- 编译日期: 2026-09-03
- 编译器: clang (OHOS 工具链)
- 状态: built
- 目标平台: OpenHarmony / HarmonyOS PC aarch64 (armv8)

## 上游信息

- 官方源码: https://cairographics.org/snapshots/libsvg-cairo-0.1.6.tar.gz
- SHA256: `a380be6a78ec2938100ce904363815a94068fca372c666b8cc82aa8711a0215c`
- 许可证: LGPL-2.0-or-later（见 `COPYING`）
- 上游 `configure.in`: `PKG_CHECK_MODULES(LIBSVG_CAIRO, libsvg >= 0.1.2 cairo >= 0.5.0)`

## 源码结构

```
libsvg-cairo-0.1.6/
├── configure / configure.in   # Autoconf 2.59（2005）
├── config.guess / config.sub  # 2005-06-17 快照，不识别 aarch64/ohos
├── libsvg-cairo.pc.in
└── src/
    ├── svg-cairo.h              # 公共 API 头
    ├── svg-cairo-internal.h
    ├── svg_cairo.c              # 渲染引擎（svg_render_engine_t 回调实现）
    ├── svg_cairo_state.c        # 渲染状态栈
    └── svg_cairo_sprintf_alloc.c
```

## API 兼容性核对（适配前逐项确认）

1. **libsvg 侧**：libsvg-cairo 只 `#include <svg.h>`（公共头），不使用
   `svgint.h` 内部头；用到的全部公共符号（`svg_create`/`svg_destroy`/
   `svg_parse_buffer`/`svg_render`/`svg_get_size`/`svg_element_render`/
   `svg_element_pattern`/`svg_length_t`/`svg_paint_t`/`svg_gradient_t`/
   `svg_pattern_t` 等）在已发布的 libsvg/0.1.4 `svg.h`（`aarch64-ohos`
   包内 `include/svg.h`）中逐一核对存在。
2. **cairo 侧**：从源码精确提取调用的公共 API（排除 `_svg_cairo_*`
   静态函数误匹配），共 60+ 个（`cairo_create`/`cairo_set_source_rgba`/
   `cairo_surface_create_similar`/`cairo_pattern_create_linear`/
   `cairo_text_extents`/`cairo_image_surface_create_for_data`…），在
   cairo/1.18.4 的 `cairo.h`（`CAIRO_VERSION 1.18.4` 包）中逐一核对
   全部仍存在。2005 代码仅用 cairo 核心绘制 API，无一被移除或改名。
3. 注意：`librsvg` 不是 `libsvg`，两者无关，本配方不涉及 librsvg。

## 上游测试分析

上游**无正式测试套件**：

- 无 `test/` 目录、无 `examples/`、无 `check_PROGRAMS`、无上游 CI；
- `make -n check` 展开后为 Automake 默认空 check 目标，无可执行用例；
- 按任务要求明确统计：
  - 单元测试 **0**
  - 集成测试 **0**
  - 其他测试 **0**

按仓库规范，新增的 `test_package` 按一个消费者集成测试套件计数，
内部断言单独统计（16 条 CHECK，详见 test_package/MANIFEST.yml）。

## 编译步骤

```bash
# Conan recipe（Autotools + PkgConfigDeps）
conan create archives/l/libsvg-cairo/0.1.6 \
    -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

recipe 要点：

- `requirements`: `libsvg/0.1.4` + `cairo/1.18.4`（均已在 ohpcd 发布，
  **不 vendor** libsvg/cairo/libpng/jpeg/zlib/libxml2 任何一个）
- `generators`: `AutotoolsDeps` + `PkgConfigDeps`；`build()` 中把
  generators 目录加入 `PKG_CONFIG_PATH`，让 2005 年 configure 的
  `PKG_CHECK_MODULES` 找到 Conan 缓存里的 `libsvg.pc` / `cairo.pc`
- OHOS 交叉构建显式传 `--host/--build=aarch64-unknown-linux-ohos`
  （configure 只认识 linux-gnu）
- `--without-x` 关闭 `AC_PATH_XTRA` 探测：本库渲染到任意 cairo
  surface（含 image surface），构建与运行均不需要 X11
- 上游构建逻辑（configure + make + make install）原样保留，仅加
  HarmonyOS 兼容补丁（见下）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `config.guess` 在 HarmonyOS 上报 "unable to guess system type"（实测复现，`uname -s = HarmonyOS`） | 2005-06-17 快照不认识 HarmonyOS/aarch64 | 补丁 0001：`config.guess` 增加 `aarch64:HarmonyOS` 分支输出 `aarch64-unknown-linux-ohos`；`config.sub` 三处增加 `aarch64` CPU 与 `linux-ohos` OS 识别（与已合入 main 的 libsvg/0.1.4 补丁同源写法） |
| 2 | configure 的 mktemp 探针目录用 `umask 077` 创建 0700 目录 | HarmonyOS MAC 策略拒绝 Conan 构建目录下的 0700 目录（同仓 a52dec/libsvg 先例） | 补丁 0002：`umask 077` → `umask 022` |
| 3 | configure 会探测 X11（`AC_PATH_XTRA`） | 2005 年 cairo 常与 X11 一起使用；headless 构建不应捡到宿主 X11 路径 | configure 参数 `--without-x`（无需改源码；渲染走 cairo image surface，与 X11 无关） |
| 4 | configure 测试程序报 "cannot run C compiled programs" / "Error relocating libcairo.so.2" | 链接行 `-rpath` 只写入测试程序自身 DT_RUNPATH，不传递给 cairo 的间接依赖（freetype/pixman/fontconfig），加载器捡到系统旧库 | `build()` 中收集所有 shared 依赖（含传递）的 libdir 注入 `LD_LIBRARY_PATH`，覆盖整条 NEEDED 链（比 libsvg/0.1.4 的纯 rpath 方案更完整） |
| 5 | 消费者编译 test_package 报 `svg.h: No such file or directory` | 已发布 libsvg/0.1.4 包的 CMakeDeps 传递 include 不含 libsvg 自身 include 目录（上游包 cpp_info 限制，无法改） | test_package 显式 `find_package(libsvg)` + `find_package(cairo)` 并链接（与仓内 cairomm/1.16.2 先例同模式）；README 使用方法同步说明 |

> 补丁共 2 个，均为 portability；未修改任何上游源码 `.c/.h`。

## 源码修改

| 补丁 | 文件 | 内容 |
|------|------|------|
| 0001-config-guess-config-sub-ohos.patch | `config.guess`, `config.sub` | 识别 `aarch64:HarmonyOS` 与 `aarch64-unknown-linux-ohos` 三元组 |
| 0002-configure-umask-022.patch | `configure` | mktemp 探针目录 umask 077→022 |

## 依赖版本

- libsvg/0.1.4（ohpcd 制品仓，OHOS aarch64，静态库 libsvg.a）
- cairo/1.18.4（ohpcd 制品仓，OHOS aarch64，**共享库** libcairo.so.2，
  传递依赖 freetype/pixman/fontconfig 亦为共享库——这正是问题 4 中
  configure 探针需要 LD_LIBRARY_PATH 的原因）
- （libsvg 自身传递依赖 libxml2/libpng/libjpeg/zlib，由 Conan 图解析，
  本配方不直接引用、不 vendor）

## 验证结果

```bash
# 1. conan create（含 test_package 消费者测试）
conan create archives/l/libsvg-cairo/0.1.6 -pr:h=...ohos-aarch64 -pr:b=...ohos-aarch64
#    → libsvg-cairo/0.1.6: Package 'xxx' created
#    → test_package: 16/16 CHECK 通过（TAP 1..16，exit 0）

# 2. HarmonyOS AArch64 实际运行
#    test_package 在目标设备运行，SVG 解析→渲染→像素断言全部通过

# 3. ELF 验证
readelf -h/-d/dyn-syms …  # aarch64 OHOS ELF、静态库无 NEEDED、NX/PIE 等

# 4. git diff --check
#    无空白错误

# 5. scoped CI（junk_check / knowledge_check / preflight / build_and_test）
#    全部通过（Success: 1 / Failed: 0 / Pass rate: 100.0%）
```

（实际输出见 task #7 验证记录。）

## 交付物

| 文件 | 说明 |
|------|------|
| include/svg-cairo.h | 公共 API 头 |
| include/svg-cairo-version.h | 版本头 |
| lib/libsvg-cairo.a | 静态库 |
| lib/pkgconfig/libsvg-cairo.pc | pkg-config 文件 |
| licenses/COPYING | LGPL-2.0 文本 |

## 注意事项

- `libsvg-cairo` 库名带连字符：Conan `cpp_info.libs = ["svg-cairo"]`
  （对应安装的 `libsvg-cairo.a`），CMake target 为
  `libsvg-cairo::libsvg-cairo`，pkg-config 名 `libsvg-cairo`。
- 本库为 library 类型，无 CLI 工具，按 R38/L0k 不添加 commands.json。
- 测试使用纯 headless cairo image surface（`CAIRO_FORMAT_ARGB32`），
  不依赖 X11 或任何显示服务器。
- SVG fixture 在测试源码中以字符串常量生成，未提交二进制 fixture。
- **宿主工具环境与目标运行环境必须严格分离（CI #42924）**：
  test_package 的 test() 曾把 conanrun（VirtualRunEnv）的
  LD_LIBRARY_PATH 用于全流程；该路径前置了目标依赖包 lib/ 目录
  （libxml2 等）。宿主工具链 lld 是 musl 动态二进制，musl 中
  LD_LIBRARY_PATH 优先于 DT_RUNPATH，lld 因此解析到目标侧
  libxml2.so.16（不含宿主工具所需 xml 符号）→ 启动即崩，报约 17 行
  `Error relocating ld.lld: xml*: symbol not found`，曾被误判为
  归档 non-PIC。修复：
  - 宿主工具（clang/lld/llvm-ar/readelf）一律经 `run_tool` 包装，
    `env LD_LIBRARY_PATH="$OHOS_TOOL_LD_LIBRARY_PATH"` 运行；
    该变量由 conanfile.py 从当前 profile 推导（E429 恢复目录 +
    VirtualBuildEnv 的 buildenv LD_LIBRARY_PATH，并剔除目标依赖
    目录），不含任何硬编码安装位置；
  - 目标依赖解析走 `-L`/绝对库路径（OHOS_DEP_LIBS →
    LIB_SEARCH_FLAGS），不进入宿主加载路径；
  - 目标程序运行时才命令局部设置 `LD_LIBRARY_PATH="$OUT:…"`，
    不再全局 export；
  - 宿主工具路径（OHOS_CC/OHOS_READELF/OHOS_AR）全部从当前
    profile 的 tools.build:compiler_executables / `-print-prog-name`
    推导，CI worker 与本地 dev 机两侧通用，无硬编码回退；
  - 链接失败按三类互斥诊断：`[host-tool-env]`（加载器错误/rc=127/
    126，附工具环境与 conanrun 环境的逐目录 diff）、`[non-PIC]`
    （lld relocation 诊断 + 涉事成员提取）、`[undefined-symbols]`
    （lld undefined symbol 清单，封顶 20）；都不匹配则原文兜底，
    不强行归类。注意 glibc 加载器也写 `symbol lookup error:
    undefined symbol:`，须先剔除加载器行再判 undefined，否则误报。

## 知识库申报（路径 B）

- **路径**：路径 B（知识库扩展）——本轮 rule12 修复中真实遇到、可跨项目
  复用、现有知识未完整覆盖的问题，已登记草稿
  `knowledge/drafts/DRAFT-E2175-static-pkg-ohos-artifact-test-link-assert.{md,kv}`。
- **主题**：静态 Conan 包的鸿蒙特有测试方法：以最终包静态归档为输入，
  先做归档直接验证（ar archive / 非空 / 成员 ELF64 LE AArch64 REL），
  再链接消费者 ELF 后对消费者产物断言 SONAME/INTERP/.code_signature/
  NEEDED 并运行真实流程；严格区分包产物、测试派生共享库、消费者
  可执行文件三类对象的断言边界；`--whole-archive` 仅用于确认归档成员
  进入派生产物（防零导出空壳），以成员满足 PIC 为前提，非 PIC 归档
  回退到可执行消费者路径。
- **查重结论**：已对七组语义完整查重——static archive member
  architecture（E236 仅 thin archive 场景）、ar archive ELF object
  （E371 仅提及）、consumer-linked artifact（E234 是 whole-archive→fPIC
  映射，无消费者产物分层断言）、whole-archive empty shared object
  （E234 不含空壳检测链路）、PIC boundary（E539 是共享目标捕获非 PIC，
  无回退形态）、static Conan package OHOS test（E541 是 zlib 静态 PIC
  策略）、package_folder artifact validation（E241 是数据清单 hash）——
  均为部分重叠，无条目覆盖完整链路，故保留草稿并申报路径 B。
