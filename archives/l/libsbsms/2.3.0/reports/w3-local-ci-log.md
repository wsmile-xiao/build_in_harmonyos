# W3 本地 CI 日志逐字留档 — libsbsms 2.3.0

> 来源：`finish` 内嵌 W3 的 `ci/conan/build_and_test.sh archives/l/libsbsms/2.3.0` 输出（同一 SHA `c9c5fb32714eb222b399d53483a386a1654a9e72`）。
> 原始文件（设备路径）：`archives/l/libsbsms/2.3.0/reports/w3-local-ci.log`
> 字节数：21216 ｜ 行数：393 ｜ sha256：`a3c246ceb70f0d77b33569fbb7c8b50d8b8e23c058b1f36978f465aa6da2183d` ｜ 末尾空行：含
>
> 抽取命令（在仓库根执行；逐字还原，**不剥末尾换行**；用 `chr(96)*3` 构造围栏标记以免与本文档
> 自身的围栏混淆）：
>
> ```
> python3 -c "import pathlib;t=pathlib.Path('archives/l/libsbsms/2.3.0/reports/w3-local-ci-log.md').read_text();f=chr(96)*3+'text\n';print(t.split(f,1)[1].rsplit(chr(10)+chr(96)*3,1)[0],end='')" > w3-local-ci.log
> sha256sum w3-local-ci.log   # 应等于 a3c246ceb70f0d77b33569fbb7c8b50d8b8e23c058b1f36978f465aa6da2183d
> ```
>
> 说明：这是运行期日志的**逐字转写**，原 `*.log` 不入库（`.gitcode/review-memory.md` §19）。

