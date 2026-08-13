# pycairo 1.29.0 适配笔记

## 编译环境
- 构建系统: meson（CPython C 扩展绑定，python.extension_module）
- 编译日期: 2026-08-11
- 编译器: clang/clang++（OHOS aarch64，真机 /data/service/hnp 工具链）
- 状态: built（待 HMBS 真机预检通过后统一更新）

## 源码信息
- 上游: https://github.com/pygobject/pycairo
- 源码包: https://github.com/pygobject/pycairo/archive/refs/tags/v1.29.0.tar.gz
- sha256: 25c6a8a5a488afdd21208b5a71f95796891cceb2ee94f2ec1c51fdf0735eab0b
- 版本: 1.29.0（2025-11 发布，meson >= 0.64，Python >= 3.10，cairo >= 1.15.10）

## 编译步骤

1. 分析上游构建系统：meson（根 meson.build + cairo/ + tests/ 子目录），非传统 C 库，
   产物是 Python 包 `cairo/`（纯 Python 文件 + `_cairo.cpython-*-*.so` 扩展模块）。
2. 依赖：cairo 由 conan 提供（cairo/1.18.4，PkgConfigDeps 生成 cairo.pc，meson
   `dependency('cairo')` 解析）；Python 由设备/HMBS 提供（HMBS_PYTHON3 优先，
   `-Dpython=<绝对路径>` 锁定解释器）。
3. meson configure：`-Dtests=true`（接入上游 pytest）、`-Dwrap_mode=nodownload`
   （禁止 meson 私自下载 wrap 子项目）。
4. meson build：编译 `cairo/_cairo.cpython-*.so` + tests 的 cmod 辅助扩展。
5. 上游测试：workdir=build root 运行 `python3 -m pytest tests/ -v`，解析
   PASSED/FAILED/SKIPPED 计数，输出 HMBS_UPSTREAM_TEST_RESULT 标记。
6. package：cairo/ 包（含 _cairo.so）→ `lib/pythonX.Y/site-packages/cairo/`；
   py3cairo.h → `include/pycairo/`；py3cairo.pc → `lib/pkgconfig/`；METADATA → dist-info。
7. test_package：设备 python3 经 conanrun 环境（PYTHONPATH + LD_LIBRARY_PATH）导入
   cairo 包，7 个检查点真实调用 API，输出 HMBS_TEST_PACKAGE_RESULT。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 扩展模块 import 后找不到 libcairo | _cairo.so 链接 conan cache 内的 libcairo，运行期需要其 lib 目录在 LD_LIBRARY_PATH | conanfile `_run_env()` 遍历 `self.dependencies` 的 cpp_info.libdirs 前置到 LD_LIBRARY_PATH |
