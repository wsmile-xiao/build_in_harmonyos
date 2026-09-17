# conan create 日志逐字留档 — libsbsms 2.3.0（采信轮干净轮）

> 来源：采信轮（`tools/conan_verify_round.sh` → `conan-verify`）里 G2 的 `conan create` 输出，即被审 SHA `c9c5fb32714eb222b399d53483a386a1654a9e72` 的清缓存干净轮日志。
> 原始文件（设备路径）：`archives/l/libsbsms/2.3.0/reports/conan-create.log`
> 字节数：17432 ｜ 行数：278 ｜ sha256：`c570f8bbf0b8f11dfec93b8424292476832be1f0d4d6326d9dce11b78add9004` ｜ 末尾空行：含
>
> 抽取命令（在仓库根执行；逐字还原，**不剥末尾换行**；用 `chr(96)*3` 构造围栏标记以免与本文档
> 自身的围栏混淆）：
>
> ```
> python3 -c "import pathlib;t=pathlib.Path('archives/l/libsbsms/2.3.0/reports/conan-create-log.md').read_text();f=chr(96)*3+'text\n';print(t.split(f,1)[1].rsplit(chr(10)+chr(96)*3,1)[0],end='')" > conan-create.log
> sha256sum conan-create.log   # 应等于 c570f8bbf0b8f11dfec93b8424292476832be1f0d4d6326d9dce11b78add9004
> ```
>
> 说明：这是运行期日志的**逐字转写**，原 `*.log` 不入库（`.gitcode/review-memory.md` §19）。

