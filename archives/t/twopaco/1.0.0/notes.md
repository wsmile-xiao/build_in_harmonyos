# twopaco 1.0.0 适配笔记（HarmonyOS PC · CMake 双可执行包）

## 定位
- 产 2 个命令行程序 `bin/twopaco` + `bin/graphdump`，**无库无头**。
- 上游：medvedevgroup/TwoPaCo v1.0.0（2022-09-29，TBB 依赖版本；1.1.0 起去 TBB）。
- 源码 sha256（`v1.0.0.tar.gz`，curl 实测）：`2e32a8f924d42526a5298ddf5baa78a24880934f62cc958d073a34cd9c4eaa3d`。

## 关键适配
- **唯一外部依赖 TBB**：TCLAP 已 vendored（`src/common/tclap`）。上游 CMake
  用 `TBB_INCLUDE_DIR`/`TBB_LIB_DIR` 变量接线（`link_directories` + `-ltbb
  -ltbbmalloc -ltbbmalloc_proxy -lpthread`），配方从 `tbb/2023.0.0` 的
  `cpp_info` 取绝对路径喂入（`tbb/tbb.h` 兼容头 + `oneapi/tbb/*` 新头均由
  oneTBB 2023 提供）。
- **`<cmath>` 补丁**：`src/graphconstructor/constructor.cpp` 用 `log2` 却未含
  `<cmath>`，GCC 宽松通过、clang/libc++ 报 `use of undeclared identifier`。
  见 `patches/0001-ohos-cmath-include.patch`（portability）。
- **裸 cmake + 自发现 ohos.toolchain**：os=OHOS 下不用 CMakeToolchain
 （CMAKE_SYSTEM_NAME 映射问题），沿用 tinyxml2 的自发现函数；Linux 本机
  验证允许无工具链。
- **签名**：build() 内先签再测、package() 再签（OHOS exec 要求有效签名）。

## 上游测试
- `twopaco --test` 跑 10 组随机 junction 对照（`RunTests(10, ...)`），每组
  打印 `Test # N PASSED|FAILED`（stderr）。**main 恒 return 0**，退出码不可信。
- 配方 `_save_upstream_result` 逐行正则解析，`passed+failed==10` 且 id 为
  0..9 全集才放行；空输出/行数漂移/id 缺失/FAILED 均判失败（宁缺毋假）。

## test_package
- `test_twopaco.py` 4 个真实用例：双 `--help` + 确定性 2x200bp FASTA 端到端
  建图（out.bin 非空）+ `graphdump -f seq`（非空、三列、行数>0）。
- 产物为空或桩二进制（exit 1）会被用例 3/4 直接抓获；静默跳过记失败不记跳过。

## 状态
adapting —— 待 HMBS 真机预检（conan create 全量：构建 + 上游 10/10 + test_package 4/4）。

## 2026-09-30 真机失败修复（Error relocating tbb 符号 exit 127）
- 现象：build 成功，`twopaco --test` 启动即 `Error relocating ... _ZN3tbb...: symbol not found` + `scalable_allocation_command: symbol not found`，exit 127（conanrun 下 TBB 运行时路径未覆盖）。
- 根因：配方只给了 `-L`（链接期），没给运行时路径；`conanrun` 未把 `tbb/2023.0.0` lib 目录带入执行环境，musl loader 找不到 `libtbb.so.12`/`libtbbmalloc.so`，并非 TBB 版本错配（`constructor.cpp` 需 `scalable_malloc`，即 `libtbbmalloc`，proxy 仅做 malloc 劫持非必需但保留）。
- 修复（`conanfile.py`，不改上游构建语义）：`CMAKE_EXE_LINKER_FLAGS` 追加 `-Wl,-rpath,DIR`（tbb lib + shim 双目录 baked 进 RUNPATH，installed 二进制同样受益）；`_run_upstream_tests` 显式 `LD_LIBRARY_PATH="<tbb>:$LD_LIBRARY_PATH"` 前缀双保险 + 打印 link_dirs 内容供审计。

## 2026-09-30 真机失败修复（proxy 相对 DT_NEEDED 致 Error 127）
- 现象：沿用上一轮 RPATH+LD_LIBRARY_PATH 后，直连库已就绪，但 `twopaco --test` 仍 exit 127：`Error loading shared library ../../clang_15.0_cxx17_64_release/libtbbmalloc.so: (needed by .../libtbbmalloc_proxy.so)`。上一轮“缺运行时路径”假设已证伪——缺的是可被搜索的 soname，而非路径：含 `/` 的 NEEDED 按 musl 语义走路径加载，搜索路径永远满足不了。
- 根因：`tbb/2023.0.0` 包内 `libtbbmalloc_proxy.so` 的 DT_NEEDED 为相对路径（构建期记录的 `../../clang_*/libtbbmalloc.so`），与搜索路径无关；`twopaco` 直链该 proxy 即必败。`constructor.cpp` 仅显式调用 `scalable_malloc/scalable_free/scalable_allocation_command`（`oneapi/tbb/scalable_allocator.h`，由 `libtbbmalloc` 提供），proxy 系透明 malloc 劫持，本包未用。
- 修复（换路线，不再加搜索路径）：新增 `patches/0002-ohos-drop-tbbmalloc-proxy.patch`，`graphconstructor/CMakeLists.txt` 去 `-ltbbmalloc_proxy`（`graphdump` 本就不链）；`conanfile.py` 的 `_tbb_link_shim` 同步缩为 `("tbb", "tbbmalloc")`；保留上一轮 RPATH+LD 前缀给剩余两库。功能无损：`--test` 与端到端建图均不依赖 proxy 的劫持语义。

## 2026-09-30 真机失败修复（裸 --test 被 TCLAP 必选参数拦截）
- 现象：链接修复后二进制已可启动，但 `twopaco --test --tmpdir X` 报 `PARSE ERROR: Required arguments missing: filtermemory, filtersize, filenames`，exit 1，`_save_upstream_result` 因无 Test # 行而拒绝继续。上一周期“缺运行时路径/proxy 相对 DT_NEEDED”假设已失效——本轮日志无 loader Error 127，而是 TCLAP 用法错误，属测试调用域新失败。
- 根因：`src/graphconstructor/constructor.cpp` 中 filterSize/filterMemory 均为 required=true 且 xorAdd，filenames（UnlabeledMultiArg）亦 required=true；`cmd.parse` 在进入 `if (runTests)` 分支前即校验，裸 `--test` 永远过不了 parse。上游 README 的裸 `--test` 写法在其 TCLAP 版本下不可达。
- 修复（换路线，不动链接/补丁）：`conanfile.py:_run_upstream_tests` 在 upstream-tmp 内生成 `upstream-dummy.fa`（占位 FASTA，内容不被 --test 分支使用），命令改为 `twopaco --test --tmpdir T -f 32 dummy.fa`（-f 满足 xor 必选其一）；`test_package/MANIFEST.yml` 的两个 command 同步。解析与恒等式逻辑不变，仍只认 `Test # N PASSED|FAILED` 行。
