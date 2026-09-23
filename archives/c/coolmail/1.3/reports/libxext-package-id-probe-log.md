# libxext 与 libxt/libx11 1.8.13 图不兼容的探针实测日志

> 留档对象：`libxext-package-id-probe.log`（工具生成，libxext 与 libxt/libx11 1.8.13 图不兼容的探针实测）
> **权威副本即本文件正文**：下方 fenced 代码块与生成当时的原始 `.log` 逐字节相同。
> 正文 sha256 `cd759ab2b4ec85000431f8288053a4ee74b2e1070b318059c42510abedd5acaa`；正文 6370 字节 / 128 行。
> 生成命令：`conan install probe -pr:h=<abs>/ci/conan/profiles/ohos-aarch64 --build=never -of probe/out`
> 原始 `.log` 由 `.gitignore` 的 `reports/` 规则忽略且**每轮重跑会被覆盖**（W3 尤其明显，其中含时间戳与每轮重建的缓存分片目录名），因此正文才是稳定基线，引用请用可搜索标记而不是行号。
> 仓库规则 `.gitcode/review-memory.md` 第 19 条把 `*.log` 列为 PR 禁入文件，故以 `.md` 留档。

```text
# libxext 与 libxt/libx11 1.8.13 图不兼容的实测原始日志
# probe conanfile.py（/storage/Users/currentUser/tmp/coolmail-1.3/w0-xext/conanfile.py）：
#   name=coolmailxextprobe version=1.3
#   requirements: libxt/1.3.1, libxext/6.4.0.1, libx11/1.8.13(force=True)
# 命令：conan install <probe-dir> -pr:h=ci/conan/profiles/ohos-aarch64 --build=never -of <out>
# 退出码: 1
#

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
compiler.cppstd=gnu14
compiler.libcxx=libstdc++11
compiler.version=15
os=OHOS
os.version=6.0


======== Computing dependency graph ========
Graph root
    conanfile.py (coolmailxextprobe/1.3): /storage/Users/currentUser/tmp/coolmail-1.3/w0-xext/conanfile.py
Requirements
    libice/1.1.2#d8a6c94803be16b407b7403cc9d3b2ea - Cache
    libsm/1.2.6#20094b163d064411916677b92556810e - Cache
    libx11/1.8.13#e3ce69008a37ca95d1f0918c47709057 - Cache
    libxau/1.0.11#e70832a1f31a85a0398300bf72179ad9 - Cache
    libxcb/1.17.0#86ecb60c68ff97abdd8075b63777e4ec - Cache
    libxdmcp/1.1.5#8aaf268abc5f64d20cb46f0ec0c6fdb7 - Cache
    libxext/6.4.0.1#a99fc9be29be359b10cb24a344f682bb - Cache
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
Overrides
    libx11/1.8.13#e3ce69008a37ca95d1f0918c47709057: [None, 'libx11/1.8.13']
    libx11/6.4.0: ['libx11/1.8.13']
WARN: risk: Packages required both with visible=True and visible=False
    xorgproto/2025.1: Required by libice/1.1.2, libsm/1.2.6

======== Computing necessary packages ========
Connecting to remote 'ohpcd' anonymously
libxext/6.4.0.1: Main binary package 'eab79208a9437a856077cc57885309d75bdb4a31' missing
libxext/6.4.0.1: Checking 11 compatible configurations
libxext/6.4.0.1: Compatible configurations not found in cache, checking servers
libxext/6.4.0.1: '5a3c087b0c14e68bb7481d00056e210f1ba7f5b4': compiler.cppstd=98
libxext/6.4.0.1: 'befdb8381e0bec8ade51463f9dd1c30710afbb34': compiler.cppstd=gnu98
libxext/6.4.0.1: '13d6789ec0789f68ce72cb836620f48e01332bd7': compiler.cppstd=11
libxext/6.4.0.1: '635c6ca7d9a1bb04317776ffb792f2648bdba778': compiler.cppstd=gnu11
libxext/6.4.0.1: '67b75fa560ba8fabfcfec6b972a2c72380611998': compiler.cppstd=14
libxext/6.4.0.1: '3d715cf65005a4fb42b93d63dd272d25e13a9db8': compiler.cppstd=gnu14
libxext/6.4.0.1: 'fe39614f9996a69df8bdcd3374a72b4453d4ecd4': compiler.cppstd=gnu17
libxext/6.4.0.1: '65c86586b4820de11ed12f44a87b10de6b1615d2': compiler.cppstd=20
libxext/6.4.0.1: '7b497aa2ffce566932a3672ee068d38636b1d7fd': compiler.cppstd=gnu20
libxext/6.4.0.1: 'a96d405acde6d41a3dfb0f18c1f2cf50d0057d7e': compiler.cppstd=23
libxext/6.4.0.1: 'ad2b62d4ba48e512c9a55e36f04b5d21713a1458': compiler.cppstd=gnu23
libxext/6.4.0.1: No compatible configuration found

A new experimental approach for binary compatibility detection is available.
    Enable it by setting the core.graph:compatibility_mode=optimized conf
    and get improved performance when querying multiple compatible binaries in remotes.

Requirements
    libice/1.1.2#d8a6c94803be16b407b7403cc9d3b2ea:b661fd7d193eba49082337bd3d77c7ce66163b13#79a4ecfba208ab21747f040b61f4db2a - Cache
    libsm/1.2.6#20094b163d064411916677b92556810e:4f586cea8e74412a180e21e8ab38b4af72ae0177#3bb2a3f52339e4d8d5ce9e907d9acb04 - Cache
    libx11/1.8.13#e3ce69008a37ca95d1f0918c47709057:cae7d429fb6839b6840b7602f11bf20c76efecdf#701e81816807aea0ad862a324557f4e9 - Cache
    libxau/1.0.11#e70832a1f31a85a0398300bf72179ad9:b33b73a64003feb619a47ac2da762d7e7521ab18#2875a48c0f9c6168a810db745fe96324 - Cache
    libxcb/1.17.0#86ecb60c68ff97abdd8075b63777e4ec:1913acd6b909292031fa8d8bbe2094cc57a71423#7675f8ba8257aac6cb048e6278dbfffc - Cache
    libxdmcp/1.1.5#8aaf268abc5f64d20cb46f0ec0c6fdb7:b33b73a64003feb619a47ac2da762d7e7521ab18#b9dab63027b7d0ce0f0c04f8ceef5197 - Cache
    libxext/6.4.0.1#a99fc9be29be359b10cb24a344f682bb:eab79208a9437a856077cc57885309d75bdb4a31 - Missing
    libxt/1.3.1#984522669afc4e011b761123dbb7e8bd:40beeeb2980b87253b8656a29c55a979c80f536a#1e1b323aa0b57a2333a211fb9c65ba9d - Cache
    xorgproto/2025.1#f5274e33759da898a6e8d87d7708d47c:283a988d63e011a731408b6abe0950de49e6171d#b7dc443b533634631c412ae235a57198 - Cache
    xtrans/1.6.0#664ea4b0b501c5f144fc094ab1a4dfc5:283a988d63e011a731408b6abe0950de49e6171d#f07ea55c2b81548d01d94db631e0ac0e - Cache
Test requirements
Skipped binaries
    xcb-proto/1.17.0, xtrans/1.4.0, glib/2.84.0.1, libffi/3.4.4, pcre2/10.45, zlib/1.3.1.1
ERROR: Missing binary: libxext/6.4.0.1:eab79208a9437a856077cc57885309d75bdb4a31

libxext/6.4.0.1: WARN: Can't find a 'libxext/6.4.0.1' package binary 'eab79208a9437a856077cc57885309d75bdb4a31' for the configuration:
[settings]
arch=armv8
build_type=Release
compiler=clang
compiler.cppstd=17
compiler.libcxx=libc++
compiler.version=15
os=OHOS
os.version=6.0
[options]
shared=True
[requires]
libx11/1.8.Z
xorgproto/2025.1#f5274e33759da898a6e8d87d7708d47c:283a988d63e011a731408b6abe0950de49e6171d

ERROR: Missing prebuilt package for 'libxext/6.4.0.1'. You can try:
    - List all available packages using 'conan list "libxext/6.4.0.1:*" -r=remote'
    - Explain missing binaries: replace 'conan install ...' with 'conan graph explain ...'
    - Try to build locally from sources using the '--build=libxext/6.4.0.1' argument

More Info at 'https://docs.conan.io/2/knowledge/faq.html#error-missing-prebuilt-package'

```
