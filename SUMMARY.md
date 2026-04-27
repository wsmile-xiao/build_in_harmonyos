# 鸿蒙平台开源软件编译兼容性总览

> 最后更新：2026-04-27
> 已收录软件：226 款 / 249 个版本

## 📊 总体统计

| 指标 | 数量 |
|------|------|
| 收录软件 | **226** 款 |
| 软件版本 | **249** 个 |
| ✅ 完全成功 | 113 |
| ⚠️ 部分成功 | 118 |
| ❌ 编译失败 | 0 |

| 构建系统 | 数量 |
|----------|------|
| Autotools | 163 |
| CMake | 43 |
| Makefile | 23 |
| Script | 2 |
| Meson | 2 |
| custom_configure | 2 |
| unknown | 2 |
| Custom Perl | 1 |
| manual  # 使用手动编译（autotools configure 失败） | 1 |
| cmake  # 实际使用 cmake，因为缺少 automake 无法生成 configure 脚本 | 1 |
| custom | 1 |
| python | 1 |
| manual | 1 |
| perl_script | 1 |
| make | 1 |

## 📋 软件兼容性一览

| 软件 | 版本 | 状态 | 兼容性 | 构建系统 | 补丁数 | 依赖 | 详情 |
|------|------|------|--------|----------|--------|------|------|
| **7zip** | 23.01、25.01 | ✅ 完全成功 |  | Autotools | - | - | [📄](archives/7/7zip/25.01/) |
| **abseil-cpp** | 20260107.1 | ✅ 完全成功 |  | Autotools | - | - | [📄](archives/a/abseil-cpp/20260107.1/) |
| **argon2** | 20190702 | ✅ 完全成功 |  | Makefile | - | [] | [📄](archives/a/argon2/20190702/) |
| **argp-standalone** | 1.5.0 | ⚠️ 部分成功 |  | Autotools | 1 | - | [📄](archives/a/argp-standalone/1.5.0/) |
| **autoconf-archive** | 2024.10.16 | ✅ 完全成功 |  | Autotools | 3 | - | [📄](archives/a/autoconf-archive/2024.10.16/) |
| **automake** | 1.16.5 | ✅ 完全成功 | 🟢 高 | Autotools | 1 | perl    # 运行时必需（纯 Perl 项目）,autoconf  # 配合 autoreconf 使用,gnu-make   # 构建 Autotools 项目时需要 | [📄](archives/a/automake/1.16.5/) |
| **avro-c** | 1.12.0 | ✅ 完全成功 |  | CMake | 2 | jansson 2.14 (required),zlib 1.3.1 (codec: deflate),snappy 1.1.10 (codec: snappy),liblzma 5.6.2 (codec: lzma) | [📄](archives/a/avro-c/1.12.0/) |
| **aws-c-cal** | 0.9.13 | ✅ 完全成功 |  | CMake | - | aws-c-common 0.12.6,aws-lc 1.72.0 (crypto backend) | [📄](archives/a/aws-c-cal/0.9.13/) |
| **aws-c-common** | 0.12.6 | ⚠️ 部分成功 |  | Autotools | - | - | [📄](archives/a/aws-c-common/0.12.6/) |
| **aws-c-compression** | 0.3.2 | ✅ 完全成功 |  | Autotools | - | - | [📄](archives/a/aws-c-compression/0.3.2/) |
| **aws-c-event-stream** | 0.7.0 | ⚠️ 部分成功 |  | Autotools | - | - | [📄](archives/a/aws-c-event-stream/0.7.0/) |
| **aws-c-http** | 0.10.14 | compiling |  | Autotools | - | - | [📄](archives/a/aws-c-http/0.10.14/) |
| **aws-c-io** | 0.26.3 | ⚠️ 部分成功 |  | CMake | - | aws-c-common 0.12.6,aws-c-cal 0.9.13,aws-c-compression 0.3.2 | [📄](archives/a/aws-c-io/0.26.3/) |
| **aws-c-mqtt** | 0.14.0、0.15.2 | ⚠️ 部分成功 |  | Autotools | - | - | [📄](archives/a/aws-c-mqtt/0.15.2/) |
| **aws-c-s3** | 0.12.2 | ⚠️ 部分成功 |  | Autotools | - | - | [📄](archives/a/aws-c-s3/0.12.2/) |
| **aws-c-sdkutils** | 0.2.4 | ⚠️ 部分成功 |  | Autotools | - | - | [📄](archives/a/aws-c-sdkutils/0.2.4/) |
| **aws-checksums** | 0.2.10 | compiling |  | Autotools | - | - | [📄](archives/a/aws-checksums/0.2.10/) |
| **aws-crt-cpp** | 0.38.5 | ⚠️ 部分成功 |  | Autotools | - | - | [📄](archives/a/aws-crt-cpp/0.38.5/) |
| **aws-lc** | 1.72.0 | ⚠️ 部分成功 |  | CMake | - | - | [📄](archives/a/aws-lc/1.72.0/) |
| **b3sum** | 1.8.4 | ✅ 完全成功 |  | CMake | 2 | - | [📄](archives/b/b3sum/1.8.4/) |
| **bash** | 5.3 | ✅ 完全成功 | 🟢 高 | Autotools | 1 | - | [📄](archives/b/bash/5.3/) |
| **bbe** | 0.2.2 | ⚠️ 部分成功 |  | Autotools | 2 | - | [📄](archives/b/bbe/0.2.2/) |
| **bcrypt** | 1.0 | ✅ 完全成功 |  | Autotools | 2 | - | [📄](archives/b/bcrypt/1.0/) |
| **bear** | 3.1.6 | ⚠️ 部分成功 |  | CMake | 2 | - | [📄](archives/b/bear/3.1.6/) |
| **bearssl** | 0.6 | ⚠️ 部分成功 |  | Autotools | - | - | [📄](archives/b/bearssl/0.6/) |
| **blosc** | 1.21.5、1.21.6 | ✅ 完全成功 |  | CMake | - | - | [📄](archives/b/blosc/1.21.6/) |
| **boxes** | 2.3.1 | ⚠️ 部分成功 |  | Makefile | 1 | libunistring-1.0,pcre2-10.40 | [📄](archives/b/boxes/2.3.1/) |
| **brotli** | 1.1.0、1.2.0 | ✅ 完全成功 |  | Autotools | - | - | [📄](archives/b/brotli/1.2.0/) |
| **bsd-compat-headers** | 0.7.2 | ✅ 完全成功 |  | Autotools | - | - | [📄](archives/b/bsd-compat-headers/0.7.2/) |
| **bzip2** | 1.0.8 | ✅ 完全成功 | 🟢 高 | Makefile | 0 | - | [📄](archives/b/bzip2/1.0.8/) |
| **bzip3** | 1.4.0、1.5.3 | ✅ 完全成功 |  | CMake | 3 | - | [📄](archives/b/bzip3/1.5.3/) |
| **c-ares** | 1.34.6 | ⚠️ 部分成功 |  | Autotools | 2 | - | [📄](archives/c/c-ares/1.34.6/) |
| **ccache** | 4.12.1 | ⚠️ 部分成功 |  | CMake | 2 | - | [📄](archives/c/ccache/4.12.1/) |
| **check** | 0.15.2 | ⚠️ 部分成功 |  | Autotools | 2 | - | [📄](archives/c/check/0.15.2/) |
| **ciso** | 1.0、1.0.0 | ✅ 完全成功 |  | Makefile | 1 | - | [📄](archives/c/ciso/1.0.0/) |
| **cjson** | 1.7.18 | ⚠️ 部分成功 |  | Autotools | 1 | - | [📄](archives/c/cjson/1.7.18/) |
| **cmocka** | 2.0.2 | ⚠️ 部分成功 |  | Autotools | 0 | - | [📄](archives/c/cmocka/2.0.2/) |
| **cmph** | 2.0 | compiling |  | Autotools | - | - | [📄](archives/c/cmph/2.0/) |
| **coreutils** | 9.10 | ⚠️ 部分成功 | 🟡 中 | Autotools | 2 | []  # 无额外依赖 | [📄](archives/c/coreutils/9.10/) |
| **cpptoml** | v0.1.1 | ⚠️ 部分成功 |  | Autotools | 0 | - | [📄](archives/c/cpptoml/v0.1.1/) |
| **cramfs** | 1.1 | ✅ 完全成功 |  | Makefile | 3 | - | [📄](archives/c/cramfs/1.1/) |
| **croaring** | 4.6.1 | ✅ 完全成功 |  | CMake | - | - | [📄](archives/c/croaring/4.6.1/) |
| **cryptopp** | 8.9.0 | ⚠️ 部分成功 |  | Autotools | - | - | [📄](archives/c/cryptopp/8.9.0/) |
| **cunit** | 2.1-3 | ✅ 完全成功 |  | manual  # 使用手动编译（autotools configure 失败） | 3 | - | [📄](archives/c/cunit/2.1-3/) |
| **dar** | 2.8.1 | ✅ 完全成功 |  | Autotools | 15 | - | [📄](archives/d/dar/2.8.1/) |
| **distcc** | 3.4 | ⚠️ 部分成功 |  | Autotools | 5 | - | [📄](archives/d/distcc/3.4/) |
| **dmg2img** | 1.6.7 | ✅ 完全成功 |  | Makefile | 1 | zlib >= 1.3.1,bzip2 >= 1.0.8,openssl >= 1.1.1w | [📄](archives/d/dmg2img/1.6.7/) |
| **doctest** | 2.5.2 | ✅ 完全成功 |  | Autotools | - | - | [📄](archives/d/doctest/2.5.2/) |
| **dos2unix** | 7.5.4 | ✅ 完全成功 | 🟢 高 | Makefile | 1 | name: gettext | [📄](archives/d/dos2unix/7.5.4/) |
| **eigen** | 3.4.0 | ⚠️ 部分成功 |  | Autotools | 0 | - | [📄](archives/e/eigen/3.4.0/) |
| **expat** | 2.8.0 | compiling |  | Autotools | 0 | - | [📄](archives/e/expat/2.8.0/) |
| **farbfeld** | 4 | ⚠️ 部分成功 |  | Makefile | 1 | - | [📄](archives/f/farbfeld/4/) |
| **fastjar** | 0.98 | ✅ 完全成功 |  | Autotools | 4 | - | [📄](archives/f/fastjar/0.98/) |
| **fcrackzip** | 1.0 | ⚠️ 部分成功 |  | Autotools | 3 | - | [📄](archives/f/fcrackzip/1.0/) |
| **fftw** | 3.3.10 | ⚠️ 部分成功 |  | CMake | 2 | - | [📄](archives/f/fftw/3.3.10/) |
| **file** | 5.45 | ✅ 完全成功 | 🟢 高 | Autotools | 0 | - | [📄](archives/f/file/5.45/) |
| **flac** | 1.4.3 | ✅ 完全成功 |  | Autotools | 2 | - | [📄](archives/f/flac/1.4.3/) |
| **fribidi** | 1.0.16 | compiling |  | Autotools | 0 | - | [📄](archives/f/fribidi/1.0.16/) |
| **ftxui** | 6.1.9 | ✅ 完全成功 |  | CMake | - | - | [📄](archives/f/ftxui/6.1.9/) |
| **gawk** | 5.3.0 | ✅ 完全成功 | 🟢 高 | Autotools | 1 | - | [📄](archives/g/gawk/5.3.0/) |
| **gdbm** | 1.23 | ✅ 完全成功 | 🟢 高 | Autotools | 2 | - | [📄](archives/g/gdbm/1.23/) |
| **giflib** | 5.2.2 | ⚠️ 部分成功 |  | Autotools | 0 | - | [📄](archives/g/giflib/5.2.2/) |
| **glib** | 2.88.0 | ⚠️ 部分成功 |  | Meson | 4 | - | [📄](archives/g/glib/2.88.0/) |
| **glm** | 0.9.9.8 | ⚠️ 部分成功 |  | CMake | 1 | - | [📄](archives/g/glm/0.9.9.8/) |
| **gmp** | 6.3.0 | compiling |  | Autotools | 0 | - | [📄](archives/g/gmp/6.3.0/) |
| **gmssl** | 3.1.1 | ⚠️ 部分成功 |  | CMake | - | - | [📄](archives/g/gmssl/3.1.1/) |
| **gsl** | 2.8 | compiling |  | Autotools | 0 | - | [📄](archives/g/gsl/2.8/) |
| **gsm** | 1.0.22、1.0.23 | ✅ 完全成功 |  | Makefile | 1 | - | [📄](archives/g/gsm/1.0.23/) |
| **gzip** | 1.13 | ✅ 完全成功 | 🟢 高 | Autotools | 0 | - | [📄](archives/g/gzip/1.13/) |
| **hdrhistogram** | 0.11.9 | unknown |  |  | 2 | pthread (libpthread),rt (librt - clock_gettime),m (libm - math functions),zlib (disabled due to HDR_LOG_REQUIRED=OFF) | [📄](archives/h/hdrhistogram/0.11.9/) |
| **help2man** | 1.49.3 | ✅ 完全成功 | 🟢 高 | Script | 0 | - | [📄](archives/h/help2man/1.49.3/) |
| **hiredis** | 1.2.0 | ⚠️ 部分成功 |  | Autotools | 1 | - | [📄](archives/h/hiredis/1.2.0/) |
| **htop** | 3.4.1 | ⚠️ 部分成功 | 🟡 中 | Autotools | 3 | - | [📄](archives/h/htop/3.4.1/) |
| **intltool** | 0.51.0 | ✅ 完全成功 |  | Autotools | 1 | - | [📄](archives/i/intltool/0.51.0/) |
| **isa-l_crypto** | 2.26 | ⚠️ 部分成功 |  | CMake | - | - | [📄](archives/i/isa-l_crypto/2.26/) |
| **jansson** | 2.15.0 | ⚠️ 部分成功 |  | cmake  # 实际使用 cmake，因为缺少 automake 无法生成 configure 脚本 | 0 | - | [📄](archives/j/jansson/2.15.0/) |
| **jbig2dec** | 0.20 | ✅ 完全成功 |  | Autotools | - | - | [📄](archives/j/jbig2dec/0.20/) |
| **jna** | 5.19.0 | ✅ 完全成功 |  |  | - | bishengjdk17 (signed),libffi (static, already ported to HarmonyOS) | [📄](archives/j/jna/5.19.0/) |
| **jq** | 1.7.1 | ✅ 完全成功 | 🟢 高 | Autotools | 2 | - | [📄](archives/j/jq/1.7.1/) |
| **json-c** | 0.16、0.17 | ✅ 完全成功 |  | CMake | 1 | - | [📄](archives/j/json-c/0.17/) |
| **jsoncpp** | 1.9.7 | compiling |  | Autotools | 0 | - | [📄](archives/j/jsoncpp/1.9.7/) |
| **laszip** | 3.5.0 | ⚠️ 部分成功 |  | Autotools | 2 | - | [📄](archives/l/laszip/3.5.0/) |
| **lemon** | 3.53.0 | ✅ 完全成功 |  | Autotools | 1 | - | [📄](archives/l/lemon/3.53.0/) |
| **lerc** | 2.2、4.0.0 | ✅ 完全成功 |  | CMake | - | - | [📄](archives/l/lerc/4.0.0/) |
| **lha** | 1.14.20211125 | unknown |  | custom | 6 | [] | [📄](archives/l/lha/1.14.20211125/) |
| **libaio** | 0.3.112 | ⚠️ 部分成功 |  | Autotools | 2 | - | [📄](archives/l/libaio/0.3.112/) |
| **libarchive** | 3.7.4、3.8.7 | compiling |  | Autotools | - | - | [📄](archives/l/libarchive/3.8.7/) |
| **libassuan** | 3.0.2 | ⚠️ 部分成功 |  | Autotools | - | - | [📄](archives/l/libassuan/3.0.2/) |
| **libatomic_ops** | 7.8.2 | ⚠️ 部分成功 |  | CMake | 2 | - | [📄](archives/l/libatomic_ops/7.8.2/) |
| **libb2** | 0.98.1 | ⚠️ 部分成功 |  | Autotools | 1 | - | [📄](archives/l/libb2/0.98.1/) |
| **libbcrypt** | 1.3 | ⚠️ 部分成功 |  | Autotools | 0 | - | [📄](archives/l/libbcrypt/1.3/) |
| **libbsd** | 0.12.2 | compiling |  | Autotools | 0 | - | [📄](archives/l/libbsd/0.12.2/) |
| **libcap** | 2.69 | ⚠️ 部分成功 |  | Makefile | 2 | - | [📄](archives/l/libcap/2.69/) |
| **libconfig** | 1.7.3 | ⚠️ 部分成功 |  | Autotools | 2 | - | [📄](archives/l/libconfig/1.7.3/) |
| **libcuckoo** | 0.3.1 | ⚠️ 部分成功 |  | Autotools | - | - | [📄](archives/l/libcuckoo/0.3.1/) |
| **libdaemon** | 0.14 | ⚠️ 部分成功 |  | Autotools | 0 | - | [📄](archives/l/libdaemon/0.14/) |
| **libde265** | 1.0.18 | ✅ 完全成功 |  | CMake | 2 | - | [📄](archives/l/libde265/1.0.18/) |
| **libdeflate** | 1.25 | ✅ 完全成功 |  | CMake | - | - | [📄](archives/l/libdeflate/1.25/) |
| **libdmtx** | 0.7.5 | compiling |  | Autotools | 0 | - | [📄](archives/l/libdmtx/0.7.5/) |
| **libev** | 4.33 | ⚠️ 部分成功 |  | Autotools | 0 | - | [📄](archives/l/libev/4.33/) |
| **libevent** | 2.1.12-stable | ✅ 完全成功 |  | CMake | 2 | - | [📄](archives/l/libevent/2.1.12-stable/) |
| **libffi** | 3.4.4、3.5.2 | ✅ 完全成功 | 🟢 高 | Autotools | 2 | - | [📄](archives/l/libffi/3.5.2/) |
| **libgcrypt** | 1.11.0 | ⚠️ 部分成功 |  | Autotools | - | - | [📄](archives/l/libgcrypt/1.11.0/) |
| **libgpg-error** | 1.50、1.55 | ⚠️ 部分成功 |  | Autotools | 2 | - | [📄](archives/l/libgpg-error/1.55/) |
| **libiconv** | 1.17 | ✅ 完全成功 |  | Autotools | 6 | - | [📄](archives/l/libiconv/1.17/) |
| **libidn** | 1.43 | compiling |  | Autotools | 0 | - | [📄](archives/l/libidn/1.43/) |
| **libjpeg-turbo** | 3.1.4.1 | ✅ 完全成功 |  | CMake | - | - | [📄](archives/l/libjpeg-turbo/3.1.4.1/) |
| **libksba** | 1.6.7 | ⚠️ 部分成功 |  | Autotools | 6 | - | [📄](archives/l/libksba/1.6.7/) |
| **liblinear** | 2.50 | ⚠️ 部分成功 |  | Autotools | 0 | - | [📄](archives/l/liblinear/2.50/) |
| **liblzf** | 3.6 | ✅ 完全成功 |  | Autotools | 2 | - | [📄](archives/l/liblzf/3.6/) |
| **libmd** | 1.1.0 | ⚠️ 部分成功 |  | Autotools | 0 | - | [📄](archives/l/libmd/1.1.0/) |
| **libmnl** | 1.0.5 | ⚠️ 部分成功 |  | Autotools | 0 | - | [📄](archives/l/libmnl/1.0.5/) |
| **libmspack** | 0.11alpha | ⚠️ 部分成功 |  | Autotools | 2 | - | [📄](archives/l/libmspack/0.11alpha/) |
| **libntlm** | 1.2 | compiling |  | Autotools | 0 | - | [📄](archives/l/libntlm/1.2/) |
| **libogg** | 1.3.5 | ⚠️ 部分成功 |  | CMake | 2 | - | [📄](archives/l/libogg/1.3.5/) |
| **libpcap** | 1.10.6 | ✅ 完全成功 |  | CMake | 3 | - | [📄](archives/l/libpcap/1.10.6/) |
| **libpciaccess** | 0.17 | compiling |  | Autotools | 0 | - | [📄](archives/l/libpciaccess/0.17/) |
| **libpipeline** | 1.5.8 | ✅ 完全成功 | 🟢 高 | Autotools | 2 | - | [📄](archives/l/libpipeline/1.5.8/) |
| **libpng** | 1.6.43 | ✅ 完全成功 |  | Autotools | - | - | [📄](archives/l/libpng/1.6.43/) |
| **libpsl** | 0.21.5 | ⚠️ 部分成功 |  | Meson | 1 | - | [📄](archives/l/libpsl/0.21.5/) |
| **libqb3** | 1.3.2 | ✅ 完全成功 |  | Autotools | - | - | [📄](archives/l/libqb3/1.3.2/) |
| **libqrcodegen** | 1.8.0 | ✅ 完全成功 |  | CMake | 3 | - | [📄](archives/l/libqrcodegen/1.8.0/) |
| **libqrencode** | 4.1.1 | ⚠️ 部分成功 |  | Autotools | 1 | - | [📄](archives/l/libqrencode/4.1.1/) |
| **libressl** | 4.3.1 | ⚠️ 部分成功 |  | CMake | 2 | - | [📄](archives/l/libressl/4.3.1/) |
| **libsamplerate** | 0.2.2 | ✅ 完全成功 |  | CMake | - | - | [📄](archives/l/libsamplerate/0.2.2/) |
| **libsodium** | 1.0.22 | ⚠️ 部分成功 |  | Autotools | 2 | - | [📄](archives/l/libsodium/1.0.22/) |
| **libsoxr** | 0.1.3 | unknown |  |  | - | - | [📄](archives/l/libsoxr/0.1.3/) |
| **libssh** | 0.11.4 | ⚠️ 部分成功 |  | Autotools | - | - | [📄](archives/l/libssh/0.11.4/) |
| **libssh2** | 1.11.0 | ⚠️ 部分成功 |  | Autotools | - | - | [📄](archives/l/libssh2/1.11.0/) |
| **libtasn1** | 4.21.0 | ⚠️ 部分成功 |  | Autotools | 8 | - | [📄](archives/l/libtasn1/4.21.0/) |
| **libtool** | 2.4.7 | ✅ 完全成功 | 🟢 高 | Autotools | 1 | - | [📄](archives/l/libtool/2.4.7/) |
| **libunistring** | 1.0 | ✅ 完全成功 |  | Autotools | 1 | [] | [📄](archives/l/libunistring/1.0/) |
| **libuv** | 1.52.1 | ✅ 完全成功 |  | CMake | 4 | - | [📄](archives/l/libuv/1.52.1/) |
| **libyaml** | 0.2.5 | ⚠️ 部分成功 |  | Autotools | 2 | - | [📄](archives/l/libyaml/0.2.5/) |
| **libzip** | 1.10.1 | ⚠️ 部分成功 |  | Autotools | - | - | [📄](archives/l/libzip/1.10.1/) |
| **llhttp** | 9.3.1 | ✅ 完全成功 |  | CMake | - | - | [📄](archives/l/llhttp/9.3.1/) |
| **lmdb** | 0.9.35 | ⚠️ 部分成功 |  | Makefile | 0 | - | [📄](archives/l/lmdb/0.9.35/) |
| **lz4** | 1.10.0 | ✅ 完全成功 |  | Makefile | - | [] | [📄](archives/l/lz4/1.10.0/) |
| **lz4jsoncat** | v2 | ⚠️ 部分成功 |  | Autotools | 1 | - | [📄](archives/l/lz4jsoncat/v2/) |
| **lzbench** | 2.2 | ⚠️ 部分成功 |  | Makefile | - | - | [📄](archives/l/lzbench/2.2/) |
| **lzip** | 1.25、1.26 | ✅ 完全成功 |  | Autotools | 1 | - | [📄](archives/l/lzip/1.26/) |
| **lzlib** | 1.15、1.9 | ✅ 完全成功 |  | Autotools | - | - | [📄](archives/l/lzlib/1.9/) |
| **lzo** | 2.10 | ✅ 完全成功 |  | Autotools | 3 | - | [📄](archives/l/lzo/2.10/) |
| **lzo2** | 2.10 | ✅ 完全成功 |  | Autotools | - | [] | [📄](archives/l/lzo2/2.10/) |
| **lzop** | 1.04 | ⚠️ 部分成功 |  | Autotools | 13 | - | [📄](archives/l/lzop/1.04/) |
| **man-db** | 2.13.1 | ✅ 完全成功 | 🟡 中 | Autotools | 4 | gdbm 1.23,bzip2 1.0.8,libpipeline 1.5.8,groff 1.23.0  # 运行时依赖 | [📄](archives/m/man-db/2.13.1/) |
| **mbedtls** | 2.28.8、3.6.6、4.1.0 | ⚠️ 部分成功 |  | Autotools | 0 | - | [📄](archives/m/mbedtls/4.1.0/) |
| **meson** | 1.11.0 | ✅ 完全成功 |  | Autotools | 2 | - | [📄](archives/m/meson/1.11.0/) |
| **minizip** | 1.3.1 | ⚠️ 部分成功 |  | Autotools | 2 | - | [📄](archives/m/minizip/1.3.1/) |
| **minizip-ng** | 4.1.1 | ⚠️ 部分成功 |  | Autotools | - | - | [📄](archives/m/minizip-ng/4.1.1/) |
| **mpfr** | 4.2.1 | ⚠️ 部分成功 |  | Autotools | 0 | - | [📄](archives/m/mpfr/4.2.1/) |
| **musl-fts** | 1.2.7 | ⚠️ 部分成功 |  | Autotools | - | - | [📄](archives/m/musl-fts/1.2.7/) |
| **musl-obstack** | 1.2.3 | ⚠️ 部分成功 |  | Autotools | - | - | [📄](archives/m/musl-obstack/1.2.3/) |
| **ncurses** | 6.4 | ✅ 完全成功 | 🟢 高 | Autotools | 1 | - | [📄](archives/n/ncurses/6.4/) |
| **nettle** | 3.10.2 | ⚠️ 部分成功 |  | Autotools | - | - | [📄](archives/n/nettle/3.10.2/) |
| **nlohmann-json** | 3.11.2 | ⚠️ 部分成功 |  | Autotools | 1 | - | [📄](archives/n/nlohmann-json/3.11.2/) |
| **notcurses** | 3.0.17 | ✅ 完全成功 |  | CMake | 10 | ncursesw-6.4,libunistring,libdeflate | [📄](archives/n/notcurses/3.0.17/) |
| **npth** | 1.8 | ⚠️ 部分成功 |  | Autotools | 3 | name: pthread | [📄](archives/n/npth/1.8/) |
| **olm** | 3.2.16 | ⚠️ 部分成功 |  | CMake | - | - | [📄](archives/o/olm/3.2.16/) |
| **openblas** | 0.3.33 | ⚠️ 部分成功 |  | Autotools | 0 | - | [📄](archives/o/openblas/0.3.33/) |
| **openssl** | 1.1.1w | ✅ 完全成功 | 🟢 高 | Custom Perl | 1 | - | [📄](archives/o/openssl/1.1.1w/) |
| **osslsigncode** | 2.13 | ⚠️ 部分成功 |  | Autotools | - | - | [📄](archives/o/osslsigncode/2.13/) |
| **p7zip** | 17.05 | ✅ 完全成功 |  | Autotools | 2 | - | [📄](archives/p/p7zip/17.05/) |
| **patch** | 2.7.6 | ⚠️ 部分成功 | 🟡 中 | Autotools | 1 | - | [📄](archives/p/patch/2.7.6/) |
| **pax** | 20240817 | ✅ 完全成功 |  | Autotools | - | - | [📄](archives/p/pax/20240817/) |
| **pbzip2** | 1.1.13 | ⚠️ 部分成功 |  | Autotools | 1 | - | [📄](archives/p/pbzip2/1.1.13/) |
| **pcre** | 8.45 | ✅ 完全成功 |  | Autotools | 4 | - | [📄](archives/p/pcre/8.45/) |
| **pcre2** | 10.40 | ✅ 完全成功 |  | Autotools | 1 | [] | [📄](archives/p/pcre2/10.40/) |
| **perl** | 5.42.2 | ⚠️ 部分成功 |  | unknown | - | - | [📄](archives/p/perl/5.42.2/) |
| **physfs** | 3.2.0 | ✅ 完全成功 |  | Autotools | - | - | [📄](archives/p/physfs/3.2.0/) |
| **pigz** | 2.8 | ⚠️ 部分成功 |  | Makefile | - | zlib | [📄](archives/p/pigz/2.8/) |
| **pixman** | 0.46.4 | ⚠️ 部分成功 |  | Autotools | 0 | - | [📄](archives/p/pixman/0.46.4/) |
| **pkg-config** | 0.29.2 | ✅ 完全成功 |  | Autotools | 6 | - | [📄](archives/p/pkg-config/0.29.2/) |
| **plzip** | 1.13 | ✅ 完全成功 |  | custom_configure | - | lzlib | [📄](archives/p/plzip/1.13/) |
| **popt** | 1.16 | ⚠️ 部分成功 |  | Autotools | 1 | - | [📄](archives/p/popt/1.16/) |
| **protobuf** | 34.1 | ✅ 完全成功 |  | CMake | - | abseil-cpp (20260107.1) | [📄](archives/p/protobuf/34.1/) |
| **python** | 3.12.9、3.9.0、3.9.25 | tested |  | Autotools | 82 | - | [📄](archives/p/python/3.9.25/) |
| **ragel** | 6.10 | ✅ 完全成功 |  | Autotools | 1 | - | [📄](archives/r/ragel/6.10/) |
| **rapidjson** | 1.1.0 | ⚠️ 部分成功 |  | CMake | 0 | - | [📄](archives/r/rapidjson/1.1.0/) |
| **re2c** | 4.3.1 | ⚠️ 部分成功 |  | Autotools | - | - | [📄](archives/r/re2c/4.3.1/) |
| **readline** | 8.2 | ✅ 完全成功 | 🟢 高 | Autotools | 2 | name: ncurses | [📄](archives/r/readline/8.2/) |
| **rhash** | 1.4.4 | ✅ 完全成功 |  | Makefile | - | openssl (optimized algorithms),gettext (internationalization) - disabled due to compatibility | [📄](archives/r/rhash/1.4.4/) |
| **robin-map** | 1.4.1 | ✅ 完全成功 |  | CMake | - | - | [📄](archives/r/robin-map/1.4.1/) |
| **rsync** | 3.3.0 | ⚠️ 部分成功 | 🟡 中 | Autotools | 2 | - | [📄](archives/r/rsync/3.3.0/) |
| **s2n-tls** | 1.7.2 | ⚠️ 部分成功 |  | CMake | - | libcrypto (OpenSSL or AWS libcrypto) | [📄](archives/s/s2n-tls/1.7.2/) |
| **samurai** | 1.2 | ✅ 完全成功 |  | Makefile | 2 | - | [📄](archives/s/samurai/1.2/) |
| **scintilla** | 5.6.1 | ⚠️ 部分成功 | 🟡 中 | Makefile | 0 | - | [📄](archives/s/scintilla/5.6.1/) |
| **scons** | 4.10.0 | ✅ 完全成功 |  | python | - | - | [📄](archives/s/scons/4.10.0/) |
| **sed** | 4.9、4.10 | ✅ 完全成功 |  | Autotools | 3 | - | [📄](archives/s/sed/4.10/) |
| **simdjson** | 4.6.3 | ⚠️ 部分成功 |  | CMake | 0 | - | [📄](archives/s/simdjson/4.6.3/) |
| **snappy** | 1.2.2 | ✅ 完全成功 |  | Autotools | - | - | [📄](archives/s/snappy/1.2.2/) |
| **sparsehash** | 2.0.4 | ✅ 完全成功 |  | Autotools | - | - | [📄](archives/s/sparsehash/2.0.4/) |
| **spdlog** | 1.17.0 | ✅ 完全成功 |  | CMake | - | - | [📄](archives/s/spdlog/1.17.0/) |
| **speex** | 1.2.1 | ✅ 完全成功 |  | Autotools | 7 | - | [📄](archives/s/speex/1.2.1/) |
| **speexdsp** | 1.2.1 | ✅ 完全成功 |  | Autotools | 2 | - | [📄](archives/s/speexdsp/1.2.1/) |
| **sqlite3** | 3.49.1 | ✅ 完全成功 |  | manual | 2 | - | [📄](archives/s/sqlite3/3.49.1/) |
| **squashfs-tools** | 4.6.1 | ⚠️ 部分成功 |  | Makefile | 1 | zlib | [📄](archives/s/squashfs-tools/4.6.1/) |
| **strace** | 6.19 | ⚠️ 部分成功 | 🔴 低 | Autotools | 3 | - | [📄](archives/s/strace/6.19/) |
| **swig** | 4.4.0 | ✅ 完全成功 |  | Autotools | 4 | - | [📄](archives/s/swig/4.4.0/) |
| **tar** | 1.35 | ✅ 完全成功 | 🟢 高 | Autotools | 1 | - | [📄](archives/t/tar/1.35/) |
| **testssl** | 3.2.3 | ⚠️ 部分成功 |  | Script | 1 | openssl | [📄](archives/t/testssl/3.2.3/) |
| **texinfo** | 7.3 | ✅ 完全成功 | 🟢 高 | Autotools | 0 | - | [📄](archives/t/texinfo/7.3/) |
| **tinyssh** | 20260401 | ⚠️ 部分成功 |  | Makefile | - | - | [📄](archives/t/tinyssh/20260401/) |
| **tomlplusplus** | 3.4.0 | ⚠️ 部分成功 |  | Autotools | 0 | - | [📄](archives/t/tomlplusplus/3.4.0/) |
| **triehash** | 0.3 | ✅ 完全成功 |  | perl_script | 1 | - | [📄](archives/t/triehash/0.3/) |
| **ttaenc** | 3.4.1 | ✅ 完全成功 |  | Makefile | 5 | - | [📄](archives/t/ttaenc/3.4.1/) |
| **ucl** | 1.03 | ✅ 完全成功 |  | Autotools | 2 | - | [📄](archives/u/ucl/1.03/) |
| **utf8proc** | 2.11.3 | ⚠️ 部分成功 |  | Autotools | 0 | - | [📄](archives/u/utf8proc/2.11.3/) |
| **uthash** | 2.3.0 | ✅ 完全成功 |  | Autotools | - | - | [📄](archives/u/uthash/2.3.0/) |
| **vala** | 0.56.18 | ⚠️ 部分成功 |  | Autotools | 3 | - | [📄](archives/v/vala/0.56.18/) |
| **waf** | 2.1.9 | ✅ 完全成功 |  | Autotools | - | - | [📄](archives/w/waf/2.1.9/) |
| **wavpack** | 5.7.0、5.8.1 | ✅ 完全成功 |  | Autotools | 8 | - | [📄](archives/w/wavpack/5.8.1/) |
| **wget** | 1.19.1 | ⚠️ 部分成功 | 🟡 中 | Autotools | 2 | - | [📄](archives/w/wget/1.19.1/) |
| **wimlib** | 1.14.5 | ⚠️ 部分成功 |  | Autotools | 3 | - | [📄](archives/w/wimlib/1.14.5/) |
| **xxhash** | 0.8.3 | ⚠️ 部分成功 |  | make | - | - | [📄](archives/x/xxhash/0.8.3/) |
| **xz** | 5.6.2 | ⚠️ 部分成功 |  | unknown | 12 | - | [📄](archives/x/xz/5.6.2/) |
| **yaml-cpp** | 0.8.0 | ⚠️ 部分成功 |  | Autotools | 0 | - | [📄](archives/y/yaml-cpp/0.8.0/) |
| **yyjson** | 0.12.0 | ⚠️ 部分成功 |  | Autotools | 0 | - | [📄](archives/y/yyjson/0.12.0/) |
| **zlib** | 1.3.1 | ✅ 完全成功 | 🟢 高 | CMake | 0 | - | [📄](archives/z/zlib/1.3.1/) |
| **zlib-ng** | 2.3.3 | ✅ 完全成功 |  | CMake | - | - | [📄](archives/z/zlib-ng/2.3.3/) |
| **zlib-ng-compat** | 2.3.3 | ⚠️ 部分成功 |  | Autotools | - | - | [📄](archives/z/zlib-ng-compat/2.3.3/) |
| **zopfli** | 1.0.3 | ✅ 完全成功 |  | Makefile | 1 | - | [📄](archives/z/zopfli/1.0.3/) |
| **zstd** | 1.5.6、1.5.7 | ✅ 完全成功 |  | Autotools | - | - | [📄](archives/z/zstd/1.5.7/) |
| **zstd-jni** | 1.5.6-5 | ✅ 完全成功 |  | CMake | 1 | [] | [📄](archives/z/zstd-jni/1.5.6-5/) |
| **zutils** | 1.15、1.16 | ⚠️ 部分成功 |  | Autotools | - | - | [📄](archives/z/zutils/1.16/) |
| **zziplib** | 0.13.78 | ⚠️ 部分成功 |  | CMake | 11 | zlib | [📄](archives/z/zziplib/0.13.78/) |

---

*本文档由 `ohc summary` 从编译档案自动生成，请勿手动编辑。*

Copyright (c) 2024-2026 OpenHarmony PC Developer社区