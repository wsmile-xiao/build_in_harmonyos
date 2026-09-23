# libemf2svg 1.8.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-15
- 编译器: clang/clang++
- 状态: built（待真机预检回填）

## 编译步骤

CMake 库-only 构建（复用仓库 ohos-aarch64 profile）：

```bash
conan create archives/l/libemf2svg/1.8.1 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

配方关键配置（conanfile.py generate 阶段注入）：
- `-DBUILD_SHARED_LIBS=ON/OFF` 跟随 shared 选项
- `-DLONLY=ON` 只构建库，不构建演示工具
- `-DUSE_SYSTEM_LIBUEMF=OFF` 使用 vendored libuemf 源码
- OHOS 下补 `-Wl,-soname,` 恢复 DT_SONAME（CMake 无 HarmonyOS 平台模块）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 演示工具 emf2svg-conv 在 OHOS 无法配置 | 上游 `include(Findargp)`，非 LONLY 时找不到 argp 直接 FATAL_ERROR；OHOS musl 无 argp.h | `-DLONLY=ON` 只构建库；库本身不依赖 argp |
| 2 | `find_package(PNG/Freetype)` 找不到包 | 本仓库 Conan 导出名为 libpng/freetype/fontconfig/libxml2，与上游期望的 PNG/Freetype/Fontconfig/LibXml2 不一致 | CMakeDeps `set_property` 桥接 file_name/target（msdfgen/leptonica 同法），Fontconfig/LibXml2/Freetype 追加全大写变量前缀（cmake_file_name 只 set 首字母大写前缀变量，leptonica OPENJPEG 同例） |
| 3 | 上游永远构建共享库 | `add_library(emf2svg ${SHARED})` 写死 SHARED，BUILD_SHARED_LIBS 被忽略 | 补丁去掉显式 SHARED 关键字，由 BUILD_SHARED_LIBS 接管 |
| 4 | 上游完整测试套件 OHOS 跑不全 | check_correctness.sh 需要 argp 构建的 conv 工具 + xmllint + valgrind，三者 OHOS 均缺 | test_upstream 直调库入口 emf2svg() 跑核心转换路径（正常/变体/截断三种情形）；全量 186 个 fixture 未跑，在 PR 补充说明如实声明 |

| 5 | 真机cmake.configure在project()处报CMAKE_C_COMPILER无法编译测试程序 | OHOS未知平台下try_compile可执行文件链接阶段失败（cfitsio/alfa同例） | 第一轮尝试：CMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY，只跳过检测链接（下一轮证实无效，已移除；E557明确禁止该绕过） |
| 6 | 同一project()失败在STATIC_LIBRARY绕过后依然复现，且日志首行即"System is unknown to cmake" | 根因假设错误：绕过只跳过链接步，但CMake对未知HarmonyOS平台根本无Platform模块（UNIX变量为空、SONAME flag缺失、fmem走ExternalProject分支），编译器检测整体不可信 | 第二策略周期改走E092路线：OHOS时CMAKE_SYSTEM_NAME=Linux + CMAKE_SYSTEM_PROCESSOR=aarch64（nanoflann/zxc/hackrf先例），主配方与test_package同步映射；移除STATIC_LIBRARY绕过 |
| 7 | E092映射后真机复检仍以同一指纹失败（-- The C/CXX compiler identification is unknown，CMakeLists.txt:18 project()，build() line 127证实新配方已生效） | E092只换平台模块，默认Unix Makefiles生成器的try_compile与构建仍经/bin/sh拉起的make规则执行，该shell层在OHOS worker上失败即报编译器未知（E346已验证模式） | 改走E346路线：OHOS时tc.generator="Ninja"（protobuf 3.17.3/caf 1.1.0先例，ninja由HMBS注入PATH），主配方与test_package同步；保留E092映射 |
| 8 | E092+Ninja后复检仍同一指纹失败（build() line 136证实新配方已生效），而HMBS平台诊断每轮均明确报readonly_tmp | 前两轮只动平台模块与生成器，从未处理诊断指出的只读/tmp：clang驱动及编译器探测的临时文件默认落/tmp，在该worker上创建即失败，表现为identification unknown；HMBS注入的TMPDIR此前仅靠环境透传，未在配方内显式固定 | 本轮改走文件系统能力路线：主配方与test_package各加_writable_tmpdir()（c-client先例：优先复用HMBS_TMPDIR/TMPDIR/TMP/TEMP并经mkstemp实测可写，回退build_folder/.tmp；libpng/xtrans先例），build()内写入os.environ后再调cmake，使try_compile/ninja/clang全链路避开只读/tmp；保留E092+Ninja |
| 9 | 前三轮（E092映射→Ninja→显式TMPDIR）全部以同一指纹失败：project()处"The C/CXX compiler identification is unknown"（/data/service/hnp/bin/clang），且ayatana-ido先例指出preflight.sh首行的/tmp只读报错是harness环境噪声、非根因 | 根因假设错误：三轮都在调CMake的环境（平台模块名、生成器、临时目录），但critnib/1.1已实证该真机上CMakeToolchain默认与Linux-override两条路线都会在compiler-ID探测失败（stock CMake 4.4.3无HarmonyOS平台模块），TMPDIR已覆盖仍红——probe本身在此worker上不可修复；继续换CMake flag组合是同根因假设的第四次重复（第三策略周期禁止） | 改走直编路线（critnib/ddate/clamav-libunrar先例，同指纹）：删除CMakeToolchain/CMakeDeps/CMake调用，主配方与test_package均用conf验证的profile clang直接编译（先跑cc smoke test暴露真实stderr）；依赖头文件/库经self.dependencies聚合直传-I/-L/-l，不再需要CMakeDeps桥接；保留TMPDIR显式固定与SONAME/soname签名等OHOS适配 |
| 10 | 直编首轮预检：smoke test已过（harmonybrew clang可用，CMake probe绕过成功），但首个源文件即报`emf2svg.c:8 fatal error: 'emf2svg.h' file not found`；同行可见一个裸相对`-I"include"`（某依赖无package_folder时相对includedirs未解析） | 新配方漏传上游`include_directories(./inc)`：公头在inc/而非源码旁，只加了src/lib与vendor目录；另 relative include 属无效输入，应按磁盘存在性过滤而非原样透传 | build()的-I首位补`source_folder/inc`（与上游./inc同义，_collect_sources已校验公头存在）；_dep_flags对incs/libdirs加os.path.isdir过滤，剔除裸相对等无效项 |
| 11 | 直编第二轮预检：编译已全部通过，package()在`binary-sign-tool sign`处Error 127：`/bin/sh: /data/service/hnp/bin/binary-sign-tool: inaccessible or not found` | 旧_sign_shared_libs只检查os.path.isfile+which：该路径在worker上存在但不可执行时检查通过，随后self.run直接抛ConanException使整个package失败；签名本应是best-effort | _sign_shared_libs改为best-effort：which优先、无which时要求isfile+X_OK，否则警告返回；两次self.run包try/except，任何失败只警告不抛错；package()入口补调_ensure_writable_tmp呼应readonly_tmp诊断 |

## 源码修改

- （第4轮，已生效）直编路线：删除全部CMake调用（E092映射/Ninja/TMPDIR绕过随之移除——三轮同指纹证实probe不可修复）；build()内用conf验证的profile clang直接编译src/lib/*.c + vendor/libuemf 4个文件（-std=c11 -fPIC -DE2S_VERSION，-I直传inc/vendor/依赖头文件），llvm-ar归档、shared时-Wl,-soname链接版本化.so并做 tolerant 代码签名；依赖-I/-L/-l经self.dependencies聚合（替代原CMakeDeps桥接）；test_package同步直编两个测试二进制并实跑。上一轮的replace_in_file补丁逻辑已无对象（不再跑CMake），同步删除。
- （历史）第1轮STATIC_LIBRARY绕过已移除（复现无效且E557禁止）；第2轮E092映射、第3轮Ninja均已随CMake一并移除。
- （复核补丁）package()的LICENSE拷贝改为存在才拷、缺失只警告：1.8.1包内有无LICENSE未经证实（此前无一轮走到package阶段），不让未知文件假设浪费一次直编预检。

## 依赖版本

- libpng/1.6.58.2
- freetype/2.14.3
- fontconfig/2.18.1.1（cairo 经验：2.18.1 的 DT_NEEDED 烤死构建机绝对路径，须用干净重建的 2.18.1.1）
- libxml2/2.15.3.1
- zlib/expat 为传递依赖（经 libpng/fontconfig 引入）

## 上游测试审计

- 总数：186 个 EMF fixture（tests/resources/emf/*.emf，GitHub 1.8.1 tag 实数）+ tests/test.c UNITTEST harness + check_correctness.sh/coverage.sh 两个 shell 套件；无 ctest 注册、无 make check 目标。
- 真机执行：test_upstream 3 例（直调 emf2svg() 入口：正常转换、变体边界转换及输出差异校验、截断输入拒绝）；test_consumer 9 断言。
- 未运行：186 个 fixture 的全量 shell 回放（缺 xmllint/valgrind/argp-conv），见 PR 正文补充说明。
- 证伪措施：输出非空 + 标签断言 + 变体输入输出差异校验，避免空文件比空文件式假通过。

## 验证结果

待 HMBS 真机预检回填（conan create 日志中的 HMBS_TEST_PACKAGE_RESULT / HMBS_UPSTREAM_TEST_RESULT）。

## 注意事项

- 本机 Windows 不运行 conan；一切编译与测试结论以 HarmonyOS aarch64 真机预检为准。
- 本轮未提交、未推送，未创建 PR。
