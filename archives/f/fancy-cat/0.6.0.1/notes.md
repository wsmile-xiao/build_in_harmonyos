# fancy-cat 0.6.0 适配 notes

## 真机预检失败（2026-08-15，compile 阶段）
- 现象：`zig build --release=small` 报 `error: failed to spawn build runner .zig-cache/o/<hash>/build: AccessDenied`，
  配方自带的重试逻辑（签名缓存 ELF 后重跑）第二次仍失败，且 runner hash 从 c9eec3a... 变为 9303ca2c...。
- 直接证据：日志中 zig 缓存路径是默认相对路径 `.zig-cache/o/<hash>/build`，而非配方设定的
  `zig-cache-home`（build_folder/zig-cache-home）——说明 Conan2 `self.run(cmd, env=[...])` 的
  env 列表参数没有传给子进程（Conan2 run() 只支持 dict 或 env 名称字符串）。

## 根因
1. `build()` 中 env（XDG_CACHE_HOME / ZIG_LOCAL_CACHE_DIR / ZIG_GLOBAL_CACHE_DIR）以 list 形式
   传给 `self.run()`，Conan2 不应用该列表 → zig 缓存落在默认 `.zig-cache`。
2. 重试逻辑 `_sign_cache_executables([cache_home])` 扫描的是 `zig-cache-home`（空目录），
   实际 runner 在 `source_folder/.zig-cache/o/<hash>/build` → 什么都没签名 → build_runner
   仍为未签名 ELF，OHOS 拒其 execve（AccessDenied），第二次重试复现。
3. runner hash 每次重跑会变（zig 重新编译 build_runner），"只重试一次"不可靠。

## 解法（复用仓库已验证方案：zig/0.16.0 配方 + minizign 0.1.13）
- 不再依赖 Conan run() 的 env 列表：改用 `os.environ[...] = ...` 直接注入
  ZIG_GLOBAL_CACHE_DIR / ZIG_LOCAL_CACHE_DIR / XDG_CACHE_HOME（绝对路径，位于 build_folder），
  并设置 ZIG_OHOS_SIGN_ROOTS 覆盖 local+global 缓存与 zig-out。
- 移植 zig/0.16.0 配方的 shell 包装器：把 zig 重命名为 zig-real（签名），写
  `zig` 包装脚本 + `zig-ohos-sign-generated` 辅助脚本；包装器运行真实 zig，失败且 stderr
  匹配 AccessDenied/failed to spawn build runner 时自动扫描 ZIG_OHOS_SIGN_ROOTS 下所有
  可执行 ELF 并签名，再重试（默认最多 5 次，ZIG_OHOS_SIGN_RETRIES 可调）。
- `zig build --release=small` 全程经包装器执行；产物 fancy-cat 照旧 chmod+签名。
- test_package 与 MANIFEST（upstream_tests_exist: false + 审计）不变。

## 平台能力证据
- HMBS_PLATFORM_CAPABILITIES: hardlink=0, symlink=1, chmod=0, local_mktemp=1, install_shim=true
- 本方案只依赖签名工具（binary-sign-tool/llvm-objcopy）与可写缓存目录，不依赖 chmod 持久性。

## 真机预检失败（2026-08-16，compile 阶段：zig 包依赖下载被重置）
- 现象：`zig build --release=small` 报 3 处 `HTTP response read failure: ConnectionResetByPeer`，
  指向 build.zig.zon 的 3 个 url 依赖（vaxis/fzwatch/fastb64z，github.com 直连被重置）。
- 根因：真机无法直连 github.com（与 2026-08-15 主源码/mupdf 下载超时同源）；`zig build`
  按 build.zig.zon 的 url+hash 自动拉取依赖，绕不开配方的镜像下载逻辑。
- 解法（vendor 全部 zig 依赖 + build.zig.zon 改写为本地 .path）：
  1. conandata.yml 新增 vaxis/fzwatch/fastb64z + vaxis 的传递依赖 zigimg/uucode 共 5 个条目，
     镜像（gh-proxy.com）优先、官方兜底，sha256 本机双源（镜像 vs github 直连）逐字节一致。
  2. source() 用 conan get() 下载 5 个包到 deps/（strip_root）。
  3. 新增 _patch_zig_zon_to_local_deps()：把根 build.zig.zon 的 3 个 url+hash 条目替换为
     `.path = "deps/<name>"`；把 deps/vaxis/build.zig.zon 的 zigimg/uucode 条目替换为
     `.path = "../zigimg" / "../uucode"`。替换失败抛 ConanInvalidConfiguration 显式报错。
  4. 本机验证：zig 0.15.2（x86_64-windows）在组装好的 deps/ 目录下 `zig build` 全程零网络，
     5 个包全部从本地路径解析并进入编译（仅因本机无 mupdf 系统库而终止，真机上配方已
     下载 deps/mupdf 走静态 vendor 路径，不受影响）。
