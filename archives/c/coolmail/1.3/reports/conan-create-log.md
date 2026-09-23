# 采信轮干净构建日志（`conan-verify` 写入的 `conan create` 完整输出）

> 留档对象：`conan-create.log`（工具生成，conan-verify 写入的 conan create 完整输出）
> **权威副本即本文件正文**：下方 fenced 代码块与生成当时的原始 `.log` 逐字节相同。
> 正文 sha256 `fe170907c6b7374306e6ba498f9acd1f2149ae83973ce549792f7967d8049424`；正文 19535 字节 / 246 行。
> 生成命令：`python3 scripts/ohc-run.py conan-verify coolmail 1.3 --project-dir <worktree>`
> 原始 `.log` 由 `.gitignore` 的 `reports/` 规则忽略且**每轮重跑会被覆盖**（W3 尤其明显，其中含时间戳与每轮重建的缓存分片目录名），因此正文才是稳定基线，引用请用可搜索标记而不是行号。
> 仓库规则 `.gitcode/review-memory.md` 第 19 条把 `*.log` 列为 PR 禁入文件，故以 `.md` 留档。

```text

======== Exporting recipe to the cache ========
coolmail/1.3@ohpcd/stable: Exporting package recipe: /storage/Users/currentUser/ws/wt-coolmail-1.3/archives/c/coolmail/1.3/conanfile.py
coolmail/1.3@ohpcd/stable: exports: File 'conandata.yml' found. Exporting it...
coolmail/1.3@ohpcd/stable: Calling export_sources()
coolmail/1.3@ohpcd/stable: Copied 1 '.yml' file: conandata.yml
coolmail/1.3@ohpcd/stable: Copied 1 '.py' file: conanfile.py
coolmail/1.3@ohpcd/stable: Copied 2 '.patch' files: 0001-coolmail.c.patch, 0002-render1.c.patch
coolmail/1.3@ohpcd/stable: Exported to cache folder: /storage/Users/currentUser/.conan2/p/coolmdf1ee98e1e717/e
coolmail/1.3@ohpcd/stable: Exported: coolmail/1.3@ohpcd/stable#4f1ca68b829e3cae69f403e536a0f273 (2026-09-11 02:47:34 UTC)

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
    coolmail/1.3@ohpcd/stable#4f1ca68b829e3cae69f403e536a0f273 - Cache
    libice/1.1.2#d8a6c94803be16b407b7403cc9d3b2ea - Cache
    libsm/1.2.6#20094b163d064411916677b92556810e - Cache
    libx11/1.8.13#e3ce69008a37ca95d1f0918c47709057 - Cache
    libxau/1.0.11#e70832a1f31a85a0398300bf72179ad9 - Cache
    libxcb/1.17.0#86ecb60c68ff97abdd8075b63777e4ec - Cache
    libxdmcp/1.1.5#8aaf268abc5f64d20cb46f0ec0c6fdb7 - Cache
    libxt/1.3.1#984522669afc4e011b761123dbb7e8bd - Cache
    xcb-proto/1.17.0#f985020ceb16e7e9ea7af4f2e57652b5 - Cache
    xorgproto/2025.1#f5274e33759da898a6e8d87d7708d47c - Cache
    xtrans/1.4.0#0cac4da870508f7f9fc9b44a891b30b6 - Cache
    xtrans/1.6.0#664ea4b0b501c5f144fc094ab1a4dfc5 - Cache
Test requirements
    glib/2.84.0.1#75f29176eede55310742f73ebcf9a572 - Cache
    libffi/3.4.4#ca8b0eb4102edbca48730e504e3afbdc - Cache
    pcre2/10.45#5ecd2f9871deb549e2ae07489f2e40df - Cache
    zlib/1.3.1.1#9a23e7d51311d0440b6e4d36cf44e4d9 - Cache
WARN: risk: Packages required both with visible=True and visible=False
    xorgproto/2025.1: Required by libice/1.1.2, libsm/1.2.6

======== Computing necessary packages ========
Connecting to remote 'ohpcd' anonymously
coolmail/1.3@ohpcd/stable: Main binary package '0263707db2a25b1fb74fb3f9a0e3bc58c8c6c1a4' missing
coolmail/1.3@ohpcd/stable: Checking 11 compatible configurations
coolmail/1.3@ohpcd/stable: Compatible configurations not found in cache, checking servers
coolmail/1.3@ohpcd/stable: '4f1afae71b8c8cded224d53201ae6791d8175f3b': compiler.cppstd=98
coolmail/1.3@ohpcd/stable: 'e30afe6d70dc0a8327b6a81344bb7c77c6950371': compiler.cppstd=gnu98
coolmail/1.3@ohpcd/stable: 'e1dc76ad81f47184d61c5e7618d0d091cd8e701c': compiler.cppstd=11
coolmail/1.3@ohpcd/stable: 'ddc7c923de564884ede858334618fb251b12fdeb': compiler.cppstd=gnu11
coolmail/1.3@ohpcd/stable: '9fe73d96d7f266a28f6493bc359c9cf8906334d8': compiler.cppstd=14
coolmail/1.3@ohpcd/stable: 'b568ae042bb9a3d575231174dab8af4afa140f9c': compiler.cppstd=gnu14
coolmail/1.3@ohpcd/stable: 'a9dc182d30d0ac5a8e07417e84da9ecc7f70a968': compiler.cppstd=gnu17
coolmail/1.3@ohpcd/stable: '22d9f31751598fe5bc255b22e773388b83600dca': compiler.cppstd=20
coolmail/1.3@ohpcd/stable: '5c962920e6601f911bb612bfcdfaf052db7e2e35': compiler.cppstd=gnu20
coolmail/1.3@ohpcd/stable: '0cc7ec184050eac157c0aa52742a4cbb4fb44f55': compiler.cppstd=23
coolmail/1.3@ohpcd/stable: 'fcf6aeb83781f32905214c76901c7bb1df9598d6': compiler.cppstd=gnu23
coolmail/1.3@ohpcd/stable: No compatible configuration found

A new experimental approach for binary compatibility detection is available.
    Enable it by setting the core.graph:compatibility_mode=optimized conf
    and get improved performance when querying multiple compatible binaries in remotes.

Requirements
    coolmail/1.3@ohpcd/stable#4f1ca68b829e3cae69f403e536a0f273:0263707db2a25b1fb74fb3f9a0e3bc58c8c6c1a4 - Build
    libice/1.1.2#d8a6c94803be16b407b7403cc9d3b2ea:b661fd7d193eba49082337bd3d77c7ce66163b13#79a4ecfba208ab21747f040b61f4db2a - Cache
    libsm/1.2.6#20094b163d064411916677b92556810e:4f586cea8e74412a180e21e8ab38b4af72ae0177#3bb2a3f52339e4d8d5ce9e907d9acb04 - Cache
    libx11/1.8.13#e3ce69008a37ca95d1f0918c47709057:cae7d429fb6839b6840b7602f11bf20c76efecdf#701e81816807aea0ad862a324557f4e9 - Cache
    libxau/1.0.11#e70832a1f31a85a0398300bf72179ad9:b33b73a64003feb619a47ac2da762d7e7521ab18#2875a48c0f9c6168a810db745fe96324 - Cache
    libxcb/1.17.0#86ecb60c68ff97abdd8075b63777e4ec:1913acd6b909292031fa8d8bbe2094cc57a71423#7675f8ba8257aac6cb048e6278dbfffc - Cache
    libxdmcp/1.1.5#8aaf268abc5f64d20cb46f0ec0c6fdb7:b33b73a64003feb619a47ac2da762d7e7521ab18#b9dab63027b7d0ce0f0c04f8ceef5197 - Cache
    libxt/1.3.1#984522669afc4e011b761123dbb7e8bd:40beeeb2980b87253b8656a29c55a979c80f536a#1e1b323aa0b57a2333a211fb9c65ba9d - Cache
    xorgproto/2025.1#f5274e33759da898a6e8d87d7708d47c:283a988d63e011a731408b6abe0950de49e6171d#b7dc443b533634631c412ae235a57198 - Cache
    xtrans/1.6.0#664ea4b0b501c5f144fc094ab1a4dfc5:283a988d63e011a731408b6abe0950de49e6171d#f07ea55c2b81548d01d94db631e0ac0e - Cache
Test requirements
Skipped binaries
    xcb-proto/1.17.0, xtrans/1.4.0, glib/2.84.0.1, libffi/3.4.4, pcre2/10.45, zlib/1.3.1.1

======== Installing packages ========
xorgproto/2025.1: Already installed! (1 of 10)
libxau/1.0.11: Already installed! (2 of 10)
libxdmcp/1.1.5: Already installed! (3 of 10)
xtrans/1.6.0: Already installed! (4 of 10)
libice/1.1.2: Already installed! (5 of 10)
libxcb/1.17.0: Already installed! (6 of 10)
libsm/1.2.6: Already installed! (7 of 10)
libx11/1.8.13: Already installed! (8 of 10)
libxt/1.3.1: Already installed! (9 of 10)
coolmail/1.3@ohpcd/stable: Calling source() in /storage/Users/currentUser/.conan2/p/coolmdf1ee98e1e717/s
coolmail/1.3@ohpcd/stable: Sources correctly downloaded from https://cdn.netbsd.org/pub/pkgsrc/distfiles/coolmail-1.3.tgz
coolmail/1.3@ohpcd/stable: Uncompressing coolmail-1.3.tgz to .

-------- Installing package coolmail/1.3@ohpcd/stable (10 of 10) --------
coolmail/1.3@ohpcd/stable: Building from source
coolmail/1.3@ohpcd/stable: Package coolmail/1.3@ohpcd/stable:0263707db2a25b1fb74fb3f9a0e3bc58c8c6c1a4
coolmail/1.3@ohpcd/stable: settings: os=OHOS os.version=6.0 arch=armv8 compiler=clang compiler.cppstd=17 compiler.libcxx=libc++ compiler.version=15 build_type=Release
coolmail/1.3@ohpcd/stable: requires: libxt/1.3.Z libx11/1.8.Z libsm/1.2.Z libice/1.1.Z xorgproto/2025.1#f5274e33759da898a6e8d87d7708d47c:283a988d63e011a731408b6abe0950de49e6171d
coolmail/1.3@ohpcd/stable: Copying sources to build folder
coolmail/1.3@ohpcd/stable: Building your package in /storage/Users/currentUser/.conan2/p/b/coolm740ad9706c621/b
coolmail/1.3@ohpcd/stable: Calling generate()
coolmail/1.3@ohpcd/stable: Generators folder: /storage/Users/currentUser/.conan2/p/b/coolm740ad9706c621/b/build-release/conan
coolmail/1.3@ohpcd/stable: Generating aggregated env files
coolmail/1.3@ohpcd/stable: Generated aggregated env files: ['conanbuild.sh', 'conanrun.sh']
coolmail/1.3@ohpcd/stable: Calling build()
coolmail/1.3@ohpcd/stable: Apply patch (portability): Make the string header unconditional and replace the obsolete cuserid() call with a passwd database lookup so the 1995 sources build with a C99+ compiler against musl libc.
coolmail/1.3@ohpcd/stable: Apply patch (portability): Add the missing string header for the strcmp() call in rend_init().
coolmail/1.3@ohpcd/stable: RUN: make -j1 CC="/data/service/hnp/bin/clang" CFLAGS="-O2" INCLUDES="-I/storage/Users/currentUser/.conan2/p/libxt9f52773f49d71/p/include -I/storage/Users/currentUser/.conan2/p/libx1c96c2c60af230/p/include -I/storage/Users/currentUser/.conan2/p/libxc29481f84b64ed/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/libsmb2a1d8b212ef1/p/include -I/storage/Users/currentUser/.conan2/p/libicb7ea26df82991/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include" LIB_DIRS="-L/storage/Users/currentUser/.conan2/p/libxt9f52773f49d71/p/lib -L/storage/Users/currentUser/.conan2/p/libx1c96c2c60af230/p/lib -L/storage/Users/currentUser/.conan2/p/libxc29481f84b64ed/p/lib -L/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/lib -L/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/lib -L/storage/Users/currentUser/.conan2/p/libsmb2a1d8b212ef1/p/lib -L/storage/Users/currentUser/.conan2/p/libicb7ea26df82991/p/lib" LIBS="-L/storage/Users/currentUser/.conan2/p/libxt9f52773f49d71/p/lib -L/storage/Users/currentUser/.conan2/p/libx1c96c2c60af230/p/lib -L/storage/Users/currentUser/.conan2/p/libxc29481f84b64ed/p/lib -L/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/lib -L/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/lib -L/storage/Users/currentUser/.conan2/p/libsmb2a1d8b212ef1/p/lib -L/storage/Users/currentUser/.conan2/p/libicb7ea26df82991/p/lib -lXt -lX11 -lm" AUDIO= AUDIO_MODULE=
/data/service/hnp/bin/clang -O2  -I/storage/Users/currentUser/.conan2/p/libxt9f52773f49d71/p/include -I/storage/Users/currentUser/.conan2/p/libx1c96c2c60af230/p/include -I/storage/Users/currentUser/.conan2/p/libxc29481f84b64ed/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/libsmb2a1d8b212ef1/p/include -I/storage/Users/currentUser/.conan2/p/libicb7ea26df82991/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include coolmail.c -c
coolmail.c:486:14: warning: using the result of an assignment as a condition without parentheses [-Wparentheses]
   if (child = fork())
       ~~~~~~^~~~~~~~
coolmail.c:486:14: note: place parentheses around the assignment to silence this warning
   if (child = fork())
             ^
       (             )
coolmail.c:486:14: note: use '==' to turn this assignment into an equality comparison
   if (child = fork())
             ^
             ==
1 warning generated.
/data/service/hnp/bin/clang -O2  -I/storage/Users/currentUser/.conan2/p/libxt9f52773f49d71/p/include -I/storage/Users/currentUser/.conan2/p/libx1c96c2c60af230/p/include -I/storage/Users/currentUser/.conan2/p/libxc29481f84b64ed/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/libsmb2a1d8b212ef1/p/include -I/storage/Users/currentUser/.conan2/p/libicb7ea26df82991/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include system/X11/display_list.c -c
/data/service/hnp/bin/clang -O2  -I/storage/Users/currentUser/.conan2/p/libxt9f52773f49d71/p/include -I/storage/Users/currentUser/.conan2/p/libx1c96c2c60af230/p/include -I/storage/Users/currentUser/.conan2/p/libxc29481f84b64ed/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/libsmb2a1d8b212ef1/p/include -I/storage/Users/currentUser/.conan2/p/libicb7ea26df82991/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include render1.c -c
/data/service/hnp/bin/clang -O2  -I/storage/Users/currentUser/.conan2/p/libxt9f52773f49d71/p/include -I/storage/Users/currentUser/.conan2/p/libx1c96c2c60af230/p/include -I/storage/Users/currentUser/.conan2/p/libxc29481f84b64ed/p/include -I/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/include -I/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/include -I/storage/Users/currentUser/.conan2/p/libsmb2a1d8b212ef1/p/include -I/storage/Users/currentUser/.conan2/p/libicb7ea26df82991/p/include -I/storage/Users/currentUser/.conan2/p/xorgp20459ba402fe7/p/include system/X11/colors.c -c
/data/service/hnp/bin/clang coolmail.o display_list.o render1.o  colors.o \
                -L/storage/Users/currentUser/.conan2/p/libxt9f52773f49d71/p/lib -L/storage/Users/currentUser/.conan2/p/libx1c96c2c60af230/p/lib -L/storage/Users/currentUser/.conan2/p/libxc29481f84b64ed/p/lib -L/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/lib -L/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/lib -L/storage/Users/currentUser/.conan2/p/libsmb2a1d8b212ef1/p/lib -L/storage/Users/currentUser/.conan2/p/libicb7ea26df82991/p/lib -lXt -lX11 -lm -o coolmail 
# Done.

coolmail/1.3@ohpcd/stable: Package '0263707db2a25b1fb74fb3f9a0e3bc58c8c6c1a4' built
coolmail/1.3@ohpcd/stable: Build folder /storage/Users/currentUser/.conan2/p/b/coolm740ad9706c621/b/build-release
coolmail/1.3@ohpcd/stable: Generating the package
coolmail/1.3@ohpcd/stable: Packaging in folder /storage/Users/currentUser/.conan2/p/b/coolm740ad9706c621/p
coolmail/1.3@ohpcd/stable: Calling package()
coolmail/1.3@ohpcd/stable: package(): Packaged 3 files: coolmail, COPYRIGHT, Coolmail
coolmail/1.3@ohpcd/stable: package(): Packaged 1 '.1' file: coolmail.1
coolmail/1.3@ohpcd/stable: Created package revision d8aaaf1caef87bc1d3b9cd5d8dcc184f
coolmail/1.3@ohpcd/stable: Package '0263707db2a25b1fb74fb3f9a0e3bc58c8c6c1a4' created
coolmail/1.3@ohpcd/stable: Full package reference: coolmail/1.3@ohpcd/stable#4f1ca68b829e3cae69f403e536a0f273:0263707db2a25b1fb74fb3f9a0e3bc58c8c6c1a4#d8aaaf1caef87bc1d3b9cd5d8dcc184f
coolmail/1.3@ohpcd/stable: Package folder /storage/Users/currentUser/.conan2/p/b/coolm740ad9706c621/p

======== Launching test_package ========

======== Computing dependency graph ========
Graph root
    coolmail/1.3@ohpcd/stable (test package): /storage/Users/currentUser/ws/wt-coolmail-1.3/archives/c/coolmail/1.3/test_package/conanfile.py
Requirements
    coolmail/1.3@ohpcd/stable#4f1ca68b829e3cae69f403e536a0f273 - Cache
    libice/1.1.2#d8a6c94803be16b407b7403cc9d3b2ea - Cache
    libsm/1.2.6#20094b163d064411916677b92556810e - Cache
    libx11/1.8.13#e3ce69008a37ca95d1f0918c47709057 - Cache
    libxau/1.0.11#e70832a1f31a85a0398300bf72179ad9 - Cache
    libxcb/1.17.0#86ecb60c68ff97abdd8075b63777e4ec - Cache
    libxdmcp/1.1.5#8aaf268abc5f64d20cb46f0ec0c6fdb7 - Cache
    libxt/1.3.1#984522669afc4e011b761123dbb7e8bd - Cache
    xcb-proto/1.17.0#f985020ceb16e7e9ea7af4f2e57652b5 - Cache
    xorgproto/2025.1#f5274e33759da898a6e8d87d7708d47c - Cache
    xtrans/1.4.0#0cac4da870508f7f9fc9b44a891b30b6 - Cache
    xtrans/1.6.0#664ea4b0b501c5f144fc094ab1a4dfc5 - Cache
Test requirements
    glib/2.84.0.1#75f29176eede55310742f73ebcf9a572 - Cache
    libffi/3.4.4#ca8b0eb4102edbca48730e504e3afbdc - Cache
    pcre2/10.45#5ecd2f9871deb549e2ae07489f2e40df - Cache
    zlib/1.3.1.1#9a23e7d51311d0440b6e4d36cf44e4d9 - Cache
WARN: risk: Packages required both with visible=True and visible=False
    xorgproto/2025.1: Required by libice/1.1.2, libsm/1.2.6

======== Computing necessary packages ========
Requirements
    coolmail/1.3@ohpcd/stable#4f1ca68b829e3cae69f403e536a0f273:0263707db2a25b1fb74fb3f9a0e3bc58c8c6c1a4#d8aaaf1caef87bc1d3b9cd5d8dcc184f - Cache
    libice/1.1.2#d8a6c94803be16b407b7403cc9d3b2ea:b661fd7d193eba49082337bd3d77c7ce66163b13#79a4ecfba208ab21747f040b61f4db2a - Cache
    libsm/1.2.6#20094b163d064411916677b92556810e:4f586cea8e74412a180e21e8ab38b4af72ae0177#3bb2a3f52339e4d8d5ce9e907d9acb04 - Cache
    libx11/1.8.13#e3ce69008a37ca95d1f0918c47709057:cae7d429fb6839b6840b7602f11bf20c76efecdf#701e81816807aea0ad862a324557f4e9 - Cache
    libxau/1.0.11#e70832a1f31a85a0398300bf72179ad9:b33b73a64003feb619a47ac2da762d7e7521ab18#2875a48c0f9c6168a810db745fe96324 - Cache
    libxcb/1.17.0#86ecb60c68ff97abdd8075b63777e4ec:1913acd6b909292031fa8d8bbe2094cc57a71423#7675f8ba8257aac6cb048e6278dbfffc - Cache
    libxdmcp/1.1.5#8aaf268abc5f64d20cb46f0ec0c6fdb7:b33b73a64003feb619a47ac2da762d7e7521ab18#b9dab63027b7d0ce0f0c04f8ceef5197 - Cache
    libxt/1.3.1#984522669afc4e011b761123dbb7e8bd:40beeeb2980b87253b8656a29c55a979c80f536a#1e1b323aa0b57a2333a211fb9c65ba9d - Cache
Test requirements
Skipped binaries
    xcb-proto/1.17.0, xorgproto/2025.1, xtrans/1.4.0, xtrans/1.6.0, glib/2.84.0.1, libffi/3.4.4, pcre2/10.45, zlib/1.3.1.1

======== Installing packages ========
libxau/1.0.11: Already installed! (1 of 8)
libxdmcp/1.1.5: Already installed! (2 of 8)
libice/1.1.2: Already installed! (3 of 8)
libxcb/1.17.0: Already installed! (4 of 8)
libsm/1.2.6: Already installed! (5 of 8)
libx11/1.8.13: Already installed! (6 of 8)
libxt/1.3.1: Already installed! (7 of 8)
coolmail/1.3@ohpcd/stable: Already installed! (8 of 8)

======== Testing the package ========
Removing previously existing 'test_package' build folder: /storage/Users/currentUser/ws/wt-coolmail-1.3/archives/c/coolmail/1.3/test_package/build-release
coolmail/1.3@ohpcd/stable (test package): Test package build: build-release
coolmail/1.3@ohpcd/stable (test package): Test package build folder: /storage/Users/currentUser/ws/wt-coolmail-1.3/archives/c/coolmail/1.3/test_package/build-release
coolmail/1.3@ohpcd/stable (test package): Writing generators to /storage/Users/currentUser/ws/wt-coolmail-1.3/archives/c/coolmail/1.3/test_package/build-release/conan
coolmail/1.3@ohpcd/stable (test package): Generator 'VirtualRunEnv' calling 'generate()'
coolmail/1.3@ohpcd/stable (test package): Generating aggregated env files
coolmail/1.3@ohpcd/stable (test package): Generated aggregated env files: ['conanrun.sh', 'conanbuild.sh']

======== Testing the package: Building ========

======== Testing the package: Executing test ========
coolmail/1.3@ohpcd/stable (test package): Running test()
coolmail/1.3@ohpcd/stable (test package): RUN: /bin/sh /storage/Users/currentUser/ws/wt-coolmail-1.3/archives/c/coolmail/1.3/test_package/test_coolmail.sh /storage/Users/currentUser/.conan2/p/b/coolm740ad9706c621/p /storage/Users/currentUser/.conan2/p/b/coolm740ad9706c621/p/bin/coolmail /storage/Users/currentUser/ws/wt-coolmail-1.3/archives/c/coolmail/1.3/test_package/build-release /storage/Users/currentUser/.conan2/p/libxt9f52773f49d71/p/lib:/storage/Users/currentUser/.conan2/p/libx1c96c2c60af230/p/lib:/storage/Users/currentUser/.conan2/p/libxc29481f84b64ed/p/lib:/storage/Users/currentUser/.conan2/p/libxa6898c29f5713b/p/lib:/storage/Users/currentUser/.conan2/p/libxdc31a2415c1ec8/p/lib:/storage/Users/currentUser/.conan2/p/libsmb2a1d8b212ef1/p/lib:/storage/Users/currentUser/.conan2/p/libicb7ea26df82991/p/lib
OK: packaged binary present and executable
OK: coolmail -h exited 0
OK: usage banner present
OK: documented options listed
OK: headless run exited 1 after loading the X11/Xt chain
OK: man page installed
OK: X11 app-defaults installed
coolmail smoke test OK (7 checks)

```
