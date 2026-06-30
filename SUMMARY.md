# 鸿蒙平台开源软件编译兼容性总览

> 最后更新：2026-06-26
> 已收录软件：437 款 / 493 个版本

## 📊 总体统计

| 指标 | 数量 |
|------|------|
| 收录软件 | **437** 款 |
| 软件版本 | **493** 个 |
| ✅ 已发布 | 33 |
| ✅ 已编译 | 78 |
| ❌ 编译失败 | 0 |

| 构建系统 | 数量 |
|----------|------|
| Autotools | 175 |
| unknown | 101 |
| CMake | 66 |
| Makefile | 41 |
| Meson | 16 |
| custom | 5 |
| openssl-perl | 1 |
| python | 1 |
| perl | 1 |
| simple-configure | 1 |
| perl_makemaker | 1 |
| go | 1 |
| manual_makefile | 1 |
| custom-configure | 1 |
| Makefile | 1 |
| cmake-ninja | 1 |
| Script | 1 |
| custom-makefile | 1 |
| shell | 1 |
| waf | 1 |
| simple_makefile | 1 |

## 📋 软件兼容性一览

| 软件 | 版本 | 状态 | 兼容性 | 构建系统 | 补丁数 | 依赖 | 详情 |
|------|------|------|--------|----------|--------|------|------|
| **7zip** | 23.01、25.01 | uploaded |  | unknown | 0 | - | [📄](archives/7/7zip/25.01/) |
| **SDL2_image** | 2.6.0 | ✅ 已编译 |  | CMake | 2 | - | [📄](archives/s/SDL2_image/2.6.0/) |
| **abseil-cpp** | 20260107.1、20240116.1 | partial |  | Autotools | 1 | - | [📄](archives/a/abseil-cpp/20240116.1/) |
| **apr** | 1.7.6 | ✅ 已编译 |  |  | 3 | - | [📄](archives/a/apr/1.7.6/) |
| **argon2** | 20190702 | uploaded |  | unknown | 0 | - | [📄](archives/a/argon2/20190702/) |
| **argp-standalone** | 1.5.0 | uploaded |  | unknown | 0 | - | [📄](archives/a/argp-standalone/1.5.0/) |
| **aria2** | 1.37.0 | 📦 已归档 |  |  | - | - | [📄](archives/a/aria2/1.37.0/) |
| **arp-scan** | 1.10.0 | partial |  | Autotools | - | libpcap >= 1.5.0,libpcap 1.10.6 (静态链接) | [📄](archives/a/arp-scan/1.10.0/) |
| **asciidoc** | 10.2.1 | ✅ 已编译 |  | python | 3 | - | [📄](archives/a/asciidoc/10.2.1/) |
| **autoconf** | 2.72 | uploaded |  | Autotools | 0 | - | [📄](archives/a/autoconf/2.72/) |
| **autoconf-archive** | 2024.10.16 | uploaded |  | unknown | 0 | - | [📄](archives/a/autoconf-archive/2024.10.16/) |
| **automake** | 1.16.5、1.17 | uploaded |  | Autotools | 0 | - | [📄](archives/a/automake/1.17/) |
| **autossh** | 1.4g | success |  | Autotools | - | ssh (OpenSSH 9.6p1, system installed at /usr/bin/ssh) | [📄](archives/a/autossh/1.4g/) |
| **avro-c** | 1.12.0 | ✅ 已发布 |  |  | 2 | - | [📄](archives/a/avro-c/1.12.0/) |
| **awk** | 20251225 | success |  | Makefile | - | - | [📄](archives/a/awk/20251225/) |
| **aws-c-auth** | 0.10.1 | ✅ 已发布 |  |  | - | - | [📄](archives/a/aws-c-auth/0.10.1/) |
| **aws-c-cal** | 0.9.13 | uploaded |  | unknown | 0 | - | [📄](archives/a/aws-c-cal/0.9.13/) |
| **aws-c-common** | 0.12.6 | uploaded |  | unknown | 0 | - | [📄](archives/a/aws-c-common/0.12.6/) |
| **aws-c-compression** | 0.3.2 | uploaded |  | unknown | 0 | - | [📄](archives/a/aws-c-compression/0.3.2/) |
| **aws-c-event-stream** | 0.7.0 | uploaded |  | unknown | 0 | - | [📄](archives/a/aws-c-event-stream/0.7.0/) |
| **aws-c-http** | 0.10.14 | uploaded |  | unknown | 0 | - | [📄](archives/a/aws-c-http/0.10.14/) |
| **aws-c-io** | 0.26.3 | uploaded |  | unknown | 0 | - | [📄](archives/a/aws-c-io/0.26.3/) |
| **aws-c-mqtt** | 0.15.2、0.14.0 | partial |  |  | - | - | [📄](archives/a/aws-c-mqtt/0.14.0/) |
| **aws-c-s3** | 0.12.2 | uploaded |  | unknown | 0 | - | [📄](archives/a/aws-c-s3/0.12.2/) |
| **aws-c-sdkutils** | 0.2.4 | uploaded |  | unknown | 0 | - | [📄](archives/a/aws-c-sdkutils/0.2.4/) |
| **aws-checksums** | 0.2.10 | uploaded |  | unknown | 0 | - | [📄](archives/a/aws-checksums/0.2.10/) |
| **aws-crt-cpp** | 0.38.5 | uploaded |  | unknown | 0 | - | [📄](archives/a/aws-crt-cpp/0.38.5/) |
| **aws-lc** | 1.72.0 | uploaded |  | unknown | 0 | - | [📄](archives/a/aws-lc/1.72.0/) |
| **b3sum** | 1.8.4 | uploaded |  | CMake | 0 | - | [📄](archives/b/b3sum/1.8.4/) |
| **bash** | 5.3 | verified |  | Autotools | 0 | - | [📄](archives/b/bash/5.3/) |
| **bash-completion** | 2.17.0 | ✅ 已编译 |  |  | 2 | - | [📄](archives/b/bash-completion/2.17.0/) |
| **bbe** | 0.2.2 | partial |  |  | 2 | - | [📄](archives/b/bbe/0.2.2/) |
| **bc** | 1.07.1 | partial |  | Autotools | - | - | [📄](archives/b/bc/1.07.1/) |
| **bcrypt** | 1.0 | uploaded |  | unknown | 0 | - | [📄](archives/b/bcrypt/1.0/) |
| **bear** | 3.1.6 | uploaded |  | Makefile | 0 | - | [📄](archives/b/bear/3.1.6/) |
| **bearssl** | 0.6 | uploaded |  | CMake | 0 | - | [📄](archives/b/bearssl/0.6/) |
| **bind** | 9.20.22 | ✅ 已编译 |  | Autotools | - | - | [📄](archives/b/bind/9.20.22/) |
| **bison** | 3.8.2 | ✅ 已编译 |  |  | 5 | - | [📄](archives/b/bison/3.8.2/) |
| **blake3** | 1.8.3 | success |  | Autotools | - | - | [📄](archives/b/blake3/1.8.3/) |
| **blockhash** | 0.1 | ✅ 已发布 |  |  | 1 | - | [📄](archives/b/blockhash/0.1/) |
| **blosc** | 1.21.5、1.21.6 | uploaded |  | unknown | 0 | - | [📄](archives/b/blosc/1.21.6/) |
| **boxes** | 2.3.1 | uploaded |  | unknown | 0 | - | [📄](archives/b/boxes/2.3.1/) |
| **brotli** | 1.1.0、1.2.0 | uploaded |  | Autotools | 0 | - | [📄](archives/b/brotli/1.2.0/) |
| **bsd-compat-headers** | 0.7.2 | uploaded |  | Makefile | 0 | - | [📄](archives/b/bsd-compat-headers/0.7.2/) |
| **bullet** | 3.25 | success |  | CMake | - | [] | [📄](archives/b/bullet/3.25/) |
| **bzip2** | 1.0.8 | verified |  | Autotools | 0 | - | [📄](archives/b/bzip2/1.0.8/) |
| **bzip3** | 1.4.0、1.5.3 | uploaded |  | Autotools | 0 | - | [📄](archives/b/bzip3/1.5.3/) |
| **c-ares** | 1.34.4、1.34.6 | uploaded |  | Autotools | 0 | - | [📄](archives/c/c-ares/1.34.6/) |
| **c-blosc** | 1.21.6 | success |  | CMake | - | - | [📄](archives/c/c-blosc/1.21.6/) |
| **ca-certificates** | 20250416、20250419 | ✅ 已编译 |  |  | - | - | [📄](archives/c/ca-certificates/20250419/) |
| **cairo** | 1.18.4 | ✅ 已编译 |  |  | 2 | - | [📄](archives/c/cairo/1.18.4/) |
| **capnp** | 1.3.0 | success |  | CMake | - | - | [📄](archives/c/capnp/1.3.0/) |
| **capstone** | 5.0.7-r0 | success |  | Autotools | - | - | [📄](archives/c/capstone/5.0.7-r0/) |
| **catch2** | 2.13.10-r0 | success |  | CMake | - | - | [📄](archives/c/catch2/2.13.10-r0/) |
| **ccache** | 4.12.1 | uploaded |  | Makefile | 0 | - | [📄](archives/c/ccache/4.12.1/) |
| **cgif** | 0.5.2 | success |  | Meson | - | - | [📄](archives/c/cgif/0.5.2/) |
| **check** | 0.15.2 | ✅ 已编译 |  |  | 2 | - | [📄](archives/c/check/0.15.2/) |
| **chibi-scheme** | 0.12 | success |  | Makefile | - | - | [📄](archives/c/chibi-scheme/0.12/) |
| **chicken** | 5.4.0 | partial |  | Autotools | - | - | [📄](archives/c/chicken/5.4.0/) |
| **chromaprint** | 1.6.0 | ✅ 已发布 |  |  | - | - | [📄](archives/c/chromaprint/1.6.0/) |
| **ciso** | 1.0、1.0.0 | uploaded |  | unknown | 0 | - | [📄](archives/c/ciso/1.0.0/) |
| **cjson** | 1.7.18 | uploaded |  | Autotools | 0 | - | [📄](archives/c/cjson/1.7.18/) |
| **cloc** | 2.08 | success |  | perl | - | perl >= 5.10.0,Regexp::Common,Parallel::ForkManager,Algorithm::Diff | [📄](archives/c/cloc/2.08/) |
| **cmake** | 3.30.0 | ✅ 已编译 |  |  | - | - | [📄](archives/c/cmake/3.30.0/) |
| **cmocka** | 2.0.2 | uploaded |  | CMake | 0 | - | [📄](archives/c/cmocka/2.0.2/) |
| **cmph** | 2.0 | ✅ 已编译 |  |  | - | - | [📄](archives/c/cmph/2.0/) |
| **confuse** | 3.3 | ✅ 已编译 |  |  | 2 | - | [📄](archives/c/confuse/3.3/) |
| **coreutils** | 9.10 | verified |  | Autotools | 0 | - | [📄](archives/c/coreutils/9.10/) |
| **cpptoml** | v0.1.1 | uploaded |  | CMake | 0 | - | [📄](archives/c/cpptoml/v0.1.1/) |
| **cramfs** | 1.1 | uploaded |  | unknown | 0 | - | [📄](archives/c/cramfs/1.1/) |
| **croaring** | 4.6.1 | uploaded |  | CMake | 0 | - | [📄](archives/c/croaring/4.6.1/) |
| **cryptopp** | 8.9.0 | uploaded |  | unknown | 0 | - | [📄](archives/c/cryptopp/8.9.0/) |
| **cunit** | 2.1-3 | uploaded |  | CMake | 0 | - | [📄](archives/c/cunit/2.1-3/) |
| **curl** | 8.15.0 | ✅ 已编译 |  | CMake | 1 | - | [📄](archives/c/curl/8.15.0/) |
| **czmq** | 4.2.1 | partial |  | Autotools | - | - | [📄](archives/c/czmq/4.2.1/) |
| **daemonize** | 1.7.8 | partial |  | Autotools | - | - | [📄](archives/d/daemonize/1.7.8/) |
| **dar** | 2.8.1 | ✅ 已编译 |  |  | 15 | - | [📄](archives/d/dar/2.8.1/) |
| **dash** | 0.5.12 | partial |  | Autotools | 2 | - | [📄](archives/d/dash/0.5.12/) |
| **dbus** | 1.14.10 | partial |  | Autotools | 4 | - | [📄](archives/d/dbus/1.14.10/) |
| **ddrescue** | 1.30 | partial |  | simple-configure | - | [] | [📄](archives/d/ddrescue/1.30/) |
| **dialog** | 1.3-20240307 | partial |  | Autotools | 2 | - | [📄](archives/d/dialog/1.3-20240307/) |
| **discount** | 2.2.7、2.2.7b | partial |  | Autotools | 1 | - | [📄](archives/d/discount/2.2.7b/) |
| **distcc** | 3.4 | uploaded |  | Makefile | 0 | - | [📄](archives/d/distcc/3.4/) |
| **dmg2img** | 1.6.7 | uploaded |  | unknown | 0 | - | [📄](archives/d/dmg2img/1.6.7/) |
| **dmidecode** | 3.6 | uploaded |  | Makefile | 0 | - | [📄](archives/d/dmidecode/3.6/) |
| **dnsmasq** | 2.90、2.92 | success |  | Autotools | 2 | - | [📄](archives/d/dnsmasq/2.92/) |
| **doctest** | 2.5.2 | uploaded |  | CMake | 0 | - | [📄](archives/d/doctest/2.5.2/) |
| **dos2unix** | 7.5.4 | verified |  | Makefile | 0 | - | [📄](archives/d/dos2unix/7.5.4/) |
| **dspdfviewer** | 1.15.1 | ❌ 编译失败 |  |  | - | - | [📄](archives/d/dspdfviewer/1.15.1/) |
| **dtc** | 1.7.2 | partial |  | Autotools | 1 | - | [📄](archives/d/dtc/1.7.2/) |
| **duckdb** | 1.2.0 | partial |  | Autotools | - | - | [📄](archives/d/duckdb/1.2.0/) |
| **dvisvgm** | 3.6 | ✅ 已编译 |  | Autotools | 3 | - | [📄](archives/d/dvisvgm/3.6/) |
| **dwarfutils** | 2.3.1 | success |  | CMake | 1 | - | [📄](archives/d/dwarfutils/2.3.1/) |
| **e2fsimage** | 1.0.0 | ❌ 编译失败 |  |  | 0 | - | [📄](archives/e/e2fsimage/1.0.0/) |
| **e2fsprogs** | 1.47.0 | ✅ 已发布 |  |  | 0 | - | [📄](archives/e/e2fsprogs/1.47.0/) |
| **easyeffects** | 7.2.0 | ❌ 编译失败 |  |  | 0 | - | [📄](archives/e/easyeffects/7.2.0/) |
| **eigen** | 3.4.0 | uploaded |  | CMake | 0 | - | [📄](archives/e/eigen/3.4.0/) |
| **elinks** | 0.19.1 | ✅ 已发布 |  | Meson | - | - | [📄](archives/e/elinks/0.19.1/) |
| **entr** | 5.8 | partial |  | Autotools | - | - | [📄](archives/e/entr/5.8/) |
| **exiftool** | 13.50 | partial |  | perl_makemaker | - | - | [📄](archives/e/exiftool/13.50/) |
| **expat** | 2.7.1、2.8.0 | uploaded |  | Autotools | 0 | - | [📄](archives/e/expat/2.8.0/) |
| **faac** | 1.40 | success |  | Meson | - | - | [📄](archives/f/faac/1.40/) |
| **faad2** | 2.11.2 | success |  | CMake | - | - | [📄](archives/f/faad2/2.11.2/) |
| **farbfeld** | 4 | uploaded |  | unknown | 0 | - | [📄](archives/f/farbfeld/4/) |
| **fastjar** | 0.98 | uploaded |  | unknown | 0 | - | [📄](archives/f/fastjar/0.98/) |
| **fbida** | 2.15 | ✅ 已编译 |  |  | 2 | - | [📄](archives/f/fbida/2.15/) |
| **fcrackzip** | 1.0 | uploaded |  | unknown | 0 | - | [📄](archives/f/fcrackzip/1.0/) |
| **fdk-aac** | 2.0.3 | partial |  | CMake | - | [] | [📄](archives/f/fdk-aac/2.0.3/) |
| **fftw** | 3.3.10 | uploaded |  | unknown | 0 | - | [📄](archives/f/fftw/3.3.10/) |
| **figlet** | 2.2.5 | success |  | Makefile | 1 | - | [📄](archives/f/figlet/2.2.5/) |
| **file** | 5.45、5.46 | ✅ 已编译 |  |  | 3 | - | [📄](archives/f/file/5.46/) |
| **findutils** | 4.10.0 | ✅ 已编译 |  | Autotools | 2 | [] | [📄](archives/f/findutils/4.10.0/) |
| **fio** | 3.41 | partial |  | Autotools | 1 | - | [📄](archives/f/fio/3.41/) |
| **fish** | 3.7.1 | partial |  | Autotools | - | - | [📄](archives/f/fish/3.7.1/) |
| **flac** | 1.4.3 | uploaded |  | Autotools | 0 | - | [📄](archives/f/flac/1.4.3/) |
| **flatbuffers** | 24.3.25 | ✅ 已发布 |  | CMake | - | - | [📄](archives/f/flatbuffers/24.3.25/) |
| **flex** | 2.6.4 | ✅ 已编译 |  |  | 5 | - | [📄](archives/f/flex/2.6.4/) |
| **fontconfig** | 2.16.0 | uploaded |  | Autotools | 0 | - | [📄](archives/f/fontconfig/2.16.0/) |
| **fortune** | 9708 | ✅ 已发布 |  |  | 1 | - | [📄](archives/f/fortune/9708/) |
| **freetype** | 2.14.3 | uploaded |  | Autotools | 0 | - | [📄](archives/f/freetype/2.14.3/) |
| **frei0r-plugins** | 3.1.3 | ✅ 已编译 |  | CMake | 0 | - | [📄](archives/f/frei0r-plugins/3.1.3/) |
| **fribidi** | 1.0.13、1.0.16 | uploaded |  | Meson | 0 | - | [📄](archives/f/fribidi/1.0.16/) |
| **ftgl** | 2.4.0 | ✅ 已编译 |  |  | 2 | - | [📄](archives/f/ftgl/2.4.0/) |
| **ftxui** | 6.1.9 | uploaded |  | unknown | 0 | - | [📄](archives/f/ftxui/6.1.9/) |
| **gawk** | 5.3.0 | verified |  | Autotools | 0 | - | [📄](archives/g/gawk/5.3.0/) |
| **gd** | 2.3.3 | uploaded |  | unknown | 0 | - | [📄](archives/g/gd/2.3.3/) |
| **gdbm** | 1.23 | verified |  | Autotools | 0 | - | [📄](archives/g/gdbm/1.23/) |
| **gdk-pixbuf** | 2.42.12 | ✅ 已编译 |  | Meson | 3 | - | [📄](archives/g/gdk-pixbuf/2.42.12/) |
| **gflags** | 2.2.2 | partial |  | Autotools | - | - | [📄](archives/g/gflags/2.2.2/) |
| **ghostscript** | 10.07.1 | ✅ 已编译 |  |  | 7 | - | [📄](archives/g/ghostscript/10.07.1/) |
| **giflib** | 5.2.2 | uploaded |  | unknown | 0 | - | [📄](archives/g/giflib/5.2.2/) |
| **gifsicle** | 1.96 | ✅ 已编译 |  |  | - | - | [📄](archives/g/gifsicle/1.96/) |
| **git** | 2.49.0、2.45 | partial |  | Autotools | - | - | [📄](archives/g/git/2.45/) |
| **glances** | 4.5.4 | ✅ 已编译 |  |  | 1 | - | [📄](archives/g/glances/4.5.4/) |
| **glfw** | 3.4 | ✅ 已发布 |  | CMake | 1 | - | [📄](archives/g/glfw/3.4/) |
| **glib** | 2.84.0 | ✅ 已编译 |  | Meson | 3 | libffi >= 3.4.4,pcre2 >= 10.47,meson >= 1.11.1,ninja >= 1.13 | [📄](archives/g/glib/2.84.0/) |
| **glm** | 0.9.9.8 | uploaded |  | CMake | 0 | - | [📄](archives/g/glm/0.9.9.8/) |
| **glog** | 0.7.1 | partial |  | Autotools | 1 | - | [📄](archives/g/glog/0.7.1/) |
| **glproto** | 1.4.17 | compiling |  | Autotools | - | - | [📄](archives/g/glproto/1.4.17/) |
| **glslang** | vulkan-sdk-1.3.290.0 | ✅ 已编译 |  | CMake | 1 | cmake >= 3.17.2,gcc,g++,spirv-tools | [📄](archives/g/glslang/vulkan-sdk-1.3.290.0/) |
| **gmp** | 6.3.0 | ✅ 已编译 |  | Autotools | 3 | [] | [📄](archives/g/gmp/6.3.0/) |
| **gmssl** | 3.1.1 | uploaded |  | CMake | 0 | - | [📄](archives/g/gmssl/3.1.1/) |
| **gnunet** | 0.24.3 | ✅ 已发布 |  |  | 0 | - | [📄](archives/g/gnunet/0.24.3/) |
| **gocr** | 0.48 | ✅ 已编译 |  | Autotools | 8 | - | [📄](archives/g/gocr/0.48/) |
| **gpatch** | 2.8 | partial |  | Autotools | 2 | libattr (未安装，无xattr支持) | [📄](archives/g/gpatch/2.8/) |
| **grep** | 3.11 | ✅ 已编译 |  | Autotools | 1 | pcre2 10.47 (system preinstalled) | [📄](archives/g/grep/3.11/) |
| **gsm** | 1.0.22、1.0.23 | uploaded |  | unknown | 0 | - | [📄](archives/g/gsm/1.0.23/) |
| **gtk** | 4.22.4 | ✅ 已编译 |  | Meson | 1 | - | [📄](archives/g/gtk/4.22.4/) |
| **gtk+** | 3.24.43 | packaged |  |  | 1 | - | [📄](archives/g/gtk+/3.24.43/) |
| **gzip** | 1.13 | verified |  | Autotools | 0 | - | [📄](archives/g/gzip/1.13/) |
| **halloy** | 2026.7 | ✅ 已编译 |  | cargo | 1 | - | [📄](archives/h/halloy/2026.7/) |
| **harfbuzz** | 14.2.0 | uploaded |  | Meson | 0 | - | [📄](archives/h/harfbuzz/14.2.0/) |
| **hdf5** | 1.13.0 | ✅ 已发布 |  |  | 2 | - | [📄](archives/h/hdf5/1.13.0/) |
| **hdrhistogram** | 0.11.9 | ✅ 已发布 |  |  | 1 | - | [📄](archives/h/hdrhistogram/0.11.9/) |
| **help2man** | 1.49.3 | verified |  | Autotools | 0 | - | [📄](archives/h/help2man/1.49.3/) |
| **hexchat** | 2.16.2 | ✅ 已编译 |  |  | 0 | - | [📄](archives/h/hexchat/2.16.2/) |
| **hidapi** | 0.14.0 | ✅ 已编译 |  |  | - | - | [📄](archives/h/hidapi/0.14.0/) |
| **hiredis** | 1.2.0 | uploaded |  | Autotools | 0 | - | [📄](archives/h/hiredis/1.2.0/) |
| **hping** | 3.0.0-alpha-1 | ✅ 已编译 |  | Makefile | 2 | libpcap | [📄](archives/h/hping/3.0.0-alpha-1/) |
| **htop** | 3.4.1 | verified |  | Makefile | 0 | - | [📄](archives/h/htop/3.4.1/) |
| **hwinfo** | 25.2 | ✅ 已编译 |  | Makefile | 1 | [] | [📄](archives/h/hwinfo/25.2/) |
| **hwloc** | 2.11.0 | partial |  | Autotools | 1 | - | [📄](archives/h/hwloc/2.11.0/) |
| **hyprgraphics** | 0.5.1 | ✅ 已编译 |  |  | 1 | - | [📄](archives/h/hyprgraphics/0.5.1/) |
| **ices** | 2.0.3 | ❌ 编译失败 |  |  | 0 | - | [📄](archives/i/ices/2.0.3/) |
| **icoutils** | 0.32.3 | ✅ 已编译 |  |  | 1 | - | [📄](archives/i/icoutils/0.32.3/) |
| **iipsrv** | 1.3 | ✅ 已编译 |  | Autotools | 2 | - | [📄](archives/i/iipsrv/1.3/) |
| **image-roll** | 2.1.0 | ❌ 编译失败 |  |  | 0 | - | [📄](archives/i/image-roll/2.1.0/) |
| **imageoptim-cli** | 3.1.9 | ✅ 已发布 |  |  | - | - | [📄](archives/i/imageoptim-cli/3.1.9/) |
| **img** | 0.5.11 | ✅ 已编译 |  |  | 1 | - | [📄](archives/i/img/0.5.11/) |
| **imv** | 4.3.0 | ✅ 已编译 |  |  | 2 | - | [📄](archives/i/imv/4.3.0/) |
| **inetutils** | 2.5 | ❌ 编译失败 |  |  | - | - | [📄](archives/i/inetutils/2.5/) |
| **inkscape** | 1.4.4 | ❌ 编译失败 |  |  | 0 | - | [📄](archives/i/inkscape/1.4.4/) |
| **intltool** | 0.51.0 | uploaded |  | Autotools | 0 | - | [📄](archives/i/intltool/0.51.0/) |
| **iperf3** | 3.18 | uploaded |  | unknown | 0 | - | [📄](archives/i/iperf3/3.18/) |
| **iputils** | 20240905 | ✅ 已发布 |  |  | 1 | meson >= 0.44,ninja,clang/gcc,libcap (未安装，禁用 USE_CAP),libidn2 (未安装，禁用 USE_IDN)... | [📄](archives/i/iputils/20240905/) |
| **isa-l_crypto** | 2.26 | uploaded |  | CMake | 0 | - | [📄](archives/i/isa-l_crypto/2.26/) |
| **isoimagewriter** | 26.04.1 | ✅ 已发布 |  |  | 0 | - | [📄](archives/i/isoimagewriter/26.04.1/) |
| **iwgtk** | 0.9 | ✅ 已发布 |  |  | 0 | - | [📄](archives/i/iwgtk/0.9/) |
| **jansson** | 2.15.0 | uploaded |  | Autotools | 0 | - | [📄](archives/j/jansson/2.15.0/) |
| **jasper** | 4.2.9 | uploaded |  | unknown | 0 | - | [📄](archives/j/jasper/4.2.9/) |
| **jbig2dec** | 0.20 | uploaded |  | unknown | 0 | - | [📄](archives/j/jbig2dec/0.20/) |
| **jellyfin-ffmpeg** | 7.1.4-1 | ✅ 已发布 |  |  | 0 | - | [📄](archives/j/jellyfin-ffmpeg/7.1.4-1/) |
| **jitsi-meet** | 2.0.10978 | ✅ 已发布 |  |  | 0 | - | [📄](archives/j/jitsi-meet/2.0.10978/) |
| **jitsi-videobridge** | 2.3 | ✅ 已编译 |  |  | 3 | - | [📄](archives/j/jitsi-videobridge/2.3/) |
| **jna** | 5.19.0 | ✅ 已发布 |  |  | - | - | [📄](archives/j/jna/5.19.0/) |
| **jo** | 1.9 | partial |  | Autotools | 5 | - | [📄](archives/j/jo/1.9/) |
| **jpeg** | 10 | success |  | Autotools | 2 | - | [📄](archives/j/jpeg/10/) |
| **jq** | 1.7.1 | verified |  | Autotools | 0 | - | [📄](archives/j/jq/1.7.1/) |
| **json-c** | 0.16 | partial |  |  | 1 | - | [📄](archives/j/json-c/0.16/) |
| **krb5** | 1.22.1 | ✅ 已编译 |  |  | 4 | - | [📄](archives/k/krb5/1.22.1/) |
| **kustomize** | 5.8.1 | ✅ 已编译 |  | go | - | go >= 1.21 | [📄](archives/k/kustomize/5.8.1/) |
| **laszip** | 3.5.0 | uploaded |  | unknown | 0 | - | [📄](archives/l/laszip/3.5.0/) |
| **lcms2** | 2.19 | uploaded |  | unknown | 0 | - | [📄](archives/l/lcms2/2.19/) |
| **lemon** | 3.53.0 | uploaded |  | unknown | 0 | - | [📄](archives/l/lemon/3.53.0/) |
| **lerc** | 2.2、4.0.0 | uploaded |  | unknown | 0 | - | [📄](archives/l/lerc/4.0.0/) |
| **less** | 661 | partial |  | Autotools | 2 | - | [📄](archives/l/less/661/) |
| **leveldb** | 1.23 | uploaded |  | CMake | 0 | - | [📄](archives/l/leveldb/1.23/) |
| **lha** | 1.14.20211125 | uploaded |  | unknown | 0 | - | [📄](archives/l/lha/1.14.20211125/) |
| **libaec** | 1.1.6 | success |  | CMake | - | [] | [📄](archives/l/libaec/1.1.6/) |
| **libaio** | 0.3.112 | uploaded |  | Autotools | 0 | - | [📄](archives/l/libaio/0.3.112/) |
| **libarchive** | 3.7.4、3.8.7 | ✅ 已编译 |  |  | - | - | [📄](archives/l/libarchive/3.8.7/) |
| **libassuan** | 3.0.2 | uploaded |  | Autotools | 0 | - | [📄](archives/l/libassuan/3.0.2/) |
| **libatomic_ops** | 7.8.2 | uploaded |  | Autotools | 0 | - | [📄](archives/l/libatomic_ops/7.8.2/) |
| **libb2** | 0.98.1 | uploaded |  | Autotools | 0 | - | [📄](archives/l/libb2/0.98.1/) |
| **libbcrypt** | 1.3 | uploaded |  | unknown | 0 | - | [📄](archives/l/libbcrypt/1.3/) |
| **libbsd** | 0.11.7、0.12.2 | ✅ 已编译 |  |  | - | - | [📄](archives/l/libbsd/0.12.2/) |
| **libcap** | 2.69 | uploaded |  | Autotools | 0 | - | [📄](archives/l/libcap/2.69/) |
| **libcap-ng** | 0.9.1 | ✅ 已编译 |  | manual_makefile | 0 | linux-kernel-headers (linux/capability.h),pthread | [📄](archives/l/libcap-ng/0.9.1/) |
| **libccd** | 2.1 | success |  | CMake | 3 | - | [📄](archives/l/libccd/2.1/) |
| **libcerf** | 3.3 | success |  | CMake | - | - | [📄](archives/l/libcerf/3.3/) |
| **libconfig** | 1.7.3 | uploaded |  | CMake | 0 | - | [📄](archives/l/libconfig/1.7.3/) |
| **libconfuse** | 3.3 | ✅ 已编译 |  |  | 2 | - | [📄](archives/l/libconfuse/3.3/) |
| **libcuckoo** | 0.3.1 | uploaded |  | CMake | 0 | - | [📄](archives/l/libcuckoo/0.3.1/) |
| **libcuefile** | r475 | success |  | CMake | 1 | - | [📄](archives/l/libcuefile/r475/) |
| **libdaemon** | 0.14 | uploaded |  | Autotools | 0 | - | [📄](archives/l/libdaemon/0.14/) |
| **libdatrie** | 0.2.14 | partial |  | Autotools | 2 | - | [📄](archives/l/libdatrie/0.2.14/) |
| **libde265** | 1.0.18 | ✅ 已编译 |  |  | 2 | - | [📄](archives/l/libde265/1.0.18/) |
| **libdeflate** | 1.25、1.21 | partial |  | Autotools | - | - | [📄](archives/l/libdeflate/1.21/) |
| **libdmtx** | 0.7.8、0.7.5 | ✅ 已编译 |  |  | - | - | [📄](archives/l/libdmtx/0.7.5/) |
| **libdrm** | 2.4.133 | ✅ 已编译 |  |  | - | - | [📄](archives/l/libdrm/2.4.133/) |
| **libdvdcss** | 1.5.0 | success |  | Meson | - | [] | [📄](archives/l/libdvdcss/1.5.0/) |
| **libedit** | 20240808、20240817、20251016-3.1 | partial |  | Autotools | 2 | - | [📄](archives/l/libedit/20251016-3.1/) |
| **libepoxy** | 1.5.10 | ✅ 已发布 |  |  | - | - | [📄](archives/l/libepoxy/1.5.10/) |
| **libev** | 4.33 | uploaded |  | Autotools | 0 | - | [📄](archives/l/libev/4.33/) |
| **libevent** | 2.1.12-stable、2.1.12 | ✅ 已编译 |  | Autotools | 5 | - | [📄](archives/l/libevent/2.1.12/) |
| **libffi** | 3.4.4、3.5.2、3.4.6 | partial |  | Autotools | 3 | - | [📄](archives/l/libffi/3.4.6/) |
| **libfontenc** | 1.1.9 | success |  | Autotools | 3 | xproto (手动安装头文件),zlib (预编译包已安装) | [📄](archives/l/libfontenc/1.1.9/) |
| **libgcrypt** | 1.11.0 | uploaded |  | Autotools | 0 | - | [📄](archives/l/libgcrypt/1.11.0/) |
| **libgee** | 0.20.6 | ✅ 已编译 |  | Autotools | 2 | - | [📄](archives/l/libgee/0.20.6/) |
| **libgpg-error** | 1.50、1.55 | uploaded |  | Autotools | 0 | - | [📄](archives/l/libgpg-error/1.55/) |
| **libgpiod** | 2.0、2.1.3 | ✅ 已编译 |  |  | 4 | - | [📄](archives/l/libgpiod/2.1.3/) |
| **libgsm** | 1.0.18 | ✅ 已发布 |  | Makefile | 1 | [] | [📄](archives/l/libgsm/1.0.18/) |
| **libiconv** | 1.17 | uploaded |  | Autotools | 0 | - | [📄](archives/l/libiconv/1.17/) |
| **libidn** | 1.43 | 📦 已归档 |  |  | - | - | [📄](archives/l/libidn/1.43/) |
| **libiio** | 0.26 | ✅ 已编译 |  |  | - | - | [📄](archives/l/libiio/0.26/) |
| **libjpeg** | 10 | ✅ 已发布 |  |  | 3 | - | [📄](archives/l/libjpeg/10/) |
| **libjpeg-turbo** | 3.1.4.1、2.1.5.1 | partial |  | Autotools | - | - | [📄](archives/l/libjpeg-turbo/2.1.5.1/) |
| **libkcddb** | 26.04.1 | ✅ 已编译 |  | CMake | 1 | - | [📄](archives/l/libkcddb/26.04.1/) |
| **libkeyfinder** | 2.2.8 | ✅ 已发布 |  |  | 0 | - | [📄](archives/l/libkeyfinder/2.2.8/) |
| **libksba** | 1.6.7 | uploaded |  | Autotools | 0 | - | [📄](archives/l/libksba/1.6.7/) |
| **liblinear** | 2.50 | uploaded |  | Autotools | 0 | - | [📄](archives/l/liblinear/2.50/) |
| **liblzf** | 3.6 | uploaded |  | unknown | 0 | - | [📄](archives/l/liblzf/3.6/) |
| **libmaxminddb** | 1.13.3 | partial |  | Autotools | 3 | - | [📄](archives/l/libmaxminddb/1.13.3/) |
| **libmd** | 1.1.0 | ✅ 已编译 |  |  | - | - | [📄](archives/l/libmd/1.1.0/) |
| **libmnl** | 1.0.5 | uploaded |  | Autotools | 0 | - | [📄](archives/l/libmnl/1.0.5/) |
| **libmspack** | 0.11alpha | uploaded |  | unknown | 0 | - | [📄](archives/l/libmspack/0.11alpha/) |
| **libnetfilter_conntrack** | 1.1.0 | ✅ 已编译 |  | Autotools | 2 | - | [📄](archives/l/libnetfilter_conntrack/1.1.0/) |
| **libnl** | 3.7.0 | ✅ 已编译 |  |  | 3 | - | [📄](archives/l/libnl/3.7.0/) |
| **libntlm** | 1.2 | 📦 已归档 |  |  | - | - | [📄](archives/l/libntlm/1.2/) |
| **libogg** | 1.3.5、1.3.6 | uploaded |  | Autotools | 0 | - | [📄](archives/l/libogg/1.3.6/) |
| **libomp** | 15.0.4 | ✅ 已编译 |  | CMake | 2 | - | [📄](archives/l/libomp/15.0.4/) |
| **liboqs** | 0.15.0 | ✅ 已编译 |  |  | - | - | [📄](archives/l/liboqs/0.15.0/) |
| **libpcap** | 1.10.6 | uploaded |  | Autotools | 0 | - | [📄](archives/l/libpcap/1.10.6/) |
| **libpciaccess** | 0.17 | ✅ 已编译 |  |  | - | - | [📄](archives/l/libpciaccess/0.17/) |
| **libpipeline** | 1.5.8 | verified |  | unknown | 0 | - | [📄](archives/l/libpipeline/1.5.8/) |
| **libpng** | 1.6.39 | ✅ 已编译 |  | CMake | 0 | - | [📄](archives/l/libpng/1.6.39/) |
| **libpq** | 17.2 | ✅ 已编译 |  |  | 3 | - | [📄](archives/l/libpq/17.2/) |
| **libpsl** | 0.21.5 | uploaded |  | Autotools | 0 | - | [📄](archives/l/libpsl/0.21.5/) |
| **libqb3** | 1.3.2 | uploaded |  | unknown | 0 | - | [📄](archives/l/libqb3/1.3.2/) |
| **libqrcodegen** | 1.8.0 | uploaded |  | unknown | 0 | - | [📄](archives/l/libqrcodegen/1.8.0/) |
| **libqrencode** | 4.1.1 | uploaded |  | Autotools | 0 | - | [📄](archives/l/libqrencode/4.1.1/) |
| **libraw** | 0.22.1 | uploaded |  | Autotools | 0 | - | [📄](archives/l/libraw/0.22.1/) |
| **libraw1394** | 2.1.2 | ✅ 已编译 |  |  | 2 | - | [📄](archives/l/libraw1394/2.1.2/) |
| **librdkafka** | 2.5.3 | uploaded |  | unknown | 0 | - | [📄](archives/l/librdkafka/2.5.3/) |
| **libreplaygain** | r475 | success |  | CMake | 1 | - | [📄](archives/l/libreplaygain/r475/) |
| **libressl** | 4.3.1 | uploaded |  | CMake | 0 | - | [📄](archives/l/libressl/4.3.1/) |
| **libsamplerate** | 0.2.2 | ✅ 已发布 |  |  | - | - | [📄](archives/l/libsamplerate/0.2.2/) |
| **libshout** | 2.4.6 | ✅ 已编译 |  | Autotools | 3 | - | [📄](archives/l/libshout/2.4.6/) |
| **libsixel** | 1.10.5 | uploaded |  | unknown | 0 | - | [📄](archives/l/libsixel/1.10.5/) |
| **libsmi** | 0.5.0 | success |  | Autotools | 26 | - | [📄](archives/l/libsmi/0.5.0/) |
| **libsoup** | 2.74.3 | success |  | Meson | 1 | libpsl 0.21.1,glib 2.88.0,libxml2 2.15.3,sqlite3 3.49.1,brotli 1.1.0 | [📄](archives/l/libsoup/2.74.3/) |
| **libsoxr** | 0.1.3 | 📦 已归档 |  |  | - | - | [📄](archives/l/libsoxr/0.1.3/) |
| **libspng** | 0.7.4 | unknown |  | CMake | - | zlib >= 1.2.0 | [📄](archives/l/libspng/0.7.4/) |
| **libssh** | 0.11.4 | uploaded |  | Autotools | 0 | - | [📄](archives/l/libssh/0.11.4/) |
| **libssh2** | 1.11.0 | uploaded |  | Autotools | 0 | - | [📄](archives/l/libssh2/1.11.0/) |
| **libtap** | 0.1.0 | ✅ 已编译 |  |  | - | - | [📄](archives/l/libtap/0.1.0/) |
| **libtasn1** | 4.21.0 | uploaded |  | Autotools | 0 | - | [📄](archives/l/libtasn1/4.21.0/) |
| **libtextstyle** | 0.8 | partial |  |  | - | ncurses | [📄](archives/l/libtextstyle/0.8/) |
| **libtiff** | 4.6.0 | uploaded |  | Autotools | 0 | - | [📄](archives/l/libtiff/4.6.0/) |
| **libtommath** | 1.3.0 | unknown |  | Makefile | - | [] | [📄](archives/l/libtommath/1.3.0/) |
| **libtool** | 2.4.7 | verified |  | Autotools | 0 | autoconf,automake,m4 | [📄](archives/l/libtool/2.4.7/) |
| **libunistring** | 1.0 | uploaded |  | unknown | 0 | - | [📄](archives/l/libunistring/1.0/) |
| **libusb** | 1.0.27 | uploaded |  | unknown | 0 | - | [📄](archives/l/libusb/1.0.27/) |
| **libusrsctp** | 0.9.5.0 | success |  | CMake | 5 | - | [📄](archives/l/libusrsctp/0.9.5.0/) |
| **libuv** | 1.52.1 | uploaded |  | Autotools | 0 | - | [📄](archives/l/libuv/1.52.1/) |
| **libwebp** | 1.3.2 | uploaded |  | Autotools | 0 | - | [📄](archives/l/libwebp/1.3.2/) |
| **libxau** | 1.0.11 | ✅ 已发布 |  |  | - | - | [📄](archives/l/libxau/1.0.11/) |
| **libxcb** | 1.16 | ✅ 已发布 |  |  | - | - | [📄](archives/l/libxcb/1.16/) |
| **libxcvt** | 0.1.3 | success |  | Meson | - | - | [📄](archives/l/libxcvt/0.1.3/) |
| **libxdmcp** | 1.1.4 | ✅ 已发布 |  |  | - | - | [📄](archives/l/libxdmcp/1.1.4/) |
| **libxfce4util** | 4.18.2 | ✅ 已发布 |  |  | 0 | - | [📄](archives/l/libxfce4util/4.18.2/) |
| **libxml2** | 2.15.3 | ✅ 已编译 |  |  | 6 | - | [📄](archives/l/libxml2/2.15.3/) |
| **libxrender** | 0.9.12 | ✅ 已发布 |  | Autotools | 3 | - | [📄](archives/l/libxrender/0.9.12/) |
| **libxshmfence** | 1.3.3 | success |  | Autotools | 2 | - | [📄](archives/l/libxshmfence/1.3.3/) |
| **libzip** | 1.10.1、1.11.4 | ✅ 已编译 |  |  | - | - | [📄](archives/l/libzip/1.11.4/) |
| **llhttp** | 9.3.1 | ✅ 已发布 |  |  | - | - | [📄](archives/l/llhttp/9.3.1/) |
| **lm-sensors** | 3.6.0 | uploaded |  | Makefile | 0 | - | [📄](archives/l/lm-sensors/3.6.0/) |
| **lmdb** | 0.9.33、0.9.35 | uploaded |  | Autotools | 0 | - | [📄](archives/l/lmdb/0.9.35/) |
| **lolcat** | 100.0.1 | ✅ 已发布 |  |  | - | - | [📄](archives/l/lolcat/100.0.1/) |
| **lshw** | B.02.20 | ✅ 已编译 |  |  | 2 | - | [📄](archives/l/lshw/B.02.20/) |
| **lsof** | 4.99.0 | ✅ 已编译 |  |  | 2 | - | [📄](archives/l/lsof/4.99.0/) |
| **lua** | 5.4.7 | ✅ 已发布 |  | Makefile | - | - | [📄](archives/l/lua/5.4.7/) |
| **lz4** | 1.10.0 | uploaded |  | unknown | 0 | - | [📄](archives/l/lz4/1.10.0/) |
| **lz4jsoncat** | v2 | uploaded |  | Makefile | 0 | - | [📄](archives/l/lz4jsoncat/v2/) |
| **lzbench** | 2.2 | uploaded |  | Makefile | 0 | - | [📄](archives/l/lzbench/2.2/) |
| **lzip** | 1.25、1.26 | uploaded |  | Autotools | 0 | - | [📄](archives/l/lzip/1.26/) |
| **lzlib** | 1.15、1.9 | uploaded |  | Autotools | 0 | - | [📄](archives/l/lzlib/1.9/) |
| **lzma** | 5.6.2 | uploaded |  | Autotools | 0 | - | [📄](archives/l/lzma/5.6.2/) |
| **lzo** | 2.10 | uploaded |  | Autotools | 0 | - | [📄](archives/l/lzo/2.10/) |
| **lzop** | 1.04 | uploaded |  | Autotools | 0 | - | [📄](archives/l/lzop/1.04/) |
| **m4** | 1.4.19 | uploaded |  | Autotools | 0 | - | [📄](archives/m/m4/1.4.19/) |
| **make** | 4.4.1 | ✅ 已编译 |  | Autotools | 2 | [] | [📄](archives/m/make/4.4.1/) |
| **man-db** | 2.13.1 | verified |  | Autotools | 0 | - | [📄](archives/m/man-db/2.13.1/) |
| **mandoc** | 1.14.6 | success |  | custom-configure | 1 | - | [📄](archives/m/mandoc/1.14.6/) |
| **masscan** | 1.3.9 | ✅ 已编译 |  | Makefile | 6 | - | [📄](archives/m/masscan/1.3.9/) |
| **matio** | 1.5.23 | ✅ 已编译 |  |  | 2 | - | [📄](archives/m/matio/1.5.23/) |
| **mawk** | 1.3.4-20260302 | ✅ 已编译 |  |  | 4 | - | [📄](archives/m/mawk/1.3.4-20260302/) |
| **mbedtls** | 2.28.8、3.6.6、4.1.0、3.6.0 | ✅ 已编译 |  | CMake | - | - | [📄](archives/m/mbedtls/3.6.0/) |
| **mdbtools** | 1.0.1 | ✅ 已发布 |  | Autotools | 2 | glib,bison,flex | [📄](archives/m/mdbtools/1.0.1/) |
| **mecab** | 0.996 | partial |  | Autotools | 3 | libc++ (替换 libstdc++) | [📄](archives/m/mecab/0.996/) |
| **meson** | 1.11.0、1.11.1、1.5.1 | ✅ 已编译 |  |  | - | - | [📄](archives/m/meson/1.5.1/) |
| **metis** | 5.1.0 | success |  | CMake | - | - | [📄](archives/m/metis/5.1.0/) |
| **micropython** | 1.27.0 | success |  | custom | - | - | [📄](archives/m/micropython/1.27.0/) |
| **minicom** | 2.10 | success |  | Autotools | 11 | libtinfo.so.6,make 4.4.1,autoconf 2.72,automake 1.16.5 | [📄](archives/m/minicom/2.10/) |
| **miniupnpc** | 2.3.3 | success |  | Makefile | - | - | [📄](archives/m/miniupnpc/2.3.3/) |
| **minizip** | 1.3.1 | uploaded |  | unknown | 0 | - | [📄](archives/m/minizip/1.3.1/) |
| **minizip-ng** | 4.1.1 | uploaded |  | unknown | 0 | - | [📄](archives/m/minizip-ng/4.1.1/) |
| **mongoc-driver** | 1.29.0 | partial |  | cmake-ninja | - | openssl 1.1.1w,zlib 1.3.1 (bundled),zstd 1.5.7,snappy | [📄](archives/m/mongoc-driver/1.29.0/) |
| **mosquitto** | 2.0.18 | uploaded |  | Autotools | 0 | - | [📄](archives/m/mosquitto/2.0.18/) |
| **mp3gain** | 1.6.2 | ✅ 已编译 |  | Makefile | 1 | - | [📄](archives/m/mp3gain/1.6.2/) |
| **mp3splt** | 2.6.2 | ✅ 已编译 |  | Autotools | 6 | - | [📄](archives/m/mp3splt/2.6.2/) |
| **mpfr** | 4.2.1 | uploaded |  | unknown | 0 | - | [📄](archives/m/mpfr/4.2.1/) |
| **mpg123** | 1.33.5 | ✅ 已发布 |  | Autotools | 3 | - | [📄](archives/m/mpg123/1.33.5/) |
| **mujs** | 1.3.9 | success |  | Makefile | - | - | [📄](archives/m/mujs/1.3.9/) |
| **mupdf-tools** | 1.27.2 | ✅ 已编译 |  |  | - | - | [📄](archives/m/mupdf-tools/1.27.2/) |
| **musl-fts** | 1.2.7 | uploaded |  | unknown | 0 | - | [📄](archives/m/musl-fts/1.2.7/) |
| **musl-obstack** | 1.2.3 | uploaded |  | unknown | 0 | - | [📄](archives/m/musl-obstack/1.2.3/) |
| **nano** | 9.0 | ✅ 已发布 |  |  | 0 | - | [📄](archives/n/nano/9.0/) |
| **ncurses** | 6.4 | verified |  | Autotools | 0 | - | [📄](archives/n/ncurses/6.4/) |
| **netlistsvg** | 1.0.2 | ✅ 已编译 |  | custom | 11 | - | [📄](archives/n/netlistsvg/1.0.2/) |
| **nettle** | 3.10.2、3.10 | partial |  | Autotools | 47 | - | [📄](archives/n/nettle/3.10/) |
| **nghttp2** | 1.69.0 | ✅ 已编译 |  |  | 1 | - | [📄](archives/n/nghttp2/1.69.0/) |
| **nghttp3** | 1.15.0 | success |  | CMake | 1 | [] | [📄](archives/n/nghttp3/1.15.0/) |
| **nginx** | 1.26.2 | partial |  | Autotools | - | - | [📄](archives/n/nginx/1.26.2/) |
| **ngtcp2** | 1.22.1 | ✅ 已发布 |  |  | - | - | [📄](archives/n/ngtcp2/1.22.1/) |
| **nim** | 2.2.8 | success |  | custom | - | - | [📄](archives/n/nim/2.2.8/) |
| **ninja** | 1.12.1 | uploaded |  | Makefile | 0 | - | [📄](archives/n/ninja/1.12.1/) |
| **nlohmann-json** | 3.11.2 | uploaded |  | CMake | 0 | - | [📄](archives/n/nlohmann-json/3.11.2/) |
| **nmap** | 7.95、7.97 | ✅ 已编译 |  | Autotools | 2 | - | [📄](archives/n/nmap/7.97/) |
| **nnn** | 5.0 | partial |  | Makefile | - | name: ncursesw,name: readline,name: musl-fts | [📄](archives/n/nnn/5.0/) |
| **notcurses** | 3.0.17 | uploaded |  | unknown | 0 | ncursesw-6.4,libunistring,libdeflate | [📄](archives/n/notcurses/3.0.17/) |
| **npth** | 1.8 | uploaded |  | Autotools | 0 | name: pthread | [📄](archives/n/npth/1.8/) |
| **numactl** | 2.0.18 | partial |  | Autotools | - | - | [📄](archives/n/numactl/2.0.18/) |
| **nyancat** | 1.5.1 | ✅ 已编译 |  |  | 1 | - | [📄](archives/n/nyancat/1.5.1/) |
| **olm** | 3.2.16 | uploaded |  | unknown | 0 | - | [📄](archives/o/olm/3.2.16/) |
| **oniguruma** | 6.9.10 | ✅ 已发布 |  | CMake | 2 | - | [📄](archives/o/oniguruma/6.9.10/) |
| **openal-soft** | 1.24.3 | partial |  | Autotools | - | - | [📄](archives/o/openal-soft/1.24.3/) |
| **openblas** | 0.3.33 | partial |  | Autotools | - | - | [📄](archives/o/openblas/0.3.33/) |
| **openexr** | 2.2.1 | ✅ 已编译 |  | Autotools | 2 | - | [📄](archives/o/openexr/2.2.1/) |
| **openjpeg** | 2.5.0 | uploaded |  | unknown | 0 | - | [📄](archives/o/openjpeg/2.5.0/) |
| **opensc** | 0.27.1 | partial |  | Autotools | 2 | - | [📄](archives/o/opensc/0.27.1/) |
| **openssh** | 10.0p1 | partial |  | Autotools | 2 | - | [📄](archives/o/openssh/10.0p1/) |
| **openssl** | 1.1.1w、3.5.6 | partial | 🟢 高 | openssl-perl | 0 | - | [📄](archives/o/openssl/3.5.6/) |
| **optipng** | 7.9.1 | uploaded |  | unknown | 0 | - | [📄](archives/o/optipng/7.9.1/) |
| **opus** | 1.4 | ✅ 已发布 |  | Meson | 1 | - | [📄](archives/o/opus/1.4/) |
| **osslsigncode** | 2.13 | uploaded |  | unknown | 0 | - | [📄](archives/o/osslsigncode/2.13/) |
| **oxipng** | v10.1.1 | ✅ 已编译 |  |  | - | - | [📄](archives/o/oxipng/v10.1.1/) |
| **p11-kit** | 0.25.5 | uploaded |  | Autotools | 0 | - | [📄](archives/p/p11-kit/0.25.5/) |
| **p7zip** | 17.05 | uploaded |  | unknown | 0 | - | [📄](archives/p/p7zip/17.05/) |
| **paho-mqtt-c** | 1.3.13 | partial |  | CMake | - | openssl (1.1.1w, 预编译包已安装) | [📄](archives/p/paho-mqtt-c/1.3.13/) |
| **pango** | 1.50.14 | ✅ 已发布 |  | Meson | - | - | [📄](archives/p/pango/1.50.14/) |
| **patch** | 2.7.6 | verified |  | Autotools | 0 | - | [📄](archives/p/patch/2.7.6/) |
| **pax** | 20240817 | uploaded |  | unknown | 0 | - | [📄](archives/p/pax/20240817/) |
| **pbzip2** | 1.1.13 | uploaded |  | Makefile | 0 | - | [📄](archives/p/pbzip2/1.1.13/) |
| **pcaudiolib** | 1.3 | ✅ 已编译 |  | Autotools | 1 | - | [📄](archives/p/pcaudiolib/1.3/) |
| **pciutils** | 3.13.0 | uploaded |  | Makefile | 0 | - | [📄](archives/p/pciutils/3.13.0/) |
| **pcre** | 8.45 | uploaded |  | Autotools | 0 | - | [📄](archives/p/pcre/8.45/) |
| **pcre2** | 10.40 | uploaded |  | Autotools | 0 | [] | [📄](archives/p/pcre2/10.40/) |
| **pdftohtml** | 0.14.6 | ✅ 已发布 |  |  | - | - | [📄](archives/p/pdftohtml/0.14.6/) |
| **perf** | 6.6.9 | ✅ 已编译 |  |  | - | - | [📄](archives/p/perf/6.6.9/) |
| **perl** | 5.42.2 | uploaded |  | Autotools | 0 | - | [📄](archives/p/perl/5.42.2/) |
| **physfs** | 3.2.0 | uploaded |  | unknown | 0 | - | [📄](archives/p/physfs/3.2.0/) |
| **pigz** | 2.8 | uploaded |  | Makefile | 0 | zlib | [📄](archives/p/pigz/2.8/) |
| **pixman** | 0.46.4 | uploaded |  | Autotools | 0 | [] | [📄](archives/p/pixman/0.46.4/) |
| **pkg-config** | 0.29.2 | uploaded |  | Makefile | 0 | - | [📄](archives/p/pkg-config/0.29.2/) |
| **plzip** | 1.13 | uploaded |  | Makefile | 0 | lzlib | [📄](archives/p/plzip/1.13/) |
| **polipo** | 1.1.1 | ✅ 已发布 |  | Makefile | - | - | [📄](archives/p/polipo/1.1.1/) |
| **popt** | 1.16 | uploaded |  | unknown | 0 | - | [📄](archives/p/popt/1.16/) |
| **portmidi** | 2.0.8 | ✅ 已编译 |  |  | 1 | - | [📄](archives/p/portmidi/2.0.8/) |
| **protobuf** | 34.1 | uploaded |  | CMake | 0 | abseil-cpp (20260107.1) | [📄](archives/p/protobuf/34.1/) |
| **proxychains-ng** | 4.16 | ✅ 已编译 |  | Autotools | - | - | [📄](archives/p/proxychains-ng/4.16/) |
| **psmisc** | 23.6 | partial |  | Autotools | - | ncurses | [📄](archives/p/psmisc/23.6/) |
| **pwgen** | 2.08 | partial |  | Autotools | - | - | [📄](archives/p/pwgen/2.08/) |
| **python** | 3.12.9、3.9.0、3.9.25 | verified |  | Autotools | 0 | - | [📄](archives/p/python/3.9.25/) |
| **qt5-qtbase** | 5.15.2 | ✅ 已发布 |  |  | 0 | - | [📄](archives/q/qt5-qtbase/5.15.2/) |
| **qtdeclarative** | 6.11.1 | ✅ 已发布 |  |  | 0 | - | [📄](archives/q/qtdeclarative/6.11.1/) |
| **qtimageformats** | 6.11.1 | ✅ 已编译 |  |  | 0 | - | [📄](archives/q/qtimageformats/6.11.1/) |
| **qtsvg** | 6.11.1 | ✅ 已编译 |  |  | 0 | - | [📄](archives/q/qtsvg/6.11.1/) |
| **rabbitmq-c** | 0.13.0、0.15.0 | ✅ 已编译 |  | CMake | - | openssl/1.1.1w | [📄](archives/r/rabbitmq-c/0.15.0/) |
| **ragel** | 6.10 | uploaded |  | unknown | 0 | - | [📄](archives/r/ragel/6.10/) |
| **rapidjson** | 1.1.0 | uploaded |  | CMake | 0 | - | [📄](archives/r/rapidjson/1.1.0/) |
| **rclone** | 1.72.1 | ✅ 已发布 |  |  | - | - | [📄](archives/r/rclone/1.72.1/) |
| **re2** | 2024-04-01、2024-07-01 | partial |  | unknown | - | - | [📄](archives/r/re2/2024-07-01/) |
| **re2c** | 4.3.1 | uploaded |  | unknown | 0 | - | [📄](archives/r/re2c/4.3.1/) |
| **readline** | 8.2 | verified |  | Autotools | 0 | name: ncurses | [📄](archives/r/readline/8.2/) |
| **readosm** | 1.1.0a | ✅ 已编译 |  |  | 1 | - | [📄](archives/r/readosm/1.1.0a/) |
| **redis** | 7.4.2、8.6.0 | ✅ 已编译 |  | Makefile | 4 | - | [📄](archives/r/redis/8.6.0/) |
| **rhash** | 1.4.4 | uploaded |  | unknown | 0 | openssl (optimized algorithms),gettext (internationalization) - disabled due to compatibility | [📄](archives/r/rhash/1.4.4/) |
| **rmpc** | 0.11.0 | ✅ 已编译 |  |  | - | - | [📄](archives/r/rmpc/0.11.0/) |
| **robin-map** | 1.4.1 | uploaded |  | CMake | 0 | - | [📄](archives/r/robin-map/1.4.1/) |
| **rocksdb** | 9.10.0 | uploaded |  | CMake | 0 | - | [📄](archives/r/rocksdb/9.10.0/) |
| **rsync** | 3.3.0 | verified |  | Autotools | 0 | - | [📄](archives/r/rsync/3.3.0/) |
| **ruby-build** | 20260512 | ✅ 已发布 |  | Script | - | - | [📄](archives/r/ruby-build/20260512/) |
| **s2n-tls** | 1.7.2 | uploaded |  | unknown | 0 | libcrypto (OpenSSL or AWS libcrypto) | [📄](archives/s/s2n-tls/1.7.2/) |
| **samurai** | 1.2 | uploaded |  | unknown | 0 | - | [📄](archives/s/samurai/1.2/) |
| **scdoc** | 1.11.3 | partial |  | Autotools | - | - | [📄](archives/s/scdoc/1.11.3/) |
| **scikit-image** | 0.26.0 | ✅ 已编译 |  | pip | - | - | [📄](archives/s/scikit-image/0.26.0/) |
| **scintilla** | 5.6.1 | device_testing |  |  | 10 | - | [📄](archives/s/scintilla/5.6.1/) |
| **scons** | 4.10.0 | uploaded |  | custom | 0 | - | [📄](archives/s/scons/4.10.0/) |
| **screen** | 5.0.0 | uploaded |  | Makefile | 0 | - | [📄](archives/s/screen/5.0.0/) |
| **sed** | 4.10、4.9 | verified |  | Autotools | 0 | - | [📄](archives/s/sed/4.9/) |
| **sevenzip** | 26.00 | success |  | custom-makefile | 1 | - | [📄](archives/s/sevenzip/26.00/) |
| **shorewall** | 5.2.8-r1 | success |  | shell | 1 | - | [📄](archives/s/shorewall/5.2.8-r1/) |
| **simdjson** | 4.6.3 | uploaded |  | CMake | 0 | - | [📄](archives/s/simdjson/4.6.3/) |
| **simple-scan** | 50.0 | ✅ 已发布 |  |  | - | - | [📄](archives/s/simple-scan/50.0/) |
| **skopeo** | v1.22.2 | ❌ 编译失败 |  |  | - | - | [📄](archives/s/skopeo/v1.22.2/) |
| **smartmontools** | 7.4 | uploaded |  | Makefile | 0 | - | [📄](archives/s/smartmontools/7.4/) |
| **snappy** | 1.2.2 | uploaded |  | CMake | 0 | - | [📄](archives/s/snappy/1.2.2/) |
| **socat** | 1.7.4.4、1.8.0.3 | partial |  | Autotools | 1 | - | [📄](archives/s/socat/1.8.0.3/) |
| **sparsehash** | 2.0.4 | uploaded |  | CMake | 0 | - | [📄](archives/s/sparsehash/2.0.4/) |
| **spdlog** | 1.17.0 | uploaded |  | unknown | 0 | - | [📄](archives/s/spdlog/1.17.0/) |
| **speex** | 1.2.1 | uploaded |  | Autotools | 0 | - | [📄](archives/s/speex/1.2.1/) |
| **speexdsp** | 1.2.1 | uploaded |  | Autotools | 0 | - | [📄](archives/s/speexdsp/1.2.1/) |
| **spirv-headers** | vulkan-sdk-1.3.290.0 | ✅ 已编译 |  | CMake | - | - | [📄](archives/s/spirv-headers/vulkan-sdk-1.3.290.0/) |
| **spirv-tools** | vulkan-sdk-1.3.290.0 | ✅ 已编译 |  |  | 1 | - | [📄](archives/s/spirv-tools/vulkan-sdk-1.3.290.0/) |
| **sqlite3** | 3.49.1 | uploaded |  | Autotools | 0 | - | [📄](archives/s/sqlite3/3.49.1/) |
| **squashfs-tools** | 4.6.1 | uploaded |  | unknown | 0 | zlib | [📄](archives/s/squashfs-tools/4.6.1/) |
| **sshpass** | 1.10 | success |  | Autotools | 2 | [] | [📄](archives/s/sshpass/1.10/) |
| **strace** | 6.19、6.10 | partial |  | Autotools | 67 | - | [📄](archives/s/strace/6.10/) |
| **stunnel** | 5.73 | partial |  | Autotools | - | - | [📄](archives/s/stunnel/5.73/) |
| **svg2pdf** | 0.13.0 | ❌ 编译失败 |  |  | - | - | [📄](archives/s/svg2pdf/0.13.0/) |
| **svg2png** | 4.1.1 | ❌ 编译失败 |  |  | - | - | [📄](archives/s/svg2png/4.1.1/) |
| **swig** | 4.4.0 | uploaded |  | unknown | 0 | - | [📄](archives/s/swig/4.4.0/) |
| **syft** | v1.44.0 | ❌ 编译失败 |  |  | - | - | [📄](archives/s/syft/v1.44.0/) |
| **sysfsutils** | 2.1.0 | uploaded |  | Makefile | 0 | - | [📄](archives/s/sysfsutils/2.1.0/) |
| **ta-lib** | 0.6.4 | success |  | Autotools | 3 | - | [📄](archives/t/ta-lib/0.6.4/) |
| **tailscale** | 1.90.9 | ✅ 已发布 |  |  | - | - | [📄](archives/t/tailscale/1.90.9/) |
| **talloc** | 2.4.4 | ✅ 已编译 |  | waf | 1 | [] | [📄](archives/t/talloc/2.4.4/) |
| **tar** | 1.35 | verified |  | Autotools | 0 | - | [📄](archives/t/tar/1.35/) |
| **tcping** | 2.1.0 | ✅ 已编译 |  | Makefile | 1 | - | [📄](archives/t/tcping/2.1.0/) |
| **tenv** | 4.12.2 | ✅ 已发布 |  |  | - | - | [📄](archives/t/tenv/4.12.2/) |
| **testssl** | 3.2.3 | uploaded |  | unknown | 0 | - | [📄](archives/t/testssl/3.2.3/) |
| **texinfo** | 7.3 | verified |  | Autotools | 0 | - | [📄](archives/t/texinfo/7.3/) |
| **tiff2png** | 0.0.1 | ✅ 已编译 |  | custom | - | - | [📄](archives/t/tiff2png/0.0.1/) |
| **tinyssh** | 20260401 | uploaded |  | unknown | 0 | - | [📄](archives/t/tinyssh/20260401/) |
| **tmux** | 3.4 | ✅ 已发布 |  |  | 0 | - | [📄](archives/t/tmux/3.4/) |
| **toml11** | 4.4.0 | ✅ 已编译 |  | CMake | - | - | [📄](archives/t/toml11/4.4.0/) |
| **tomlplusplus** | 3.4.0 | uploaded |  | CMake | 0 | - | [📄](archives/t/tomlplusplus/3.4.0/) |
| **traceroute** | 2.1.6 | ✅ 已编译 |  | Makefile | 1 | - | [📄](archives/t/traceroute/2.1.6/) |
| **tree** | 2.1.3 | uploaded |  | Makefile | 0 | - | [📄](archives/t/tree/2.1.3/) |
| **triehash** | 0.3 | uploaded |  | CMake | 0 | - | [📄](archives/t/triehash/0.3/) |
| **ttaenc** | 3.4.1 | uploaded |  | unknown | 0 | - | [📄](archives/t/ttaenc/3.4.1/) |
| **ttygif** | 1.4.0 | ✅ 已编译 |  | Makefile | 3 | - | [📄](archives/t/ttygif/1.4.0/) |
| **ucl** | 1.03 | uploaded |  | unknown | 0 | - | [📄](archives/u/ucl/1.03/) |
| **udpping** | 0.0.2 | ✅ 已编译 |  | CMake | 2 | - | [📄](archives/u/udpping/0.0.2/) |
| **unarj** | 2.63a | uploaded |  | unknown | 0 | - | [📄](archives/u/unarj/2.63a/) |
| **unrar** | 6.2.4 | compiling |  | Makefile | 2 | - | [📄](archives/u/unrar/6.2.4/) |
| **upx** | 5.1.1 | success |  | CMake | - | - | [📄](archives/u/upx/5.1.1/) |
| **usbutils** | 017 | uploaded |  | Makefile | 0 | - | [📄](archives/u/usbutils/017/) |
| **userspace-rcu** | 0.15.6 | success |  | Autotools | 1 | - | [📄](archives/u/userspace-rcu/0.15.6/) |
| **utf8proc** | 2.11.3、2.9.0 | uploaded |  | CMake | 0 | - | [📄](archives/u/utf8proc/2.9.0/) |
| **uthash** | 2.3.0 | uploaded |  | CMake | 0 | - | [📄](archives/u/uthash/2.3.0/) |
| **vala** | 0.56.18 | uploaded |  | Meson | 0 | - | [📄](archives/v/vala/0.56.18/) |
| **verilator** | 5.046 | ✅ 已编译 |  | Autotools | 3 | - | [📄](archives/v/verilator/5.046/) |
| **vulkan-headers** | 1.3.295 | partial |  | Autotools | 1 | - | [📄](archives/v/vulkan-headers/1.3.295/) |
| **waf** | 2.1.9 | uploaded |  | custom | 0 | - | [📄](archives/w/waf/2.1.9/) |
| **watchdog** | 5.16 | success |  | Autotools | - | - | [📄](archives/w/watchdog/5.16/) |
| **wavpack** | 5.7.0、5.8.1 | uploaded |  | unknown | 0 | - | [📄](archives/w/wavpack/5.8.1/) |
| **wayland** | 1.23.1 | ✅ 已发布 |  |  | 0 | - | [📄](archives/w/wayland/1.23.1/) |
| **wayland-protocols** | 1.36 | ✅ 已发布 |  |  | 0 | - | [📄](archives/w/wayland-protocols/1.36/) |
| **webkit2png** | 0.7 | ❌ 编译失败 |  |  | - | - | [📄](archives/w/webkit2png/0.7/) |
| **wget** | 1.19.1 | verified |  | Autotools | 0 | - | [📄](archives/w/wget/1.19.1/) |
| **which** | 2.21 | partial |  | Autotools | 2 | - | [📄](archives/w/which/2.21/) |
| **wimlib** | 1.14.5 | uploaded |  | unknown | 0 | - | [📄](archives/w/wimlib/1.14.5/) |
| **wireguard-tools** | 1.0.20250521 | ✅ 已发布 |  | Makefile | 1 | - | [📄](archives/w/wireguard-tools/1.0.20250521/) |
| **xclip** | 0.13 | ✅ 已编译 |  |  | 2 | - | [📄](archives/x/xclip/0.13/) |
| **xmlrpc-c** | 1.64.03 | ✅ 已编译 |  | Autotools | 2 | - | [📄](archives/x/xmlrpc-c/1.64.03/) |
| **xmlstarlet** | 1.6.1 | ✅ 已编译 |  | Autotools | - | libxml2 >= 2.15.0,libxslt >= 1.1.42,clang,libxml2-dev,libxslt-dev | [📄](archives/x/xmlstarlet/1.6.1/) |
| **xorgproto** | 2024.1 | success |  | Meson | 2 | [] | [📄](archives/x/xorgproto/2024.1/) |
| **xterm** | 410 | ✅ 已编译 |  |  | 5 | - | [📄](archives/x/xterm/410/) |
| **xxd** | 9.1.0 | success |  | simple_makefile | - | - | [📄](archives/x/xxd/9.1.0/) |
| **xxhash** | 0.8.3、0.8.2 | partial |  | Autotools | - | - | [📄](archives/x/xxhash/0.8.2/) |
| **xz** | 5.6.2 | verified |  | Autotools | 0 | - | [📄](archives/x/xz/5.6.2/) |
| **yajl** | 2.1.0 | success |  | CMake | 2 | - | [📄](archives/y/yajl/2.1.0/) |
| **yaml-cpp** | 0.8.0 | uploaded |  | CMake | 0 | - | [📄](archives/y/yaml-cpp/0.8.0/) |
| **yyjson** | 0.12.0 | uploaded |  | CMake | 0 | - | [📄](archives/y/yyjson/0.12.0/) |
| **zeromq** | 4.3.5 | uploaded |  | unknown | 0 | - | [📄](archives/z/zeromq/4.3.5/) |
| **zip** | 3.0 | partial |  | Makefile | 1 | - | [📄](archives/z/zip/3.0/) |
| **zlib** | 1.3.1 | verified |  | CMake | 0 | - | [📄](archives/z/zlib/1.3.1/) |
| **zlib-ng** | 2.3.3 | uploaded |  | unknown | 0 | - | [📄](archives/z/zlib-ng/2.3.3/) |
| **zlib-ng-compat** | 2.3.3 | uploaded |  | unknown | 0 | - | [📄](archives/z/zlib-ng-compat/2.3.3/) |
| **zopfli** | 1.0.3 | uploaded |  | unknown | 0 | - | [📄](archives/z/zopfli/1.0.3/) |
| **zsh** | 5.9 | partial |  | Autotools | 430 | ncurses 6.4 | [📄](archives/z/zsh/5.9/) |
| **zstd** | 1.5.6、1.5.7 | ✅ 已发布 |  |  | - | - | [📄](archives/z/zstd/1.5.7/) |
| **zstd-jni** | 1.5.6-5 | uploaded |  | unknown | 0 | - | [📄](archives/z/zstd-jni/1.5.6-5/) |
| **zutils** | 1.15、1.16 | uploaded |  | unknown | 0 | - | [📄](archives/z/zutils/1.16/) |
| **zziplib** | 0.13.78 | uploaded |  | unknown | 0 | - | [📄](archives/z/zziplib/0.13.78/) |

---

*本文档由 `ohc summary` 从编译档案自动生成，请勿手动编辑。*

Copyright (c) 2024-2026 OpenHarmony PC Developer社区