- 上游测试：fancy-cat 无测试套件，MANIFEST.yml 维持 upstream_tests_exist: false 不变。
- 关键点：zig 依赖的 hash 是包内容哈希，改 URL 不影响 hash 校验；改 .path 后无需 hash，
  内容由 conandata.yml 的 sha256 保证与官方一致。


## 真机预检失败（2026-08-16 第3次，compile 阶段：mupdf thirdparty 缺失）
- 现象：`make -j8 -C deps/mupdf ...` 报 `source/fitz/color-lcms.c:38:10: fatal error:
  'lcms2mt.h' file not found` 与 `source/fitz/encode-jpx.c:25:10: fatal error:
  'openjpeg.h' file not found`，make 退出码 2，zig build 整体失败。
- 根因：mupdf 的 thirdparty/ 是 git submodule（.gitmodules 列出 freetype/harfbuzz/
  jbig2dec/libjpeg/lcms2/mujs/openjpeg/zlib/gumbo-parser/extract/curl/freeglut/
  tesseract/leptonica/zxing-cpp/zint 共 16 个），GitHub commit archive tarball
  不含子模块内容 → thirdparty/* 目录全空 → fitz 编译缺头文件。
- 佐证：日志中 zig AccessDenied（build runner/uucode_build_tables）在 wrapper
  重试后已被解决（Build Summary 从 2/7 失败 2 项 → 3/7 仅剩 run make failure）；
  `make: jobserver mkfifo: Operation not permitted` 为非致命警告（make 降级继续）。
- 解法（vendor mupdf thirdparty）：
  1. 用 GitHub trees API 查 mupdf 固定 commit 2b0b591 的 gitlink，拿到 16 个
     submodule 各自 SHA（记录于 conandata.yml 注释）。
  2. 仅 vendor Makethird/Makelists 中无条件下必建进 libmupdf-third.a 的 10 个：
     freetype/gumbo-parser/harfbuzz/libjpeg/lcms2/mujs/zlib/jbig2dec/openjpeg/extract。
     tesseract/leptonica/zxing-cpp/zint 由 USE_TESSERACT/USE_ZXINGCPP gate 关闭，
     freeglut 由 build.zig 传 HAVE_GLUT=no 关闭，curl 由系统 curl 探测（无）关闭。
  3. conandata.yml 新增 mupdf_freetype 等 10 条目：gh-proxy.com 镜像优先、官方
     URL 兜底，sha256 为镜像下载值（本机已双源解包逐字节比对一致；libjpeg/
     openjpeg/extract 官方直连成功且内容与镜像完全一致，gzip 容器字节略有差异
     不影响校验——sha256 与镜像下载文件一致，conan 走镜像优先路径）。
  4. conanfile.py source() 循环 get() 到 deps/mupdf/thirdparty/<name>，与 mupdf
     源码树对齐。
- 平台能力证据：chmod=0/hardlink=0（zig 缓存签名重试方案不变）；本方案只增加
  10 个 source 下载，不依赖真机额外能力。
- 上游测试：fancy-cat 无测试套件，MANIFEST.yml 维持 upstream_tests_exist: false。

## 真机预检失败（2026-08-18 第3次，compile 阶段：sysroot bits/ 整体缺失，单头 shim 打地鼠）
- 现象：上一轮 bits/setjmp.h shim 生效（错误命令已含 `-I deps/ohos-shim`，setjmp.h 错误消失），
  但翻译继续下探到 `sysroot/usr/include/stdint.h:20:10: error: 'bits/alltypes.h' file not found`，
  Build Summary 4/7 仍剩 compile 失败。
- 根因：OHOS SDK sysroot（/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot）
  的 usr/include 不完整——bits/ 下多个头缺失（setjmp.h、alltypes.h、后续还会有 errno/limits 等），
  逐头 shim 不可持续（打地鼠）；make 侧 clang 编译 mupdf 不触发该链（fitz-z.c 预编译成功即旁证），
  而 zig cc 的 @cImport 翻译必经完整标准头链。
- 解法（第3次，与前两轮"预编译绕行/单头 shim"不同的策略：vendor 完整 musl 头集）：
  1. zig 0.15.2 发行包自带完整 musl libc 头（lib/libc/include/）：generic-musl/（标准头+通用
     bits，含 bits/errno.h）、aarch64-linux-musl/（架构覆盖层，含生成的 bits/alltypes.h）。
  2. build() OHOS 分支按「generic-musl → any-linux-any → aarch64-linux-musl」顺序拷贝合并到
     deps/ohos-shim（同名文件后者覆盖前者），与 zig 自身目标头解析顺序一致。
  3. build.zig 已在上轮追加 `exe.addIncludePath(.{ .cwd_relative = "deps/ohos-shim" })`
     （-I 先于 sysroot 搜索），vendor 后所有标准头含 bits/* 从完整 musl 集解析，
     OHOS 专属头仍回落 sysroot。
  4. lib/libc/include 缺失时抛 ConanInvalidConfiguration 显式报错；拷贝幂等可重入。
- 上游测试：fancy-cat 无测试套件，MANIFEST.yml 维持 upstream_tests_exist: false。

## 真机预检失败（2026-08-18 第2次，compile 阶段：PdfHandler.zig @cImport 缺 bits/setjmp.h）
- 现象：配方可加载（上一轮缩进修复生效），uucode_build_tables/build_runner 的
  AccessDenied 已被 wrapper 重试签名解决（Build Summary 4/7，仅剩 compile 失败）；
  最终失败在 `src/handlers/PdfHandler.zig:9:11: error: C import failed`，
  zig cc 翻译 mupdf 头链（fitz.h → system.h → <setjmp.h>）时命中
  `sysroot/usr/include/setjmp.h:10: error: 'bits/setjmp.h' file not found`。
- 根因：fitz-z.c 预编译（addObjectFile）只绕开了 build.zig 显式 C 源文件的 zig cc
  编译路径，PdfHandler.zig 的 `@cImport({@cInclude("fitz-z.h"); @cInclude("mupdf/fitz.h");
  @cInclude("mupdf/pdf.h")})` 仍由 zig cc 翻译头文件，必经 OHOS sysroot 的
  setjmp.h → bits/setjmp.h（该 SDK sysroot 缺失此头）；make 侧 clang 编译 mupdf
  C 文件不触发该链（此前 fitz-z.c 预编译成功即证据）。
- 解法（与上一轮"预编译绕行"不同的策略：补齐缺失系统头）：
  1. build() OHOS 分支写入 `deps/ohos-shim/bits/setjmp.h`，内容为 musl aarch64
     定义 `typedef unsigned long __jmp_buf[22];`（musl master arch/aarch64/
     bits/setjmp.h 原文）。
  2. 改写 build.zig：在 `exe.addIncludePath(... "src/mupdf-z")` 后追加
     `exe.addIncludePath(.{ .cwd_relative = "deps/ohos-shim" })`——-I 目录先于
     sysroot 搜索，angle include（<bits/setjmp.h>）也能命中 shim（日志中
     `-I ./deps/mupdf/local/include -I src/mupdf-z` 即 addIncludePath → -I →
     @cImport 生效的证据）。
  3. 两处补丁均幂等（已存在则跳过），锚点缺失抛 ConanInvalidConfiguration。
- 上游测试：fancy-cat 无测试套件，MANIFEST.yml 维持 upstream_tests_exist: false。

## 真机预检失败（2026-08-18，compile 阶段：conanfile.py 缩进错误）
- 现象：conan create 在 Exporting recipe 阶段报
  `conanfile.py line 432: IndentationError: unexpected indent`，指向
  `build_zig = os.path.join(self.source_folder, "build.zig")`，配方整体无法加载。
- 根因：OHOS 分支内 fitz-z.c 预编译 `self.run(...)` 之后的 build.zig 改写块
  （addCSourceFile → addObjectFile）被多缩进一级（16 空格而非 12 空格），意外嵌套进
  `self.run()` 的括号内，Python 语法错误。
- 解法：将 build_zig 改写块整体回退 4 空格，与 `self.run(` 同级（12 空格）；
  本机 `python -m py_compile` 与 `ast.parse` 双验证通过。
- 上游测试：fancy-cat 无测试套件，MANIFEST.yml 维持 upstream_tests_exist: false。

## 真机预检失败（2026-08-16 第4次，compile 阶段：mupdf C++ 文件编译失败）
- 现象：mupdf make 中 `CC build/release/source/fitz/archive.o` 等 C 文件编译正常，
  但 `CXX build/release/source/fitz/barcode.o` 报
  `/bin/sh: /home/runner/work/ohos-make/ohos-make/ohos-sdk/linux/native/llvm/bin/clang++:
  inaccessible or not found`，`make: *** [Makefile:168: .../barcode.o] Error 127`，
  同批 tessocr.o 同样失败；make 退出码 2 → zig build 整体失败。
- 根因：真机环境（与官方 CI 同源）的 `CXX` 被硬编码为 CI 镜像内的 SDK 路径
  `/home/runner/work/ohos-make/.../clang++`（ace 8.0.5 / highlight 4.18 同款问题），
  真机上该路径不存在；配方 build() 只显式设置了 `CC`（C 文件编译正常即证据），
  未设置 `CXX`，mupdf 的 C++ 源文件（barcode.cxx/tessocr.cxx 等）遂用坏路径编译失败。
- 佐证：本轮 AccessDenied（build runner / uucode_build_tables）在 wrapper 重试
  签名后已被解决（Build Summary 2/7 失败 2 项 → 3/7 仅剩 run make failure），
  `make: jobserver mkfifo: Operation not permitted` 仍为非致命警告。
- 解法：build() 中与 CC 同样式显式设置 `CXX`——`_find_ohos_tool("OHOS_CXX",
  "clang++", "/data/service/hnp/bin/clang++")` 找到真机 clang++ 后写入
  `os.environ["CXX"]`，经 wrapper → zig build runner → make 继承生效。
- 上游测试：fancy-cat 无测试套件，MANIFEST.yml 维持 upstream_tests_exist: false。

## CI 校验失败（2026-08-18，build #27204：L0d 门禁 stub_test_method）
- 现象：CI 报 `[fail] L0d: test() method has no self.run() call — likely a stub`，
  L0_RESULT=fail: gate failed: stub_test_method，其余 L0 项（版本碰撞/commands.json/目录结构）全过。
- 根因：test_package/conanfile.py 的 test() 用 `subprocess.run()` 执行 fancy-cat --version，
  而 ci/conan/build_and_test.sh L0d 门禁只 grep `self.run` 字符串，判定为空壳测试。
- 解法：test() 改用 Conan 的 `self.run(cmd, env="conanrun")` 真实执行被测二进制
  （self.run 默认非 0 退出即抛异常，等价原退出码校验），保留 HMBS_TEST_PACKAGE_RESULT
  标记（discovered=1/passedCount=1），删除不再使用的 subprocess 导入；同步更新
  conanfile.py/CMakeLists.txt/MANIFEST.yml 注释与 test_package_tests 描述。
- 验证：本机与门禁同款 grep（def test / self.run）均命中，py 语法检查通过。

## 真机预检失败（2026-08-18 第4次，evidence 阶段：缺少 HMBS_UPSTREAM_TEST_RESULT）
- 现象：conan create 通过（compile 全部解决），但 hmbs 判 incomplete——
  「缺少 HMBS_UPSTREAM_TEST_RESULT 上游测试证据」，上游测试发现 0/执行 0/通过 0。
- 根因：预检日志中 `fancy-cat/0.6.0: Already installed! (1 of 1)`——包已缓存，
  主配方 build() 本轮被跳过，而 HMBS_UPSTREAM_TEST_RESULT(no_tests) 标记只在
  build() 末尾输出（conanfile.py build() 内），本轮输出里根本不会出现该标记；
  test_package test() 每轮必跑，却只复发 HMBS_TEST_PACKAGE_RESULT。
- 解法（复用 git-who/1.3 已验证方案：由每轮必跑的 test_package 复发上游测试标记）：
  1. test_package/conanfile.py test() 在 HMBS_TEST_PACKAGE_RESULT 之后追加复发
     HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests","framework":"zig",
     "command":"zig build --release=small","discovered":0,"executed":0,
     "passed":0,"failed":0,"skipped":0,"reason":"..."}——上游无测试套件，
     no_tests 计数为 0（MANIFEST.yml 已有 upstream_tests_exist:false + 审计）。
  2. 主配方 build() 的标记保留（首次真实构建时仍输出，作首轮证据）；
     缓存命中时由 test_package test() 保证标记每轮必现。
  3. 同步更新 test_package/conanfile.py 头注释与 MANIFEST.yml upstream_test_audit。
- 上游测试审计（本机复查 GitHub API v0.6.0 树）：.github/workflows/test.yml 仅
  `zig build`（compile job）+ `zig fmt --check src/*.zig`（lint job），无任何测试
  执行/断言；build.zig 无 test step（只有 addExecutable/addSystemCommand/run step）；
  src/ 全树（Cache/Context/Config/handlers/modes/main）无 *_test.zig。
- 验证：本机 python -m py_compile 通过。
---

**编译结束**: 2026-08-28 11:51
**最终状态**: built