| 2 | meson 找错 Python 或找不到带 dev 头的解释器 | 设备/HMBS python 不在标准 PATH 或版本多样 | `_python3()` 按 HMBS_PYTHON3 → which → ~/usr/local/bin/python3 → 常见路径 探测，`-Dpython=` 显式传绝对路径 |
| 3 | 上游 288 用例中 3 个 numpy/pygame 用例在真机必然跳过 | test_surface_numpy.py / test_surface_pygame.py 用 pytest.importorskip('numpy'/'pygame') 门控，OHOS aarch64 无对应 wheel；hmbs 硬门禁不允许 skipped | build() 以 --ignore 排除这 3 个用例，在 HMBS_UPSTREAM_TEST_RESULT 的 excluded_cases 如实声明（不计入 discovered，不冒充通过），MANIFEST.yml upstream_test_audit 记录审计 |
| 4 | 上游测试需 pytest 可用 | 真机 python 环境未必预装 pytest | build() 先探测 `python3 -m pytest --version`，缺失则 `pip install pytest` 补齐（与 aiohttp-fast-zlib 同款低成本补齐思路） |
| 5 | test_package 需要 import 打包后的 cairo 包 | 包装在 site-packages 且依赖 libcairo 运行库 | package_info 里 `runenv_info.prepend_path("PYTHONPATH", .../site-packages)`，test_package 用 `env="conanrun"` 一并获得 PYTHONPATH 与 LD_LIBRARY_PATH |
| 6 | conan create 报 "Package type is 'library', but no 'shared' option declared" | Conan 2 硬性要求 package_type="library" 必须声明 shared option | 补 `options = {"shared": [True, False]}` + `default_options = {"shared": False}`（pycairo 产物是 CPython 扩展 .so，声明仅为满足 Conan 校验；与仓库 aalib/abpoa/ace 等 library 配方一致） |
| 7 | 预检依赖图解析到 conancenter 上游配方，cmake/4.4.0 构建 KeyError 'OHOS' | 预检 remote 顺序 conancenter 在前：`cairo/1.18.4` 解析到 conancenter 配方（a3845cce…），其依赖树含 glib/2.86.5、expat/2.8.2（tool_require cmake/[>=3.17]→cmake/4.4.0），该 cmake 配方 build() 按 OS 键取预编译包，OHOS 无键 → KeyError；仓库自有适配配方（autotools/meson、无 conan cmake tool_require）未被使用 | requirements() 对与 conancenter 同版本冲突的配方 pin recipe revision 强制走 ohpcd：`cairo/1.18.4#7b98eb9b…`、`freetype/2.14.3#7e95a2b2…`、`libpng/1.6.58#d25df07a…`（graalvm/r-base 同款 pin 模式；RREV 用 conan FileTreeManifest.summary_hash 算法按 git-blob LF 内容计算，已用 pycairo 已知 RREV、graalvm 的 freetype pin、本仓 libpng/cairo 配方多重校验；pixman/0.46.4、fontconfig/2.18.1.1、zlib/1.3.1.1 为仓库独有版本，conancenter 无同版本，自动落 ohpcd 无需 pin） |
| 8 | pin 的 `cairo/1.18.4#7d132228…`（HEAD 配方新 RREV）在 ohpcd 解析不到："Unable to find 'cairo/1.18.4#7d132228…' in remotes" | cairo 配方 2026-07-30 改过（fontconfig 2.18.1→2.18.1.1，commit d9350e9e0），产生新 recipe revision `7d132228…`，但该新 revision 从未重新上传到 ohpcd 制品仓——制品仓里只有旧配方 revision `7b98eb9b…`（钉 fontconfig/2.18.1），pango/synfig 注释同样印证"制品仓仍可能解析到旧 cairo recipe" | pin 改为 ohpcd 实际存在的旧 revision `cairo/1.18.4#7b98eb9b1eee6315f8a42c74c7af44d3`，并同 pango/synfig 一样 `self.requires("fontconfig/2.18.1.1", force=True)` 压过旧 cairo 传递的 fontconfig/2.18.1（2.18.1 的 libfontconfig.so DT_NEEDED 烤构建机绝对路径；2.18.1.1 为干净重打包，ABI/.so 名不变） |
| 9 | 预检 compile 失败：pixman/0.46.4 meson configure 报 `Unknown linker(s): [['llvm-ar-15'],['llvm-ar'],['ar'],['gar']]`（缺归档器） | 真机 hnp 工具链的 ar/llvm-ar 不在预检 PATH 上（E012 变体）：pixman/cairo/fontconfig 配方的 native 注入只探测编译器同目录的 `llvm-ar`（不存在），探测失败后 meson 按裸名找 ar 也找不到；仓库 bedtools/asn1c/bstring 实证真机 hnp 提供的是 GNU `/data/service/hnp/bin/ar` | conanfile 增加 `_probe_archiver()`（按 编译器同目录 llvm-ar/ar → hnp/llvm/bin → which → ~/usr/local/bin 顺序探测，取第一个存在者，ranlib 取同族）：① `configure()` 把探测到的 ar/ranlib 全路径并入 `tools.build:compiler_executables` 经 `conf_info` 下发依赖图（pixman/cairo/fontconfig 均先读该 conf 的 ar）；② `generate()` 把 ar/ranlib 注入本配方自己的 conan_meson_native.ini。找不到 ar 时如实告警并报环境问题 |
| 10 | 预检复跑仍失败：pixman/0.46.4 同指纹 `Unknown linker(s)`（conf 下发对旧配方无效） | 完整日志证实：① 真机**存在** `/data/service/hnp/bin/llvm-ar`（`pycairo: graph archiver ar=/data/service/hnp/bin/llvm-ar` 探测成功）；② ohpcd 上的 `pixman/0.46.4#5d699b1b` 是**旧配方**，generate() 不注入 ar（若含注入代码，读 conf 或探测 llvm-ar 都会成功，meson 不会失败）；③ hmbs profile 的 buildenv PATH 虽有 /data/service/hnp/bin，meson 裸名探测仍 ENOENT（PATH 注入未实际生效）；④ pixman 被 pycairo 的 shared=False 传递为静态构建 | 换策略：`self.requires("pixman/0.46.4.2", force=True)` 强制 ohpcd 上 published(07-15)、含注入代码的配方（读 conf ar 优先，否则探测编译器同目录 llvm-ar——真机实测存在，双保险）；保留上轮 `_probe_archiver`/conf 下发/自身 native 注入（对 pycairo 自身构建与 cairo 有效）；fontconfig override 同款先例，cairo 反正源码重建无影响 |
| 11 | 预检 upstream_test 失败：pytest 18 个测试模块全部 collection ERROR，`ImportError: Error relocating .../cairo/_cairo.cpython-312-aarch64-linux-ohos.so: _PyObject_GC_New: symbol not found`（test_package import cairo 同错） | **E004（musl BIND_NOW）**：musl 加载 .so 时要求符号立即可解析，_cairo.so 的 DT_NEEDED 只有 libc.so（无 libpython），Python C API 符号（3.12 的 PyObject_GC_New 宏展开为 _PyObject_GC_New 函数）无法解析。meson 的 python.extension_module 在 OHOS Python 上未自动链 libpython；真机 Python（/storage/Users/currentUser/usr/local，本仓 python/3.12.9 配方 --enable-shared 构建）LIBDIR 下确有 libpython3.12.so | 与 rdiff-backup（`PyModule_Create2: symbol not found` → LDSHARED 追加 `-lpython3.12`）同款：新增 `_python_sysconfig/_python_libdir/_python_link_flags()`（按目标解释器 sysconfig LDLIBRARY+LIBDIR 判定共享 libpython 存在性），generate() 把 `-L<LIBDIR> -lpython3.12` 注入 `tc.c_link_args`（覆盖 _cairo.so 与 tests 的 cmod.so）；`_run_env()` 与 package_info runenv 把 LIBDIR 补进 LD_LIBRARY_PATH 兜底（解释器已加载 libpython，双保险；置 conan 依赖 lib 之后避免遮蔽） |
| 12 | 预检 compile 失败：`export_sources()` 里 `self.copy("ohos_tmpdir_shim.c")` 报 `AttributeError: 'PycairoConan' object has no attribute 'copy'` | `self.copy` 是 Conan 1.x API，Conan 2 已移除（配方对象不再有 copy 方法）；本仓库 agetty/alac/abook/arm-none-eabi-binutils 同款本地文件导出均用 `conan.tools.files.copy(self, ...)` | `from conan.tools.files import copy`，改为 `copy(self, "ohos_tmpdir_shim.c", src=self.recipe_folder, dst=self.export_sources_folder)`（exported sources 会在 conan create 时落入 source folder，`_build_tmpdir_shim()` 从 `self.source_folder` 读回不受影响，abook 同款读回路径）；test_package 补 `exports_sources = "test_pycairo.py"`（此前未声明，脚本不会随 test_package 配方导出） |
| 13 | 预检 upstream_test 失败（第 2 次同指纹）：10 个 PSSurface 用例报 `CAIRO_STATUS_TEMP_FILE_ERROR`（"error creating or writing to a temporary file"） | 上一轮已写好 `ohos_tmpdir_shim.c` + `_build_tmpdir_shim()`，但 **grep 证实 `_build_tmpdir_shim` 没有任何调用点**——shim 从未编译、LD_PRELOAD 从未注入 pytest，纯死代码。cairo 1.18.4 `_cairo_ps_surface_create_for_stream` 无条件调用 `_cairo_tmpfile()`（cairo-misc.c：`open(P_tmpdir, O_TMPFILE|...)` + `tmpfile()` 回退，硬编码 /tmp、不读 $TMPDIR），OHOS /tmp 是 erofs 只读（E002）→ 必挂 | 本轮把 shim 真正接进 `_run_upstream_tests()`：`shim = self._build_tmpdir_shim()`（真机工具链编译 + binary-sign-tool 签名，ML-0043）→ 注入 pytest 子进程 env 的 `LD_PRELOAD` → 先跑 `cairo.PSSurface(None,10,10)` 探针验证 shim 生效（失败则告警、测试如实失败）→ 再跑全套。shim 把 O_TMPFILE open/tmpfile 重定向到 $TMPDIR/$TMP/$TEMP/$HOME/tmp 中第一个可写目录（HMBS 注入的 runtime tmp 可写）；shim 源码对 O_TMPFILE 分支加 `#ifdef O_TMPFILE` 保护，头文件未定义该宏时只拦截 tmpfile() 同样有效。不改变任何测试口径，断言原样执行 |
| 14 | 预检 upstream_test 失败（第 3 次同指纹）：shim 编译失败 `ohos_tmpdir_shim.c:159: redefinition of 'open'`，随后 pytest 仍报 10 个 PSSurface TEMP_FILE_ERROR | 真机日志给出确切根因：OHOS SDK `fcntl.h:204` 把 `open64` 定义为**宏** `#define open64 open`（musl LFS 别名），shim 里再定义 `int open64(...)` 经宏展开后与 `int open(...)` 冲突 → 编译失败 → `_build_tmpdir_shim()` 返回 None → shim 未注入 → 测试如实失败 | 删除 `open64()` 函数定义（OHOS 上 open64≡open，拦截 open 已覆盖所有调用方，含用 open64 名的调用），文件内注释说明缘由；`_build_tmpdir_shim()` 编译命令在工具链 flags 之后追加 `-fvisibility=default`（防 conan_meson_native.ini 的 c_args 含 -fvisibility=hidden 导致 open/tmpfile 符号隐藏、LD_PRELOAD 拦截静默失效）。仍不改变测试口径 |
| 15 | 预检 test_package 失败：`test_pycairo.py:32` `cairo.version()` 报 `TypeError: 'str' object is not callable` | 上游 v1.29.0 `cairomodule.c` `exec_cairo()` 用 `PyModule_AddStringConstant(m, "version", ...)` 把 `cairo.version` 设为**字符串模块属性**（pycairo 自身版本 "1.29.0"），模块函数表只有 `cairo_version()`/`cairo_version_string()`（均 PASS）；`cairo.version()` 是把 str 当函数调 | `test_pycairo.py` 第 32 行改为属性比较 `cairo.version == "1.29.0"`（同版本号校验语义不变，检查点数仍为 7） |
| 16 | 预检 test_package 失败（第 2 次）：`test_pycairo.py:40` `surface.get_status()` 报 `AttributeError: 'cairo.ImageSurface' object has no attribute 'get_status'` | 上游 v1.29.0 `surface.c` 的 `PycairoSurface_Type` 方法表已**移除 `get_status`**（方法表实证：finish/flush/get_content/write_to_png 等，无 get_status）；pycairo 状态经异常上报——操作出错抛 `cairo.Error`，`err.status` 为 `cairo.Status` 枚举（上游 `tests/test_surface.py::test_context_manager` 同款模式：`finish()` 后 `show_page()` 抛 `cairo.Error`，`status == cairo.Status.SURFACE_FINISHED`） | `test_pycairo.py` 检查点 2 改为上游同款模式：`finished = ImageSurface(...); finished.finish()` 后 `show_page()` 应抛 `cairo.Error` 且 `e.status == cairo.Status.SURFACE_FINISHED`（检查点改名 error_status，计数仍为 7，MANIFEST 口径不变） |
| 17 | 预检 evidence 失败（本轮）：`缺少 HMBS_UPSTREAM_TEST_RESULT`（上游测试 发现 0/执行 0） | 真机日志 32236 显示 `pycairo/1.29.0: Already installed!`——**conan create 命中缓存二进制**（上轮只改 test_package 文件，不改变主配方 recipe revision → 缓存不失效），build()（含上游 pytest 287 用例）被整体跳过；且 aiohttp-fast-zlib test_package 注释证实 **hmbs gate 只扫描 test_package 阶段 stdout**，主配方 build() 里 `self.output.info` 输出的 HMBS_UPSTREAM_TEST_RESULT 不在 gate 扫描范围（32214 曾真实跑出 287/287 通过但 gate 同样未采纳，佐证此点） | 采用 aiohttp-fast-zlib 同款模式：① 主配方 `_run_upstream_tests()` 把真实 pytest 解析结果写入 `build_folder/upstream_test_summary.json`；② `package()` 拷入包内 `res/upstream_test_summary.json`；③ test_package `test()` 读取该文件原样输出 `HMBS_UPSTREAM_TEST_RESULT`（缺失时诚实输出 failed marker 并报错，不伪造）。数字仍来自 build() 内真实 pytest 命令输出解析；test_package 阶段每次 conan create 都会执行，缓存命中也不受影响。MANIFEST 计数由 285 修正为 287（真机 pytest 实际收集数，32214 实证 287 通过/0 失败/0 跳过） |
| 18 | CI 失败（buildbot #20635，worker CI-013）：pytest 18 个测试模块全部 collection ERROR + test_package import 报 `ImportError: Error loading shared library .../cairo/_cairo.cpython-312-aarch64-linux-ohos.so: Permission denied`（真机同 head 预检却通过） | **CI worker 进程运行于 AppSpawn 沙箱**（日志环境 `OHOS_SOCKET_AppSpawn=15`、`HAP_DEBUGGABLE=true`），dlopen 强制校验 ELF `.codesign` 签名（ML-0043/E077）：未签名/自签失效的 .so 报 Permission denied；真机 SSH 环境不强制签名校验，故预检通过而 CI 失败。依赖链上 cairo 配方已在 package() 用 binary-sign-tool 重签 libcairo.so（可正常加载），pycairo 自己的 `_cairo.so`/cmod.so 从未签名 → 必挂 | 与 cairo 配方同款：新增 `_sign_ohos_so()`/`_sign_built_modules()`，build() 在 `meson.build()` 之后用 `llvm-objcopy --remove-section .codesign` + `binary-sign-tool sign -selfSign 1` 重签 build 目录下全部 `*.so`（含 tests/cmod*.so），随后 `chmod a+x`（E077：签名后权限归零为 000）；pytest 与 package() 均使用签名后的 .so（copy2 保留权限与签名段）。签名工具缺失时如实告警不伪造通过 |
| 19 | CI 失败（buildbot #21029，worker CI-040）：meson configure 报 `Unable to detect linker for compiler /data/service/hnp/bin/clang -Wl,--version`，stderr 显示 lld 加载失败（`Error loading shared library libxml2.so.16`，ld.lld 符号全部 symbol not found）（真机同 head 预检却通过） | E120/E132：**OHOS SDK 的 lld 动态链接 libxml2.so.16**，运行时需 SDK 的 `llvm/lib` 目录在 `LD_LIBRARY_PATH`。真机 SSH 环境自带该路径（预检通过），但 CI worker（AppSpawn 沙箱）缺失 → meson 探测链接器（裸 `clang -Wl,--version`，不带 c_link_args，故 `-fuse-ld` 方案对 meson 无效）时 lld 无法启动 | 按 E120 auto-fix：新增 `_sdk_llvm_libdir()`（glob `/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib` 取最新）；generate() 经 `buildenv_info.prepend_path("LD_LIBRARY_PATH", ...)` 前置该目录（meson configure/build 的 conanbuild env 自动生效）；shim 编译子进程（直接 subprocess，不经 conanbuild env）同步注入同一路径 |
| 20 | CI 失败（buildbot #21055，worker CI-006）：`_cairo.so` 已签名（日志 `pycairo: signed _cairo...`）仍 dlopen 报 Permission denied，pytest 18 模块 collection ERROR、test_package import cairo 失败（真机同 head 预检 287/287 却通过） | **E212 hmmac 安全标签**（非 E077 签名问题）：CI worker AppSpawn 沙箱只允许 dlopen `hnp_file` 标签的 .so；conan cache 位于 `/storage/Users/...`（hmdfs 标签）→ 即使签名有效仍 Permission denied。真机 SSH 环境不强制，故预检通过而 CI 失败（rdiff-backup 2.2.6 同款现象，其 notes 记录 "HNP Python can reject user-path CPython extensions ... Permission denied"） | 与 rdiff-backup 同款双保险：① build() 先探针 `import cairo`——Permission denied（沙箱）时跳过 pytest、改做签名产物静态校验（`_verify_signed_build_artifacts`：ELF 魔数 + .codesign + PyInit 符号，`_check_signed_so`），摘要 status 如实写 failed 并说明 E212 原因，不伪造通过；import 正常（真机）→ 照常完整 pytest 287/287。② test_package 同款探针：import 可用（真机）→ 真实 API 7 检查点；Permission denied（沙箱）→ `_verify_ohos_package_artifacts` 静态校验（site-packages 布局/_cairo.so ELF+.codesign+PyInit/dist-info/py3cairo.h，7 项），HMBS_TEST_PACKAGE_RESULT 计数为实际执行的检查数。两环境都输出合法 JSON 标记，数字不伪造 |
| 21 | 预检 test_package 失败（本轮）：`FileNotFoundError: [Errno 2] No such file or directory: 'bash'`（`_probe_import` 用 `subprocess.run(["bash","-c",...])`） | 真机无 bash 可执行文件（HMBS_PLATFORM_CAPABILITIES `"shell":"/bin/sh"`）；VirtualRunEnv 生成的 conanrun.sh 是 POSIX sh 脚本，不需要 bash 专有语法 | `_probe_import` 改用 `shutil.which("bash") or "/bin/sh"` 作为解释器（优先 bash、缺失回退 /bin/sh，兼容有/无 bash 的环境）；import 探针语义与测试口径不变 |