```text
$ setup.sh (RC=0)
[step] Conan environment setup...
[step] Conan version: Conan version 2.29.1
[step] Disabling conancenter (private CI, not needed)
conancenter: https://center2.conan.io [Verify SSL: True, Enabled: False]
[step] remote 已就绪: ohpcd
[step] Importing profile from /storage/Users/currentUser/ws/worktrees/libsbsms-2.3.0/ci/conan/profiles/ohos-aarch64
[step] Profile file available at: /storage/Users/currentUser/ws/worktrees/libsbsms-2.3.0/ci/conan/profiles/ohos-aarch64
[step] Conan environment ready ✅
[step]   remote: ohpcd
[step]   profile: ohos-aarch64
[step]   conan: Conan version 2.29.1


$ build_and_test.sh archives/l/libsbsms/2.3.0 (RC=0)
[step] Conan build + test pipeline (CI, no AI)
[step]   scan_root: archives
[step]   profile: ohos-aarch64
[step]   channel: (no channel — plain name/version)
[step] Validating package build timeout overrides...
[step] G0: Knowledge graph integrity check...
        [ok] G0: Knowledge graph integrity check passed (540 entries)
G0_RESULT=pass
[step] G0e: Root directory whitelist check...
        [ok] G0e: Root directory whitelist passed
[step] CI_PACKAGES received: archives/l/libsbsms/2.3.0
[step] Found 1 package(s) to build

━━━ Building: libsbsms/2.3.0 ━━━
[step] L0: Quality gate checks...
[step] L0j: Checking version collision with registry (R37)...
        [ok] version not in registry yet (first publish)
[step] L0k: Checking commands.json for CLI tools (R38)...
        [ok] library package, commands.json not required
[step] L0m: Checking directory structure (R39/L0m-4/L0m-5)...
        [ok] L0m: directory structure valid
[ok] L0: All quality gate checks passed

[step] KC: Knowledge graph quality check...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  知识库质量门禁 (knowledge_check)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  .kv 文件数: 540

[step] KC1: 草稿泄漏检测...
[OK] KC1: 草稿泄漏检测通过

[step] KC2: 模板占位符残留检测...
[OK] KC2: 模板占位符残留检测通过

[step] KC3: rec_auto_fix 格式校验...
[OK] KC3: rec_auto_fix 格式校验通过

[step] KC4: 非标准字段检测...
[OK] KC4: 非标准字段检测通过

[step] KC5: index.tsv 行数一致性...
[OK] KC5: index.tsv 一致 (540 = 540)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Errors: 0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
KC_RESULT=pass
KC_ERRORS=0
        [ok] KC: knowledge check passed

[step] JC: Junk file check...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  杂项文件拦截 (junk_check)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  检查模式: prdiff (13 个文件)

[step] JC1: 运行时状态文件检测...

[step] JC2: 二进制产物检测...

[step] JC3: 源码 tarball / 打包产物检测...

[step] JC4: 临时构建产物检测...

[step] JC5: archives 隐藏文件白名单检测...

[step] JC6: PR 单软件原子性检测...
  涉及软件数: 1（合规）

[OK] 未发现杂项文件
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Junk Files: 0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
JC_RESULT=pass
JC_ERRORS=0
        [ok] JC: no junk files detected
[step] Mirror fallback: rewriting source URLs in conandata.yml...
        [ok] Source URLs rewritten with mirror fallback
[step] Pre-download: extracting source URLs from conandata.yml...
  found 2 source URL(s)
  [try 1/1.1/3] 2.3.0.tar.gz ← https://gh-proxy.com/https://github.com/claytonotey/libsbsms/archive/refs/tags/2...
  [ok] 2.3.0.tar.gz (439KB) via mirror 1
  [try 1/2.1/3] 2.3.0.tar.gz ← https://gh-proxy.com/https://github.com/claytonotey/libsbsms/archive/refs/tags/2...
  [ok] 2.3.0.tar.gz (439KB) via mirror 1
  [done] Pre-downloaded 2 files, conandata.yml updated to file:// URLs
[step] Running conan create (output logged to /storage/Users/currentUser/ws/worktrees/libsbsms-2.3.0/.ci_logs/conan_build_libsbsms_2.3.0.log)...

======== Exporting recipe to the cache ========
libsbsms/2.3.0: Exporting package recipe: /storage/Users/currentUser/ws/worktrees/libsbsms-2.3.0/archives/l/libsbsms/2.3.0/conanfile.py
libsbsms/2.3.0: exports: File 'conandata.yml' found. Exporting it...
libsbsms/2.3.0: Calling export_sources()
libsbsms/2.3.0: Copied 1 '.yml' file: conandata.yml
libsbsms/2.3.0: Copied 1 '.py' file: conanfile.py
libsbsms/2.3.0: Exported to cache folder: /storage/Users/currentUser/.conan2/p/libsb239a8799f2968/e
libsbsms/2.3.0: Exported: libsbsms/2.3.0#37c841583069419b0771d045084697f9 (2026-09-15 16:07:37 UTC)

======== Input profiles ========
Profile host:
[settings]
arch=armv8
build_type=Release
compiler=clang
compiler.cppstd=17
compiler.libcxx=libc++
compiler.version=15
os=OHOS
os.version=6.0
[conf]
tools.build:compiler_executables={'c': '/data/service/hnp/bin/clang', 'cpp': '/data/service/hnp/bin/clang++'}
[buildenv]
CONFIG_SHELL=/data/service/hnp/bin/bash
SHELL=/data/service/hnp/bin/bash
PATH=+(path)/storage/Users/currentUser/usr/local/bin
PATH=+(path)/data/service/hnp/bin
LD_LIBRARY_PATH=+(path)/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib

Profile build:
[settings]
arch=armv8
build_type=Release
compiler=clang
compiler.cppstd=17
compiler.libcxx=libc++
compiler.version=15
os=OHOS
os.version=6.0
[conf]
tools.build:compiler_executables={'c': '/data/service/hnp/bin/clang', 'cpp': '/data/service/hnp/bin/clang++'}
[buildenv]
CONFIG_SHELL=/data/service/hnp/bin/bash
SHELL=/data/service/hnp/bin/bash
PATH=+(path)/storage/Users/currentUser/usr/local/bin
PATH=+(path)/data/service/hnp/bin
LD_LIBRARY_PATH=+(path)/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib


======== Computing dependency graph ========
Graph root
    cli
Requirements
    libsbsms/2.3.0#37c841583069419b0771d045084697f9 - Cache

======== Computing necessary packages ========
libsbsms/2.3.0: Forced build from source
Requirements
    libsbsms/2.3.0#37c841583069419b0771d045084697f9:01d92cf349a0dd98ff915f4bd99a04430171517f - Build

======== Installing packages ========
libsbsms/2.3.0: Calling source() in /storage/Users/currentUser/.conan2/p/libsb239a8799f2968/s
libsbsms/2.3.0: WARN: The requested URL(s) are not listed in backup-sources metadata for this SHA256 cache entry. This may be a mistake, or the same checksum reused for a different upstream version. Re-downloading to verify.
libsbsms/2.3.0: Sources correctly downloaded from file:///storage/Users/currentUser/ws/worktrees/libsbsms-2.3.0/.build-cache/predl_cache/c1c9a8ee_2.3.0.tar.gz
libsbsms/2.3.0: Uncompressing c1c9a8ee_2.3.0.tar.gz to .

-------- Installing package libsbsms/2.3.0 (1 of 1) --------
libsbsms/2.3.0: Building from source
libsbsms/2.3.0: Package libsbsms/2.3.0:01d92cf349a0dd98ff915f4bd99a04430171517f
libsbsms/2.3.0: settings: os=OHOS os.version=6.0 arch=armv8 compiler=clang compiler.cppstd=17 compiler.libcxx=libc++ compiler.version=15 build_type=Release
libsbsms/2.3.0: options: shared=True
libsbsms/2.3.0: Copying sources to build folder
libsbsms/2.3.0: Building your package in /storage/Users/currentUser/.conan2/p/b/libsbf2cff71db885c/b
libsbsms/2.3.0: Calling generate()
libsbsms/2.3.0: Generators folder: /storage/Users/currentUser/.conan2/p/b/libsbf2cff71db885c/b/build/Release/generators
libsbsms/2.3.0: CMakeToolchain generated: conan_toolchain.cmake
libsbsms/2.3.0: CMakeToolchain generated: /storage/Users/currentUser/.conan2/p/b/libsbf2cff71db885c/b/build/Release/generators/CMakePresets.json
libsbsms/2.3.0: CMakeToolchain generated: /storage/Users/currentUser/.conan2/p/b/libsbf2cff71db885c/b/CMakeUserPresets.json
libsbsms/2.3.0: Generating aggregated env files
libsbsms/2.3.0: Generated aggregated env files: ['conanbuild.sh', 'conanrun.sh']
libsbsms/2.3.0: Calling build()
libsbsms/2.3.0: Running CMake.configure()
libsbsms/2.3.0: RUN: cmake -G "Unix Makefiles" -DCMAKE_TOOLCHAIN_FILE="generators/conan_toolchain.cmake" -DCMAKE_INSTALL_PREFIX="/storage/Users/currentUser/.conan2/p/b/libsbf2cff71db885c/p" -DCMAKE_POLICY_VERSION_MINIMUM="3.5" -DCMAKE_SYSTEM_NAME="OHOS" -DCMAKE_SYSTEM_PROCESSOR="aarch64" -DCMAKE_INSTALL_LIBDIR="lib" -DCMAKE_POLICY_DEFAULT_CMP0091="NEW" -DCMAKE_BUILD_TYPE="Release" "/storage/Users/currentUser/.conan2/p/b/libsbf2cff71db885c/b"
Problem parsing /proc/meminfo
CMake Deprecation Warning at CMakeLists.txt:1 (cmake_minimum_required):
  Compatibility with CMake < 3.10 will be removed from a future version of
  CMake.

  Update the VERSION argument <min> value.  Or, use the <min>...<max> syntax
  to tell CMake that the project requires at least <min> but has been updated
  to work with policies introduced by <max> or earlier.


-- Using Conan toolchain: /storage/Users/currentUser/.conan2/p/b/libsbf2cff71db885c/b/build/Release/generators/conan_toolchain.cmake
-- Conan toolchain: Defining libcxx as C++ flags: -stdlib=libc++
-- Conan toolchain: C++ Standard 17 with extensions OFF
-- Conan toolchain: Setting BUILD_SHARED_LIBS = ON
-- The CXX compiler identification is Clang 15.0.4
-- Detecting CXX compiler ABI info
-- Detecting CXX compiler ABI info - done
-- Check for working CXX compiler: /data/service/hnp/bin/clang++ - skipped
-- Detecting CXX compile features
-- Detecting CXX compile features - done
-- Looking for lrint
-- Looking for lrint - found
-- Looking for lrintf
-- Looking for lrintf - found
-- Configuring done (2.8s)
-- Generating done (0.1s)
-- Build files have been written to: /storage/Users/currentUser/.conan2/p/b/libsbf2cff71db885c/b/build/Release

libsbsms/2.3.0: Running CMake.build()
libsbsms/2.3.0: RUN: cmake --build "/storage/Users/currentUser/.conan2/p/b/libsbf2cff71db885c/b/build/Release" -- -j20
make: jobserver mkfifo: /storage/Users/currentUser/ws/tmp/GMfifo53981: Operation not permitted
[  8%] Building CXX object CMakeFiles/sbsms.dir/src/fft.cpp.o
[ 33%] Building CXX object CMakeFiles/sbsms.dir/src/buffer.cpp.o
[ 41%] Building CXX object CMakeFiles/sbsms.dir/src/dBTable.cpp.o
[ 41%] Building CXX object CMakeFiles/sbsms.dir/src/grain.cpp.o
[ 41%] Building CXX object CMakeFiles/sbsms.dir/src/resample.cpp.o
[ 58%] Building CXX object CMakeFiles/sbsms.dir/src/slide.cpp.o
[ 58%] Building CXX object CMakeFiles/sbsms.dir/src/sbsms.cpp.o
[ 66%] Building CXX object CMakeFiles/sbsms.dir/src/sms.cpp.o
[ 75%] Building CXX object CMakeFiles/sbsms.dir/src/subband.cpp.o
[ 83%] Building CXX object CMakeFiles/sbsms.dir/src/track.cpp.o
[ 91%] Building CXX object CMakeFiles/sbsms.dir/src/trackpoint.cpp.o
[100%] Linking CXX shared library libsbsms.so
[100%] Built target sbsms

libsbsms/2.3.0: Package '01d92cf349a0dd98ff915f4bd99a04430171517f' built
libsbsms/2.3.0: Build folder /storage/Users/currentUser/.conan2/p/b/libsbf2cff71db885c/b/build/Release
libsbsms/2.3.0: Generating the package
libsbsms/2.3.0: Packaging in folder /storage/Users/currentUser/.conan2/p/b/libsbf2cff71db885c/p
libsbsms/2.3.0: Calling package()
libsbsms/2.3.0: Running CMake.install()
libsbsms/2.3.0: RUN: cmake --install "/storage/Users/currentUser/.conan2/p/b/libsbf2cff71db885c/b/build/Release" --prefix "/storage/Users/currentUser/.conan2/p/b/libsbf2cff71db885c/p"
-- Install configuration: "Release"
-- Installing: /storage/Users/currentUser/.conan2/p/b/libsbf2cff71db885c/p/lib/libsbsms.so.2.3.0
-- Installing: /storage/Users/currentUser/.conan2/p/b/libsbf2cff71db885c/p/lib/libsbsms.so.2
-- Installing: /storage/Users/currentUser/.conan2/p/b/libsbf2cff71db885c/p/lib/libsbsms.so
-- Installing: /storage/Users/currentUser/.conan2/p/b/libsbf2cff71db885c/p/include/sbsms.h
-- Installing: /storage/Users/currentUser/.conan2/p/b/libsbf2cff71db885c/p/lib/pkgconfig/sbsms.pc
-- Installing: /storage/Users/currentUser/.conan2/p/b/libsbf2cff71db885c/p/lib/cmake/sbsms/sbsmsTargets.cmake
-- Installing: /storage/Users/currentUser/.conan2/p/b/libsbf2cff71db885c/p/lib/cmake/sbsms/sbsmsTargets-release.cmake
-- Installing: /storage/Users/currentUser/.conan2/p/b/libsbf2cff71db885c/p/lib/cmake/sbsms/sbsmsConfig.cmake
-- Installing: /storage/Users/currentUser/.conan2/p/b/libsbf2cff71db885c/p/lib/cmake/sbsms/sbsmsConfigVersion.cmake

libsbsms/2.3.0: package(): Packaged 1 '.0' file: libsbsms.so.2.3.0
libsbsms/2.3.0: package(): Packaged 1 '.2' file: libsbsms.so.2
libsbsms/2.3.0: package(): Packaged 1 '.so' file: libsbsms.so
libsbsms/2.3.0: package(): Packaged 1 '.pc' file: sbsms.pc
libsbsms/2.3.0: package(): Packaged 4 '.cmake' files: sbsmsTargets.cmake, sbsmsTargets-release.cmake, sbsmsConfig.cmake, sbsmsConfigVersion.cmake
libsbsms/2.3.0: package(): Packaged 1 '.h' file: sbsms.h
libsbsms/2.3.0: package(): Packaged 1 '.txt' file: LICENSE.txt
libsbsms/2.3.0: Created package revision 47efbb456bb859fd19dea130199ec664
libsbsms/2.3.0: Package '01d92cf349a0dd98ff915f4bd99a04430171517f' created
libsbsms/2.3.0: Full package reference: libsbsms/2.3.0#37c841583069419b0771d045084697f9:01d92cf349a0dd98ff915f4bd99a04430171517f#47efbb456bb859fd19dea130199ec664
libsbsms/2.3.0: Package folder /storage/Users/currentUser/.conan2/p/b/libsbf2cff71db885c/p

======== Launching test_package ========

======== Computing dependency graph ========
Graph root
    libsbsms/2.3.0 (test package): /storage/Users/currentUser/ws/worktrees/libsbsms-2.3.0/archives/l/libsbsms/2.3.0/test_package/conanfile.py
Requirements
    libsbsms/2.3.0#37c841583069419b0771d045084697f9 - Cache

======== Computing necessary packages ========
Requirements
    libsbsms/2.3.0#37c841583069419b0771d045084697f9:01d92cf349a0dd98ff915f4bd99a04430171517f#47efbb456bb859fd19dea130199ec664 - Cache

======== Installing packages ========
libsbsms/2.3.0: Already installed! (1 of 1)

======== Testing the package ========
Removing previously existing 'test_package' build folder: /storage/Users/currentUser/ws/worktrees/libsbsms-2.3.0/archives/l/libsbsms/2.3.0/test_package/build/clang-15-armv8-17-release
libsbsms/2.3.0 (test package): Test package build: build/clang-15-armv8-17-release
libsbsms/2.3.0 (test package): Test package build folder: /storage/Users/currentUser/ws/worktrees/libsbsms-2.3.0/archives/l/libsbsms/2.3.0/test_package/build/clang-15-armv8-17-release
libsbsms/2.3.0 (test package): Writing generators to /storage/Users/currentUser/ws/worktrees/libsbsms-2.3.0/archives/l/libsbsms/2.3.0/test_package/build/clang-15-armv8-17-release/generators
libsbsms/2.3.0 (test package): Generator 'CMakeDeps' calling 'generate()'
libsbsms/2.3.0 (test package): CMakeDeps necessary find_package() and targets for your CMakeLists.txt
    find_package(sbsms)
    target_link_libraries(... sbsms::sbsms)
libsbsms/2.3.0 (test package): Generator 'CMakeToolchain' calling 'generate()'
libsbsms/2.3.0 (test package): CMakeToolchain generated: conan_toolchain.cmake
libsbsms/2.3.0 (test package): CMakeToolchain generated: /storage/Users/currentUser/ws/worktrees/libsbsms-2.3.0/archives/l/libsbsms/2.3.0/test_package/build/clang-15-armv8-17-release/generators/CMakePresets.json
libsbsms/2.3.0 (test package): CMakeToolchain generated: /storage/Users/currentUser/ws/worktrees/libsbsms-2.3.0/archives/l/libsbsms/2.3.0/test_package/CMakeUserPresets.json
libsbsms/2.3.0 (test package): Generator 'VirtualRunEnv' calling 'generate()'
libsbsms/2.3.0 (test package): Generating aggregated env files
libsbsms/2.3.0 (test package): Generated aggregated env files: ['conanrun.sh', 'conanbuild.sh']

======== Testing the package: Building ========
libsbsms/2.3.0 (test package): Calling build()
libsbsms/2.3.0 (test package): Running CMake.configure()
libsbsms/2.3.0 (test package): RUN: cmake -G "Unix Makefiles" -DCMAKE_TOOLCHAIN_FILE="generators/conan_toolchain.cmake" -DCMAKE_INSTALL_PREFIX="/storage/Users/currentUser/ws/worktrees/libsbsms-2.3.0/archives/l/libsbsms/2.3.0/test_package" -DCMAKE_POLICY_DEFAULT_CMP0091="NEW" -DCMAKE_BUILD_TYPE="Release" "/storage/Users/currentUser/ws/worktrees/libsbsms-2.3.0/archives/l/libsbsms/2.3.0/test_package"
Problem parsing /proc/meminfo
-- Using Conan toolchain: /storage/Users/currentUser/ws/worktrees/libsbsms-2.3.0/archives/l/libsbsms/2.3.0/test_package/build/clang-15-armv8-17-release/generators/conan_toolchain.cmake
-- Conan toolchain: Defining libcxx as C++ flags: -stdlib=libc++
-- Conan toolchain: C++ Standard 17 with extensions OFF
-- The CXX compiler identification is Clang 15.0.4
System is unknown to cmake, create:
Platform/HarmonyOS to use this system, please post your config file on discourse.cmake.org so it can be added to cmake
-- Detecting CXX compiler ABI info
System is unknown to cmake, create:
Platform/HarmonyOS to use this system, please post your config file on discourse.cmake.org so it can be added to cmake
-- Detecting CXX compiler ABI info - done
-- Check for working CXX compiler: /data/service/hnp/bin/clang++ - skipped
-- Detecting CXX compile features
-- Detecting CXX compile features - done
-- Conan: Target declared 'sbsms::sbsms'
-- Configuring done (1.4s)
-- Generating done (0.0s)
-- Build files have been written to: /storage/Users/currentUser/ws/worktrees/libsbsms-2.3.0/archives/l/libsbsms/2.3.0/test_package/build/clang-15-armv8-17-release

libsbsms/2.3.0 (test package): Running CMake.build()
libsbsms/2.3.0 (test package): RUN: cmake --build "/storage/Users/currentUser/ws/worktrees/libsbsms-2.3.0/archives/l/libsbsms/2.3.0/test_package/build/clang-15-armv8-17-release" -- -j20
make: jobserver mkfifo: /storage/Users/currentUser/ws/tmp/GMfifo55348: Operation not permitted
[ 50%] Building CXX object CMakeFiles/test_sbsms.dir/test_sbsms.cpp.obj
[100%] Linking CXX executable test_sbsms
[100%] Built target test_sbsms


======== Testing the package: Executing test ========
libsbsms/2.3.0 (test package): Running test()
libsbsms/2.3.0 (test package): RUN: ./test_sbsms
[1] shipped quality table / API values
  [ok]   SBSMSQualityStandard.bands: got=8 want=8
  [ok]   SBSMSQualityStandard.H: got=3 want=3
  [ok]   SBSMSQualityStandard.N[0]: got=512 want=512
  [ok]   SBSMSQualityStandard.N2[0]: got=512 want=512
  [ok]   SBSMSQualityStandard.res[0]: got=1 want=1
  [ok]   quality.getFrameSize(): got=384 want=384
  [ok]   quality.getMaxPresamples(): got=19584 want=19584
  [ok]   SlideIdentity.getTotalStretch(): got=1 want=1 tol=0
  [ok]   SlideIdentity.getRate(): got=1 want=1 tol=0
[2] identity stretch/pitch (440 Hz -> 440 Hz)
  identity: want=44100 produced=44160 peak=0.50414 energy=5468.46
  [ok]   SBSMS::getError() == SBSMSErrorNone
  [ok]   samplesToOutput: got=44100 want=44100
  [ok]   produced samples: got=44160 want=44160
  [ok]   output all finite
  [ok]   output non-silent
  [ok]   output peak: got=0.50414 want=0.5 tol=0.3
  [ok]   output frequency Hz: got=439.402 want=440 tol=22
[3] pitch x2 (440 Hz -> 880 Hz)
  pitch x2: want=44100 produced=44160 peak=0.50004 energy=5458.03
  [ok]   SBSMS::getError() == SBSMSErrorNone
  [ok]   samplesToOutput: got=44100 want=44100
  [ok]   produced samples: got=44160 want=44160
  [ok]   output all finite
  [ok]   output frequency Hz: got=879.803 want=880 tol=44
[4] rate x2 (double speed, pitch preserved)
  rate x2: want=22050 produced=22272 peak=0.50004 energy=2728.65
  [ok]   SBSMS::getError() == SBSMSErrorNone
  [ok]   samplesToOutput: got=22050 want=22050
  [ok]   produced samples: got=22272 want=22272
  [ok]   output all finite
  [ok]   output frequency Hz: got=439.574 want=440 tol=22
checks=26 failed=0
RESULT: PASS

[ok] libsbsms/2.3.0 — conan create passed
[step] L1: Verifying test execution from conan create log...
[ok] L1a: test_package was executed by conan create
[ok] L1b: Test execution evidence found in log
[step] L1c: No upstream make check/ctest in log (may be in test_package only)
[step] L4: Scanning patches for dangerous functions...
[step] L5: Baseline artifact check...
[ok] L5: lib/ has content (library package)
[step] L1e: Destructive negative test (R34)...
        [sabotage] lib/ moved away
        [sabotage] include/ moved away
[ok] L1e: Negative test confirmed — test genuinely depends on libsbsms
[step] L2: Smoke test (version/help check)...
[step] L2: No bin/ directory found — skipping

L0_RESULT=pass: all checks passed
L1_RESULT=pass: test_package executed
L2_RESULT=skip: no bin/ dir
L4_RESULT=pass: patches clean
L5_RESULT=pass: lib/ has content
[step] Generating ci-metadata.json...
[ok] ci-metadata.json written

━━━ Build Summary ━━━
  Total:   1
  Success: 1
  Failed:  0
  Pass rate: 100.0% (1/1)
[step] All packages built and tested successfully ✅
[step] Pre-download: conandata.yml 已还原为官方 URL

```
