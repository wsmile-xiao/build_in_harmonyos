# Enchant 2.8.2 HarmonyOS 适配说明

使用官方 release 与真实 SHA-256。必需依赖为 glib/2.84.0.1；关闭可选 provider，保留库、broker API 与两个 CLI。启用 relocatable 以运行上游测试。删除旧 gettext shim 和无条件 SIGTRAP 忽略补丁：前者未集成，后者会掩盖真实陷阱且无 OHOS 守卫。test_package 提供 7 个消费者断言、负向字典行为、CLI smoke、包结构校验；CI L1e 另做破坏性反向验证。上游测试按 Automake 2 个 TESTS 计，不把 37 个翻译单元误报为 assertion 数。

- 首轮 CI 在 configure 阶段因 config.guess 在 HarmonyOS 上无法创建探测源文件而失败；通过明确传入当前设备 triplet --build=aarch64-unknown-linux-ohos，避免调用 config.guess。经验仓未命中同指纹条目，修复来自真实日志。

- Round 2 的 config.sub 不识别 linux-ohos；仅将 build triplet 改为上游可识别且匹配设备 musl ABI 的 aarch64-unknown-linux-musl。
- Round 3 的 configure 探测程序已成功编译，但运行时找不到 Conan GLib 共享库；仅在 build 上下文为 configure/build/check 前置该依赖的 lib 目录到 LD_LIBRARY_PATH。针对新指纹查询经验仓无命中。
- Round 4 进入 GLib pkg-config 探测后失败；AutotoolsDeps 只提供编译链接 flags，没有生成上游要求的 glib-2.0/gmodule/gobject/gio .pc 搜索路径。仅扩展同一构建环境，收集直接与传递 Conan 依赖中的 lib/pkgconfig、share/pkgconfig 到 PKG_CONFIG_PATH。
- Round 5 暴露遍历传递依赖时存在仅配方上下文、package_folder 为空的节点；仅跳过无 package_folder 的节点，保留实际二进制依赖的 pkg-config 路径收集。
- Round 6 已找到 GLib .pc，但其 Requires.private 引用 libpcre2-8，而当前 GLib 包未随包提供该别名 .pc；AutotoolsDeps 已传播真实 PCRE2 链接参数，因此仅在生成环境补一个无链接 flags 的 pkg-config 元数据别名以满足依赖解析。
- Round 7 表明在缓存包目录写临时 .pc 不可靠，且 pkg-config 仍未稳定解析 GLib；改用上游明确支持的 GLIB_CFLAGS/GLIB_LIBS 覆盖，值直接来自 Conan glib cpp_info，不再写依赖包缓存。
- Round 8 configure 已完成依赖探测，但 config.status 以 umask 077 创建 conf* 目录后在 HMDFS 内执行 subs1.awk 被拒绝。仅对 OHOS 使用 configure --no-create，随后将生成的 config.status 中 umask 077 改为 022 并执行，再继续 make；不修改上游生产源文件。
- Round 9 上游测试缺 UnitTest++。使用官方 unittest-cpp v2.0.0 作为仅构建期测试夹具，SHA-256 已在设备核验；临时静态库只供 make check，不打包、不进入消费者依赖图。
- Round 10 的测试夹具 URL 无 .tar.gz 文件名，Conan get 自动按 ZIP 解压导致 BadZipFile；仅固定下载文件名并用 untargz 解压，源码与哈希不变。
- Round 11 暴露当前 Conan 2.29.1 不导出 untargz API；仅改为调用设备已有 tar 解压已校验夹具。
- Round 12 表明本 Conan get 不支持 extract=False；改用其 download API 下载并校验固定文件，再调用 tar。
- Round 15 预检确认 Conan 未定义 AR；改为从 compiler_executables 或编译器同目录解析并验证绝对 llvm-ar。同时修复预检发现的消费者 C 源物理换行与 CLI 路径字符串，均属测试工具链显式缺项。
- Round 15 main.test 因测试夹具 g_mkdir_with_parents 在 HMDFS 实际生成 2751 目录，mock provider 无法复制/发现而 256/474 失败；新增仅测试、仅 OHOS 补丁，使用 shell quote 后的系统 mkdir -p 创建可写目录。生产源码不变。

## 关于 tests/Makefile 的 sed 处理（R6 合规）

R6 禁止在 patches/ 中修改 Makefile.in 等 configure 生成产物。当前 patch 0001
仅修改源文件 tests/Makefile.am（把裸 `sed` 改为 `$(SED)`），不触及任何生成文件。

sed -> $(SED) 的替换发生在 conanfile.py 的 build() 中：configure 生成 tests/Makefile
（构建树产物，非 git 追踪的 patches/ 源码）后，用 replace_in_file 把其中的裸 `sed`
改为 `$(SED)`，使 provider 测试夹具路径替换使用 configure 探测到的 SED。这是运行时
改构建树产物，每次 build 动态执行、可复现，不违反 R6（R6 约束的是把 sed 结果固化进
patches/ 提交的源码生成物）。

此外 conanfile.py 在 apply_conandata_patches 后对齐 tests/Makefile.in 与
tests/Makefile.am 的 mtime，避免 GNU make 触发 automake 重生成规则（鸿蒙 PC 设备
未安装 automake，重生成会以 127 失败）。详见知识库草稿 E258。