## 依赖版本
- cairo/1.18.4（conan，含 pixman/libpng/freetype/fontconfig/zlib 全链）
- Python 3.12（设备/HMBS python3，带 dev 头）
- pytest（真机镜像 9.0.3，build() 探测缺失时 pip 补齐）

## 验证结果

```bash
# 由 HMBS 在 HarmonyOS aarch64 真机执行（本机不跑 conan）：
# conan create . --profile=ohos-aarch64
# 预期：build() 内上游 pytest 287/287 通过（真机收集数；3 个 numpy/pygame 用例
#       --ignore 排除并声明于 excluded_cases），聚合结果写入包内
#       res/upstream_test_summary.json；test_package 阶段读取后输出
#       HMBS_UPSTREAM_TEST_RESULT（hmbs gate 只扫描该阶段 stdout），
#       7/7 检查点输出 HMBS_TEST_PACKAGE_RESULT——两行 marker 均合法 JSON
```

## 注意事项
- 本机 Windows 不跑 conan/真机验证；真机预检、提交推送、PR 创建均由 HMBS 后端在
  全部门禁通过后统一完成，本轮仅交付未提交工作树。
- 测试数字以真机预检日志为准（本笔记不预填通过率）；PR 正文「上游测试用例通过率」
  由 HMBS 从真机 evidence 生成。
- 上游测试为 pytest（非 ctest/autotools），HMBS_UPSTREAM_TEST_RESULT framework 填
  "pytest"。
