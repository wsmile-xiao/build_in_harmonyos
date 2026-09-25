# libstxxl 1.4.1 适配笔记

## 编译环境

- 构建系统: cmake
- 编译日期: 2026-09-19
- 编译器: clang/clang++ (HarmonyOS PC aarch64)
- 状态: built

## 编译步骤

1. 获取上游源码 `https://github.com/stxxl/stxxl/releases/download/1.4.1/stxxl-1.4.1.tar.gz`，sha256 为 `92789d60cd6eca5c37536235eefae06ad3714781ab5e7eec7794b1c10ace67ac`。
2. 上游为 CMake 项目，禁止 in-source 构建，使用 `cmake_layout` 的 out-of-source 目录。
3. `generate()` 强制 `CMAKE_SYSTEM_NAME=Linux`（E092，CMake 无 HarmonyOS 平台模块），关闭 `USE_BOOST` 与 `USE_GNU_PARALLEL`，开启 `BUILD_TESTS=ON`，关闭 `BUILD_EXAMPLES` 与 `BUILD_EXTRAS`，按 `shared` 选项切换 `BUILD_SHARED_LIBS` 与 `BUILD_STATIC_LIBS`。
4. `cmake.configure()` 后 `cmake.build()` 编译静态库 `libstxxl.a`。
5. 上游测试在 `build()` 末尾执行 `ctest --output-on-failure`，`STXXL_TMPDIR` 透传 HMBS 可写临时目录，并输出 `HMBS_UPSTREAM_TEST_RESULT` 机器证据。
6. `cmake.install()` 安装头文件、库与 cmake 配置，`LICENSE_1_0.txt` 复制到 `licenses` 目录。
7. `test_package` 编译 `test_stxxl.cpp`（vector 读写、bufwriter/bufreader、sorter 排序共 6 项检查），经 `ctest` 运行并输出 `HMBS_TEST_PACKAGE_RESULT` 机器证据。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 报未知系统 HarmonyOS | CMake 缺少 Platform/HarmonyOS 模块 | generate() 强制 CMAKE_SYSTEM_NAME=Linux，走通用 Unix 分支 |
| 2 | 上游测试需写临时大文件 | 默认 STXXL_TMPDIR 为构建目录，可能不可写或空间不足 | build() 取 TMPDIR/HMBS_TMPDIR 透传为 STXXL_TMPDIR |
| 3 | 旧版 CMake 最低要求 2.6.2，CMake 4.4 直接报错 Compatibility with CMake < 3.5 has been removed | CMake 4.x 移除了对 <3.5 的兼容模式 | generate() 设 `CMAKE_POLICY_VERSION_MINIMUM=3.5`，不改上游源码（julius/lzham 先例） |
| 4 | 真机 /tmp 只读，preflight 报 can't create temporary file /tmp/*.tmp | HMBS runner 的 /tmp 不可写 | build() 在 configure 前把 TMPDIR/TMP/TEMP/STXXL_TMPDIR 全部指向可写探测后的 TMPDIR（上游 CMake 在 configure 期读 $ENV{STXXL_TMPDIR}），_writable_tmpdir 增加可写探测、永不回退不可写目录，复用 HMBS_AUTOCONF_MKTEMP_FALLBACK/HMBS_TMPDIR/PLATFORM_CAPABILITIES 候选 |
| 5 | 真机 compiler identification is unknown（CMAKE_C/CXX_COMPILER=/data/service/hnp/bin/clang） | CMakeToolchain 烘焙的 profile 编译器路径在沙箱不可用，文件内容优先级高于缓存 | 真实 --version 探测可用编译器，generate()/build() 双阶段直改 conan_toolchain.cmake 并 FORCE 追加编译器与 WORKS/ABI 跳过标记，删除含坏路径的 CMakeCache.txt（libchdr 策略） |
| 6 | 真机 clang15 报 request/counting_ptr 虚基转换失败 cannot initialize object parameter（profile C++17 vs 上游 C++11） | 上游 1.4.1 为 C++11 时代代码，profile 强制 C++17，双 -std 冲突下新标准收紧导致 12 个编译错误 | generate() 固定 `CMAKE_CXX_STANDARD=11/REQUIRED=ON`，与上游自带 -std=c++11 一致 |
| 7 | 真机上游 ctest 22/109 通过、87 项 Subprocess aborted | 上游 lib/mng/config.cpp 默认磁盘为 `/var/tmp/stxxl`（1000MiB），真机不可写，block_manager 抛 io_error 未捕获 abort；与 STXXL_TMPDIR 无关 | build()/test 全链路生成可写 STXXL 配置：`disk=<TMPDIR>/stxxl-###.tmp,0,syscall autogrow delete nodirect`，经 STXXLCFG（最高优先级）+ build 目录 `.stxxl` 双保险透传；nodirect 规避 OHOS 文件系统 O_DIRECT 限制，size 0 按需 autogrow 免预分配 |
| 9 | 真机 compile 阶段 Signal 9（stdout/stderr 均空） | 小内存盒上模板大户在默认 -O3/-g 下峰值内存 OOM 被 SIGKILL；已核实 examples 下 stxxl_test 同属 ctest 口径（109 含示例注册用例），不得裁剪示例 | generate() 按构建类型封顶优化/调试等级：Release -O1、RelWithDebInfo -O1 -g1、MinSizeRel -Os、Debug -O0 -g1，仅降优化器/调试信息，不改库行为与测试口径 |
| 8 | STXXLCFG 生效后仍剩 4/109 失败：linuxaio 两项 SEGFAULT、test_mmap abort、test_config 失败 | test_config 的 test2() 硬编码 `/tmp/stxxl-*.tmp`（100M+200M），真机 /tmp 只读导致 block_manager 建盘失败；其余三项为绕过 STXXLCFG 的文件实现直测：tests/io 下 linuxaio_file 用内核 KAIO（io_setup/io_submit），mmap_file 用 mmap+O_DIRECT 路径，在 HongMeng 内核/受限 FS（HMBS chmod=0/hardlink=0）上不支持 | 新增补丁 `0001-test_config-writable-tmp.patch`：test2() 改读 TMPDIR/STXXL_TMPDIR 可写路径；linuxaio+mmap 保留 105/109 实数并附 gaps（ohos_feature），gaps 全覆盖时不再抛编译错误继续产包 |

## 源码修改

补丁 `patches/0001-test_config-writable-tmp.patch`（portability）：上游 tests/mng/test_config.cpp 的 test2() 硬编码 `/tmp/stxxl-*.tmp`，真机 /tmp 只读导致用例失败；改为优先读 TMPDIR/STXXL_TMPDIR/TEMP 可写路径，仅替换测试用盘路径与断言，不改库逻辑。

## 依赖版本

无外部 Conan 依赖。系统库仅需 pthread（libc 自带，package_info 声明透传）。

## 验证结果

```bash
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

上游 109 个 ctest 用例在真机完整执行，test_package 6 项检查经 ctest 运行，具体通过数以 HMBS 真机预检日志的机器证据为准。

## 注意事项

- Debug 构建产物为 `libstxxl_debug.a`，Release 为 `libstxxl.a`，package_info 已按 build_type 区分。
- 上游测试含 512MiB 排序等重型用例，真机执行时间较长，不得跳过或抽样。
- 测试输出参照文件均非空，退出码为 0 时仍需核对 ctest 通过数与发现数一致。