```text

======== Exporting recipe to the cache ========
libsbsms/2.3.0@ohpcd/stable: Exporting package recipe: /storage/Users/currentUser/ws/worktrees/libsbsms-2.3.0/archives/l/libsbsms/2.3.0/conanfile.py
libsbsms/2.3.0@ohpcd/stable: exports: File 'conandata.yml' found. Exporting it...
libsbsms/2.3.0@ohpcd/stable: Calling export_sources()
libsbsms/2.3.0@ohpcd/stable: Copied 1 '.yml' file: conandata.yml
libsbsms/2.3.0@ohpcd/stable: Copied 1 '.py' file: conanfile.py
libsbsms/2.3.0@ohpcd/stable: Exported to cache folder: /storage/Users/currentUser/.conan2/p/libsb39d6ddc12bd16/e
libsbsms/2.3.0@ohpcd/stable: Exported: libsbsms/2.3.0@ohpcd/stable#d3b4965a7ceeb8d3a740471a362facc4 (2026-09-15 16:04:55 UTC)

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
    libsbsms/2.3.0@ohpcd/stable#d3b4965a7ceeb8d3a740471a362facc4 - Cache

======== Computing necessary packages ========
Connecting to remote 'ohpcd' anonymously
libsbsms/2.3.0@ohpcd/stable: Main binary package '01d92cf349a0dd98ff915f4bd99a04430171517f' missing
libsbsms/2.3.0@ohpcd/stable: Checking 11 compatible configurations
libsbsms/2.3.0@ohpcd/stable: Compatible configurations not found in cache, checking servers
libsbsms/2.3.0@ohpcd/stable: '27f8847e00770ed889e6b1742b059fd3546550c6': compiler.cppstd=98
libsbsms/2.3.0@ohpcd/stable: '99e160260adb3c6c4a9939fa0851e92633ba044b': compiler.cppstd=gnu98
libsbsms/2.3.0@ohpcd/stable: 'fe269bd8f49f9feb35db33e326f2654cae485702': compiler.cppstd=11
libsbsms/2.3.0@ohpcd/stable: '29e8682faa417ead602bee8fadda47780ef446bc': compiler.cppstd=gnu11
libsbsms/2.3.0@ohpcd/stable: '8aaf80a4a38c646bd2485a6e112ded6e7e88a6e7': compiler.cppstd=14
libsbsms/2.3.0@ohpcd/stable: '074f586e623739ef73df0e5d2a7077b5115f0379': compiler.cppstd=gnu14
libsbsms/2.3.0@ohpcd/stable: '9ed621a4e032bcc91f1c4a0c878d828b26de5ac1': compiler.cppstd=gnu17
libsbsms/2.3.0@ohpcd/stable: 'c829397a1351f7fa8c04bcef99eb3177634a79f3': compiler.cppstd=20
libsbsms/2.3.0@ohpcd/stable: '206f143b9551e22eb462ef49e1edf5d67be7b55c': compiler.cppstd=gnu20
libsbsms/2.3.0@ohpcd/stable: '2d3266f001ed3df09e4e3cf278e4794c9b11ebce': compiler.cppstd=23
libsbsms/2.3.0@ohpcd/stable: '42db5f8712784dd68e0151c1172beedb52475a7d': compiler.cppstd=gnu23
libsbsms/2.3.0@ohpcd/stable: No compatible configuration found

A new experimental approach for binary compatibility detection is available.
    Enable it by setting the core.graph:compatibility_mode=optimized conf
    and get improved performance when querying multiple compatible binaries in remotes.

Requirements
    libsbsms/2.3.0@ohpcd/stable#d3b4965a7ceeb8d3a740471a362facc4:01d92cf349a0dd98ff915f4bd99a04430171517f - Build

======== Installing packages ========
libsbsms/2.3.0@ohpcd/stable: Calling source() in /storage/Users/currentUser/.conan2/p/libsb39d6ddc12bd16/s
libsbsms/2.3.0@ohpcd/stable: Source https://ghfast.top/https://github.com/claytonotey/libsbsms/archive/refs/tags/2.3.0.tar.gz retrieved from local download cache
libsbsms/2.3.0@ohpcd/stable: Uncompressing 2.3.0.tar.gz to .

-------- Installing package libsbsms/2.3.0@ohpcd/stable (1 of 1) --------
libsbsms/2.3.0@ohpcd/stable: Building from source
libsbsms/2.3.0@ohpcd/stable: Package libsbsms/2.3.0@ohpcd/stable:01d92cf349a0dd98ff915f4bd99a04430171517f
libsbsms/2.3.0@ohpcd/stable: settings: os=OHOS os.version=6.0 arch=armv8 compiler=clang compiler.cppstd=17 compiler.libcxx=libc++ compiler.version=15 build_type=Release
libsbsms/2.3.0@ohpcd/stable: options: shared=True
libsbsms/2.3.0@ohpcd/stable: Copying sources to build folder
libsbsms/2.3.0@ohpcd/stable: Building your package in /storage/Users/currentUser/.conan2/p/b/libsb698b9c997c655/b
libsbsms/2.3.0@ohpcd/stable: Calling generate()
libsbsms/2.3.0@ohpcd/stable: Generators folder: /storage/Users/currentUser/.conan2/p/b/libsb698b9c997c655/b/build/Release/generators
libsbsms/2.3.0@ohpcd/stable: CMakeToolchain generated: conan_toolchain.cmake
libsbsms/2.3.0@ohpcd/stable: CMakeToolchain generated: /storage/Users/currentUser/.conan2/p/b/libsb698b9c997c655/b/build/Release/generators/CMakePresets.json
libsbsms/2.3.0@ohpcd/stable: CMakeToolchain generated: /storage/Users/currentUser/.conan2/p/b/libsb698b9c997c655/b/CMakeUserPresets.json
libsbsms/2.3.0@ohpcd/stable: Generating aggregated env files
libsbsms/2.3.0@ohpcd/stable: Generated aggregated env files: ['conanbuild.sh', 'conanrun.sh']
libsbsms/2.3.0@ohpcd/stable: Calling build()
libsbsms/2.3.0@ohpcd/stable: Running CMake.configure()
libsbsms/2.3.0@ohpcd/stable: RUN: cmake -G "Unix Makefiles" -DCMAKE_TOOLCHAIN_FILE="generators/conan_toolchain.cmake" -DCMAKE_INSTALL_PREFIX="/storage/Users/currentUser/.conan2/p/b/libsb698b9c997c655/p" -DCMAKE_POLICY_VERSION_MINIMUM="3.5" -DCMAKE_SYSTEM_NAME="OHOS" -DCMAKE_SYSTEM_PROCESSOR="aarch64" -DCMAKE_INSTALL_LIBDIR="lib" -DCMAKE_POLICY_DEFAULT_CMP0091="NEW" -DCMAKE_BUILD_TYPE="Release" "/storage/Users/currentUser/.conan2/p/b/libsb698b9c997c655/b"
Problem parsing /proc/meminfo
CMake Deprecation Warning at CMakeLists.txt:1 (cmake_minimum_required):
  Compatibility with CMake < 3.10 will be removed from a future version of
  CMake.

  Update the VERSION argument <min> value.  Or, use the <min>...<max> syntax
  to tell CMake that the project requires at least <min> but has been updated
  to work with policies introduced by <max> or earlier.


-- Using Conan toolchain: /storage/Users/currentUser/.conan2/p/b/libsb698b9c997c655/b/build/Release/generators/conan_toolchain.cmake
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
-- Configuring done (1.8s)
-- Generating done (0.0s)
-- Build files have been written to: /storage/Users/currentUser/.conan2/p/b/libsb698b9c997c655/b/build/Release

libsbsms/2.3.0@ohpcd/stable: Running CMake.build()
libsbsms/2.3.0@ohpcd/stable: RUN: cmake --build "/storage/Users/currentUser/.conan2/p/b/libsb698b9c997c655/b/build/Release" -- -j20
[  8%] Building CXX object CMakeFiles/sbsms.dir/src/dBTable.cpp.o
[ 16%] Building CXX object CMakeFiles/sbsms.dir/src/buffer.cpp.o
[ 25%] Building CXX object CMakeFiles/sbsms.dir/src/fft.cpp.o
[ 33%] Building CXX object CMakeFiles/sbsms.dir/src/slide.cpp.o
[ 41%] Building CXX object CMakeFiles/sbsms.dir/src/grain.cpp.o
[ 66%] Building CXX object CMakeFiles/sbsms.dir/src/sms.cpp.o
[ 66%] Building CXX object CMakeFiles/sbsms.dir/src/resample.cpp.o
[ 75%] Building CXX object CMakeFiles/sbsms.dir/src/trackpoint.cpp.o
[ 83%] Building CXX object CMakeFiles/sbsms.dir/src/sbsms.cpp.o
[ 83%] Building CXX object CMakeFiles/sbsms.dir/src/subband.cpp.o
[ 91%] Building CXX object CMakeFiles/sbsms.dir/src/track.cpp.o
[100%] Linking CXX shared library libsbsms.so
[100%] Built target sbsms

libsbsms/2.3.0@ohpcd/stable: Package '01d92cf349a0dd98ff915f4bd99a04430171517f' built
libsbsms/2.3.0@ohpcd/stable: Build folder /storage/Users/currentUser/.conan2/p/b/libsb698b9c997c655/b/build/Release
libsbsms/2.3.0@ohpcd/stable: Generating the package
libsbsms/2.3.0@ohpcd/stable: Packaging in folder /storage/Users/currentUser/.conan2/p/b/libsb698b9c997c655/p
libsbsms/2.3.0@ohpcd/stable: Calling package()
libsbsms/2.3.0@ohpcd/stable: Running CMake.install()
libsbsms/2.3.0@ohpcd/stable: RUN: cmake --install "/storage/Users/currentUser/.conan2/p/b/libsb698b9c997c655/b/build/Release" --prefix "/storage/Users/currentUser/.conan2/p/b/libsb698b9c997c655/p"
-- Install configuration: "Release"
-- Installing: /storage/Users/currentUser/.conan2/p/b/libsb698b9c997c655/p/lib/libsbsms.so.2.3.0
-- Installing: /storage/Users/currentUser/.conan2/p/b/libsb698b9c997c655/p/lib/libsbsms.so.2
-- Installing: /storage/Users/currentUser/.conan2/p/b/libsb698b9c997c655/p/lib/libsbsms.so
-- Installing: /storage/Users/currentUser/.conan2/p/b/libsb698b9c997c655/p/include/sbsms.h
-- Installing: /storage/Users/currentUser/.conan2/p/b/libsb698b9c997c655/p/lib/pkgconfig/sbsms.pc
-- Installing: /storage/Users/currentUser/.conan2/p/b/libsb698b9c997c655/p/lib/cmake/sbsms/sbsmsTargets.cmake
-- Installing: /storage/Users/currentUser/.conan2/p/b/libsb698b9c997c655/p/lib/cmake/sbsms/sbsmsTargets-release.cmake
-- Installing: /storage/Users/currentUser/.conan2/p/b/libsb698b9c997c655/p/lib/cmake/sbsms/sbsmsConfig.cmake
-- Installing: /storage/Users/currentUser/.conan2/p/b/libsb698b9c997c655/p/lib/cmake/sbsms/sbsmsConfigVersion.cmake

libsbsms/2.3.0@ohpcd/stable: package(): Packaged 1 '.0' file: libsbsms.so.2.3.0
libsbsms/2.3.0@ohpcd/stable: package(): Packaged 1 '.2' file: libsbsms.so.2
libsbsms/2.3.0@ohpcd/stable: package(): Packaged 1 '.so' file: libsbsms.so
libsbsms/2.3.0@ohpcd/stable: package(): Packaged 1 '.pc' file: sbsms.pc
libsbsms/2.3.0@ohpcd/stable: package(): Packaged 4 '.cmake' files: sbsmsTargets.cmake, sbsmsTargets-release.cmake, sbsmsConfig.cmake, sbsmsConfigVersion.cmake
libsbsms/2.3.0@ohpcd/stable: package(): Packaged 1 '.h' file: sbsms.h
libsbsms/2.3.0@ohpcd/stable: package(): Packaged 1 '.txt' file: LICENSE.txt
libsbsms/2.3.0@ohpcd/stable: Created package revision 47efbb456bb859fd19dea130199ec664
libsbsms/2.3.0@ohpcd/stable: Package '01d92cf349a0dd98ff915f4bd99a04430171517f' created
libsbsms/2.3.0@ohpcd/stable: Full package reference: libsbsms/2.3.0@ohpcd/stable#d3b4965a7ceeb8d3a740471a362facc4:01d92cf349a0dd98ff915f4bd99a04430171517f#47efbb456bb859fd19dea130199ec664
libsbsms/2.3.0@ohpcd/stable: Package folder /storage/Users/currentUser/.conan2/p/b/libsb698b9c997c655/p

======== Launching test_package ========

======== Computing dependency graph ========
Graph root
    libsbsms/2.3.0@ohpcd/stable (test package): /storage/Users/currentUser/ws/worktrees/libsbsms-2.3.0/archives/l/libsbsms/2.3.0/test_package/conanfile.py
Requirements
    libsbsms/2.3.0@ohpcd/stable#d3b4965a7ceeb8d3a740471a362facc4 - Cache

======== Computing necessary packages ========
Requirements
    libsbsms/2.3.0@ohpcd/stable#d3b4965a7ceeb8d3a740471a362facc4:01d92cf349a0dd98ff915f4bd99a04430171517f#47efbb456bb859fd19dea130199ec664 - Cache

======== Installing packages ========
libsbsms/2.3.0@ohpcd/stable: Already installed! (1 of 1)

======== Testing the package ========
Removing previously existing 'test_package' build folder: /storage/Users/currentUser/ws/worktrees/libsbsms-2.3.0/archives/l/libsbsms/2.3.0/test_package/build/clang-15-armv8-17-release
libsbsms/2.3.0@ohpcd/stable (test package): Test package build: build/clang-15-armv8-17-release
libsbsms/2.3.0@ohpcd/stable (test package): Test package build folder: /storage/Users/currentUser/ws/worktrees/libsbsms-2.3.0/archives/l/libsbsms/2.3.0/test_package/build/clang-15-armv8-17-release
libsbsms/2.3.0@ohpcd/stable (test package): Writing generators to /storage/Users/currentUser/ws/worktrees/libsbsms-2.3.0/archives/l/libsbsms/2.3.0/test_package/build/clang-15-armv8-17-release/generators
libsbsms/2.3.0@ohpcd/stable (test package): Generator 'CMakeDeps' calling 'generate()'
libsbsms/2.3.0@ohpcd/stable (test package): CMakeDeps necessary find_package() and targets for your CMakeLists.txt
    find_package(sbsms)
    target_link_libraries(... sbsms::sbsms)
libsbsms/2.3.0@ohpcd/stable (test package): Generator 'CMakeToolchain' calling 'generate()'
libsbsms/2.3.0@ohpcd/stable (test package): CMakeToolchain generated: conan_toolchain.cmake
libsbsms/2.3.0@ohpcd/stable (test package): CMakeToolchain generated: /storage/Users/currentUser/ws/worktrees/libsbsms-2.3.0/archives/l/libsbsms/2.3.0/test_package/build/clang-15-armv8-17-release/generators/CMakePresets.json
libsbsms/2.3.0@ohpcd/stable (test package): CMakeToolchain generated: /storage/Users/currentUser/ws/worktrees/libsbsms-2.3.0/archives/l/libsbsms/2.3.0/test_package/CMakeUserPresets.json
libsbsms/2.3.0@ohpcd/stable (test package): Generator 'VirtualRunEnv' calling 'generate()'
libsbsms/2.3.0@ohpcd/stable (test package): Generating aggregated env files
libsbsms/2.3.0@ohpcd/stable (test package): Generated aggregated env files: ['conanrun.sh', 'conanbuild.sh']

======== Testing the package: Building ========
libsbsms/2.3.0@ohpcd/stable (test package): Calling build()
libsbsms/2.3.0@ohpcd/stable (test package): Running CMake.configure()
libsbsms/2.3.0@ohpcd/stable (test package): RUN: cmake -G "Unix Makefiles" -DCMAKE_TOOLCHAIN_FILE="generators/conan_toolchain.cmake" -DCMAKE_INSTALL_PREFIX="/storage/Users/currentUser/ws/worktrees/libsbsms-2.3.0/archives/l/libsbsms/2.3.0/test_package" -DCMAKE_POLICY_DEFAULT_CMP0091="NEW" -DCMAKE_BUILD_TYPE="Release" "/storage/Users/currentUser/ws/worktrees/libsbsms-2.3.0/archives/l/libsbsms/2.3.0/test_package"
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
-- Configuring done (1.1s)
-- Generating done (0.1s)
-- Build files have been written to: /storage/Users/currentUser/ws/worktrees/libsbsms-2.3.0/archives/l/libsbsms/2.3.0/test_package/build/clang-15-armv8-17-release

libsbsms/2.3.0@ohpcd/stable (test package): Running CMake.build()
libsbsms/2.3.0@ohpcd/stable (test package): RUN: cmake --build "/storage/Users/currentUser/ws/worktrees/libsbsms-2.3.0/archives/l/libsbsms/2.3.0/test_package/build/clang-15-armv8-17-release" -- -j20
[ 50%] Building CXX object CMakeFiles/test_sbsms.dir/test_sbsms.cpp.obj
[100%] Linking CXX executable test_sbsms
[100%] Built target test_sbsms


======== Testing the package: Executing test ========
libsbsms/2.3.0@ohpcd/stable (test package): Running test()
libsbsms/2.3.0@ohpcd/stable (test package): RUN: ./test_sbsms
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


```
