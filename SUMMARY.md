# 鸿蒙平台开源软件编译兼容性总览

> 最后更新：2026-07-11
> 已收录软件：2515 款 / 2670 个版本

## 📊 总体统计

| 指标 | 数量 |
|------|------|
| 收录软件 | **2515** 款 |
| 软件版本 | **2670** 个 |
| ✅ 已发布 | 998 |
| ✅ 已编译 | 1232 |
| ❌ 编译失败 | 10 |

| 构建系统 | 数量 |
|----------|------|
| Autotools | 523 |
| CMake | 261 |
| Makefile | 204 |
| unknown | 102 |
| custom | 95 |
| Meson | 87 |
| go | 69 |
| perl | 60 |
| cargo | 18 |
| python | 14 |
| perl_makefile | 12 |
| Script | 10 |
| perl-eumm | 8 |
| npm | 7 |
| make | 6 |
| manual | 5 |
| perl_xs | 4 |
| shell | 4 |
| qmake | 4 |
| autoconf | 4 |
| none | 3 |
| waf | 3 |
| perl-makefile | 3 |
| lua | 3 |
| perl-extutils-makemaker | 3 |
| perl-makemaker | 3 |
| Custom Perl | 3 |
| perl-makefile-pl | 3 |
| perl-extutils | 3 |
| pgxs | 3 |
| manual_makefile | 2 |
| header-only | 2 |
| perl-xs | 2 |
| perl-build | 2 |
| perl_makemaker | 2 |
| pip | 2 |
| rust | 2 |
| Makefile | 2 |
| perl-module | 2 |
| module-build | 2 |
| perl-module-build | 2 |
| python_wheel | 2 |
| autotools  # 标准 conan Autotools（CI 原生 clang） | 2 |
| configure | 2 |
| openssl-perl | 1 |
| builtin | 1 |
| prebuilt | 1 |
| simple-configure | 1 |
| nodejs | 1 |
| makemaker | 1 |
| shell_script | 1 |
| cmake-manual | 1 |
| rust (precompiled_binary) | 1 |
| go_bootstrap | 1 |
| maven | 1 |
| makefile-legacy | 1 |
| bmake | 1 |
| sendmail-devtools | 1 |
| bsd-make | 1 |
| makefile-gnu | 1 |
| configure-make | 1 |
| luarocks | 1 |
| lua-builtin | 1 |
| custom-configure | 1 |
| cmake-ninja | 1 |
| Perl-Makefile.PL | 1 |
| perl-modulebuild | 1 |
| perl-build-tiny | 1 |
| phpize | 1 |
| golang | 1 |
| prebuilt/go | 1 |
| python3 | 1 |
| python-pip | 1 |
| configure+make | 1 |
| custom-makefile | 1 |
| autosetup | 1 |
| prebuilt-musl | 1 |
| simple_makefile | 1 |
| python-zipapp | 1 |

## 📋 软件兼容性一览

| 软件 | 版本 | 状态 | 兼容性 | 构建系统 | 补丁数 | 依赖 | 详情 |
|------|------|------|--------|----------|--------|------|------|
| **7zip** | 23.01、25.01 | uploaded |  | unknown | 0 | - | [📄](archives/7/7zip/25.01/) |
| **CLI11** | 2.6.2 | ✅ 已发布 |  | CMake | - | - | [📄](archives/c/CLI11/2.6.2/) |
| **Crypt-OpenSSL-Guess** | 0.15 | ✅ 已发布 |  | perl_makefile | - | perl (>= 5.006),perl | [📄](archives/c/Crypt-OpenSSL-Guess/0.15/) |
| **Crypt-OpenSSL-RSA** | 0.33 | built   |  | perl_makefile | - | perl (>= 5.006),openssl/1.1.1w,Crypt::OpenSSL::Random/0.11,perl,openssl... | [📄](archives/c/Crypt-OpenSSL-RSA/0.33/) |
| **Crypt-OpenSSL-Random** | 0.11 | built   |  | perl_makefile | - | perl (>= 5.006),openssl/1.1.1w,perl,openssl | [📄](archives/c/Crypt-OpenSSL-Random/0.11/) |
| **Data-Peek** | 0.53 | ✅ 已编译 |  |  | 1 | - | [📄](archives/d/Data-Peek/0.53/) |
| **Data-UUID** | 1.227 | ✅ 已编译 |  | perl-xs | - | - | [📄](archives/d/Data-UUID/1.227/) |
| **DateTime** | 1.66 | ✅ 已编译 |  | Autotools | 1 | - | [📄](archives/d/DateTime/1.66/) |
| **Devel-Caller** | 2.07 | ✅ 已编译 |  |  | 1 | - | [📄](archives/d/Devel-Caller/2.07/) |
| **Devel-CheckCompiler** | 0.03 | ✅ 已编译 |  | perl-build | - | - | [📄](archives/d/Devel-CheckCompiler/0.03/) |
| **Digest-HMAC** | 1.05 | ✅ 已发布 |  | perl | - | - | [📄](archives/d/Digest-HMAC/1.05/) |
| **ElaWidgetTools** | 2.0.0 | ✅ 已发布 |  | CMake | 1 | - | [📄](archives/e/ElaWidgetTools/2.0.0/) |
| **Email-Address-XS** | 1.05 | ✅ 已编译 |  | perl_xs | - | - | [📄](archives/e/Email-Address-XS/1.05/) |
| **Encode** | 3.24 | 📦 已归档 |  |  | 1 | - | [📄](archives/e/Encode/3.24/) |
| **ExtUtils-Builder-Compiler** | 0.032 | ✅ 已编译 |  | perl | - | - | [📄](archives/e/ExtUtils-Builder-Compiler/0.032/) |
| **FMILibrary** | 2.0.3 | ✅ 已发布 |  |  | 3 | - | [📄](archives/f/FMILibrary/2.0.3/) |
| **IO-Socket-IP** | 0.43 | ✅ 已发布 |  | perl | - | - | [📄](archives/i/IO-Socket-IP/0.43/) |
| **IO-Stringy** | 2.113 | ✅ 已编译 |  | perl-makefile | - | - | [📄](archives/i/IO-Stringy/2.113/) |
| **LWP-MediaTypes** | 6.04 | ✅ 已发布 |  |  | 1 | perl >= 5.006002,Carp,Exporter,File::Basename,Scalar::Util... | [📄](archives/l/LWP-MediaTypes/6.04/) |
| **LWP-Protocol-https** | 6.14 | ✅ 已编译 |  |  | - | - | [📄](archives/l/LWP-Protocol-https/6.14/) |
| **LockFile-Simple** | 0.208 | ✅ 已发布 |  |  | - | - | [📄](archives/l/LockFile-Simple/0.208/) |
| **Log-Log4perl** | 1.57 | published   |  | perl_makefile | - | perl-File-Spec (>= 0.82),perl-File-Path (>= 2.07),perl-Log-Dispatch (>= 2.00)     # ✅ published 2.71,perl-DBI (>= 1.607)              # ✅ PurePerl mode 1.637 (DBI.so 无法签名),perl-DBD-SQLite                  # ✅ published... | [📄](archives/l/Log-Log4perl/1.57/) |
| **Memory-Process** | 0.06-r3 | ✅ 已发布 |  |  | - | - | [📄](archives/m/Memory-Process/0.06-r3/) |
| **Menlo** | 1.9019 | ✅ 已发布 |  | perl_makefile | - | perl (>= 5.008),perl | [📄](archives/m/Menlo/1.9019/) |
| **Menlo-Legacy** | 1.9022 | ✅ 已编译 |  | perl | - | - | [📄](archives/m/Menlo-Legacy/1.9022/) |
| **SDL2** | 2.30.0 | ✅ 已发布 |  | CMake | 1 | - | [📄](archives/s/SDL2/2.30.0/) |
| **SDL2_image** | 2.6.0、2.8.0 | ✅ 已发布 |  | CMake | - | - | [📄](archives/s/SDL2_image/2.8.0/) |
| **SDL2_ttf** | 2.22.0 | ✅ 已编译 |  | Autotools | 2 | - | [📄](archives/s/SDL2_ttf/2.22.0/) |
| **a2ps** | 4.15.7 | ✅ 已发布 |  |  | - | - | [📄](archives/a/a2ps/4.15.7/) |
| **aamath** | 0.3 | ✅ 已发布 |  | Makefile | 3 | - | [📄](archives/a/aamath/0.3/) |
| **abseil-cpp** | 20260107.1、20240116.1 | partial |  | Autotools | 1 | - | [📄](archives/a/abseil-cpp/20240116.1/) |
| **abyss** | 2.3.10 | ✅ 已编译 |  |  | - | - | [📄](archives/a/abyss/2.3.10/) |
| **acl** | 2.3.2 | ✅ 已发布 |  | Autotools | 3 | - | [📄](archives/a/acl/2.3.2/) |
| **acme-client** | 0.1.16 | ✅ 已编译 |  | make | 9 | libressl (>= 3.9.2) | [📄](archives/a/acme-client/0.1.16/) |
| **acme-tiny** | 5.0.1 | ✅ 已编译 |  |  | - | - | [📄](archives/a/acme-tiny/5.0.1/) |
| **acme.sh** | 3.1.3 | ✅ 已编译 |  | none | - | - | [📄](archives/a/acme.sh/3.1.3/) |
| **adb-enhanced** | 2.8.0 | ✅ 已编译 |  |  | 1 | - | [📄](archives/a/adb-enhanced/2.8.0/) |
| **addlicense** | 1.1.1 | ✅ 已发布 |  |  | - | - | [📄](archives/a/addlicense/1.1.1/) |
| **adr-tools** | 3.0.0 | ✅ 已发布 |  |  | - | - | [📄](archives/a/adr-tools/3.0.0/) |
| **advancecomp** | 2.6 | ✅ 已编译 |  | Autotools | 3 | - | [📄](archives/a/advancecomp/2.6/) |
| **advancescan** | 1.18 | ✅ 已编译 |  | Autotools | 9 | - | [📄](archives/a/advancescan/1.18/) |
| **adwaita-icon-theme** | 49.0 | ✅ 已编译 |  | Meson | - | - | [📄](archives/a/adwaita-icon-theme/49.0/) |
| **aes** | 0.7.4 | ❌ 编译失败 |  | cargo | - | rust-toolchain,cfg-if-1,cipher-0.3,ctr-0.7,opaque-debug-0.3... | [📄](archives/a/aes/0.7.4/) |
| **aescrypt** | 0.7 | ✅ 已编译 |  | Autotools | 2 | - | [📄](archives/a/aescrypt/0.7/) |
| **agensgraph** | 2.13.0 | ✅ 已编译 |  |  | 3 | - | [📄](archives/a/agensgraph/2.13.0/) |
| **aha** | 0.5.1 | ✅ 已发布 |  | Makefile | 2 | - | [📄](archives/a/aha/0.5.1/) |
| **aircrack-ng** | 1.7 | ✅ 已编译 |  |  | 2 | - | [📄](archives/a/aircrack-ng/1.7/) |
| **airspyone-host** | 1.0.10 | ✅ 已编译 |  |  | 1 | - | [📄](archives/a/airspyone-host/1.0.10/) |
| **akamai** | v2.0.0 | ✅ 已编译 |  | go | - | [] | [📄](archives/a/akamai/v2.0.0/) |
| **aliyun-cli** | homebrew | ✅ 已发布 |  |  | - | - | [📄](archives/a/aliyun-cli/homebrew/) |
| **allegro** | 5.2.11.3 | ✅ 已编译 |  |  | 1 | - | [📄](archives/a/allegro/5.2.11.3/) |
| **alpine-make-rootfs** | 0.8.1 | ✅ 已发布 |  |  | - | - | [📄](archives/a/alpine-make-rootfs/0.8.1/) |
| **alpine-make-vm-image** | 0.13.4 | ✅ 已编译 |  |  | - | - | [📄](archives/a/alpine-make-vm-image/0.13.4/) |
| **alsa-lib** | 1.2.12 | ✅ 已发布 |  | Autotools | 2 | - | [📄](archives/a/alsa-lib/1.2.12/) |
| **alsa-utils** | 1.2.14 | ✅ 已发布 |  | Autotools | 4 | - | [📄](archives/a/alsa-utils/1.2.14/) |
| **altermime** | 0.3.10 | ✅ 已发布 |  | Makefile | 2 | - | [📄](archives/a/altermime/0.3.10/) |
| **amass** | 4.2.0 | ✅ 已编译 |  | custom | - | - | [📄](archives/a/amass/4.2.0/) |
| **anthy** | 0.4 | ✅ 已编译 |  | Autotools | 3 | - | [📄](archives/a/anthy/0.4/) |
| **antidote** | 2.1.0 | ✅ 已发布 |  | Script | - | zsh >= 5.0,git | [📄](archives/a/antidote/2.1.0/) |
| **antiword** | 0.37 | ✅ 已发布 |  | manual_makefile | 1 | [] | [📄](archives/a/antiword/0.37/) |
| **aom** | 3.9.1 | ✅ 已发布 |  |  | 1 | - | [📄](archives/a/aom/3.9.1/) |
| **apache-arrow** | 24.0.0 | ✅ 已编译 |  |  | - | - | [📄](archives/a/apache-arrow/24.0.0/) |
| **apcupsd** | 3.14.14 | ✅ 已编译 |  |  | 5 | - | [📄](archives/a/apcupsd/3.14.14/) |
| **apg** | 2.2.3 | ✅ 已编译 |  | Makefile | 1 | - | [📄](archives/a/apg/2.2.3/) |
| **api-sanity-checker** | 1.98.7 | ✅ 已发布 |  |  | 1 | - | [📄](archives/a/api-sanity-checker/1.98.7/) |
| **apitrace** | 14.0 | ✅ 已编译 |  |  | - | - | [📄](archives/a/apitrace/14.0/) |
| **apko** | 1.2.17 | ✅ 已编译 |  | custom | - | - | [📄](archives/a/apko/1.2.17/) |
| **apngasm** | 3.1.10 | ✅ 已编译 |  | CMake | - | - | [📄](archives/a/apngasm/3.1.10/) |
| **apparmor** | 4.1.0 | ✅ 已编译 |  |  | 8 | - | [📄](archives/a/apparmor/4.1.0/) |
| **apr** | 1.7.6 | ✅ 已编译 |  |  | 3 | - | [📄](archives/a/apr/1.7.6/) |
| **apr-util** | 1.6.3 | ✅ 已编译 |  | Autotools | 3 | - | [📄](archives/a/apr-util/1.6.3/) |
| **apt-dater-host** | 1.0.1 | ✅ 已发布 |  | Makefile | - | - | [📄](archives/a/apt-dater-host/1.0.1/) |
| **aqbanking** | 6.9.2 | ✅ 已发布 |  |  | 2 | - | [📄](archives/a/aqbanking/6.9.2/) |
| **aqua** | v2.60.0 | ✅ 已编译 |  | go | - | [] | [📄](archives/a/aqua/v2.60.0/) |
| **arduino-cli** | 1.5.0 | ✅ 已编译 |  | go | - | [] | [📄](archives/a/arduino-cli/1.5.0/) |
| **argo** | 4.0.5 | ✅ 已发布 |  | custom | - | - | [📄](archives/a/argo/4.0.5/) |
| **argon2** | 20190702 | uploaded |  | unknown | 0 | - | [📄](archives/a/argon2/20190702/) |
| **argp-standalone** | 1.5.0 | uploaded |  | unknown | 0 | - | [📄](archives/a/argp-standalone/1.5.0/) |
| **argparse** | 0.6.0 | ✅ 已编译 |  | builtin | - | lua >= 5.1 | [📄](archives/a/argparse/0.6.0/) |
| **argtable3** | 3.3.1 | ✅ 已发布 |  | CMake | 2 | - | [📄](archives/a/argtable3/3.3.1/) |
| **argus** | 5.0.2 | ✅ 已发布 |  |  | 5 | - | [📄](archives/a/argus/5.0.2/) |
| **argus-clients** | 5.0.3 | ✅ 已发布 |  | Autotools | 3 | - | [📄](archives/a/argus-clients/5.0.3/) |
| **aria2** | 1.37.0 | 📦 已归档 |  |  | - | - | [📄](archives/a/aria2/1.37.0/) |
| **armadillo** | 12.8.4 | ✅ 已发布 |  | CMake | - | - | [📄](archives/a/armadillo/12.8.4/) |
| **arp-scan** | 1.10.0 | partial |  | Autotools | - | libpcap >= 1.5.0,libpcap 1.10.6 (静态链接) | [📄](archives/a/arp-scan/1.10.0/) |
| **arping** | 2.26 | ✅ 已编译 |  | Autotools | 1 | - | [📄](archives/a/arping/2.26/) |
| **arpwatch** | 3.9 | ✅ 已编译 |  | Autotools | 16 | name: libpcap,name: libresolv | [📄](archives/a/arpwatch/3.9/) |
| **asahi-audio** | v3.4 | ✅ 已编译 |  |  | - | - | [📄](archives/a/asahi-audio/v3.4/) |
| **ascii** | 3.32 | ✅ 已发布 |  | Makefile | - | - | [📄](archives/a/ascii/3.32/) |
| **asciidoc** | 10.2.1 | ✅ 已编译 |  | python | 3 | - | [📄](archives/a/asciidoc/10.2.1/) |
| **asciiquarium** | 1.6 | ✅ 已编译 |  | Script | - | perl >= 5.42.0,Curses (Perl module),Term::Animation (Perl module) | [📄](archives/a/asciiquarium/1.6/) |
| **asio** | 1.30.2 | ✅ 已发布 |  |  | - | - | [📄](archives/a/asio/1.30.2/) |
| **asn1c** | 0.9.28 | ✅ 已编译 |  | Autotools | 4 | - | [📄](archives/a/asn1c/0.9.28/) |
| **aspcud** | 1.9.6 | ✅ 已发布 |  |  | 3 | - | [📄](archives/a/aspcud/1.9.6/) |
| **aspell** | 0.60.8 | ✅ 已编译 |  |  | 2 | - | [📄](archives/a/aspell/0.60.8/) |
| **assimp** | 5.4.3、6.0.5 | ✅ 已发布 |  |  | - | - | [📄](archives/a/assimp/6.0.5/) |
| **astroterm** | 1.0.9-r0 | ✅ 已编译 |  |  | 1 | - | [📄](archives/a/astroterm/1.0.9-r0/) |
| **astyle** | 3.6.13 | ✅ 已发布 |  |  | - | - | [📄](archives/a/astyle/3.6.13/) |
| **async_simple** | 1.4 | ✅ 已发布 |  | CMake | - | - | [📄](archives/a/async_simple/1.4/) |
| **at** | 3.2.5 | ✅ 已编译 |  |  | 3 | - | [📄](archives/a/at/3.2.5/) |
| **atf** | 0.23 | ✅ 已编译 |  |  | 3 | - | [📄](archives/a/atf/0.23/) |
| **atinout** | 0.9.1 | ✅ 已发布 |  |  | - | - | [📄](archives/a/atinout/0.9.1/) |
| **atk** | 2.38.0 | ✅ 已发布 |  |  | 3 | - | [📄](archives/a/atk/2.38.0/) |
| **atlas** | 1.2.0 | ✅ 已编译 |  | go | - | name: go | [📄](archives/a/atlas/1.2.0/) |
| **atomicparsley** | 20240608.083822.1ed9031 | ✅ 已发布 |  | CMake | - | - | [📄](archives/a/atomicparsley/20240608.083822.1ed9031/) |
| **attr** | 2.5.2 | ✅ 已编译 |  |  | 5 | - | [📄](archives/a/attr/2.5.2/) |
| **aubio** | 0.4.9 | ✅ 已发布 |  | waf | 3 | - | [📄](archives/a/aubio/0.4.9/) |
| **audacious-plugins** | 4.5.1 | ✅ 已发布 |  | Autotools | 2 | - | [📄](archives/a/audacious-plugins/4.5.1/) |
| **audiocd-kio** | 26.04.1 | ✅ 已编译 |  | CMake | 6 | - | [📄](archives/a/audiocd-kio/26.04.1/) |
| **audiotube** | v26.04.1 | ✅ 已编译 |  | CMake | 2 | - | [📄](archives/a/audiotube/v26.04.1/) |
| **audiowaveform** | 1.10.3 | ✅ 已编译 |  | CMake | 1 | - | [📄](archives/a/audiowaveform/1.10.3/) |
| **audit** | 4.1.2 | ✅ 已发布 |  | Autotools | 86 | - | [📄](archives/a/audit/4.1.2/) |
| **aumix** | 2.9.1 | ✅ 已编译 |  | Autotools | 5 | - | [📄](archives/a/aumix/2.9.1/) |
| **autoconf** | 2.72 | uploaded |  | Autotools | 0 | - | [📄](archives/a/autoconf/2.72/) |
| **autoconf-archive** | 2024.10.16 | uploaded |  | unknown | 0 | - | [📄](archives/a/autoconf-archive/2024.10.16/) |
| **autocutsel** | 0.10.1 | ✅ 已发布 |  |  | 5 | - | [📄](archives/a/autocutsel/0.10.1/) |
| **autojump** | 22.5.3 | ✅ 已编译 |  | custom | 1 | - | [📄](archives/a/autojump/22.5.3/) |
| **automake** | 1.16.5、1.17 | uploaded |  | Autotools | 0 | - | [📄](archives/a/automake/1.17/) |
| **autopep8** | 2.1.1 | ✅ 已编译 |  |  | 1 | - | [📄](archives/a/autopep8/2.1.1/) |
| **autossh** | 1.4g | success |  | Autotools | - | ssh (OpenSSH 9.6p1, system installed at /usr/bin/ssh) | [📄](archives/a/autossh/1.4g/) |
| **autotrace** | 0.31.10 | ✅ 已编译 |  | Autotools | - | - | [📄](archives/a/autotrace/0.31.10/) |
| **avfs** | 1.2.0 | ✅ 已编译 |  |  | 3 | - | [📄](archives/a/avfs/1.2.0/) |
| **avrdude** | 8.1-r0 | ✅ 已编译 |  |  | - | [] | [📄](archives/a/avrdude/8.1-r0/) |
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
| **aws-shell** | 0.2.2 | ✅ 已编译 |  |  | 3 | - | [📄](archives/a/aws-shell/0.2.2/) |
| **awscurl** | 0.42 | ✅ 已编译 |  | python | 2 | python3,python3-requests,python3-configargparse,python3-configparser,python3-urllib3... | [📄](archives/a/awscurl/0.42/) |
| **axel** | 2.17.14 | ✅ 已发布 |  |  | 3 | - | [📄](archives/a/axel/2.17.14/) |
| **b2sum** | 20190724 | ✅ 已发布 |  | Makefile | 1 | - | [📄](archives/b/b2sum/20190724/) |
| **b3sum** | 1.8.4 | uploaded |  | CMake | 0 | - | [📄](archives/b/b3sum/1.8.4/) |
| **babl** | 0.1.126 | ✅ 已发布 |  |  | - | - | [📄](archives/b/babl/0.1.126/) |
| **bamtools** | 2.5.3 | ✅ 已编译 |  |  | 1 | - | [📄](archives/b/bamtools/2.5.3/) |
| **bandwhich** | 0.23.0 | ✅ 已发布 |  | cargo | - | - | [📄](archives/b/bandwhich/0.23.0/) |
| **base64** | 1.5 | ✅ 已发布 |  | Autotools | 2 | - | [📄](archives/b/base64/1.5/) |
| **basedpyright** | 1.39.6 | ✅ 已发布 |  |  | - | - | [📄](archives/b/basedpyright/1.39.6/) |
| **bash** | 5.3 | verified |  | Autotools | 0 | - | [📄](archives/b/bash/5.3/) |
| **bash-completion** | 2.17.0 | ✅ 已编译 |  |  | 2 | - | [📄](archives/b/bash-completion/2.17.0/) |
| **basis_universal** | v2.1.0 | ✅ 已发布 |  |  | 1 | - | [📄](archives/b/basis_universal/v2.1.0/) |
| **basisu** | v2_1_0r | ✅ 已编译 |  |  | - | - | [📄](archives/b/basisu/v2_1_0r/) |
| **bbe** | 0.2.2 | partial |  |  | 2 | - | [📄](archives/b/bbe/0.2.2/) |
| **bc** | 1.07.1 | partial |  | Autotools | - | - | [📄](archives/b/bc/1.07.1/) |
| **bcal** | 2.5 | ✅ 已编译 |  | Makefile | - | - | [📄](archives/b/bcal/2.5/) |
| **bchunk** | 1.2.2 | ✅ 已发布 |  |  | 1 | - | [📄](archives/b/bchunk/1.2.2/) |
| **bcrypt** | 1.0 | uploaded |  | unknown | 0 | - | [📄](archives/b/bcrypt/1.0/) |
| **bdw-gc** | 8.2.6 | ✅ 已发布 |  |  | 2 | - | [📄](archives/b/bdw-gc/8.2.6/) |
| **beanstalkd** | 1.13 | ✅ 已发布 |  | Makefile | 2 | - | [📄](archives/b/beanstalkd/1.13/) |
| **bear** | 3.1.6 | uploaded |  | Makefile | 0 | - | [📄](archives/b/bear/3.1.6/) |
| **bearssl** | 0.6 | uploaded |  | CMake | 0 | - | [📄](archives/b/bearssl/0.6/) |
| **bento4** | 1.6.0-641 | ✅ 已编译 |  | CMake | - | - | [📄](archives/b/bento4/1.6.0-641/) |
| **berkeley-db4** | 4.8.30 | ✅ 已编译 |  | Autotools | 4 | - | [📄](archives/b/berkeley-db4/4.8.30/) |
| **bettercap** | 2.33.0 | ✅ 已发布 |  | go | - | - | [📄](archives/b/bettercap/2.33.0/) |
| **bfs** | 4.1 | ✅ 已编译 |  | custom | 2 | - | [📄](archives/b/bfs/4.1/) |
| **bgrep** | 0.2 | ✅ 已发布 |  | Makefile | - | - | [📄](archives/b/bgrep/0.2/) |
| **bib-tool** | 2.68 | ✅ 已发布 |  | Makefile | - | - | [📄](archives/b/bib-tool/2.68/) |
| **bibtexconv** | 2.2.2 | ✅ 已发布 |  |  | - | - | [📄](archives/b/bibtexconv/2.2.2/) |
| **bibutils** | 7.2 | ✅ 已编译 |  | Autotools | - | - | [📄](archives/b/bibutils/7.2/) |
| **binaryen** | 123 | ✅ 已编译 |  |  | - | - | [📄](archives/b/binaryen/123/) |
| **bind** | 9.20.22 | ✅ 已编译 |  | Autotools | - | - | [📄](archives/b/bind/9.20.22/) |
| **binutils** | 2.46.0 | ✅ 已编译 |  |  | 2 | - | [📄](archives/b/binutils/2.46.0/) |
| **binwalk** | 2.3.4、3.1.0 | ✅ 已发布 |  |  | - | - | [📄](archives/b/binwalk/3.1.0/) |
| **bison** | 2.7、3.8.2 | ✅ 已编译 |  |  | 5 | - | [📄](archives/b/bison/3.8.2/) |
| **bitrise** | 2.40.5 | ✅ 已发布 |  | go | - | [] | [📄](archives/b/bitrise/2.40.5/) |
| **bkcrack** | 1.8.1 | ✅ 已发布 |  | CMake | 2 | - | [📄](archives/b/bkcrack/1.8.1/) |
| **black** | 26.5.1 | ✅ 已编译 |  |  | 1 | - | [📄](archives/b/black/26.5.1/) |
| **blake3** | 1.8.3 | ✅ 已编译 |  | CMake | - | - | [📄](archives/b/blake3/1.8.3/) |
| **blend2d** | 0.21.2 | ✅ 已编译 |  |  | - | - | [📄](archives/b/blend2d/0.21.2/) |
| **blind** | 1.1 | ✅ 已编译 |  |  | - | - | [📄](archives/b/blind/1.1/) |
| **blockhash** | 0.1 | ✅ 已发布 |  |  | 1 | - | [📄](archives/b/blockhash/0.1/) |
| **blosc** | 1.21.5、1.21.6 | uploaded |  | unknown | 0 | - | [📄](archives/b/blosc/1.21.6/) |
| **bluez-alsa** | v4.3.1 | ✅ 已编译 |  | Autotools | 5 | - | [📄](archives/b/bluez-alsa/v4.3.1/) |
| **bmd-tools** | v1.0.2 | ✅ 已编译 |  | Makefile | 1 | - | [📄](archives/b/bmd-tools/v1.0.2/) |
| **bombardier** | 2.0.2 | ✅ 已编译 |  |  | 1 | - | [📄](archives/b/bombardier/2.0.2/) |
| **bonnie++** | 2.00a | ✅ 已发布 |  | Autotools | 3 | - | [📄](archives/b/bonnie++/2.00a/) |
| **boolector** | 3.2.4 | ✅ 已发布 |  |  | - | - | [📄](archives/b/boolector/3.2.4/) |
| **boost** | 1.76.0、1.84.0 | ✅ 已编译 |  | header-only | 2 | [] | [📄](archives/b/boost/1.84.0/) |
| **boost-build** | 1.90.0 | ✅ 已编译 |  | custom | - | - | [📄](archives/b/boost-build/1.90.0/) |
| **borgbackup** | 1.4.4 | ✅ 已编译 |  | python | 14 | - | [📄](archives/b/borgbackup/1.4.4/) |
| **bossa** | 1.9.1 | ✅ 已发布 |  | Makefile | - | - | [📄](archives/b/bossa/1.9.1/) |
| **botan** | 3.6.1 | ✅ 已发布 |  | custom | - | - | [📄](archives/b/botan/3.6.1/) |
| **bottom** | 0.12.3 | ✅ 已编译 |  |  | - | - | [📄](archives/b/bottom/0.12.3/) |
| **bowtie2** | 2.5.5 | ✅ 已发布 |  | Makefile | - | - | [📄](archives/b/bowtie2/2.5.5/) |
| **boxes** | 2.3.1 | uploaded |  | unknown | 0 | - | [📄](archives/b/boxes/2.3.1/) |
| **bpm-tools** | 0.3 | ✅ 已编译 |  | Makefile | - | - | [📄](archives/b/bpm-tools/0.3/) |
| **breakpad** | v2023.06.01 | ✅ 已编译 |  |  | 5 | - | [📄](archives/b/breakpad/v2023.06.01/) |
| **brev-cli** | 0.6.326 | unknown |  |  | 1 | go-runtime (optional) | [📄](archives/b/brev-cli/0.6.326/) |
| **brew-cask-completion** | 2.1 | ✅ 已编译 |  | Makefile | - | - | [📄](archives/b/brew-cask-completion/2.1/) |
| **brotli** | 1.1.0、1.2.0 | uploaded |  | Autotools | 0 | - | [📄](archives/b/brotli/1.2.0/) |
| **bruno-cli** | 3.4.2 | ✅ 已发布 |  | npm | - | - | [📄](archives/b/bruno-cli/3.4.2/) |
| **brunsli** | v0.1 | ✅ 已编译 |  | CMake | 1 | - | [📄](archives/b/brunsli/v0.1/) |
| **bsd-compat-headers** | 0.7.2 | uploaded |  | Makefile | 0 | - | [📄](archives/b/bsd-compat-headers/0.7.2/) |
| **bsdiff** | 4.3 | ✅ 已发布 |  | Makefile | 2 | - | [📄](archives/b/bsdiff/4.3/) |
| **bstring** | 1.0.3 | ✅ 已发布 |  | Meson | - | - | [📄](archives/b/bstring/1.0.3/) |
| **btllib** | 1.7.8 | ✅ 已发布 |  |  | 18 | - | [📄](archives/b/btllib/1.7.8/) |
| **btrfs-progs** | 5.19.1 | ✅ 已发布 |  |  | - | - | [📄](archives/b/btrfs-progs/5.19.1/) |
| **bubblewrap** | 0.11.0 | ✅ 已发布 |  | Meson | 2 | - | [📄](archives/b/bubblewrap/0.11.0/) |
| **buildah** | 1.44.0 | ✅ 已发布 |  | Makefile | 2 | - | [📄](archives/b/buildah/1.44.0/) |
| **buildifier** | 8.0.3 | ✅ 已编译 |  | go | - | - | [📄](archives/b/buildifier/8.0.3/) |
| **bullet** | 3.25 | success |  | CMake | - | [] | [📄](archives/b/bullet/3.25/) |
| **bvi** | 1.5.0 | ✅ 已编译 |  |  | 4 | - | [📄](archives/b/bvi/1.5.0/) |
| **bwfmetaedit** | 26.01 | ✅ 已编译 |  | Autotools | 2 | - | [📄](archives/b/bwfmetaedit/26.01/) |
| **byacc** | 20241231、20260126 | ✅ 已编译 |  | Autotools | 3 | - | [📄](archives/b/byacc/20260126/) |
| **byobu** | 6.13 | ✅ 已编译 |  |  | 1 | - | [📄](archives/b/byobu/6.13/) |
| **bzip2** | 1.0.8 | verified |  | Autotools | 0 | - | [📄](archives/b/bzip2/1.0.8/) |
| **bzip3** | 1.4.0、1.5.3 | uploaded |  | Autotools | 0 | - | [📄](archives/b/bzip3/1.5.3/) |
| **c-ares** | 1.34.4、1.34.6 | uploaded |  | Autotools | 0 | - | [📄](archives/c/c-ares/1.34.6/) |
| **c-blosc** | 1.21.6 | success |  | CMake | - | - | [📄](archives/c/c-blosc/1.21.6/) |
| **ca-certificates** | 20250416、20250419 | ✅ 已编译 |  |  | - | - | [📄](archives/c/ca-certificates/20250419/) |
| **cabextract** | 1.11 | ✅ 已编译 |  |  | 2 | - | [📄](archives/c/cabextract/1.11/) |
| **caddy** | 2.11.2-r1 | ✅ 已编译 |  |  | - | - | [📄](archives/c/caddy/2.11.2-r1/) |
| **cairo** | 1.18.2、1.18.4 | ✅ 已编译 |  |  | - | - | [📄](archives/c/cairo/1.18.4/) |
| **cairomm** | 1.18.0 | ✅ 已编译 |  | Meson | - | cairo 1.18.4,sigc++-3.0 3.6.0,pixman-1 0.46.4,freetype2 26.6.20 | [📄](archives/c/cairomm/1.18.0/) |
| **callaudiocli** | 0.1.10 | ✅ 已编译 |  | Meson | - | - | [📄](archives/c/callaudiocli/0.1.10/) |
| **capnp** | 1.3.0 | success |  | CMake | - | - | [📄](archives/c/capnp/1.3.0/) |
| **caps** | 0.9.26 | ✅ 已编译 |  | Makefile | 5 | - | [📄](archives/c/caps/0.9.26/) |
| **capstone** | 5.0.7-r0 | success |  | Autotools | - | - | [📄](archives/c/capstone/5.0.7-r0/) |
| **carapace** | 1.11.7 | ✅ 已编译 |  | custom | - | - | [📄](archives/c/carapace/1.11.7/) |
| **carburetor** | 4.5.1 | ✅ 已编译 |  | Meson | 2 | - | [📄](archives/c/carburetor/4.5.1/) |
| **cargo-binstall** | homebrew | ✅ 已发布 |  |  | - | - | [📄](archives/c/cargo-binstall/homebrew/) |
| **cargo-c** | 0.10.18 | ✅ 已编译 |  | cargo | 1 | - | [📄](archives/c/cargo-c/0.10.18/) |
| **cargo-nextest** | 0.9.110 | ✅ 已发布 |  |  | - | - | [📄](archives/c/cargo-nextest/0.9.110/) |
| **casablanca** | 2.10.16 | ✅ 已发布 |  | CMake | 4 | - | [📄](archives/c/casablanca/2.10.16/) |
| **cask** | 0.9.1 | ✅ 已发布 |  | Script | - | coreutils,emacs | [📄](archives/c/cask/0.9.1/) |
| **cassandra-cpp-driver** | 2.17.1 | ✅ 已编译 |  | CMake | 4 | - | [📄](archives/c/cassandra-cpp-driver/2.17.1/) |
| **catatonit** | 0.2.1 | ✅ 已发布 |  | Autotools | 2 | - | [📄](archives/c/catatonit/0.2.1/) |
| **catch2** | 2.13.10-r0 | success |  | CMake | - | - | [📄](archives/c/catch2/2.13.10-r0/) |
| **catgirl** | 2.2a | ✅ 已发布 |  |  | - | - | [📄](archives/c/catgirl/2.2a/) |
| **catimg** | 2.8.0 | ✅ 已编译 |  | CMake | - | - | [📄](archives/c/catimg/2.8.0/) |
| **cbc** | 2.10.10 | ✅ 已编译 |  |  | 1 | - | [📄](archives/c/cbc/2.10.10/) |
| **ccache** | 4.12.1 | uploaded |  | Makefile | 0 | - | [📄](archives/c/ccache/4.12.1/) |
| **ccrypt** | 1.11 | ✅ 已编译 |  |  | 2 | libcrypt | [📄](archives/c/ccrypt/1.11/) |
| **cctz** | 2.5 | ✅ 已发布 |  | CMake | - | - | [📄](archives/c/cctz/2.5/) |
| **cdk** | 5.0-20260119 | ✅ 已发布 |  |  | 2 | - | [📄](archives/c/cdk/5.0-20260119/) |
| **cdparanoia** | 10.2 | ✅ 已编译 |  |  | - | - | [📄](archives/c/cdparanoia/10.2/) |
| **cdrkit** | 1.1.11 | ✅ 已编译 |  |  | - | - | [📄](archives/c/cdrkit/1.1.11/) |
| **cdrtools** | 3.02a09 | ✅ 已编译 |  | Makefile | 5 | - | [📄](archives/c/cdrtools/3.02a09/) |
| **cepces** | 0.3.17 | ✅ 已编译 |  |  | - | - | [📄](archives/c/cepces/0.3.17/) |
| **ceres-solver** | 2.2.0 | ✅ 已发布 |  |  | - | - | [📄](archives/c/ceres-solver/2.2.0/) |
| **cfitsio** | 4.6.4 | ✅ 已发布 |  | CMake | - | zlib 1.3.1 (static) | [📄](archives/c/cfitsio/4.6.4/) |
| **cflow** | 1.8 | ✅ 已发布 |  | Autotools | 7 | - | [📄](archives/c/cflow/1.8/) |
| **cgal** | 6.1.1 | ✅ 已编译 |  |  | - | - | [📄](archives/c/cgal/6.1.1/) |
| **cgif** | 0.5.2 | success |  | Meson | - | - | [📄](archives/c/cgif/0.5.2/) |
| **cglm** | 0.9.6 | ✅ 已编译 |  |  | - | - | [📄](archives/c/cglm/0.9.6/) |
| **chadwick** | 0.10.0 | ✅ 已编译 |  |  | 19 | - | [📄](archives/c/chadwick/0.10.0/) |
| **chafa** | 1.18.2 | ✅ 已发布 |  |  | 2 | - | [📄](archives/c/chafa/1.18.2/) |
| **check** | 0.15.2 | ✅ 已编译 |  |  | 2 | - | [📄](archives/c/check/0.15.2/) |
| **check-jsonschema** | 0.28.4 | ✅ 已发布 |  |  | 0 | - | [📄](archives/c/check-jsonschema/0.28.4/) |
| **chezscheme** | 10.3.0 | ✅ 已编译 |  |  | 1 | - | [📄](archives/c/chezscheme/10.3.0/) |
| **chibi-scheme** | 0.12 | success |  | Makefile | - | - | [📄](archives/c/chibi-scheme/0.12/) |
| **chicken** | 5.4.0 | partial |  | Autotools | - | - | [📄](archives/c/chicken/5.4.0/) |
| **chkrootkit** | 0.59 | ✅ 已发布 |  | Makefile | - | - | [📄](archives/c/chkrootkit/0.59/) |
| **chmlib** | 0.40 | ✅ 已发布 |  | Autotools | 4 | - | [📄](archives/c/chmlib/0.40/) |
| **chromaprint** | 1.6.0 | ✅ 已发布 |  |  | - | - | [📄](archives/c/chromaprint/1.6.0/) |
| **chronograf** | 1.11.3 | ✅ 已发布 |  | prebuilt | - | - | [📄](archives/c/chronograf/1.11.3/) |
| **chruby** | 0.3.9 | ✅ 已编译 |  | Makefile | - | [] | [📄](archives/c/chruby/0.3.9/) |
| **chsrc** | 0.2.4 | ✅ 已编译 |  | Makefile | 4 | - | [📄](archives/c/chsrc/0.2.4/) |
| **cidrmerge** | 1.5.3 | ✅ 已发布 |  | Makefile | - | - | [📄](archives/c/cidrmerge/1.5.3/) |
| **cilium-cli** | v0.19.4 | ✅ 已编译 |  | go | - | - | [📄](archives/c/cilium-cli/v0.19.4/) |
| **cimg** | 2.21 | ✅ 已编译 |  |  | 1 | - | [📄](archives/c/cimg/2.21/) |
| **cinecli** | 0.1.2 | success |  | python | - | - | [📄](archives/c/cinecli/0.1.2/) |
| **ciso** | 1.0、1.0.0 | uploaded |  | unknown | 0 | - | [📄](archives/c/ciso/1.0.0/) |
| **citus** | 13.0.4 | ✅ 已编译 |  |  | 2 | - | [📄](archives/c/citus/13.0.4/) |
| **cjson** | 1.7.18、1.7.19 | ✅ 已编译 |  | CMake | 1 | - | [📄](archives/c/cjson/1.7.19/) |
| **ckermit** | 302 | ✅ 已发布 |  |  | 4 | - | [📄](archives/c/ckermit/302/) |
| **clamsmtp** | 1.10 | ✅ 已发布 |  | Autotools | 4 | - | [📄](archives/c/clamsmtp/1.10/) |
| **clip** | 0.7 | ✅ 已编译 |  | CMake | 1 | - | [📄](archives/c/clip/0.7/) |
| **clipper** | 2.0.1 | ✅ 已发布 |  | CMake | - | [] | [📄](archives/c/clipper/2.0.1/) |
| **clipper2** | 2.0.1 | ✅ 已发布 |  | CMake | - | - | [📄](archives/c/clipper2/2.0.1/) |
| **cloc** | 2.08 | success |  | perl | - | perl >= 5.10.0,Regexp::Common,Parallel::ForkManager,Algorithm::Diff | [📄](archives/c/cloc/2.08/) |
| **cloud-sql-proxy** | 1.38.0 | ✅ 已发布 |  | custom | - | - | [📄](archives/c/cloud-sql-proxy/1.38.0/) |
| **cloud-utils** | 0.33 | ✅ 已编译 |  |  | - | - | [📄](archives/c/cloud-utils/0.33/) |
| **cloudfoundry-cli** | 8.18.3 | ✅ 已编译 |  | Autotools | 1 | - | [📄](archives/c/cloudfoundry-cli/8.18.3/) |
| **cloudfox** | 2.0.5 | ❌ 编译失败 |  | go | - | go >= 1.21 | [📄](archives/c/cloudfox/2.0.5/) |
| **clusterawsadm** | 2.10.3 | unknown |  |  | - | - | [📄](archives/c/clusterawsadm/2.10.3/) |
| **clusterctl** | 1.13.2 | ✅ 已发布 |  | go | - | - | [📄](archives/c/clusterctl/1.13.2/) |
| **cmake** | 3.30.0 | ✅ 已编译 |  |  | - | - | [📄](archives/c/cmake/3.30.0/) |
| **cmake-docs** | 3.30.0 | ✅ 已编译 |  |  | - | - | [📄](archives/c/cmake-docs/3.30.0/) |
| **cmark** | 0.31.2 | ✅ 已发布 |  | CMake | - | - | [📄](archives/c/cmark/0.31.2/) |
| **cmark-gfm** | 0.29.0.gfm.13 | ✅ 已发布 |  | CMake | 1 | - | [📄](archives/c/cmark-gfm/0.29.0.gfm.13/) |
| **cmatrix** | 2.0-r2 | unknown |  |  | 3 | - | [📄](archives/c/cmatrix/2.0-r2/) |
| **cminpack** | 1.3.9 | ✅ 已发布 |  | CMake | - | - | [📄](archives/c/cminpack/1.3.9/) |
| **cmix** | 21 | ✅ 已编译 |  | Makefile | 2 | - | [📄](archives/c/cmix/21/) |
| **cmocka** | 2.0.2 | uploaded |  | CMake | 0 | - | [📄](archives/c/cmocka/2.0.2/) |
| **cmph** | 2.0 | ✅ 已编译 |  |  | - | - | [📄](archives/c/cmph/2.0/) |
| **cni-plugin-flannel** | 1.8.0-r5 | ✅ 已编译 |  |  | - | - | [📄](archives/c/cni-plugin-flannel/1.8.0-r5/) |
| **cni-plugins** | 1.8.0-r5 | ✅ 已编译 |  |  | - | - | [📄](archives/c/cni-plugins/1.8.0-r5/) |
| **codec2** | 1.2.0 | ✅ 已编译 |  | CMake | - | - | [📄](archives/c/codec2/1.2.0/) |
| **codecov-cli** | 0.8.0 | ✅ 已编译 |  |  | 1 | - | [📄](archives/c/codecov-cli/0.8.0/) |
| **codespell** | 2.4.2 | ✅ 已编译 |  |  | - | - | [📄](archives/c/codespell/2.4.2/) |
| **colordiff** | 1.0.21-r0 | ✅ 已编译 |  | Makefile | 1 | - | [📄](archives/c/colordiff/1.0.21-r0/) |
| **colortail** | 0.3.5 | ✅ 已发布 |  | Autotools | 1 | - | [📄](archives/c/colortail/0.3.5/) |
| **compiledb** | 0.10.7 | ✅ 已发布 |  |  | - | - | [📄](archives/c/compiledb/0.10.7/) |
| **concurrencykit** | 0.7.2 | ✅ 已发布 |  | Autotools | 1 | - | [📄](archives/c/concurrencykit/0.7.2/) |
| **conftest** | 0.56.0、homebrew | ✅ 已发布 |  | go | - | [] | [📄](archives/c/conftest/homebrew/) |
| **confuse** | 3.3 | ✅ 已编译 |  |  | 2 | - | [📄](archives/c/confuse/3.3/) |
| **console_bridge** | 1.0.2 | ✅ 已发布 |  |  | - | - | [📄](archives/c/console_bridge/1.0.2/) |
| **consul-template** | 0.42.0 | ✅ 已发布 |  | custom | 1 | - | [📄](archives/c/consul-template/0.42.0/) |
| **convmv** | 2.06 | ✅ 已编译 |  | Makefile | 1 | - | [📄](archives/c/convmv/2.06/) |
| **copyparty** | 1.20.9 | ✅ 已发布 |  |  | - | - | [📄](archives/c/copyparty/1.20.9/) |
| **coreimage** | latest | ✅ 已编译 |  | CMake | 2 | - | [📄](archives/c/coreimage/latest/) |
| **corepack** | 0.32.0、0.35.0 | ✅ 已发布 |  | npm | - | - | [📄](archives/c/corepack/0.35.0/) |
| **corepdf** | 1.0 | ✅ 已编译 |  | CMake | 1 | - | [📄](archives/c/corepdf/1.0/) |
| **coreutils** | 9.10 | verified |  | Autotools | 0 | - | [📄](archives/c/coreutils/9.10/) |
| **corkscrew** | 2.0 | ✅ 已发布 |  |  | 2 | - | [📄](archives/c/corkscrew/2.0/) |
| **cosign** | 3.1.1 | ✅ 已编译 |  | custom | - | - | [📄](archives/c/cosign/3.1.1/) |
| **cowsay** | 1.5.0 | ✅ 已编译 |  |  | 2 | - | [📄](archives/c/cowsay/1.5.0/) |
| **cowsql** | 1.15.9 | success |  |  | 5 | - | [📄](archives/c/cowsql/1.15.9/) |
| **cpdf** | 0.0.7 | ✅ 已编译 |  | custom | 3 | python3/3.12,pypdf2/3.0.1,click/8.4.1,pydantic/latest | [📄](archives/c/cpdf/0.0.7/) |
| **cpio** | 2.14 | ✅ 已发布 |  |  | 5 | - | [📄](archives/c/cpio/2.14/) |
| **cpprestsdk** | 2.10.19 | ✅ 已编译 |  |  | - | - | [📄](archives/c/cpprestsdk/2.10.19/) |
| **cpptoml** | v0.1.1 | uploaded |  | CMake | 0 | - | [📄](archives/c/cpptoml/v0.1.1/) |
| **cppunit** | 1.15.1 | ✅ 已发布 |  |  | 34 | - | [📄](archives/c/cppunit/1.15.1/) |
| **cppzmq** | 4.10.0 | ✅ 已发布 |  | CMake | - | - | [📄](archives/c/cppzmq/4.10.0/) |
| **cproto** | 4.7y | ✅ 已发布 |  | Autotools | 2 | - | [📄](archives/c/cproto/4.7y/) |
| **cpufetch** | 1.07 | ✅ 已发布 |  |  | - | - | [📄](archives/c/cpufetch/1.07/) |
| **cpython-tkinter** | 3.12.9 | ✅ 已编译 |  | custom | - | - | [📄](archives/c/cpython-tkinter/3.12.9/) |
| **cramfs** | 1.1 | uploaded |  | unknown | 0 | - | [📄](archives/c/cramfs/1.1/) |
| **crane** | 0.21.6 | ✅ 已编译 |  | custom | - | - | [📄](archives/c/crane/0.21.6/) |
| **crf++** | 0.58 | ✅ 已编译 |  | Autotools | 2 | - | [📄](archives/c/crf++/0.58/) |
| **croaring** | 4.6.1 | uploaded |  | CMake | 0 | - | [📄](archives/c/croaring/4.6.1/) |
| **croc** | 10.2.2 | ✅ 已发布 |  |  | - | - | [📄](archives/c/croc/10.2.2/) |
| **cronie** | 1.7.2 | ✅ 已编译 |  | Autotools | 4 | - | [📄](archives/c/cronie/1.7.2/) |
| **crosstool-ng** | 1.28.0 | ✅ 已编译 |  |  | 6 | - | [📄](archives/c/crosstool-ng/1.28.0/) |
| **crun** | 1.27.1 | ✅ 已发布 |  |  | 19 | - | [📄](archives/c/crun/1.27.1/) |
| **cryptominisat** | 5.14.4 | ✅ 已编译 |  |  | 3 | - | [📄](archives/c/cryptominisat/5.14.4/) |
| **cryptopp** | 8.9.0 | uploaded |  | unknown | 0 | - | [📄](archives/c/cryptopp/8.9.0/) |
| **csvq** | 1.18.1 | ✅ 已编译 |  |  | - | - | [📄](archives/c/csvq/1.18.1/) |
| **ctop** | 0.7.7 | ✅ 已发布 |  |  | - | - | [📄](archives/c/ctop/0.7.7/) |
| **cue** | 0.11.2 | ✅ 已发布 |  | custom | 1 | - | [📄](archives/c/cue/0.11.2/) |
| **cuetools** | 1.4.1 | ✅ 已编译 |  | Autotools | - | - | [📄](archives/c/cuetools/1.4.1/) |
| **cunit** | 2.1-3 | uploaded |  | CMake | 0 | - | [📄](archives/c/cunit/2.1-3/) |
| **cups** | 2.4.7 | ✅ 已编译 |  | Autotools | 4 | - | [📄](archives/c/cups/2.4.7/) |
| **curl** | 8.15.0、8.5.0 | ✅ 已发布 |  |  | - | - | [📄](archives/c/curl/8.5.0/) |
| **curlpp** | 0.8.1 | ✅ 已发布 |  | CMake | 1 | - | [📄](archives/c/curlpp/0.8.1/) |
| **cutter** | 1.04 | ✅ 已发布 |  |  | - | - | [📄](archives/c/cutter/1.04/) |
| **cvsync** | 0.24.19 | ✅ 已编译 |  | Makefile | 2 | - | [📄](archives/c/cvsync/0.24.19/) |
| **cweb** | 4.12.2 | ✅ 已发布 |  | Makefile | 1 | - | [📄](archives/c/cweb/4.12.2/) |
| **cyclone** | 11.0.1 | ✅ 已发布 |  |  | - | - | [📄](archives/c/cyclone/11.0.1/) |
| **czkawka** | 11.0.1 | ✅ 已编译 |  | cargo | - | [] | [📄](archives/c/czkawka/11.0.1/) |
| **czmq** | 4.2.1 | partial |  | Autotools | - | - | [📄](archives/c/czmq/4.2.1/) |
| **daemonize** | 1.7.8 | partial |  | Autotools | - | - | [📄](archives/d/daemonize/1.7.8/) |
| **daemontools** | 0.76 | ✅ 已发布 |  | Makefile | 6 | - | [📄](archives/d/daemontools/0.76/) |
| **dante** | 1.4.4 | ✅ 已发布 |  |  | 6 | - | [📄](archives/d/dante/1.4.4/) |
| **daq** | 3.0.27 | ✅ 已发布 |  | Autotools | 9 | - | [📄](archives/d/daq/3.0.27/) |
| **dar** | 2.7.15、2.8.1 | ✅ 已编译 |  |  | 15 | - | [📄](archives/d/dar/2.8.1/) |
| **darkhttpd** | 1.17 | ✅ 已编译 |  | Makefile | - | - | [📄](archives/d/darkhttpd/1.17/) |
| **darkice** | 1.6 | ✅ 已发布 |  | Autotools | 12 | - | [📄](archives/d/darkice/1.6/) |
| **darkstat** | 3.0.722-r0 | ✅ 已编译 |  |  | - | - | [📄](archives/d/darkstat/3.0.722-r0/) |
| **dasel** | 2.8.1-r14 | ✅ 已发布 |  | custom | - | - | [📄](archives/d/dasel/2.8.1-r14/) |
| **dash** | 0.5.12 | partial |  | Autotools | 2 | - | [📄](archives/d/dash/0.5.12/) |
| **dash-shell** | 0.5.13.2 | ✅ 已编译 |  | Autotools | 4 | - | [📄](archives/d/dash-shell/0.5.13.2/) |
| **datamash** | 1.9 | ✅ 已编译 |  | Autotools | 5 | - | [📄](archives/d/datamash/1.9/) |
| **dav1d** | 1.5.0 | ✅ 已编译 |  | Meson | - | - | [📄](archives/d/dav1d/1.5.0/) |
| **dbhash** | 3.53.1 | ✅ 已编译 |  | manual | 1 | sqlite3 (embedded amalgamation) | [📄](archives/d/dbhash/3.53.1/) |
| **dbmate** | 2.33.0 | ✅ 已编译 |  | go | - | [] | [📄](archives/d/dbmate/2.33.0/) |
| **dbus** | 1.14.10 | partial |  | Autotools | 4 | - | [📄](archives/d/dbus/1.14.10/) |
| **dcfldd** | 1.9.3 | ✅ 已发布 |  | Autotools | 1 | - | [📄](archives/d/dcfldd/1.9.3/) |
| **dcm2niix** | v1.0.20250506 | ✅ 已编译 |  | CMake | 1 | - | [📄](archives/d/dcm2niix/v1.0.20250506/) |
| **dcron** | 4.2 | ✅ 已编译 |  | Makefile | 1 | - | [📄](archives/d/dcron/4.2/) |
| **ddrescue** | 1.30 | partial |  | simple-configure | - | [] | [📄](archives/d/ddrescue/1.30/) |
| **deark** | 1.7.2 | ✅ 已编译 |  | Makefile | - | - | [📄](archives/d/deark/1.7.2/) |
| **debianutils** | 5.23.2 | ✅ 已发布 |  |  | 1 | - | [📄](archives/d/debianutils/5.23.2/) |
| **dejagnu** | 1.6.3 | ✅ 已编译 |  | Autotools | 4 | - | [📄](archives/d/dejagnu/1.6.3/) |
| **devcontainer** | 0.87.0 | ✅ 已发布 |  |  | - | - | [📄](archives/d/devcontainer/0.87.0/) |
| **deviceinfo** | 0.2.4 | ✅ 已编译 |  |  | 3 | - | [📄](archives/d/deviceinfo/0.2.4/) |
| **dex** | 1.0 | ✅ 已编译 |  |  | 4 | - | [📄](archives/d/dex/1.0/) |
| **dfc** | 3.1.1 | ✅ 已编译 |  |  | 3 | - | [📄](archives/d/dfc/3.1.1/) |
| **dfu-programmer** | 1.1.0 | ✅ 已发布 |  | Autotools | - | - | [📄](archives/d/dfu-programmer/1.1.0/) |
| **dhcp-probe** | 1.3.1 | ✅ 已发布 |  |  | 1 | name: libnet,name: libpcap | [📄](archives/d/dhcp-probe/1.3.1/) |
| **dhcping** | 1.2 | ✅ 已发布 |  | Autotools | 2 | - | [📄](archives/d/dhcping/1.2/) |
| **dialog** | 1.3-20240307 | partial |  | Autotools | 2 | - | [📄](archives/d/dialog/1.3-20240307/) |
| **diamond** | 2.1.24 | ✅ 已编译 |  | CMake | - | - | [📄](archives/d/diamond/2.1.24/) |
| **diff-pdf** | v0.5.3 | ✅ 已编译 |  | Makefile | 2 | - | [📄](archives/d/diff-pdf/v0.5.3/) |
| **diff-so-fancy** | 1.4.10 | ✅ 已编译 |  | custom | - | - | [📄](archives/d/diff-so-fancy/1.4.10/) |
| **diffutils** | 3.10 | ✅ 已编译 |  | Autotools | 10 | gnulib | [📄](archives/d/diffutils/3.10/) |
| **dinit** | 0.22.0 | ✅ 已发布 |  |  | - | - | [📄](archives/d/dinit/0.22.0/) |
| **dircproxy** | 1.1.0 | ✅ 已发布 |  | Autotools | 6 | - | [📄](archives/d/dircproxy/1.1.0/) |
| **directx-headers** | 1.619.1 | ✅ 已编译 |  |  | - | - | [📄](archives/d/directx-headers/1.619.1/) |
| **discount** | 2.2.7、2.2.7b | partial |  | Autotools | 1 | - | [📄](archives/d/discount/2.2.7b/) |
| **disktype** | 9 | ✅ 已发布 |  | Makefile | - | - | [📄](archives/d/disktype/9/) |
| **distcc** | 3.4 | uploaded |  | Makefile | 0 | - | [📄](archives/d/distcc/3.4/) |
| **djvu2pdf** | 1.0 | ✅ 已发布 |  | Makefile | 1 | - | [📄](archives/d/djvu2pdf/1.0/) |
| **djvulibre** | 3.5.29 | ✅ 已发布 |  | Autotools | 27 | - | [📄](archives/d/djvulibre/3.5.29/) |
| **dlib** | 19.24.2 | ✅ 已编译 |  |  | - | - | [📄](archives/d/dlib/19.24.2/) |
| **dmg2img** | 1.6.7 | uploaded |  | unknown | 0 | - | [📄](archives/d/dmg2img/1.6.7/) |
| **dmidecode** | 3.6 | uploaded |  | Makefile | 0 | - | [📄](archives/d/dmidecode/3.6/) |
| **dns2tcp** | 0.5.2 | ✅ 已发布 |  | Autotools | 5 | - | [📄](archives/d/dns2tcp/0.5.2/) |
| **dnscrypt-proxy** | 2.1.14 | ✅ 已编译 |  |  | - | - | [📄](archives/d/dnscrypt-proxy/2.1.14/) |
| **dnsmasq** | 2.90、2.92 | success |  | Autotools | 2 | - | [📄](archives/d/dnsmasq/2.92/) |
| **dnsq** | 0.19.11-r5 | ✅ 已编译 |  |  | - | - | [📄](archives/d/dnsq/0.19.11-r5/) |
| **dnstracer** | 1.9 | ✅ 已编译 |  | Autotools | 1 | - | [📄](archives/d/dnstracer/1.9/) |
| **docker** | 29.5.3 | ✅ 已发布 |  |  | 2 | - | [📄](archives/d/docker/29.5.3/) |
| **docker-completion** | 29.5.2 | ✅ 已编译 |  | Autotools | - | - | [📄](archives/d/docker-completion/29.5.2/) |
| **docker-machine** | homebrew | ✅ 已发布 |  |  | 11 | - | [📄](archives/d/docker-machine/homebrew/) |
| **dockerfile-language-server** | 0.0.24 | ✅ 已发布 |  | nodejs | - | node >= 12.0.0,dockerfile-language-service 0.0.12,dockerfile-utils 0.0.11,vscode-languageserver ^6.1.1,typescript ^3.7.5... | [📄](archives/d/dockerfile-language-server/0.0.24/) |
| **dockerfilegraph** | 0.21.0 | ✅ 已编译 |  |  | - | - | [📄](archives/d/dockerfilegraph/0.21.0/) |
| **doctest** | 2.5.2 | uploaded |  | CMake | 0 | - | [📄](archives/d/doctest/2.5.2/) |
| **docutils** | 0.23 | ✅ 已发布 |  | python | - | - | [📄](archives/d/docutils/0.23/) |
| **docx2txt** | 1.4 | ✅ 已编译 |  | Makefile | 1 | - | [📄](archives/d/docx2txt/1.4/) |
| **dog** | 0.1.0-r5 | ✅ 已编译 |  |  | - | - | [📄](archives/d/dog/0.1.0-r5/) |
| **doggo** | 1.1.2-r5 | ✅ 已发布 |  | go | 0 | go 1.26.0+ | [📄](archives/d/doggo/1.1.2-r5/) |
| **doh** | 0.1 | ✅ 已编译 |  | custom | 1 | - | [📄](archives/d/doh/0.1/) |
| **doppler** | 3.72.1 | ✅ 已编译 |  | go | - | - | [📄](archives/d/doppler/3.72.1/) |
| **dos2unix** | 7.5.4 | verified |  | Makefile | 0 | - | [📄](archives/d/dos2unix/7.5.4/) |
| **double-conversion** | 3.4.0 | ✅ 已发布 |  | CMake | - | - | [📄](archives/d/double-conversion/3.4.0/) |
| **doxygen** | 1.17.0 | ✅ 已发布 |  | CMake | 1 | - | [📄](archives/d/doxygen/1.17.0/) |
| **dpkg** | 1.22.6 | ✅ 已编译 |  | Autotools | 4 | - | [📄](archives/d/dpkg/1.22.6/) |
| **dprint** | 0.54.0 | ✅ 已编译 |  |  | - | - | [📄](archives/d/dprint/0.54.0/) |
| **dqlite** | 1.18.6 | ✅ 已编译 |  | Autotools | 3 | - | [📄](archives/d/dqlite/1.18.6/) |
| **draco** | 1.5.7 | ✅ 已发布 |  |  | - | - | [📄](archives/d/draco/1.5.7/) |
| **drawing** | 1.0.2 | ✅ 已编译 |  |  | 2 | - | [📄](archives/d/drawing/1.0.2/) |
| **dropbear** | 2025.88 | ✅ 已发布 |  |  | 2 | - | [📄](archives/d/dropbear/2025.88/) |
| **dsnet** | 0.8.1-r9 | ✅ 已编译 |  |  | - | - | [📄](archives/d/dsnet/0.8.1-r9/) |
| **dsocks** | 1.8 | ✅ 已编译 |  | Makefile | 5 | - | [📄](archives/d/dsocks/1.8/) |
| **dssim** | 3.4.0 | ✅ 已编译 |  |  | 0 | - | [📄](archives/d/dssim/3.4.0/) |
| **dtach** | 0.9 | ✅ 已发布 |  | Autotools | 2 | - | [📄](archives/d/dtach/0.9/) |
| **dtc** | 1.7.2 | partial |  | Autotools | 1 | - | [📄](archives/d/dtc/1.7.2/) |
| **dua-cli** | 2.34.0 | ✅ 已发布 |  |  | - | - | [📄](archives/d/dua-cli/2.34.0/) |
| **duckdb** | 1.2.0 | partial |  | Autotools | - | - | [📄](archives/d/duckdb/1.2.0/) |
| **duf** | 0.9.1 | ✅ 已编译 |  | custom | - | - | [📄](archives/d/duf/0.9.1/) |
| **duktape** | 2.7.0 | ✅ 已发布 |  | Makefile | - | - | [📄](archives/d/duktape/2.7.0/) |
| **dumb-init** | 1.2.5 | published (符合上库标准，签名问题已解决) |  | Makefile | - | [] | [📄](archives/d/dumb-init/1.2.5/) |
| **dummyhttp** | 1.1.2-r0 | ✅ 已编译 |  |  | - | - | [📄](archives/d/dummyhttp/1.1.2-r0/) |
| **duo_unix** | 2.2.3 | ✅ 已发布 |  |  | 4 | - | [📄](archives/d/duo_unix/2.2.3/) |
| **duperemove** | 0.15.2 | ✅ 已编译 |  | Makefile | 3 | - | [📄](archives/d/duperemove/0.15.2/) |
| **dvc** | 3.67.1 | ✅ 已编译 |  | custom | 2 | - | [📄](archives/d/dvc/3.67.1/) |
| **dvgrab** | 3.8 | ✅ 已发布 |  | Autotools | 6 | - | [📄](archives/d/dvgrab/3.8/) |
| **dwarfutils** | 2.3.1 | success |  | CMake | 1 | - | [📄](archives/d/dwarfutils/2.3.1/) |
| **dynamips** | 0.2.23 | ✅ 已发布 |  | CMake | - | - | [📄](archives/d/dynamips/0.2.23/) |
| **e2fsimage** | 0.2.3 | ✅ 已编译 |  | Makefile | 5 | - | [📄](archives/e/e2fsimage/0.2.3/) |
| **e2fsprogs** | 1.47.0 | ✅ 已编译 |  |  | 4 | - | [📄](archives/e/e2fsprogs/1.47.0/) |
| **e2tools** | 0.1.2 | ✅ 已编译 |  |  | - | - | [📄](archives/e/e2tools/0.1.2/) |
| **easy-rsa** | 3.2.6 | ✅ 已编译 |  | shell | - | - | [📄](archives/e/easy-rsa/3.2.6/) |
| **easyrpg-player** | 0.8.1.1 | ✅ 已编译 |  | CMake | - | sdl2 2.30.0,inih r62,liblcf 0.8.1,expat 2.7.1,icu4c 77... | [📄](archives/e/easyrpg-player/0.8.1.1/) |
| **easytag** | 2.4.3 | ✅ 已发布 |  | Autotools | - | - | [📄](archives/e/easytag/2.4.3/) |
| **ed** | 1.20 | ✅ 已编译 |  | Autotools | - | lzip,coreutils | [📄](archives/e/ed/1.20/) |
| **edencommon** | v2026.05.25.00 | ✅ 已发布 |  |  | 3 | - | [📄](archives/e/edencommon/v2026.05.25.00/) |
| **editorconfig** | 0.12.9 | ✅ 已编译 |  |  | 2 | - | [📄](archives/e/editorconfig/0.12.9/) |
| **efi-mkuki** | 7 | ✅ 已发布 |  | custom | - | - | [📄](archives/e/efi-mkuki/7/) |
| **eigen** | 3.4.0 | uploaded |  | CMake | 0 | - | [📄](archives/e/eigen/3.4.0/) |
| **elinks** | 0.19.1 | ✅ 已发布 |  | Meson | - | - | [📄](archives/e/elinks/0.19.1/) |
| **emacspeak** | 59.0 | ✅ 已发布 |  | Makefile | - | - | [📄](archives/e/emacspeak/59.0/) |
| **email** | 3.1.4 | ✅ 已发布 |  |  | - | - | [📄](archives/e/email/3.1.4/) |
| **embree** | 4.4.1 | ✅ 已编译 |  | CMake | - | - | [📄](archives/e/embree/4.4.1/) |
| **enca** | 1.19、1.19-r4 | ✅ 已编译 |  |  | 2 | - | [📄](archives/e/enca/1.19-r4/) |
| **enchant** | 2.8.2 | ✅ 已发布 |  | Autotools | 3 | - | [📄](archives/e/enchant/2.8.2/) |
| **ent** | 1.0 | ✅ 已发布 |  |  | 1 | - | [📄](archives/e/ent/1.0/) |
| **entr** | 5.8 | partial |  | Autotools | - | - | [📄](archives/e/entr/5.8/) |
| **envchain** | 1.1.0 | ✅ 已编译 |  |  | 1 | - | [📄](archives/e/envchain/1.1.0/) |
| **eot-utils** | 1.1 | ✅ 已发布 |  | Autotools | 1 | - | [📄](archives/e/eot-utils/1.1/) |
| **esbuild** | 0.25.12 | ✅ 已发布 |  | custom | - | - | [📄](archives/e/esbuild/0.25.12/) |
| **eslint_d** | 15.0.2 | ✅ 已发布 |  | npm | - | - | [📄](archives/e/eslint_d/15.0.2/) |
| **espeak** | 1.48.04 | ✅ 已发布 |  | Makefile | 3 | - | [📄](archives/e/espeak/1.48.04/) |
| **espeak-ng** | 1.51 | ✅ 已编译 |  | Autotools | 2 | - | [📄](archives/e/espeak-ng/1.51/) |
| **etcd** | 3.6.4-r8 | ✅ 已编译 |  | go | - | [] | [📄](archives/e/etcd/3.6.4-r8/) |
| **ethereum** | 1.15.11、1.15.8、1.17.3 | ✅ 已编译 |  |  | - | - | [📄](archives/e/ethereum/1.17.3/) |
| **ethtool** | 6.15、6.15cutter | ✅ 已发布 |  |  | - | - | [📄](archives/e/ethtool/6.15cutter/) |
| **eudev** | 3.2.14 | ✅ 已编译 |  | Autotools | 16 | - | [📄](archives/e/eudev/3.2.14/) |
| **exempi** | 2.6.6 | ✅ 已发布 |  | Autotools | 3 | - | [📄](archives/e/exempi/2.6.6/) |
| **exercism** | 3.0.11、3.5.4 | ✅ 已编译 |  | go | - | - | [📄](archives/e/exercism/3.5.4/) |
| **exiftool** | 13.50 | partial |  | perl_makemaker | - | - | [📄](archives/e/exiftool/13.50/) |
| **exiv2** | 0.28.7 | ✅ 已编译 |  |  | - | [] | [📄](archives/e/exiv2/0.28.7/) |
| **expat** | 2.7.1、2.8.0、2.8.2 | ✅ 已编译 |  |  | - | - | [📄](archives/e/expat/2.8.2/) |
| **expect** | 5.45.4 | ✅ 已编译 |  | Autotools | 5 | tcl 8.6.14 (静态库),zlib 1.3.1 (共享库) | [📄](archives/e/expect/5.45.4/) |
| **extract-dtb** | 1.2 | ✅ 已发布 |  | custom | - | - | [📄](archives/e/extract-dtb/1.2/) |
| **extutils-cppguess** | 0.27 | ✅ 已发布 |  | makemaker | - | - | [📄](archives/e/ExtUtils-CppGuess/0.27/) |
| **extutils-depends** | 0.8002 | ✅ 已发布 |  |  | - | - | [📄](archives/e/extutils-depends/0.8002/) |
| **f3** | 9.0 | ✅ 已编译 |  | Makefile | - | - | [📄](archives/f/f3/9.0/) |
| **faac** | 1.40 | success |  | Meson | - | - | [📄](archives/f/faac/1.40/) |
| **faad2** | 2.11.2 | success |  | CMake | - | - | [📄](archives/f/faad2/2.11.2/) |
| **faas-cli** | 0.0.0-20260402103051 | ✅ 已编译 |  | go | - | [] | [📄](archives/f/faas-cli/0.0.0-20260402103051/) |
| **fabric-installer** | latest | ✅ 已编译 |  | shell_script | - | [] | [📄](archives/f/fabric-installer/latest/) |
| **facad** | 2.20.16 | ✅ 已发布 |  | Meson | - | - | [📄](archives/f/facad/2.20.16/) |
| **fairy-stockfish** | 14 | ✅ 已发布 |  |  | 1 | - | [📄](archives/f/fairy-stockfish/14/) |
| **fairymax** | 5.0b | ✅ 已发布 |  | Makefile | - | - | [📄](archives/f/fairymax/5.0b/) |
| **fakeroot** | 1.37.2 | ✅ 已发布 |  | Autotools | 3 | - | [📄](archives/f/fakeroot/1.37.2/) |
| **fakesteak** | 0.2.4 | ✅ 已发布 |  | Makefile | 1 | - | [📄](archives/f/fakesteak/0.2.4/) |
| **fann** | 2.2.0 | ✅ 已发布 |  |  | 1 | - | [📄](archives/f/fann/2.2.0/) |
| **farbfeld** | 4 | uploaded |  | unknown | 0 | - | [📄](archives/f/farbfeld/4/) |
| **fast_float** | 7.0.0 | ✅ 已发布 |  | CMake | - | - | [📄](archives/f/fast_float/7.0.0/) |
| **fastdds** | 2.1.0 | ✅ 已编译 |  |  | 5 | - | [📄](archives/f/fastdds/2.1.0/) |
| **fastfetch** | 2.63.1 | ✅ 已发布 |  | CMake | 2 | name: cmake | [📄](archives/f/fastfetch/2.63.1/) |
| **fastgron** | 0.7.7 | ✅ 已发布 |  |  | - | - | [📄](archives/f/fastgron/0.7.7/) |
| **fastjar** | 0.98 | uploaded |  | unknown | 0 | - | [📄](archives/f/fastjar/0.98/) |
| **faudio** | 26.05 | ✅ 已编译 |  | CMake | - | - | [📄](archives/f/faudio/26.05/) |
| **fb303** | v2026.05.18.00 | ✅ 已发布 |  | CMake | 1 | - | [📄](archives/f/fb303/v2026.05.18.00/) |
| **fbida** | 2.14、2.15 | ✅ 已编译 |  |  | 2 | - | [📄](archives/f/fbida/2.15/) |
| **fbthrift** | 2020.08.24.00 | ✅ 已编译 |  |  | 2 | - | [📄](archives/f/fbthrift/2020.08.24.00/) |
| **fcgi** | 2.4.7 | ✅ 已发布 |  | Autotools | 1 | - | [📄](archives/f/fcgi/2.4.7/) |
| **fcrackzip** | 1.0 | uploaded |  | unknown | 0 | - | [📄](archives/f/fcrackzip/1.0/) |
| **fcron** | 3.4.1pre | ✅ 已编译 |  | Autotools | 2 | - | [📄](archives/f/fcron/3.4.1pre/) |
| **fdclone** | 3.01j | ✅ 已发布 |  | Makefile | 1 | - | [📄](archives/f/fdclone/3.01j/) |
| **fdk-aac** | 2.0.3 | partial |  | CMake | - | [] | [📄](archives/f/fdk-aac/2.0.3/) |
| **fdupes** | 2.4.0 | ✅ 已发布 |  |  | 7 | - | [📄](archives/f/fdupes/2.4.0/) |
| **feedbackd** | 0.8.1 | ✅ 已编译 |  |  | - | - | [📄](archives/f/feedbackd/0.8.1/) |
| **fetchmail** | 6.6.4 | ✅ 已发布 |  |  | 3 | - | [📄](archives/f/fetchmail/6.6.4/) |
| **ffmpeg** | 2.8.9、4.4.6、7.1.4、8.1.1 | ✅ 已编译 |  |  | - | [] | [📄](archives/f/ffmpeg/8.1.1/) |
| **ffmpeg2theora** | 0.30 | ✅ 已编译 |  |  | 4 | - | [📄](archives/f/ffmpeg2theora/0.30/) |
| **ffmpegthumbnailer** | 2.3.0 | ✅ 已发布 |  |  | 2 | - | [📄](archives/f/ffmpegthumbnailer/2.3.0/) |
| **ffmpegthumbs** | 26.04.1 | ✅ 已编译 |  |  | 6 | - | [📄](archives/f/ffmpegthumbs/26.04.1/) |
| **ffms2** | 5.0 | ✅ 已编译 |  | Autotools | - | ffmpeg (libavformat >= 60.16.0, libavcodec >= 60.31.0, libswscale >= 7.5.0, libavutil >= 58.29.0, libswresample >= 4.12.0),zlib | [📄](archives/f/ffms2/5.0/) |
| **ffnvcodec-headers** | 13.0.19.0 | ✅ 已编译 |  |  | - | - | [📄](archives/f/ffnvcodec-headers/13.0.19.0/) |
| **fftw** | 3.3.10 | uploaded |  | unknown | 0 | - | [📄](archives/f/fftw/3.3.10/) |
| **ffuf** | 2.1.0-r21 | ✅ 已发布 |  | custom | 1 | - | [📄](archives/f/ffuf/2.1.0-r21/) |
| **fig2dev** | 3.2.9a | ✅ 已编译 |  | Autotools | 1 | - | [📄](archives/f/fig2dev/3.2.9a/) |
| **figlet** | 2.2.5 | success |  | Makefile | 1 | - | [📄](archives/f/figlet/2.2.5/) |
| **file** | 5.45、5.46 | ✅ 已编译 |  | Autotools | 3 | - | [📄](archives/f/file/5.46/) |
| **findent** | 4.3.6 | ✅ 已编译 |  | Autotools | 3 | - | [📄](archives/f/findent/4.3.6/) |
| **findutils** | 4.10.0 | ✅ 已编译 |  | Autotools | 2 | [] | [📄](archives/f/findutils/4.10.0/) |
| **fio** | 3.41 | partial |  | Autotools | 1 | - | [📄](archives/f/fio/3.41/) |
| **fish** | 3.7.1 | partial |  | Autotools | - | - | [📄](archives/f/fish/3.7.1/) |
| **fizz** | v2026.05.18.00 | ✅ 已编译 |  | CMake | - | - | [📄](archives/f/fizz/v2026.05.18.00/) |
| **flac** | 1.4.3 | uploaded |  | Autotools | 0 | - | [📄](archives/f/flac/1.4.3/) |
| **flactag** | 2.0.4 | ✅ 已发布 |  |  | 2 | - | [📄](archives/f/flactag/2.0.4/) |
| **flake** | 0.11 | ✅ 已发布 |  | custom | - | - | [📄](archives/f/flake/0.11/) |
| **flashrom** | 1.6.0 | ✅ 已编译 |  |  | - | - | [📄](archives/f/flashrom/1.6.0/) |
| **flatbuffers** | 24.3.25 | ✅ 已发布 |  | CMake | - | - | [📄](archives/f/flatbuffers/24.3.25/) |
| **flatcc** | 0.6.1 | ✅ 已发布 |  | CMake | - | - | [📄](archives/f/flatcc/0.6.1/) |
| **flex** | 2.6.4 | ✅ 已编译 |  |  | 5 | - | [📄](archives/f/flex/2.6.4/) |
| **flock** | 2.40.2 | ✅ 已发布 |  | Autotools | - | - | [📄](archives/f/flock/2.40.2/) |
| **fmt** | 11.2.0-r1 | ✅ 已编译 |  | CMake | - | - | [📄](archives/f/fmt/11.2.0-r1/) |
| **folly** | v2024.11.18.00 | ✅ 已编译 |  |  | 8 | - | [📄](archives/f/folly/v2024.11.18.00/) |
| **foma** | 0.10.0 | ✅ 已编译 |  | CMake | 1 | name: zlib,name: bison,name: flex,name: readline | [📄](archives/f/foma/0.10.0/) |
| **fontconfig** | 2.16.0、2.18.1 | ✅ 已编译 |  |  | - | - | [📄](archives/f/fontconfig/2.18.1/) |
| **fontforge** | 20230101-r6 | ✅ 已编译 |  |  | 2 | - | [📄](archives/f/fontforge/20230101-r6/) |
| **fonts-encodings** | 1.1.0 | ✅ 已发布 |  |  | 2 | - | [📄](archives/f/fonts-encodings/1.1.0/) |
| **fonttools** | 4.63.0 | ✅ 已编译 |  | custom | - | - | [📄](archives/f/fonttools/4.63.0/) |
| **foremost** | 1.5.7 | ✅ 已编译 |  |  | 4 | - | [📄](archives/f/foremost/1.5.7/) |
| **fortls** | 3.2.2 | ✅ 已发布 |  |  | 1 | - | [📄](archives/f/fortls/3.2.2/) |
| **fortune** | 9708 | ✅ 已发布 |  |  | 1 | - | [📄](archives/f/fortune/9708/) |
| **fpart** | 1.7.0 | ✅ 已发布 |  | Autotools | 1 | - | [📄](archives/f/fpart/1.7.0/) |
| **fpc** | 3.2.2 | ✅ 已编译 |  |  | - | - | [📄](archives/f/fpc/3.2.2/) |
| **fping** | 5.3 | ✅ 已发布 |  | Autotools | - | - | [📄](archives/f/fping/5.3/) |
| **fprobe-ulog** | 1.2 | ✅ 已发布 |  |  | - | - | [📄](archives/f/fprobe-ulog/1.2/) |
| **freac** | 1.1.7 | ✅ 已编译 |  |  | 3 | - | [📄](archives/f/freac/1.1.7/) |
| **freealut** | 1.1.0 | ✅ 已发布 |  | Autotools | 18 | - | [📄](archives/f/freealut/1.1.0/) |
| **freeimage** | 3.18.0 | ✅ 已发布 |  |  | 1 | - | [📄](archives/f/freeimage/3.18.0/) |
| **freeipmi** | 1.6.10 | ✅ 已编译 |  | cmake-manual | 2 | - | [📄](archives/f/freeipmi/1.6.10/) |
| **freerdp** | 3.26.0 | ✅ 已编译 |  | CMake | - | - | [📄](archives/f/freerdp/3.26.0/) |
| **freetds** | 1.4.23 | ✅ 已发布 |  |  | 3 | - | [📄](archives/f/freetds/1.4.23/) |
| **freetype** | 2.14.3 | uploaded |  | Autotools | 0 | - | [📄](archives/f/freetype/2.14.3/) |
| **frei0r-plugins** | 3.1.3 | ✅ 已编译 |  | CMake | 0 | - | [📄](archives/f/frei0r-plugins/3.1.3/) |
| **fribidi** | 1.0.13、1.0.16 | uploaded |  | Meson | 0 | - | [📄](archives/f/fribidi/1.0.16/) |
| **frotz** | 2.54 | ✅ 已发布 |  | Makefile | 1 | - | [📄](archives/f/frotz/2.54/) |
| **frp** | 0.65.0-r5 | ✅ 已编译 |  |  | - | - | [📄](archives/f/frp/0.65.0-r5/) |
| **fswatch** | 1.21.0 | ✅ 已编译 |  |  | 8 | - | [📄](archives/f/fswatch/1.21.0/) |
| **ftgl** | 2.4.0 | ✅ 已编译 |  |  | 2 | - | [📄](archives/f/ftgl/2.4.0/) |
| **ftxui** | 6.1.9 | uploaded |  | unknown | 0 | - | [📄](archives/f/ftxui/6.1.9/) |
| **fwup** | 1.16.0 | ✅ 已编译 |  | Autotools | - | libarchive (预编译包),libconfuse (预编译包),lzma (预编译包) | [📄](archives/f/fwup/1.16.0/) |
| **fzy** | 1.1 | ✅ 已发布 |  | Makefile | - | - | [📄](archives/f/fzy/1.1/) |
| **gallery-dl** | 1.32.1 | ✅ 已编译 |  | custom | - | - | [📄](archives/g/gallery-dl/1.32.1/) |
| **gambit** | v4.9.5 | ✅ 已发布 |  | Autotools | 3 | - | [📄](archives/g/gambit/v4.9.5/) |
| **gauche** | 0.9.15 | ✅ 已编译 |  |  | 27 | - | [📄](archives/g/gauche/0.9.15/) |
| **gawk** | 5.3.0 | verified |  | Autotools | 0 | - | [📄](archives/g/gawk/5.3.0/) |
| **gc** | 8.2.12 | ✅ 已发布 |  | CMake | 2 | - | [📄](archives/g/gc/8.2.12/) |
| **gcab** | 1.6 | ✅ 已发布 |  |  | 2 | - | [📄](archives/g/gcab/1.6/) |
| **gcalcli** | 4.3.0 | ✅ 已编译 |  |  | - | - | [📄](archives/g/gcalcli/4.3.0/) |
| **gcr** | 4.3.91 | ✅ 已发布 |  | Meson | 1 | name: glib,name: p11-kit,name: libgcrypt,name: libgpg-error | [📄](archives/g/gcr/4.3.91/) |
| **gd** | 2.3.3 | uploaded |  | unknown | 0 | - | [📄](archives/g/gd/2.3.3/) |
| **gdal** | 3.9.2 | ✅ 已发布 |  |  | - | - | [📄](archives/g/gdal/3.9.2/) |
| **gdb** | 14.1 | ✅ 已编译 |  | Autotools | 2 | - | [📄](archives/g/gdb/14.1/) |
| **gdbm** | 1.23 | verified |  | Autotools | 0 | - | [📄](archives/g/gdbm/1.23/) |
| **gdk-pixbuf** | 2.42.12、2.44.6 | ✅ 已编译 |  |  | - | - | [📄](archives/g/gdk-pixbuf/2.44.6/) |
| **gdnsd** | 3.8.2 | ✅ 已编译 |  | Autotools | 3 | - | [📄](archives/g/gdnsd/3.8.2/) |
| **gdu** | 5.36.1 | ✅ 已编译 |  |  | - | - | [📄](archives/g/gdu/5.36.1/) |
| **geckodriver** | 0.36.0 | ✅ 已发布 |  |  | - | - | [📄](archives/g/geckodriver/0.36.0/) |
| **geeqie** | 2.7 | ✅ 已编译 |  |  | - | - | [📄](archives/g/geeqie/2.7/) |
| **gegl** | 0.4.70、0.4.71 | ✅ 已发布 |  |  | 1 | - | [📄](archives/g/gegl/0.4.71/) |
| **gengetopt** | 2.23 | ✅ 已编译 |  |  | - | - | [📄](archives/g/gengetopt/2.23/) |
| **genimage** | 19 | ✅ 已编译 |  |  | 5 | - | [📄](archives/g/genimage/19/) |
| **gensio** | 3.0.2 | ✅ 已编译 |  |  | - | - | [📄](archives/g/gensio/3.0.2/) |
| **geos** | 3.13.0 | ✅ 已发布 |  | CMake | 0 | - | [📄](archives/g/geos/3.13.0/) |
| **gettext** | 0.22.5 | compiled_success |  | Autotools | 2 | [] | [📄](archives/g/gettext/0.22.5/) |
| **gflags** | 2.2.2 | partial |  | Autotools | - | - | [📄](archives/g/gflags/2.2.2/) |
| **ggml** | latest | ✅ 已编译 |  |  | - | - | [📄](archives/g/ggml/latest/) |
| **ggshield** | 1.51.0 | ✅ 已编译 |  |  | - | - | [📄](archives/g/ggshield/1.51.0/) |
| **ghostscript** | 10.07.1 | ✅ 已编译 |  |  | 7 | - | [📄](archives/g/ghostscript/10.07.1/) |
| **ghq** | 1.10.1、1.9.4 | ✅ 已发布 |  | custom | - | - | [📄](archives/g/ghq/1.9.4/) |
| **gifify** | 2.4.0 | ✅ 已编译 |  |  | 3 | - | [📄](archives/g/gifify/2.4.0/) |
| **giflib** | 5.2.2 | uploaded |  | unknown | 0 | - | [📄](archives/g/giflib/5.2.2/) |
| **gifsicle** | 1.96 | ✅ 已编译 |  |  | - | - | [📄](archives/g/gifsicle/1.96/) |
| **gifski** | 1.34.0 | ✅ 已编译 |  | cargo | 3 | - | [📄](archives/g/gifski/1.34.0/) |
| **git** | 2.49.0、2.45 | partial |  | Autotools | - | - | [📄](archives/g/git/2.45/) |
| **git-cliff** | 2.10.1 | ✅ 已发布 |  | cargo | - | - | [📄](archives/g/git-cliff/2.10.1/) |
| **git-crypt** | 0.8.0 | ✅ 已编译 |  |  | - | - | [📄](archives/g/git-crypt/0.8.0/) |
| **git-flow** | 1.12.3 | ✅ 已发布 |  |  | 1 | - | [📄](archives/g/git-flow/1.12.3/) |
| **git-lfs** | 3.7.0 | ✅ 已编译 |  | go | - | - | [📄](archives/g/git-lfs/3.7.0/) |
| **git-remote-codecommit** | 1.17 | ✅ 已发布 |  | pip | - | - | [📄](archives/g/git-remote-codecommit/1.17/) |
| **git-secrets** | 1.3.0 | ✅ 已编译 |  | Makefile | - | - | [📄](archives/g/git-secrets/1.3.0/) |
| **git-town** | 16.4.1 | ✅ 已发布 |  | custom | - | - | [📄](archives/g/git-town/16.4.1/) |
| **git-xet** | homebrew | ✅ 已发布 |  |  | - | - | [📄](archives/g/git-xet/homebrew/) |
| **github-mcp-server** | 1.2.0 | ✅ 已编译 |  | go | - | - | [📄](archives/g/github-mcp-server/1.2.0/) |
| **gitui** | 0.27.0-r1 | ✅ 已发布 |  | rust (precompiled_binary) | - | oniguruma,openssl,libgcc,musl,pcre2... | [📄](archives/g/gitui/0.27.0-r1/) |
| **glances** | 4.5.4 | ✅ 已编译 |  |  | 2 | - | [📄](archives/g/glances/4.5.4/) |
| **glaze** | 7.7.0 | ✅ 已发布 |  |  | - | - | [📄](archives/g/glaze/7.7.0/) |
| **gleam** | 1.17.0-r0 | ✅ 已发布 |  |  | - | - | [📄](archives/g/gleam/1.17.0-r0/) |
| **glew** | 2.2.0、2.3.1 | ❌ 编译失败 |  |  | - | - | [📄](archives/g/glew/2.3.1/) |
| **glfw** | 3.4、3.4.6 | ✅ 已编译 |  | CMake | - | - | [📄](archives/g/glfw/3.4.6/) |
| **glib** | 2.84.0 | ✅ 已编译 |  | Meson | 3 | libffi >= 3.4.4,pcre2 >= 10.47,meson >= 1.11.1,ninja >= 1.13 | [📄](archives/g/glib/2.84.0/) |
| **glm** | 0.9.9.8 | uploaded |  | CMake | 0 | - | [📄](archives/g/glm/0.9.9.8/) |
| **global** | 6.6.8 | ✅ 已编译 |  | Autotools | 2 | - | [📄](archives/g/global/6.6.8/) |
| **glog** | 0.7.1 | partial |  | Autotools | 1 | - | [📄](archives/g/glog/0.7.1/) |
| **glpk** | 5.0 | ✅ 已发布 |  |  | 2 | - | [📄](archives/g/glpk/5.0/) |
| **glproto** | 1.4.17 | compiling |  | Autotools | - | - | [📄](archives/g/glproto/1.4.17/) |
| **glslang** | vulkan-sdk-1.3.290.0 | ✅ 已编译 |  | CMake | 1 | cmake >= 3.17.2,gcc,g++,spirv-tools | [📄](archives/g/glslang/vulkan-sdk-1.3.290.0/) |
| **gmime** | 3.2.7 | ✅ 已编译 |  | Autotools | - | glib/2.84.0 | [📄](archives/g/gmime/3.2.7/) |
| **gmp** | 6.3.0 | ✅ 已编译 |  | Autotools | 3 | [] | [📄](archives/g/gmp/6.3.0/) |
| **gmssl** | 3.1.1 | uploaded |  | CMake | 0 | - | [📄](archives/g/gmssl/3.1.1/) |
| **gnome-autoar** | 0.4.5 | ✅ 已编译 |  | Meson | 0 | - | [📄](archives/g/gnome-autoar/0.4.5/) |
| **gnu-which** | 2.25 | ✅ 已编译 |  |  | 3 | - | [📄](archives/g/gnu-which/2.25/) |
| **gnuastro** | 0.24 | ✅ 已编译 |  | Autotools | 2 | - | [📄](archives/g/gnuastro/0.24/) |
| **gnugo** | 3.8 | ✅ 已编译 |  | Autotools | 2 | [] | [📄](archives/g/gnugo/3.8/) |
| **gnupg** | 2.4.9 | ✅ 已编译 |  | Autotools | - | - | [📄](archives/g/gnupg/2.4.9/) |
| **gnuplot** | 5.4.10 | ✅ 已发布 |  | Autotools | 1 | - | [📄](archives/g/gnuplot/5.4.10/) |
| **gnutls** | 3.8.10、3.8.4 | ❌ 编译失败 |  |  | 2 | - | [📄](archives/g/gnutls/3.8.4/) |
| **go** | 1.21.13 | ✅ 已发布 |  | go_bootstrap | - | go-bootstrap >= 1.20 | [📄](archives/g/go/1.21.13/) |
| **goaccess** | 1.10.2 | unknown |  |  | 3 | - | [📄](archives/g/goaccess/1.10.2/) |
| **gobject-introspection** | 1.78.1 | ✅ 已编译 |  |  | 1 | - | [📄](archives/g/gobject-introspection/1.78.1/) |
| **gobo** | 26.03 | ✅ 已发布 |  |  | 1 | - | [📄](archives/g/gobo/26.03/) |
| **gobuster** | 3.8.2、v3.8.2 | ✅ 已编译 |  | go | - | [] | [📄](archives/g/gobuster/v3.8.2/) |
| **goenv** | 3.1.1 | ✅ 已发布 |  | go | - | - | [📄](archives/g/goenv/3.1.1/) |
| **goimapnotify** | 2.5.3-r7 | ✅ 已编译 |  |  | - | - | [📄](archives/g/goimapnotify/2.5.3-r7/) |
| **goimports** | 0.32.0 | ✅ 已编译 |  |  | - | - | [📄](archives/g/goimports/0.32.0/) |
| **golang-migrate** | homebrew | ✅ 已编译 |  |  | - | - | [📄](archives/g/golang-migrate/homebrew/) |
| **googletest** | 1.15.2 | ✅ 已发布 |  |  | - | - | [📄](archives/g/googletest/1.15.2/) |
| **goose** | v3.27.1 | ✅ 已编译 |  | go | - | [] | [📄](archives/g/goose/v3.27.1/) |
| **gosec** | 2.22.8 | ✅ 已发布 |  | go | - | - | [📄](archives/g/gosec/2.22.8/) |
| **gost** | 3.2.5 | ✅ 已发布 |  | go | - | - | [📄](archives/g/gost/3.2.5/) |
| **got** | 0.126 | ✅ 已编译 |  | Autotools | 3 | libbsd (0.11.7),libmd (1.1.0),libcrypto (OpenSSL),libevent (2.1.12),libuuid (1.47.0)... | [📄](archives/g/got/0.126/) |
| **gotop** | 4.2.0 | ✅ 已编译 |  | custom | - | - | [📄](archives/g/gotop/4.2.0/) |
| **gpatch** | 2.8 | partial |  | Autotools | 2 | libattr (未安装，无xattr支持) | [📄](archives/g/gpatch/2.8/) |
| **gperf** | 3.1 | ✅ 已发布 |  |  | - | - | [📄](archives/g/gperf/3.1/) |
| **gpgme** | 1.24.0 | ✅ 已编译 |  | Autotools | 12 | - | [📄](archives/g/gpgme/1.24.0/) |
| **gpgmepp** | 1.23.2 | compiled |  | Autotools | 3 | - | [📄](archives/g/gpgmepp/1.23.2/) |
| **gphoto2** | 2.5.32 | ✅ 已编译 |  | Autotools | 3 | - | [📄](archives/g/gphoto2/2.5.32/) |
| **gping** | 1.20.1-r0 | ✅ 已发布 |  | cargo | - | openssl@3,rustc,cargo | [📄](archives/g/gping/1.20.1-r0/) |
| **gpp** | 2.28 | ✅ 已发布 |  |  | - | - | [📄](archives/g/gpp/2.28/) |
| **gputils** | 1.5.0 | ✅ 已编译 |  | Autotools | 2 | - | [📄](archives/g/gputils/1.5.0/) |
| **gpx** | 2.6.8 | ✅ 已发布 |  |  | 2 | - | [📄](archives/g/gpx/2.6.8/) |
| **graphicsmagick** | 1.3.47 | ✅ 已编译 |  |  | 4 | - | [📄](archives/g/graphicsmagick/1.3.47/) |
| **graphviz** | 12.2.1 | ✅ 已发布 |  |  | - | - | [📄](archives/g/graphviz/12.2.1/) |
| **grep** | 3.11 | ✅ 已编译 |  | Autotools | 1 | pcre2 10.47 (system preinstalled) | [📄](archives/g/grep/3.11/) |
| **grepcidr** | 2.0 | ✅ 已编译 |  | Makefile | - | - | [📄](archives/g/grepcidr/2.0/) |
| **grilo** | 0.3.19 | ✅ 已编译 |  |  | - | name: glib-2.0,name: gio-2.0,name: libxml-2.0,name: libsoup-2.4,name: totem-plparser | [📄](archives/g/grilo/0.3.19/) |
| **grilo-plugins** | 0.3.16 | ✅ 已发布 |  |  | - | - | [📄](archives/g/grilo-plugins/0.3.16/) |
| **grim** | 1.4.0 | ✅ 已编译 |  | Meson | - | - | [📄](archives/g/grim/1.4.0/) |
| **groff** | 1.23.0 | ✅ 已发布 |  | Autotools | 2 | - | [📄](archives/g/groff/1.23.0/) |
| **grommunio-error-pages** | 1.0_git20231031-r0 | ✅ 已编译 |  |  | - | - | [📄](archives/g/grommunio-error-pages/1.0_git20231031-r0/) |
| **grpc** | 1.49.2 | ✅ 已编译 |  | CMake | 1 | - | [📄](archives/g/grpc/1.49.2/) |
| **grpcui** | homebrew | ✅ 已编译 |  |  | - | - | [📄](archives/g/grpcui/homebrew/) |
| **grpcurl** | 1.9.3 | ✅ 已发布 |  |  | - | - | [📄](archives/g/grpcurl/1.9.3/) |
| **grype** | 0.112.0 | ✅ 已编译 |  | custom | - | - | [📄](archives/g/grype/0.112.0/) |
| **gsasl** | 1.8.1 | ✅ 已发布 |  |  | 3 | - | [📄](archives/g/gsasl/1.8.1/) |
| **gsettings-desktop-schemas** | 49.1 | ✅ 已编译 |  | Meson | - | - | [📄](archives/g/gsettings-desktop-schemas/49.1/) |
| **gsl** | 2.7 | ✅ 已发布 |  |  | 2 | - | [📄](archives/g/gsl/2.7/) |
| **gsm** | 1.0.22、1.0.23 | uploaded |  | unknown | 0 | - | [📄](archives/g/gsm/1.0.23/) |
| **gsoap** | 2.8.142 | ✅ 已编译 |  |  | 8 | - | [📄](archives/g/gsoap/2.8.142/) |
| **gss** | 1.0.4 | ✅ 已编译 |  |  | 8 | - | [📄](archives/g/gss/1.0.4/) |
| **gst-libav** | 1.28.3 | ✅ 已编译 |  | Meson | - | - | [📄](archives/g/gst-libav/1.28.3/) |
| **gst-plugins-bad** | 1.28.3 | ✅ 已编译 |  | Meson | - | - | [📄](archives/g/gst-plugins-bad/1.28.3/) |
| **gst-plugins-base** | 1.28.3 | ✅ 已编译 |  | Meson | - | - | [📄](archives/g/gst-plugins-base/1.28.3/) |
| **gst-plugins-good** | 1.28.3 | ✅ 已编译 |  | Meson | - | - | [📄](archives/g/gst-plugins-good/1.28.3/) |
| **gst-plugins-ugly** | 1.28.3 | ✅ 已编译 |  | Meson | - | - | [📄](archives/g/gst-plugins-ugly/1.28.3/) |
| **gst-rtsp-server** | 1.28.3 | ✅ 已编译 |  | Meson | - | - | [📄](archives/g/gst-rtsp-server/1.28.3/) |
| **gstreamer** | 1.28.3 | ✅ 已编译 |  |  | 2 | - | [📄](archives/g/gstreamer/1.28.3/) |
| **gti** | 1.9.1 | ✅ 已编译 |  | Makefile | - | [] | [📄](archives/g/gti/1.9.1/) |
| **gtk+** | 3.24.38 | ✅ 已发布 |  |  | - | - | [📄](archives/g/gtk+/3.24.38/) |
| **gtk4** | 4.22.4 | ✅ 已编译 |  | Meson | 1 | - | [📄](archives/g/gtk4/4.22.4/) |
| **guile** | 2.2.7 | ✅ 已发布 |  | Autotools | 3 | - | [📄](archives/g/guile/2.2.7/) |
| **gum** | 0.17.0 | ✅ 已编译 |  | go | - | - | [📄](archives/g/gum/0.17.0/) |
| **gwenhywfar** | 5.14.1 | ✅ 已发布 |  |  | 3 | - | [📄](archives/g/gwenhywfar/5.14.1/) |
| **gzip** | 1.13 | verified |  | Autotools | 0 | - | [📄](archives/g/gzip/1.13/) |
| **h2** | 2.2.224 | ✅ 已发布 |  | maven | - | java >= 8,maven >= 3.6 | [📄](archives/h/h2/2.2.224/) |
| **h264bitstream** | 0.2.0 | ✅ 已发布 |  | Autotools | 4 | - | [📄](archives/h/h264bitstream/0.2.0/) |
| **hackrf** | 2024.02.1-r1 | ✅ 已编译 |  |  | 1 | - | [📄](archives/h/hackrf/2024.02.1-r1/) |
| **hamlib** | 4.7.1 | ✅ 已发布 |  |  | - | - | [📄](archives/h/hamlib/4.7.1/) |
| **haproxy** | 3.2.0 | ✅ 已发布 |  |  | - | name: openssl,name: zlib,name: pcre2 | [📄](archives/h/haproxy/3.2.0/) |
| **harfbuzz** | 14.2.0 | uploaded |  | Meson | 0 | - | [📄](archives/h/harfbuzz/14.2.0/) |
| **harper** | 2.4.0 | ✅ 已编译 |  | cargo | - | - | [📄](archives/h/harper/2.4.0/) |
| **hashcat** | 7.1.2 | ✅ 已发布 |  | Makefile | 3 | - | [📄](archives/h/hashcat/7.1.2/) |
| **hcxtools** | 7.1.2 | ✅ 已发布 |  | Makefile | - | - | [📄](archives/h/hcxtools/7.1.2/) |
| **hdf5** | 1.13.0、1.14.4 | ✅ 已编译 |  | CMake | - | - | [📄](archives/h/hdf5/1.14.4/) |
| **hdrhistogram** | 0.11.9 | ✅ 已发布 |  |  | 1 | - | [📄](archives/h/hdrhistogram/0.11.9/) |
| **hebcal** | 4.31 | ✅ 已编译 |  | Autotools | 17 | - | [📄](archives/h/hebcal/4.31/) |
| **heirloom-doctools** | 191015 | ✅ 已编译 |  |  | 16 | - | [📄](archives/h/heirloom-doctools/191015/) |
| **helix** | 25.07.1 | ✅ 已编译 |  |  | 1 | - | [📄](archives/h/helix/25.07.1/) |
| **hello** | 2.12 | ✅ 已发布 |  | Autotools | 4 | - | [📄](archives/h/hello/2.12/) |
| **hellwal** | 1.0.7 | ✅ 已发布 |  | Makefile | 1 | - | [📄](archives/h/hellwal/1.0.7/) |
| **help2man** | 1.49.3 | verified |  | Autotools | 0 | - | [📄](archives/h/help2man/1.49.3/) |
| **hermes** | 1.9 | ✅ 已发布 |  |  | - | - | [📄](archives/h/hermes/1.9/) |
| **hexcurse** | 1.60.0 | ✅ 已发布 |  |  | 18 | - | [📄](archives/h/hexcurse/1.60.0/) |
| **hexedit** | 1.6 | ✅ 已发布 |  | Autotools | 1 | ncurses/6.4 | [📄](archives/h/hexedit/1.6/) |
| **hexinject** | 1.6-r2 | ✅ 已编译 |  |  | - | - | [📄](archives/h/hexinject/1.6-r2/) |
| **hfsutils** | 3.2.6 | ✅ 已发布 |  | Autotools | 2 | - | [📄](archives/h/hfsutils/3.2.6/) |
| **hidapi** | 0.14.0 | ✅ 已编译 |  |  | - | - | [📄](archives/h/hidapi/0.14.0/) |
| **highlight** | 4.18 | ✅ 已发布 |  |  | - | - | [📄](archives/h/highlight/4.18/) |
| **himalaya** | 1.1.0-r0 | ✅ 已编译 |  |  | - | - | [📄](archives/h/himalaya/1.1.0-r0/) |
| **hiredis** | 1.2.0 | uploaded |  | Autotools | 0 | - | [📄](archives/h/hiredis/1.2.0/) |
| **hitch** | 1.8.0-r1 | ✅ 已编译 |  |  | 2 | - | [📄](archives/h/hitch/1.8.0-r1/) |
| **hmmer** | 3.4 | ✅ 已发布 |  |  | 3 | - | [📄](archives/h/hmmer/3.4/) |
| **hnswlib** | 0.8.0 | ✅ 已编译 |  | CMake | - | - | [📄](archives/h/hnswlib/0.8.0/) |
| **homebrew** | 5.1.12 | ✅ 已编译 |  | Script | 1 | bash >= 5.0,ruby >= 3.0 | [📄](archives/h/homebrew/5.1.12/) |
| **hping** | 3.0.0-alpha-1 | ✅ 已编译 |  | Makefile | 2 | libpcap | [📄](archives/h/hping/3.0.0-alpha-1/) |
| **hstr** | 3.2 | ✅ 已编译 |  | Autotools | 4 | ncursesw (static),readline,libm | [📄](archives/h/hstr/3.2/) |
| **html2text** | 2.4.0 | ✅ 已发布 |  |  | - | - | [📄](archives/h/html2text/2.4.0/) |
| **htop** | 3.4.1 | verified |  | Makefile | 0 | - | [📄](archives/h/htop/3.4.1/) |
| **htpdate** | 1.3.7 | ✅ 已编译 |  | Makefile | 1 | - | [📄](archives/h/htpdate/1.3.7/) |
| **http-prompt** | 2.1.0 | ✅ 已编译 |  | python | - | - | [📄](archives/h/http-prompt/2.1.0/) |
| **http-server** | 14.1.0 | ✅ 已发布 |  |  | - | - | [📄](archives/h/http-server/14.1.0/) |
| **httpd** | 2.4.67 | ✅ 已发布 |  |  | 2 | - | [📄](archives/h/httpd/2.4.67/) |
| **httpry** | 0.1.8 | ✅ 已发布 |  |  | - | - | [📄](archives/h/httpry/0.1.8/) |
| **httpx** | 1.9.0 | ✅ 已编译 |  |  | - | - | [📄](archives/h/httpx/1.9.0/) |
| **httrack** | 3.49.2 | ✅ 已发布 |  | Autotools | 3 | openssl,zlib | [📄](archives/h/httrack/3.49.2/) |
| **hub** | 2.14.2 | ✅ 已编译 |  | go | - | - | [📄](archives/h/hub/2.14.2/) |
| **hubble** | v1.17.2 | ✅ 已发布 |  | go | - | - | [📄](archives/h/hubble/v1.17.2/) |
| **hunspell** | 1.7.2 | ✅ 已编译 |  | Autotools | 3 | - | [📄](archives/h/hunspell/1.7.2/) |
| **hurl** | 8.0.1 | ✅ 已编译 |  |  | - | - | [📄](archives/h/hurl/8.0.1/) |
| **hwinfo** | 25.2 | ✅ 已编译 |  | Makefile | 1 | [] | [📄](archives/h/hwinfo/25.2/) |
| **hwloc** | 2.11.0 | partial |  | Autotools | 1 | - | [📄](archives/h/hwloc/2.11.0/) |
| **hydra** | 9.6-r1 | ✅ 已发布 |  | Autotools | 1 | - | [📄](archives/h/hydra/9.6-r1/) |
| **hydroxide** | 0.2.29-r14 | ✅ 已编译 |  |  | - | - | [📄](archives/h/hydroxide/0.2.29-r14/) |
| **hyperfine** | 1.20.0-r0 | ✅ 已发布 |  | rust | - | - | [📄](archives/h/hyperfine/1.20.0-r0/) |
| **iat** | 0.1.7 | ✅ 已发布 |  | Autotools | - | - | [📄](archives/i/iat/0.1.7/) |
| **icon** | 9.5.25a | ✅ 已编译 |  | custom | 4 | - | [📄](archives/i/icon/9.5.25a/) |
| **icoutils** | 0.32.3 | ✅ 已发布 |  |  | - | - | [📄](archives/i/icoutils/0.32.3/) |
| **icu4c** | 78 | ✅ 已编译 |  | Autotools | 1 | [] | [📄](archives/i/icu4c/78/) |
| **id3lib** | 3.8.3 | ✅ 已发布 |  |  | 9 | - | [📄](archives/i/id3lib/3.8.3/) |
| **idutils** | 4.6 | ✅ 已发布 |  | Autotools | 7 | - | [📄](archives/i/idutils/4.6/) |
| **ifstat** | 1.1 | ✅ 已发布 |  | Autotools | 1 | - | [📄](archives/i/ifstat/1.1/) |
| **iftop** | 1.0_pre4-r0 | ✅ 已编译 |  |  | 6 | - | [📄](archives/i/iftop/1.0_pre4-r0/) |
| **igmpproxy** | 0.4 | ✅ 已发布 |  |  | - | - | [📄](archives/i/igmpproxy/0.4/) |
| **iir1** | 1.10.0 | ✅ 已编译 |  | CMake | - | [] | [📄](archives/i/iir1/1.10.0/) |
| **imagemagick** | 7.1.2-23、7.1.2-24 | ✅ 已发布 |  |  | - | - | [📄](archives/i/imagemagick/7.1.2-24/) |
| **imagemagick-full** | 7.1.2-23 | ✅ 已编译 |  | Autotools | 20 | - | [📄](archives/i/imagemagick-full/7.1.2-23/) |
| **imath** | 3.2.2 | ✅ 已发布 |  |  | - | - | [📄](archives/i/imath/3.2.2/) |
| **img2pdf** | 0.6.3 | ✅ 已编译 |  | custom | 1 | - | [📄](archives/i/img2pdf/0.6.3/) |
| **imlib2** | 1.12.6 | ✅ 已发布 |  | Autotools | 3 | - | [📄](archives/i/imlib2/1.12.6/) |
| **inadyn** | 2.12.0-r0 | ✅ 已编译 |  | Autotools | - | - | [📄](archives/i/inadyn/2.12.0-r0/) |
| **incron** | 0.5.12 | ✅ 已编译 |  |  | 3 | - | [📄](archives/i/incron/0.5.12/) |
| **incus** | 7.1.0 | ✅ 已编译 |  | custom | - | - | [📄](archives/i/incus/7.1.0/) |
| **inetutils** | 2.5 | ❌ 编译失败 |  |  | - | - | [📄](archives/i/inetutils/2.5/) |
| **infisical** | 0.18.2 | ✅ 已编译 |  | go | - | - | [📄](archives/i/infisical/0.18.2/) |
| **inframap** | v0.8.1 | ✅ 已编译 |  | go | - | - | [📄](archives/i/inframap/v0.8.1/) |
| **inih** | r58 | ✅ 已编译 |  |  | - | - | [📄](archives/i/inih/r58/) |
| **iniparser** | 4.2.6 | ✅ 已发布 |  | CMake | - | - | [📄](archives/i/iniparser/4.2.6/) |
| **innoextract** | 1.9 | ✅ 已编译 |  |  | 2 | - | [📄](archives/i/innoextract/1.9/) |
| **inotify-tools** | 4.25.9.0 | ✅ 已发布 |  | Autotools | 2 | - | [📄](archives/i/inotify-tools/4.25.9.0/) |
| **internetarchive** | 5.10.1 | ✅ 已发布 |  |  | - | - | [📄](archives/i/internetarchive/5.10.1/) |
| **intltool** | 0.51.0 | uploaded |  | Autotools | 0 | - | [📄](archives/i/intltool/0.51.0/) |
| **iodine** | 0.8.0 | ✅ 已发布 |  | Makefile | 1 | - | [📄](archives/i/iodine/0.8.0/) |
| **ipatool** | 2.3.0 | ✅ 已编译 |  | go | - | - | [📄](archives/i/ipatool/2.3.0/) |
| **ipcalc** | 1.0.3 | ✅ 已发布 |  | Makefile | 1 | - | [📄](archives/i/ipcalc/1.0.3/) |
| **iperf** | 2.2.1 | ✅ 已编译 |  | Autotools | 4 | - | [📄](archives/i/iperf/2.2.1/) |
| **iperf3** | 3.18 | uploaded |  | unknown | 0 | - | [📄](archives/i/iperf3/3.18/) |
| **ipinfo** | 1.2 | ✅ 已编译 |  |  | 1 | - | [📄](archives/i/ipinfo/1.2/) |
| **ipopt** | 3.14.19 | ✅ 已编译 |  |  | 2 | - | [📄](archives/i/ipopt/3.14.19/) |
| **iputils** | 20240905 | ✅ 已发布 |  |  | 1 | meson >= 0.44,ninja,clang/gcc,libcap (未安装，禁用 USE_CAP),libidn2 (未安装，禁用 USE_IDN)... | [📄](archives/i/iputils/20240905/) |
| **ipv6toolkit** | 2.2 | ✅ 已发布 |  | Makefile | 1 | - | [📄](archives/i/ipv6toolkit/2.2/) |
| **ircii** | 20240918 | ✅ 已发布 |  |  | - | - | [📄](archives/i/ircii/20240918/) |
| **irssi** | 1.4.5 | ✅ 已发布 |  | Autotools | 3 | - | [📄](archives/i/irssi/1.4.5/) |
| **isa-l_crypto** | 2.26 | uploaded |  | CMake | 0 | - | [📄](archives/i/isa-l_crypto/2.26/) |
| **isl26** | 0.26 | ✅ 已编译 |  | Autotools | 3 | - | [📄](archives/i/isl26/0.26/) |
| **iso-codes** | 4.16.0 | ✅ 已编译 |  | Autotools | - | [] | [📄](archives/i/iso-codes/4.16.0/) |
| **isort** | 5.13.2、8.0.1 | ✅ 已编译 |  | python | - | - | [📄](archives/i/isort/8.0.1/) |
| **isync** | 1.5.1 | ✅ 已编译 |  | Autotools | 3 | - | [📄](archives/i/isync/1.5.1/) |
| **ivykis** | 0.42、0.43.2 | ✅ 已发布 |  |  | - | - | [📄](archives/i/ivykis/0.43.2/) |
| **iwgtk** | 0.9 | ✅ 已编译 |  |  | - | - | [📄](archives/i/iwgtk/0.9/) |
| **jack** | 1.9.22 | ✅ 已编译 |  |  | 4 | - | [📄](archives/j/jack/1.9.22/) |
| **janet** | 1.41.2 | ✅ 已发布 |  | Autotools | 1 | - | [📄](archives/j/janet/1.41.2/) |
| **jansson** | 2.15.0 | uploaded |  | Autotools | 0 | - | [📄](archives/j/jansson/2.15.0/) |
| **jasper** | 4.2.9 | uploaded |  | unknown | 0 | - | [📄](archives/j/jasper/4.2.9/) |
| **jbig2dec** | 0.20 | uploaded |  | unknown | 0 | - | [📄](archives/j/jbig2dec/0.20/) |
| **jc** | 1.25.6 | ✅ 已编译 |  |  | - | - | [📄](archives/j/jc/1.25.6/) |
| **jcal** | 0.4.1 | ✅ 已发布 |  |  | 1 | - | [📄](archives/j/jcal/0.4.1/) |
| **jd** | homebrew | ✅ 已编译 |  |  | - | - | [📄](archives/j/jd/homebrew/) |
| **jemalloc** | 5.3.0 | ✅ 已发布 |  | Autotools | 2 | - | [📄](archives/j/jemalloc/5.3.0/) |
| **jenkins** | 2.541.2 | ✅ 已发布 |  |  | - | - | [📄](archives/j/jenkins/2.541.2/) |
| **jhead** | 3.08 | ✅ 已发布 |  | Makefile | 1 | - | [📄](archives/j/jhead/3.08/) |
| **jigdo** | 0.8.2 | ✅ 已编译 |  |  | 1 | - | [📄](archives/j/jigdo/0.8.2/) |
| **jira-cli** | 1.7.0 | ✅ 已编译 |  | go | - | - | [📄](archives/j/jira-cli/1.7.0/) |
| **jitterentropy-library** | 3.6.3 | ✅ 已编译 |  |  | 0 | - | [📄](archives/j/jitterentropy-library/3.6.3/) |
| **jjui** | 0.10.6 | ✅ 已编译 |  | go | - | - | [📄](archives/j/jjui/0.10.6/) |
| **jna** | 5.19.0 | ✅ 已发布 |  |  | - | - | [📄](archives/j/jna/5.19.0/) |
| **jnettop** | 0.13.0 | ✅ 已发布 |  |  | 1 | - | [📄](archives/j/jnettop/0.13.0/) |
| **jo** | 1.9 | partial |  | Autotools | 5 | - | [📄](archives/j/jo/1.9/) |
| **joe** | 4.6 | ✅ 已发布 |  | Autotools | 4 | - | [📄](archives/j/joe/4.6/) |
| **john** | 1.9.0-jumbo-1、bleeding-jumbo | ✅ 已编译 |  | Autotools | 2 | - | [📄](archives/j/john/bleeding-jumbo/) |
| **jpdfbookmarks** | 2.5.4 | ✅ 已发布 |  | custom | 2 | - | [📄](archives/j/jpdfbookmarks/2.5.4/) |
| **jpeg** | 10 | success |  | Autotools | 2 | - | [📄](archives/j/jpeg/10/) |
| **jpeginfo** | 1.7.1 | ✅ 已编译 |  | Autotools | 3 | - | [📄](archives/j/jpeginfo/1.7.1/) |
| **jq** | 1.7.1 | verified |  | Autotools | 0 | - | [📄](archives/j/jq/1.7.1/) |
| **jshn** | 2025.11.14 | ✅ 已编译 |  |  | 1 | - | [📄](archives/j/jshn/2025.11.14/) |
| **json-c** | 0.16 | partial |  |  | 1 | - | [📄](archives/j/json-c/0.16/) |
| **json-glib** | 1.6.6 | ✅ 已编译 |  |  | 1 | - | [📄](archives/j/json-glib/1.6.6/) |
| **jsoncpp** | 1.9.5 | ✅ 已发布 |  | CMake | - | - | [📄](archives/j/jsoncpp/1.9.5/) |
| **jsonlint** | 1.6.3 | ✅ 已发布 |  | custom | - | - | [📄](archives/j/jsonlint/1.6.3/) |
| **jsonnet** | v0.20.0 | ✅ 已发布 |  | Makefile | 1 | - | [📄](archives/j/jsonnet/v0.20.0/) |
| **jsonrpc-glib** | 3.44.0 | ✅ 已发布 |  | Meson | - | - | [📄](archives/j/jsonrpc-glib/3.44.0/) |
| **judy** | 1.0.5 | ✅ 已发布 |  | Autotools | 3 | - | [📄](archives/j/judy/1.0.5/) |
| **katago** | v1.13.2 | ✅ 已编译 |  |  | 1 | - | [📄](archives/k/katago/v1.13.2/) |
| **kcgi** | 0.13.4 | ✅ 已发布 |  | bmake | - | - | [📄](archives/k/kcgi/0.13.4/) |
| **kcov** | 38 | ✅ 已发布 |  | CMake | 4 | - | [📄](archives/k/kcov/38/) |
| **kdegraphics-mobipocket** | 26.04.1 | ✅ 已编译 |  | CMake | - | - | [📄](archives/k/kdegraphics-mobipocket/26.04.1/) |
| **kealib** | 1.6.2 | ✅ 已编译 |  | CMake | - | - | [📄](archives/k/kealib/1.6.2/) |
| **keychain** | 2.9.8 | ✅ 已编译 |  |  | 0 | - | [📄](archives/k/keychain/2.9.8/) |
| **keyfinder-cli** | 1.2.0 | ✅ 已发布 |  | CMake | 4 | - | [📄](archives/k/keyfinder-cli/1.2.0/) |
| **keyring** | 25.6.0 | ✅ 已发布 |  | pip | - | - | [📄](archives/k/keyring/25.6.0/) |
| **kid3** | 3.9.7 | ✅ 已发布 |  | CMake | 4 | - | [📄](archives/k/kid3/3.9.7/) |
| **kimageformats** | 6.26.0 | ✅ 已编译 |  | CMake | - | - | [📄](archives/k/kimageformats/6.26.0/) |
| **kissat** | 4.0.4 | ✅ 已发布 |  | custom | - | - | [📄](archives/k/kissat/4.0.4/) |
| **kissfft** | 131.2.0 | ✅ 已发布 |  |  | - | - | [📄](archives/k/kissfft/131.2.0/) |
| **kompose** | homebrew | ✅ 已发布 |  |  | - | - | [📄](archives/k/kompose/homebrew/) |
| **kona** | 20211225 | ✅ 已发布 |  | Makefile | 1 | - | [📄](archives/k/kona/20211225/) |
| **kosli-cli** | 2.24.2 | ✅ 已发布 |  |  | - | - | [📄](archives/k/kosli-cli/2.24.2/) |
| **kpartx** | 0.14.3 | ✅ 已编译 |  | make | - | name: libdevmapper | [📄](archives/k/kpartx/0.14.3/) |
| **kquickimageeditor** | 0.3.0 | ✅ 已编译 |  | CMake | - | - | [📄](archives/k/kquickimageeditor/0.3.0/) |
| **kquickimageeditor5** | 0.2.0 | ✅ 已编译 |  | CMake | - | - | [📄](archives/k/kquickimageeditor5/0.2.0/) |
| **krb5** | 1.22.1、1.22.2 | ✅ 已编译 |  |  | 4 | - | [📄](archives/k/krb5/1.22.2/) |
| **kube-ps1** | 1.0.0 | ✅ 已发布 |  | shell | - | - | [📄](archives/k/kube-ps1/1.0.0/) |
| **kubebuilder** | 4.14.0 | ✅ 已发布 |  | custom | - | - | [📄](archives/k/kubebuilder/4.14.0/) |
| **kubecolor** | 0.0.25 | ✅ 已编译 |  | go | - | - | [📄](archives/k/kubecolor/0.0.25/) |
| **kubelogin** | 1.36.2 | ✅ 已发布 |  | custom | 1 | - | [📄](archives/k/kubelogin/1.36.2/) |
| **kubie** | 0.26.0 | ✅ 已编译 |  | cargo | 2 | - | [📄](archives/k/kubie/0.26.0/) |
| **kubo** | 0.42.0 | ✅ 已编译 |  | custom | 1 | - | [📄](archives/k/kubo/0.42.0/) |
| **kustomize** | 5.8.1 | ✅ 已编译 |  | go | - | go >= 1.21 | [📄](archives/k/kustomize/5.8.1/) |
| **kuzu** | 0.11.3 | ✅ 已发布 |  | CMake | 13 | - | [📄](archives/k/kuzu/0.11.3/) |
| **kvantum** | 1.1.8 | ✅ 已编译 |  | CMake | 1 | - | [📄](archives/k/kvantum/1.1.8/) |
| **kvazaar** | 2.3.2 | ✅ 已发布 |  | Autotools | 1 | - | [📄](archives/k/kvazaar/2.3.2/) |
| **kyotocabinet** | 1.2.80 | ✅ 已发布 |  |  | 1 | - | [📄](archives/k/kyotocabinet/1.2.80/) |
| **kyverno** | 1.13.0 | ✅ 已发布 |  | go | - | - | [📄](archives/k/kyverno/1.13.0/) |
| **ladspa** | 1.17 | ✅ 已编译 |  | Makefile | 1 | - | [📄](archives/l/ladspa/1.17/) |
| **lager** | 0.1.1 | ✅ 已发布 |  | header-only | - | - | [📄](archives/l/lager/0.1.1/) |
| **lame** | 3.100 | ✅ 已编译 |  |  | 2 | - | [📄](archives/l/lame/3.100/) |
| **largetifftools** | 1.4.1 | ✅ 已编译 |  | Autotools | 3 | - | [📄](archives/l/largetifftools/1.4.1/) |
| **lastpass-cli** | 1.6.1 | ✅ 已编译 |  | custom | - | - | [📄](archives/l/lastpass-cli/1.6.1/) |
| **laszip** | 3.5.0 | uploaded |  | unknown | 0 | - | [📄](archives/l/laszip/3.5.0/) |
| **latex2rtf** | 2.3.18a | ✅ 已发布 |  | Makefile | - | - | [📄](archives/l/latex2rtf/2.3.18a/) |
| **latexml** | 0.8.8 | ✅ 已发布 |  | perl | - | - | [📄](archives/l/latexml/0.8.8/) |
| **lavat** | 3.0.0 | ✅ 已发布 |  | Makefile | 1 | - | [📄](archives/l/lavat/3.0.0/) |
| **lcdf-typetools** | 2.110 | ✅ 已编译 |  |  | - | - | [📄](archives/l/lcdf-typetools/2.110/) |
| **lcms2** | 2.19、2.16 | ✅ 已编译 |  |  | - | - | [📄](archives/l/lcms2/2.16/) |
| **lcov** | 2.4 | success |  | Script | 3 | perl >= 5.10,perl-Capture-Tiny,perl-JSON,perl-Try-Tiny,perl-Date-Parse... | [📄](archives/l/lcov/2.4/) |
| **ldapvi** | 1.7 | ✅ 已发布 |  |  | 4 | - | [📄](archives/l/ldapvi/1.7/) |
| **ldb** | 2.9.2 | ✅ 已发布 |  | waf | 4 | - | [📄](archives/l/ldb/2.9.2/) |
| **ldid** | 2.1.5-procursus7 | ✅ 已编译 |  | Makefile | - | - | [📄](archives/l/ldid/2.1.5-procursus7/) |
| **ldns** | 1.9.0 | ✅ 已编译 |  |  | 1 | - | [📄](archives/l/ldns/1.9.0/) |
| **lemon** | 3.53.0 | uploaded |  | unknown | 0 | - | [📄](archives/l/lemon/3.53.0/) |
| **lensfun** | 0.3.4 | ✅ 已编译 |  |  | - | - | [📄](archives/l/lensfun/0.3.4/) |
| **leptonica** | 1.84.1、1.87.0 | ✅ 已编译 |  |  | - | - | [📄](archives/l/leptonica/1.87.0/) |
| **lerc** | 2.2、4.0.0 | uploaded |  | unknown | 0 | - | [📄](archives/l/lerc/4.0.0/) |
| **less** | 661 | partial |  | Autotools | 2 | - | [📄](archives/l/less/661/) |
| **leveldb** | 1.23 | uploaded |  | CMake | 0 | - | [📄](archives/l/leveldb/1.23/) |
| **lexbor** | 2.6.0 | ✅ 已发布 |  |  | - | - | [📄](archives/l/lexbor/2.6.0/) |
| **lha** | 1.14.20211125 | uploaded |  | unknown | 0 | - | [📄](archives/l/lha/1.14.20211125/) |
| **lib2geom** | 1.4 | ✅ 已编译 |  |  | - | - | [📄](archives/l/lib2geom/1.4/) |
| **libHX** | 4.27 | ✅ 已发布 |  |  | 4 | - | [📄](archives/l/libHX/4.27/) |
| **libOpenDRIVE** | 0.5.0 | ✅ 已编译 |  |  | - | - | [📄](archives/l/libOpenDRIVE/0.5.0/) |
| **libSvtAv1Enc** | 3.1.2 | ✅ 已发布 |  |  | 1 | - | [📄](archives/l/libSvtAv1Enc/3.1.2/) |
| **libXext** | 1.7.0 | ✅ 已发布 |  |  | - | - | [📄](archives/l/libXext/1.7.0/) |
| **libXfont2** | 2.0.7 | ✅ 已发布 |  |  | - | - | [📄](archives/l/libXfont2/2.0.7/) |
| **libXres** | 1.2.1 | ✅ 已编译 |  | Autotools | 3 | - | [📄](archives/l/libXres/1.2.1/) |
| **libXvMC** | 1.0.9 | ✅ 已发布 |  |  | 3 | - | [📄](archives/l/libXvMC/1.0.9/) |
| **libXxf86dga** | 1.1.5 | ✅ 已发布 |  | Autotools | 3 | - | [📄](archives/l/libXxf86dga/1.1.5/) |
| **libaacs** | 0.11.1 | ✅ 已编译 |  | Autotools | 2 | - | [📄](archives/l/libaacs/0.11.1/) |
| **libaccounts-glib** | 1.27 | ✅ 已发布 |  | Meson | 3 | - | [📄](archives/l/libaccounts-glib/1.27/) |
| **libaccounts-qt** | 1.13 | ✅ 已发布 |  | qmake | 3 | - | [📄](archives/l/libaccounts-qt/1.13/) |
| **libaec** | 1.1.6 | success |  | CMake | - | [] | [📄](archives/l/libaec/1.1.6/) |
| **libaio** | 0.3.112 | uploaded |  | Autotools | 0 | - | [📄](archives/l/libaio/0.3.112/) |
| **libao** | 1.2.2 | ✅ 已发布 |  | Autotools | 26 | - | [📄](archives/l/libao/1.2.2/) |
| **libaom** | 3.8.0 | ✅ 已发布 |  | CMake | - | - | [📄](archives/l/libaom/3.8.0/) |
| **libarchive** | 3.7.4、3.8.7 | ✅ 已编译 |  | Autotools | - | - | [📄](archives/l/libarchive/3.8.7/) |
| **libass** | 0.17.0、0.17.4 | ✅ 已编译 |  |  | 3 | - | [📄](archives/l/libass/0.17.4/) |
| **libassuan** | 3.0.2 | uploaded |  | Autotools | 0 | - | [📄](archives/l/libassuan/3.0.2/) |
| **libasyncns** | 0.8 | ✅ 已编译 |  |  | 4 | - | [📄](archives/l/libasyncns/0.8/) |
| **libatomic_ops** | 7.8.2 | uploaded |  | Autotools | 0 | - | [📄](archives/l/libatomic_ops/7.8.2/) |
| **libavc1394** | 0.5.4 | ✅ 已发布 |  | Autotools | 3 | - | [📄](archives/l/libavc1394/0.5.4/) |
| **libavif** | 1.0.4、1.4.1 | ✅ 已编译 |  | CMake | 1 | - | [📄](archives/l/libavif/1.4.1/) |
| **libax25** | 1.2.2 | ✅ 已发布 |  |  | - | zlib,zlib | [📄](archives/l/libax25/1.2.2/) |
| **libb2** | 0.98.1 | uploaded |  | Autotools | 0 | - | [📄](archives/l/libb2/0.98.1/) |
| **libbcrypt** | 1.3 | uploaded |  | unknown | 0 | - | [📄](archives/l/libbcrypt/1.3/) |
| **libbinio** | 1.5 | ✅ 已发布 |  |  | 2 | - | [📄](archives/l/libbinio/1.5/) |
| **libblockdev** | 3.4.0 | ✅ 已发布 |  | Autotools | 4 | - | [📄](archives/l/libblockdev/3.4.0/) |
| **libbluray** | 1.3.4 | ✅ 已编译 |  |  | 2 | - | [📄](archives/l/libbluray/1.3.4/) |
| **libbpf** | 1.6.2 | ✅ 已编译 |  | Makefile | 1 | - | [📄](archives/l/libbpf/1.6.2/) |
| **libbs2b** | 3.1.0 | ✅ 已发布 |  | Autotools | 4 | - | [📄](archives/l/libbs2b/3.1.0/) |
| **libbsd** | 0.11.7、0.12.2 | ✅ 已编译 |  |  | - | - | [📄](archives/l/libbsd/0.12.2/) |
| **libbson** | 1.27.1 | ✅ 已发布 |  | CMake | - | - | [📄](archives/l/libbson/1.27.1/) |
| **libbtbb** | 2020-12-R1 | ✅ 已编译 |  |  | - | - | [📄](archives/l/libbtbb/2020-12-R1/) |
| **libburn** | 1.5.6 | ✅ 已发布 |  | Autotools | 4 | - | [📄](archives/l/libburn/1.5.6/) |
| **libbytesize** | 2.11 | ✅ 已编译 |  | Autotools | 7 | - | [📄](archives/l/libbytesize/2.11/) |
| **libcap** | 2.69 | uploaded |  | Autotools | 0 | - | [📄](archives/l/libcap/2.69/) |
| **libcap-ng** | 0.9.1 | ✅ 已编译 |  | manual_makefile | 0 | linux-kernel-headers (linux/capability.h),pthread | [📄](archives/l/libcap-ng/0.9.1/) |
| **libcbor** | 0.13.0-r0 | ✅ 已编译 |  | CMake | - | - | [📄](archives/l/libcbor/0.13.0-r0/) |
| **libccd** | 2.1 | success |  | CMake | 3 | - | [📄](archives/l/libccd/2.1/) |
| **libcddb** | 1.3.2 | ✅ 已发布 |  | Autotools | 2 | - | [📄](archives/l/libcddb/1.3.2/) |
| **libcdio** | 2.3.0 | ✅ 已编译 |  | Autotools | 3 | - | [📄](archives/l/libcdio/2.3.0/) |
| **libcdr** | 0.1.3 | ✅ 已发布 |  | Autotools | 4 | - | [📄](archives/l/libcdr/0.1.3/) |
| **libcerf** | 3.3 | success |  | CMake | - | - | [📄](archives/l/libcerf/3.3/) |
| **libclc** | 18.1.6 | ✅ 已编译 |  |  | - | - | [📄](archives/l/libclc/18.1.6/) |
| **libcmatrix** | 0.0.4 | ✅ 已发布 |  | Meson | - | - | [📄](archives/l/libcmatrix/0.0.4/) |
| **libconfig** | 1.7.3 | uploaded |  | CMake | 0 | - | [📄](archives/l/libconfig/1.7.3/) |
| **libconfuse** | 3.3 | ✅ 已编译 |  |  | 2 | - | [📄](archives/l/libconfuse/3.3/) |
| **libcoro** | 6.513 | ✅ 已发布 |  | Makefile | 2 | - | [📄](archives/l/libcoro/6.513/) |
| **libcpuid** | 0.8.0 | ✅ 已发布 |  | CMake | 3 | - | [📄](archives/l/libcpuid/0.8.0/) |
| **libcrystalhd** | 20130708 | ✅ 已发布 |  | Makefile | 2 | - | [📄](archives/l/libcrystalhd/20130708/) |
| **libcuckoo** | 0.3.1 | uploaded |  | CMake | 0 | - | [📄](archives/l/libcuckoo/0.3.1/) |
| **libcue** | 2.3.0 | ✅ 已发布 |  | CMake | 1 | - | [📄](archives/l/libcue/2.3.0/) |
| **libcuefile** | r475 | success |  | CMake | 1 | - | [📄](archives/l/libcuefile/r475/) |
| **libcutl** | 1.11.0 | ✅ 已编译 |  | custom | - | - | [📄](archives/l/libcutl/1.11.0/) |
| **libdaemon** | 0.14 | uploaded |  | Autotools | 0 | - | [📄](archives/l/libdaemon/0.14/) |
| **libdap** | 3.21.1 | ✅ 已编译 |  |  | 55 | - | [📄](archives/l/libdap/3.21.1/) |
| **libdatachannel** | 0.24.0 | ✅ 已发布 |  | CMake | 2 | - | [📄](archives/l/libdatachannel/0.24.0/) |
| **libdatrie** | 0.2.14 | partial |  | Autotools | 2 | - | [📄](archives/l/libdatrie/0.2.14/) |
| **libdbi** | 0.9.0-r5 | ✅ 已发布 |  |  | 4 | - | [📄](archives/l/libdbi/0.9.0-r5/) |
| **libdc1394** | 2.2.7 | ✅ 已发布 |  | Autotools | 5 | - | [📄](archives/l/libdc1394/2.2.7/) |
| **libde265** | 1.0.15、1.0.18 | ✅ 已编译 |  |  | 2 | - | [📄](archives/l/libde265/1.0.18/) |
| **libdeflate** | 1.25、1.21 | partial |  | Autotools | - | - | [📄](archives/l/libdeflate/1.21/) |
| **libdiscid** | 0.6.5-r0 | ✅ 已发布 |  | CMake | 1 | - | [📄](archives/l/libdiscid/0.6.5-r0/) |
| **libdispatch** | 5.10.1 | ✅ 已发布 |  | CMake | 2 | - | [📄](archives/l/libdispatch/5.10.1/) |
| **libdisplay-info** | 0.3.0 | ✅ 已发布 |  | Meson | - | - | [📄](archives/l/libdisplay-info/0.3.0/) |
| **libdjinterop** | 0.24.3-r1 | ✅ 已发布 |  | CMake | 1 | - | [📄](archives/l/libdjinterop/0.24.3-r1/) |
| **libdmtx** | 0.7.8、0.7.5 | ✅ 已编译 |  |  | - | - | [📄](archives/l/libdmtx/0.7.5/) |
| **libdnet** | 1.12 | ✅ 已发布 |  |  | 3 | - | [📄](archives/l/libdnet/1.12/) |
| **libdotconf** | 1.4.1-r0 | ✅ 已发布 |  | Autotools | - | - | [📄](archives/l/libdotconf/1.4.1-r0/) |
| **libdrm** | 2.4.133 | ✅ 已编译 |  |  | - | - | [📄](archives/l/libdrm/2.4.133/) |
| **libdshconfig** | 0.20.13 | ✅ 已发布 |  |  | 11 | - | [📄](archives/l/libdshconfig/0.20.13/) |
| **libdsk** | 1.4.2 | ✅ 已发布 |  | Autotools | 22 | - | [📄](archives/l/libdsk/1.4.2/) |
| **libdv** | 1.0.0-r8 | ✅ 已发布 |  | Autotools | 3 | - | [📄](archives/l/libdv/1.0.0-r8/) |
| **libdvbcsa** | 1.1.0 | ✅ 已发布 |  | Autotools | 7 | - | [📄](archives/l/libdvbcsa/1.1.0/) |
| **libdvbpsi** | 1.3.3 | ✅ 已发布 |  | Autotools | 3 | - | [📄](archives/l/libdvbpsi/1.3.3/) |
| **libdvdcss** | 1.5.0 | success |  | Meson | - | [] | [📄](archives/l/libdvdcss/1.5.0/) |
| **libeatmydata** | 131 | ✅ 已发布 |  | Autotools | 2 | - | [📄](archives/l/libeatmydata/131/) |
| **libebml** | 1.4.5 | ✅ 已编译 |  |  | 1 | - | [📄](archives/l/libebml/1.4.5/) |
| **libebur128** | 1.2.6 | ✅ 已发布 |  |  | 2 | - | [📄](archives/l/libebur128/1.2.6/) |
| **libeconf** | 0.8.3 | ✅ 已发布 |  | CMake | 1 | - | [📄](archives/l/libeconf/0.8.3/) |
| **libecpg** | 18.3 | ✅ 已编译 |  | Autotools | 3 | - | [📄](archives/l/libecpg/18.3/) |
| **libedit** | 20240808、20240817、20251016-3.1 | partial |  | Autotools | 2 | - | [📄](archives/l/libedit/20251016-3.1/) |
| **libepoxy** | 1.5.10 | ✅ 已发布 |  |  | - | - | [📄](archives/l/libepoxy/1.5.10/) |
| **libepubgen** | 0.1.1 | ✅ 已发布 |  | Autotools | 2 | - | [📄](archives/l/libepubgen/0.1.1/) |
| **libesedb** | 20240420 | ✅ 已发布 |  |  | 6 | - | [📄](archives/l/libesedb/20240420/) |
| **libestr** | 0.1.11 | ✅ 已发布 |  | Autotools | 2 | [] | [📄](archives/l/libestr/0.1.11/) |
| **libetpan** | 1.9.4 | ✅ 已发布 |  | Autotools | 2 | - | [📄](archives/l/libetpan/1.9.4/) |
| **libev** | 4.33 | uploaded |  | Autotools | 0 | - | [📄](archives/l/libev/4.33/) |
| **libevent** | 2.1.12-stable、2.1.12 | partial |  | Autotools | 4 | - | [📄](archives/l/libevent/2.1.12/) |
| **libevhtp** | 1.2.18 | ✅ 已发布 |  | CMake | 1 | - | [📄](archives/l/libevhtp/1.2.18/) |
| **libexif** | 0.6.26 | ✅ 已编译 |  |  | 3 | - | [📄](archives/l/libexif/0.6.26/) |
| **libexosip2** | 5.3.0 | ✅ 已发布 |  | Autotools | 3 | - | [📄](archives/l/libexosip2/5.3.0/) |
| **libexttextcat** | 3.4.6 | ✅ 已发布 |  |  | 2 | - | [📄](archives/l/libexttextcat/3.4.6/) |
| **libfabric** | 2.5.0 | ✅ 已编译 |  | Autotools | 4 | - | [📄](archives/l/libfabric/2.5.0/) |
| **libfaketime** | 0.9.10 | ✅ 已发布 |  | Makefile | 2 | - | [📄](archives/l/libfaketime/0.9.10/) |
| **libfastjson** | 1.2304.0 | ✅ 已发布 |  | Autotools | 2 | - | [📄](archives/l/libfastjson/1.2304.0/) |
| **libfdka** | 2.0.2 | ✅ 已编译 |  |  | - | - | [📄](archives/l/libfdka/2.0.2/) |
| **libfds** | 0.6.0 | ✅ 已发布 |  | CMake | 4 | - | [📄](archives/l/libfds/0.6.0/) |
| **libffi** | 3.4.4、3.5.2、3.4.6 | partial |  | Autotools | 3 | - | [📄](archives/l/libffi/3.4.6/) |
| **libfido2** | 1.15.0 | ✅ 已编译 |  | CMake | 4 | - | [📄](archives/l/libfido2/1.15.0/) |
| **libfilezilla** | 0.49.0 | ✅ 已发布 |  |  | 3 | - | [📄](archives/l/libfilezilla/0.49.0/) |
| **libfixposix** | 0.5.1 | ✅ 已发布 |  | Autotools | 3 | - | [📄](archives/l/libfixposix/0.5.1/) |
| **libfm** | 1.3.2 | ✅ 已发布 |  |  | 1 | - | [📄](archives/l/libfm/1.3.2/) |
| **libfm-extra** | 1.3.2 | ✅ 已编译 |  |  | - | - | [📄](archives/l/libfm-extra/1.3.2/) |
| **libfolia** | 2.21 | ✅ 已发布 |  | Autotools | - | - | [📄](archives/l/libfolia/2.21/) |
| **libfontenc** | 1.1.7、1.1.9 | success |  | Autotools | 3 | xproto (手动安装头文件),zlib (预编译包已安装) | [📄](archives/l/libfontenc/1.1.9/) |
| **libfossil** | 0.20250730.1700 | ✅ 已发布 |  | Makefile | 1 | - | [📄](archives/l/libfossil/0.20250730.1700/) |
| **libfreeaptx** | 0.2.2 | ✅ 已发布 |  |  | - | - | [📄](archives/l/libfreeaptx/0.2.2/) |
| **libfreehand** | 0.1.1 | ✅ 已发布 |  | Autotools | 17 | - | [📄](archives/l/libfreehand/0.1.1/) |
| **libfst** | 1.8.4 | ✅ 已发布 |  |  | 3 | - | [📄](archives/l/libfst/1.8.4/) |
| **libftdi1** | 1.5 | ✅ 已发布 |  |  | - | - | [📄](archives/l/libftdi1/1.5/) |
| **libfyaml** | 0.9.6 | ✅ 已编译 |  | Autotools | 3 | name: yaml-0.1 | [📄](archives/l/libfyaml/0.9.6/) |
| **libgcab** | 1.6 | ✅ 已发布 |  |  | 1 | - | [📄](archives/l/libgcab/1.6/) |
| **libgcrypt** | 1.11.0、1.10.3 | ✅ 已发布 |  |  | - | - | [📄](archives/l/libgcrypt/1.10.3/) |
| **libgda** | 6.0.0 | ✅ 已编译 |  | Meson | - | glib-2.0 >= 2.38,libxml-2.0,sqlite3 >= 3.22,iso-codes,meson >= 0.49... | [📄](archives/l/libgda/6.0.0/) |
| **libgit2** | 1.9.0、1.9.4 | ✅ 已编译 |  |  | - | - | [📄](archives/l/libgit2/1.9.4/) |
| **libgit2-glib** | 1.2.1 | ✅ 已编译 |  |  | - | - | [📄](archives/l/libgit2-glib/1.2.1/) |
| **libglibutil** | 1.0.82 | ✅ 已编译 |  |  | - | - | [📄](archives/l/libglibutil/1.0.82/) |
| **libgme** | 0.6.3、0.6.5 | ✅ 已编译 |  |  | 2 | - | [📄](archives/l/libgme/0.6.5/) |
| **libgnt** | 2.14.0 | ✅ 已编译 |  | Meson | 2 | name: glib,name: ncursesw,name: libxml2 | [📄](archives/l/libgnt/2.14.0/) |
| **libgpg-error** | 1.50、1.55、1.61 | ✅ 已发布 |  | Autotools | 2 | - | [📄](archives/l/libgpg-error/1.61/) |
| **libgphoto2** | 2.5.31 | ✅ 已发布 |  |  | 3 | - | [📄](archives/l/libgphoto2/2.5.31/) |
| **libgpiod** | 2.0、2.1.3 | ✅ 已编译 |  |  | 4 | - | [📄](archives/l/libgpiod/2.1.3/) |
| **libgpod** | 0.8.3 | ✅ 已编译 |  | Autotools | - | - | [📄](archives/l/libgpod/0.8.3/) |
| **libgrapheme** | 3.0.0 | ✅ 已编译 |  |  | 1 | - | [📄](archives/l/libgrapheme/3.0.0/) |
| **libgsasl** | 1.10.0 | ✅ 已编译 |  |  | 3 | - | [📄](archives/l/libgsasl/1.10.0/) |
| **libgsm** | 1.0.18 | ✅ 已发布 |  | Makefile | 1 | [] | [📄](archives/l/libgsm/1.0.18/) |
| **libgssglue** | 0.7 | ✅ 已编译 |  |  | 6 | - | [📄](archives/l/libgssglue/0.7/) |
| **libgusb** | 0.4.9 | ✅ 已发布 |  |  | - | - | [📄](archives/l/libgusb/0.4.9/) |
| **libgxps** | 0.3.2 | ✅ 已编译 |  |  | - | - | [📄](archives/l/libgxps/0.3.2/) |
| **libhangul** | 0.2.0 | ✅ 已编译 |  |  | 1 | - | [📄](archives/l/libhangul/0.2.0/) |
| **libharu** | 2.4.6 | ✅ 已发布 |  |  | - | - | [📄](archives/l/libharu/2.4.6/) |
| **libhdhomerun** | 20260313 | ✅ 已编译 |  |  | 1 | - | [📄](archives/l/libhdhomerun/20260313/) |
| **libheif** | 1.18.2 | ✅ 已编译 |  | CMake | 1 | - | [📄](archives/l/libheif/1.18.2/) |
| **libhtp** | 0.5.53 | ✅ 已编译 |  |  | - | - | [📄](archives/l/libhtp/0.5.53/) |
| **libical** | 4.0.1 | ✅ 已发布 |  |  | - | - | [📄](archives/l/libical/4.0.1/) |
| **libiconv** | 1.17 | uploaded |  | Autotools | 0 | - | [📄](archives/l/libiconv/1.17/) |
| **libid3tag** | 0.16.3 | ✅ 已发布 |  |  | - | - | [📄](archives/l/libid3tag/0.16.3/) |
| **libident** | 0.32 | ✅ 已编译 |  | Autotools | 2 | - | [📄](archives/l/libident/0.32/) |
| **libidn** | 1.43 | 📦 已归档 |  |  | - | - | [📄](archives/l/libidn/1.43/) |
| **libidn2** | 2.3.7、2.3.8 | ✅ 已发布 |  | Autotools | - | - | [📄](archives/l/libidn2/2.3.8/) |
| **libiec61883** | 1.2.0 | ✅ 已编译 |  | Autotools | 3 | - | [📄](archives/l/libiec61883/1.2.0/) |
| **libieee1284** | 0.2.11 | ✅ 已编译 |  |  | 3 | - | [📄](archives/l/libieee1284/0.2.11/) |
| **libiio** | 0.26 | ✅ 已编译 |  |  | - | - | [📄](archives/l/libiio/0.26/) |
| **libilbc** | 3.0.4 | ✅ 已编译 |  | CMake | 1 | - | [📄](archives/l/libilbc/3.0.4/) |
| **libimagequant** | 2.18.0 | ✅ 已发布 |  |  | - | - | [📄](archives/l/libimagequant/2.18.0/) |
| **libime** | 1.1.12 | published   |  | CMake | 9 | - | [📄](archives/l/libime/1.1.12/) |
| **libimobiledevice-glue** | 1.3.0 | ✅ 已编译 |  | Autotools | - | - | [📄](archives/l/libimobiledevice-glue/1.3.0/) |
| **libindi** | 2.2.2 | ✅ 已编译 |  | CMake | 8 | - | [📄](archives/l/libindi/2.2.2/) |
| **libinput** | 1.26.0、1.26.2 | ✅ 已发布 |  |  | - | - | [📄](archives/l/libinput/1.26.2/) |
| **libiodata** | 0.19.14 | ✅ 已编译 |  | custom | - | - | [📄](archives/l/libiodata/0.19.14/) |
| **libiodbc** | 3.52.15、3.52.16 | ✅ 已发布 |  | Autotools | 3 | - | [📄](archives/l/libiodbc/3.52.16/) |
| **libiphb** | 1.2.8 | ✅ 已发布 |  | Autotools | 5 | glib-2.0,dbus-1 | [📄](archives/l/libiphb/1.2.8/) |
| **libirecovery** | 1.3.1 | ✅ 已编译 |  |  | 3 | - | [📄](archives/l/libirecovery/1.3.1/) |
| **libiscsi** | 1.19.0 | ✅ 已发布 |  |  | 1 | - | [📄](archives/l/libiscsi/1.19.0/) |
| **libisoburn** | 1.5.8.pl02 | ✅ 已发布 |  | Autotools | 3 | "gcc","make","autoconf","automake" | [📄](archives/l/libisoburn/1.5.8.pl02/) |
| **libite** | 2.6.2 | ✅ 已发布 |  |  | 3 | - | [📄](archives/l/libite/2.6.2/) |
| **libixion** | 0.19.0 | ✅ 已发布 |  |  | 1 | - | [📄](archives/l/libixion/0.19.0/) |
| **libjaylink** | 0.2.0 | ✅ 已发布 |  |  | - | - | [📄](archives/l/libjaylink/0.2.0/) |
| **libjcat** | 0.2.6 | ✅ 已发布 |  |  | - | - | [📄](archives/l/libjcat/0.2.6/) |
| **libjodycode** | 4.1.2 | ✅ 已发布 |  |  | - | - | [📄](archives/l/libjodycode/4.1.2/) |
| **libjpeg** | 10 | ✅ 已发布 |  |  | 3 | - | [📄](archives/l/libjpeg/10/) |
| **libjpeg-turbo** | 3.1.4.1、2.1.5.1 | partial |  | Autotools | - | - | [📄](archives/l/libjpeg-turbo/2.1.5.1/) |
| **libjwt** | 3.3.3 | ✅ 已编译 |  |  | - | - | [📄](archives/l/libjwt/3.3.3/) |
| **libjxl** | 0.11.2 | ✅ 已发布 |  | CMake | - | - | [📄](archives/l/libjxl/0.11.2/) |
| **libkcapi** | 1.4.0、1.5.0、1.5.0-r1 | ✅ 已编译 |  | Autotools | - | - | [📄](archives/l/libkcapi/1.5.0-r1/) |
| **libkiwix** | 14.2.1 | ✅ 已发布 |  | Meson | - | - | [📄](archives/l/libkiwix/14.2.1/) |
| **libks** | 2.0.11 | ✅ 已编译 |  | CMake | 2 | openssl,uuid | [📄](archives/l/libks/2.0.11/) |
| **libksba** | 1.6.7 | uploaded |  | Autotools | 0 | - | [📄](archives/l/libksba/1.6.7/) |
| **liblangtag** | 0.6.4 | ✅ 已发布 |  | Autotools | 2 | - | [📄](archives/l/liblangtag/0.6.4/) |
| **liblc3** | 1.1.3 | ✅ 已发布 |  |  | 1 | - | [📄](archives/l/liblc3/1.1.3/) |
| **liblcf** | 0.8.1 | ✅ 已发布 |  |  | - | - | [📄](archives/l/liblcf/0.8.1/) |
| **libldac** | aosp-20250110 | ✅ 已编译 |  |  | 1 | - | [📄](archives/l/libldac/aosp-20250110/) |
| **libliftoff** | 0.1.0 | ✅ 已发布 |  |  | - | - | [📄](archives/l/libliftoff/0.1.0/) |
| **liblinear** | 2.50 | uploaded |  | Autotools | 0 | - | [📄](archives/l/liblinear/2.50/) |
| **liblksctp** | 1.0.17 | ✅ 已发布 |  |  | 2 | - | [📄](archives/l/liblksctp/1.0.17/) |
| **liblo** | 0.34 | unknown |  |  | - | - | [📄](archives/l/liblo/0.34/) |
| **liblockfile** | 1.17 | ✅ 已发布 |  | Autotools | 3 | - | [📄](archives/l/liblockfile/1.17/) |
| **liblogging** | 1.0.8 | ✅ 已发布 |  |  | 3 | - | [📄](archives/l/liblogging/1.0.8/) |
| **liblognorm** | 2.0.6 | ✅ 已发布 |  | Autotools | 1 | - | [📄](archives/l/liblognorm/2.0.6/) |
| **libltc** | 1.3.2 | ✅ 已发布 |  |  | 21 | - | [📄](archives/l/libltc/1.3.2/) |
| **liblzf** | 3.6 | uploaded |  | unknown | 0 | - | [📄](archives/l/liblzf/3.6/) |
| **libmaa** | 1.4.7 | ✅ 已编译 |  | custom | 1 | - | [📄](archives/l/libmaa/1.4.7/) |
| **libmanette** | 0.2.7 | ✅ 已编译 |  | Meson | - | - | [📄](archives/l/libmanette/0.2.7/) |
| **libmanticore-columnar** | 13.0.0 | ✅ 已发布 |  | CMake | 3 | - | [📄](archives/l/libmanticore-columnar/13.0.0/) |
| **libmarisa** | 0.2.6 | ✅ 已编译 |  | Autotools | 43 | - | [📄](archives/l/libmarisa/0.2.6/) |
| **libmatemixer** | 1.28.0 | ✅ 已编译 |  |  | 1 | - | [📄](archives/l/libmatemixer/1.28.0/) |
| **libmatroska** | 1.7.1 | ✅ 已编译 |  |  | - | - | [📄](archives/l/libmatroska/1.7.1/) |
| **libmaxminddb** | 1.11.0、1.13.3 | partial |  | Autotools | 3 | - | [📄](archives/l/libmaxminddb/1.13.3/) |
| **libmbim** | 1.30.0 | ✅ 已编译 |  |  | 4 | - | [📄](archives/l/libmbim/1.30.0/) |
| **libmcrypt** | 2.5.8 | ✅ 已编译 |  |  | 3 | - | [📄](archives/l/libmcrypt/2.5.8/) |
| **libmd** | 1.1.0 | ✅ 已编译 |  |  | - | - | [📄](archives/l/libmd/1.1.0/) |
| **libmedc** | 4.1.0 | ✅ 已发布 |  | CMake | 3 | hdf5 1.10.8 | [📄](archives/l/libmedc/4.1.0/) |
| **libmediaart** | 1.9.7 | ✅ 已编译 |  | Meson | - | glib-2.0 (>= 2.38.0),gdk-pixbuf-2.0 (>= 2.12.0),gio-2.0,gio-unix-2.0,gobject-2.0 | [📄](archives/l/libmediaart/1.9.7/) |
| **libmediainfo** | 26.05 | ✅ 已编译 |  | CMake | - | - | [📄](archives/l/libmediainfo/26.05/) |
| **libmemcached** | 1.0.18 | ✅ 已编译 |  |  | 21 | - | [📄](archives/l/libmemcached/1.0.18/) |
| **libmetalink** | 0.1.3 | ✅ 已发布 |  | Autotools | 3 | - | [📄](archives/l/libmetalink/0.1.3/) |
| **libmgba** | 0.10.5 | ✅ 已发布 |  | CMake | 6 | - | [📄](archives/l/libmgba/0.10.5/) |
| **libmicrodns** | 0.2.0 | ✅ 已发布 |  |  | - | - | [📄](archives/l/libmicrodns/0.2.0/) |
| **libmicrohttpd** | 1.0.5 | ✅ 已发布 |  | Autotools | 23 | - | [📄](archives/l/libmicrohttpd/1.0.5/) |
| **libmikmod** | 3.3.13 | ✅ 已编译 |  | Autotools | 3 | - | [📄](archives/l/libmikmod/3.3.13/) |
| **libmilter** | 8.18.2 | ✅ 已发布 |  | sendmail-devtools | 2 | - | [📄](archives/l/libmilter/8.18.2/) |
| **libmlocale** | 0.8.3 | ✅ 已发布 |  |  | 2 | - | [📄](archives/l/libmlocale/0.8.3/) |
| **libmm-glib** | 1.24.2 | ✅ 已发布 |  | Meson | 2 | - | [📄](archives/l/libmm-glib/1.24.2/) |
| **libmms** | 0.6.4 | ✅ 已发布 |  |  | 3 | - | [📄](archives/l/libmms/0.6.4/) |
| **libmnl** | 1.0.5 | uploaded |  | Autotools | 0 | - | [📄](archives/l/libmnl/1.0.5/) |
| **libmodbus** | 3.1.10、3.1.12 | ✅ 已编译 |  | Autotools | 3 | - | [📄](archives/l/libmodbus/3.1.12/) |
| **libmowgli** | 1.0.0 | ✅ 已发布 |  |  | 5 | - | [📄](archives/l/libmowgli/1.0.0/) |
| **libmp3splt** | 0.9.3.1518 | ✅ 已发布 |  | Autotools | - | libtool >= 2.4.7,libltdl,libpcre >= 8.45,libmad >= 0.15.1b,libid3tag >= 0.16.3... | [📄](archives/l/libmp3splt/0.9.3.1518/) |
| **libmpack** | 1.0.3 | ✅ 已编译 |  |  | - | - | [📄](archives/l/libmpack/1.0.3/) |
| **libmpdclient** | 2.23 | ✅ 已发布 |  | Meson | - | - | [📄](archives/l/libmpdclient/2.23/) |
| **libmpeg2** | 0.5.1 | ✅ 已发布 |  |  | 2 | - | [📄](archives/l/libmpeg2/0.5.1/) |
| **libmspack** | 0.11alpha | uploaded |  | unknown | 0 | - | [📄](archives/l/libmspack/0.11alpha/) |
| **libmspub** | 0.1.2 | ✅ 已发布 |  | Autotools | - | - | [📄](archives/l/libmspub/0.1.2/) |
| **libmtp** | 1.1.21 | ✅ 已发布 |  |  | 6 | - | [📄](archives/l/libmtp/1.1.21/) |
| **libmxml** | 4.0.4 | ✅ 已发布 |  |  | 2 | - | [📄](archives/l/libmxml/4.0.4/) |
| **libmypaint** | 1.6.0 | ✅ 已发布 |  |  | 3 | - | [📄](archives/l/libmypaint/1.6.0/) |
| **libnatpmp** | 20230423 | ✅ 已发布 |  | Makefile | 3 | - | [📄](archives/l/libnatpmp/20230423/) |
| **libnbcompat** | 20150615 | ✅ 已发布 |  | bsd-make | 3 | - | [📄](archives/l/libnbcompat/20150615/) |
| **libndp** | v1.7 | ✅ 已发布 |  | Autotools | - | - | [📄](archives/l/libndp/v1.7/) |
| **libnet** | 1.2 | ✅ 已编译 |  |  | 1 | - | [📄](archives/l/libnet/1.2/) |
| **libnetfilter_acct** | 1.0.3 | ✅ 已发布 |  |  | 4 | - | [📄](archives/l/libnetfilter_acct/1.0.3/) |
| **libnetfilter_conntrack** | 1.1.0 | ✅ 已编译 |  | Autotools | 2 | - | [📄](archives/l/libnetfilter_conntrack/1.1.0/) |
| **libnetfilter_cthelper** | 1.0.1 | ✅ 已发布 |  |  | 7 | name: libmnl | [📄](archives/l/libnetfilter_cthelper/1.0.1/) |
| **libnetfilter_cttimeout** | 1.0.0 | ✅ 已发布 |  |  | - | - | [📄](archives/l/libnetfilter_cttimeout/1.0.0/) |
| **libnfnetlink** | 1.0.2 | ✅ 已编译 |  | Autotools | 4 | - | [📄](archives/l/libnfnetlink/1.0.2/) |
| **libnfs** | 6.0.2 | ✅ 已发布 |  | CMake | - | - | [📄](archives/l/libnfs/6.0.2/) |
| **libnfsidmap** | 0.25 | ✅ 已编译 |  |  | - | - | [📄](archives/l/libnfsidmap/0.25/) |
| **libngf-qt** | 0.3.1 | ✅ 已编译 |  |  | - | - | [📄](archives/l/libngf-qt/0.3.1/) |
| **libnghttp2** | 1.69.0 | ✅ 已编译 |  | CMake | - | cmake,musl | [📄](archives/l/libnghttp2/1.69.0/) |
| **libngtcp2** | 1.22.1 | ✅ 已发布 |  | Autotools | 2 | - | [📄](archives/l/libngtcp2/1.22.1/) |
| **libnice** | 0.1.21 | ✅ 已编译 |  |  | - | - | [📄](archives/l/libnice/0.1.21/) |
| **libnitrokey** | 3.7 | ✅ 已编译 |  | CMake | 1 | - | [📄](archives/l/libnitrokey/3.7/) |
| **libnjs** | 0.9.9 | ✅ 已发布 |  |  | - | - | [📄](archives/l/libnjs/0.9.9/) |
| **libnl** | 3.7.0 | ✅ 已编译 |  |  | 3 | - | [📄](archives/l/libnl/3.7.0/) |
| **libntlm** | 1.2 | 📦 已归档 |  |  | - | - | [📄](archives/l/libntlm/1.2/) |
| **libnumbertext** | 1.0.9 | ✅ 已编译 |  |  | - | - | [📄](archives/l/libnumbertext/1.0.9/) |
| **libnvme** | 1.10 | ✅ 已编译 |  |  | - | - | [📄](archives/l/libnvme/1.10/) |
| **libogg** | 1.3.5、1.3.6 | uploaded |  | Autotools | 0 | - | [📄](archives/l/libogg/1.3.6/) |
| **libomemo** | 0.8.1 | ✅ 已编译 |  | CMake | 2 | - | [📄](archives/l/libomemo/0.8.1/) |
| **libomp** | 15.0.4 | ✅ 已编译 |  | CMake | 2 | - | [📄](archives/l/libomp/15.0.4/) |
| **libopenmpt** | 0.7.13 | ✅ 已编译 |  | Autotools | 3 | - | [📄](archives/l/libopenmpt/0.7.13/) |
| **libopensmtpd** | 0.1 | ✅ 已编译 |  | makefile-gnu | - | libevent-2.1.12 | [📄](archives/l/libopensmtpd/0.1/) |
| **liboping** | 1.10.0 | ✅ 已编译 |  |  | 19 | - | [📄](archives/l/liboping/1.10.0/) |
| **liboqs** | 0.15.0 | ✅ 已编译 |  |  | - | - | [📄](archives/l/liboqs/0.15.0/) |
| **libosinfo** | 1.11.0 | ✅ 已编译 |  |  | - | - | [📄](archives/l/libosinfo/1.11.0/) |
| **libosip2** | 5.3.1 | ✅ 已发布 |  |  | 36 | - | [📄](archives/l/libosip2/5.3.1/) |
| **libosmium** | 2.20.0 | ✅ 已发布 |  |  | 1 | - | [📄](archives/l/libosmium/2.20.0/) |
| **libotr** | 4.1.1 | ✅ 已编译 |  | Autotools | 23 | - | [📄](archives/l/libotr/4.1.1/) |
| **libp11** | 0.4.16-r0 | ✅ 已编译 |  |  | - | - | [📄](archives/l/libp11/0.4.16-r0/) |
| **libpagemaker** | 0.0.3 | ✅ 已编译 |  | Autotools | 2 | - | [📄](archives/l/libpagemaker/0.0.3/) |
| **libpaper** | 1.1.28 | ✅ 已发布 |  |  | 13 | - | [📄](archives/l/libpaper/1.1.28/) |
| **libpcap** | 1.10.6 | uploaded |  | Autotools | 0 | - | [📄](archives/l/libpcap/1.10.6/) |
| **libpciaccess** | 0.17 | ✅ 已编译 |  |  | - | - | [📄](archives/l/libpciaccess/0.17/) |
| **libpcre16** | 8.45 | ✅ 已编译 |  |  | 3 | - | [📄](archives/l/libpcre16/8.45/) |
| **libpcre2-16** | 10.43 | ✅ 已发布 |  |  | 2 | - | [📄](archives/l/libpcre2-16/10.43/) |
| **libpeas** | 2.2.1 | ✅ 已编译 |  |  | 2 | - | [📄](archives/l/libpeas/2.2.1/) |
| **libpg_query** | 17-6.2.2 | ✅ 已发布 |  | Makefile | - | - | [📄](archives/l/libpg_query/17-6.2.2/) |
| **libpipeline** | 1.5.8 | verified |  | unknown | 0 | - | [📄](archives/l/libpipeline/1.5.8/) |
| **libpisp** | 1.0.6 | ✅ 已发布 |  | Meson | 3 | - | [📄](archives/l/libpisp/1.0.6/) |
| **libplacebo** | 7.349.0 | ✅ 已发布 |  | Meson | - | - | [📄](archives/l/libplacebo/7.349.0/) |
| **libplist** | 2.3.0 | ✅ 已发布 |  | Autotools | - | - | [📄](archives/l/libplist/2.3.0/) |
| **libpng** | 1.6.39、1.6.58 | ✅ 已编译 |  |  | - | - | [📄](archives/l/libpng/1.6.58/) |
| **libpostal** | 1.1 | ✅ 已编译 |  | Autotools | - | [] | [📄](archives/l/libpostal/1.1/) |
| **libpq** | 16、17.2 | ✅ 已编译 |  |  | 3 | - | [📄](archives/l/libpq/17.2/) |
| **libproxy** | 0.5.12 | ✅ 已发布 |  | Meson | 2 | glib-2.0 >= 2.71.3,gio-2.0 >= 2.71.3 | [📄](archives/l/libproxy/0.5.12/) |
| **libpsl** | 0.21.5 | uploaded |  | Autotools | 0 | - | [📄](archives/l/libpsl/0.21.5/) |
| **libpst** | 0.6.76 | ✅ 已编译 |  |  | 2 | - | [📄](archives/l/libpst/0.6.76/) |
| **libpthread-stubs** | 0.4 | ✅ 已编译 |  |  | - | - | [📄](archives/l/libpthread-stubs/0.4/) |
| **libptytty** | latest | ✅ 已编译 |  |  | - | - | [📄](archives/l/libptytty/latest/) |
| **libpwquality** | 1.4.5 | ✅ 已编译 |  |  | 8 | - | [📄](archives/l/libpwquality/1.4.5/) |
| **libqalculate** | 5.4.0 | ✅ 已发布 |  | Autotools | 7 | - | [📄](archives/l/libqalculate/5.4.0/) |
| **libqb** | 2.0.10 | ✅ 已编译 |  |  | 2 | - | [📄](archives/l/libqb/2.0.10/) |
| **libqb3** | 1.3.2 | uploaded |  | unknown | 0 | - | [📄](archives/l/libqb3/1.3.2/) |
| **libqmi** | 1.32.0 | ✅ 已编译 |  | Meson | 2 | - | [📄](archives/l/libqmi/1.32.0/) |
| **libqrcodegen** | 1.8.0 | uploaded |  | unknown | 0 | - | [📄](archives/l/libqrcodegen/1.8.0/) |
| **libqrencode** | 4.1.1 | uploaded |  | Autotools | 0 | - | [📄](archives/l/libqrencode/4.1.1/) |
| **libqrtr-glib** | 1.4.0 | ✅ 已编译 |  |  | 3 | - | [📄](archives/l/libqrtr-glib/1.4.0/) |
| **libquvi** | 0.9.4 | ✅ 已发布 |  |  | 3 | - | [📄](archives/l/libquvi/0.9.4/) |
| **libquvi-scripts** | 0.9.20131130 | ✅ 已编译 |  | Autotools | 2 | - | [📄](archives/l/libquvi-scripts/0.9.20131130/) |
| **libqxp** | 0.0.1 | ✅ 已发布 |  |  | 3 | - | [📄](archives/l/libqxp/0.0.1/) |
| **libraqm** | 0.10.5 | ✅ 已发布 |  | Meson | - | - | [📄](archives/l/libraqm/0.10.5/) |
| **libraw** | 0.22.1 | uploaded |  | Autotools | 0 | - | [📄](archives/l/libraw/0.22.1/) |
| **libraw1394** | 2.1.2 | ✅ 已编译 |  |  | 2 | - | [📄](archives/l/libraw1394/2.1.2/) |
| **librda** | 0.0.5 | ✅ 已编译 |  |  | 3 | - | [📄](archives/l/librda/0.0.5/) |
| **librdkafka** | 2.5.3 | uploaded |  | unknown | 0 | - | [📄](archives/l/librdkafka/2.5.3/) |
| **librealsense** | 2.58.1 | ✅ 已发布 |  |  | 5 | - | [📄](archives/l/librealsense/2.58.1/) |
| **librelp** | 1.12.0 | ✅ 已编译 |  | Autotools | 13 | - | [📄](archives/l/librelp/1.12.0/) |
| **libreplaygain** | r475 | success |  | CMake | 1 | - | [📄](archives/l/libreplaygain/r475/) |
| **libresample** | 0.1.5 | ✅ 已编译 |  | custom | 0 | - | [📄](archives/l/libresample/0.1.5/) |
| **libressl** | 4.3.1、3.9.2 | ✅ 已编译 |  | CMake | 1 | - | [📄](archives/l/libressl/3.9.2/) |
| **libretls** | 3.8.1 | compiling |  | Autotools | 1 | - | [📄](archives/l/libretls/3.8.1/) |
| **librevenge** | 0.0.5 | ✅ 已发布 |  |  | 5 | - | [📄](archives/l/librevenge/0.0.5/) |
| **librsvg** | 2.62.2 | ✅ 已发布 |  |  | 2 | - | [📄](archives/l/librsvg/2.62.2/) |
| **librtlsdr** | 2.0.2 | ✅ 已编译 |  |  | 4 | - | [📄](archives/l/librtlsdr/2.0.2/) |
| **libsamplerate** | 0.2.2 | ✅ 已发布 |  |  | - | - | [📄](archives/l/libsamplerate/0.2.2/) |
| **libsass** | 3.6.5 | ✅ 已编译 |  | Makefile | - | - | [📄](archives/l/libsass/3.6.5/) |
| **libsecp256k1** | 0.7.1 | ✅ 已发布 |  |  | - | - | [📄](archives/l/libsecp256k1/0.7.1/) |
| **libsepol** | 3.10 | ✅ 已发布 |  |  | - | - | [📄](archives/l/libsepol/3.10/) |
| **libserialport** | 0.1.2 | ✅ 已发布 |  |  | 2 | - | [📄](archives/l/libserialport/0.1.2/) |
| **libsfdo** | 0.1.4 | ✅ 已发布 |  |  | - | - | [📄](archives/l/libsfdo/0.1.4/) |
| **libsigc++** | 2.10.8 | ✅ 已编译 |  |  | - | - | [📄](archives/l/libsigc++/2.10.8/) |
| **libsignal-protocol-c** | 2.3.3 | ✅ 已编译 |  |  | 1 | - | [📄](archives/l/libsignal-protocol-c/2.3.3/) |
| **libsignon-glib** | 2.1 | ✅ 已发布 |  |  | - | - | [📄](archives/l/libsignon-glib/2.1/) |
| **libsigrok** | 0.5.2 | unknown |  |  | - | glib-2.0,libserialport,libzip >= 1.10,zlib | [📄](archives/l/libsigrok/0.5.2/) |
| **libsigsegv** | 2.15 | ✅ 已编译 |  |  | 3 | - | [📄](archives/l/libsigsegv/2.15/) |
| **libsixel** | 1.10.5 | uploaded |  | unknown | 0 | - | [📄](archives/l/libsixel/1.10.5/) |
| **libslirp** | 4.9.1 | ✅ 已编译 |  | Meson | - | - | [📄](archives/l/libslirp/4.9.1/) |
| **libsm** | 1.2.4 | ✅ 已编译 |  |  | 2 | - | [📄](archives/l/libsm/1.2.4/) |
| **libsmi** | 0.5.0 | success |  | Autotools | 26 | - | [📄](archives/l/libsmi/0.5.0/) |
| **libsndfile** | 1.2.2 | ✅ 已发布 |  |  | 2 | - | [📄](archives/l/libsndfile/1.2.2/) |
| **libsolv** | 0.7.30 | ✅ 已发布 |  | Autotools | - | - | [📄](archives/l/libsolv/0.7.30/) |
| **libsoundio** | 2.0.1-7 | ✅ 已编译 |  |  | 1 | - | [📄](archives/l/libsoundio/2.0.1-7/) |
| **libsoup** | 2.74.3 | success |  | Meson | 1 | libpsl 0.21.1,glib 2.88.0,libxml2 2.15.3,sqlite3 3.49.1,brotli 1.1.0 | [📄](archives/l/libsoup/2.74.3/) |
| **libsoup3** | 3.6.5-r1 | ✅ 已编译 |  |  | - | - | [📄](archives/l/libsoup3/3.6.5-r1/) |
| **libsoxr** | 0.1.3 | 📦 已归档 |  |  | - | - | [📄](archives/l/libsoxr/0.1.3/) |
| **libspatialite** | 5.1.0 | ✅ 已编译 |  | Autotools | 2 | - | [📄](archives/l/libspatialite/5.1.0/) |
| **libspf2** | 1.2.11 | ✅ 已编译 |  |  | - | - | [📄](archives/l/libspf2/1.2.11/) |
| **libspiro** | 20240903 | unknown |  |  | - | - | [📄](archives/l/libspiro/20240903/) |
| **libspnav** | 1.2 | ✅ 已编译 |  |  | - | - | [📄](archives/l/libspnav/1.2/) |
| **libspng** | 0.7.4 | unknown |  | CMake | - | zlib >= 1.2.0 | [📄](archives/l/libspng/0.7.4/) |
| **libsrtp** | 2.8.0 | ✅ 已编译 |  |  | - | - | [📄](archives/l/libsrtp/2.8.0/) |
| **libssh** | 0.11.4 | uploaded |  | Autotools | 0 | - | [📄](archives/l/libssh/0.11.4/) |
| **libssh2** | 1.11.0 | uploaded |  | Autotools | 0 | - | [📄](archives/l/libssh2/1.11.0/) |
| **libstemmer** | 3.1.1 | ✅ 已编译 |  |  | - | - | [📄](archives/l/libstemmer/3.1.1/) |
| **libsv** | 1.2 | ✅ 已编译 |  |  | - | - | [📄](archives/l/libsv/1.2/) |
| **libtap** | 0.1.0 | ✅ 已编译 |  |  | - | - | [📄](archives/l/libtap/0.1.0/) |
| **libtar** | 1.2.20 | ✅ 已编译 |  | Autotools | - | - | [📄](archives/l/libtar/1.2.20/) |
| **libtasn1** | 4.21.0 | uploaded |  | Autotools | 0 | - | [📄](archives/l/libtasn1/4.21.0/) |
| **libtermkey** | 0.22 | ✅ 已编译 |  |  | - | - | [📄](archives/l/libtermkey/0.22/) |
| **libtextstyle** | 0.8 | partial |  |  | - | ncurses | [📄](archives/l/libtextstyle/0.8/) |
| **libtheora** | 1.1.1 | ✅ 已编译 |  |  | 0 | name: libogg | [📄](archives/l/libtheora/1.1.1/) |
| **libtickit** | 0.4.6 | ✅ 已编译 |  |  | 1 | - | [📄](archives/l/libtickit/0.4.6/) |
| **libtiff** | 4.6.0 | uploaded |  | Autotools | 0 | - | [📄](archives/l/libtiff/4.6.0/) |
| **libtinycbor** | v7.0 | ✅ 已发布 |  |  | - | - | [📄](archives/l/libtinycbor/v7.0/) |
| **libtirpc** | 1.3.3 | ✅ 已编译 |  | Autotools | 4 | [] | [📄](archives/l/libtirpc/1.3.3/) |
| **libtommath** | 1.3.0 | unknown |  | Makefile | - | [] | [📄](archives/l/libtommath/1.3.0/) |
| **libtool** | 2.4.7 | verified |  | Autotools | 0 | autoconf,automake,m4 | [📄](archives/l/libtool/2.4.7/) |
| **libtorrent-rakshasa** | 0.16.12 | ✅ 已发布 |  |  | 1 | - | [📄](archives/l/libtorrent-rakshasa/0.16.12/) |
| **libtorrent-rasterbar** | 2.0.9 | ✅ 已编译 |  | CMake | 3 | - | [📄](archives/l/libtorrent-rasterbar/2.0.9/) |
| **libtraceevent** | 1.9.0 | ✅ 已编译 |  | Makefile | 1 | - | [📄](archives/l/libtraceevent/1.9.0/) |
| **libtracefs** | 1.8.3 | ✅ 已编译 |  | Makefile | 1 | - | [📄](archives/l/libtracefs/1.8.3/) |
| **libtree** | 3.2.0-dev | ✅ 已编译 |  |  | - | - | [📄](archives/l/libtree/3.2.0-dev/) |
| **libu2f-server** | 1.1.0 | ✅ 已发布 |  |  | 1 | - | [📄](archives/l/libu2f-server/1.1.0/) |
| **libucl** | 0.9.4 | ✅ 已发布 |  |  | - | - | [📄](archives/l/libucl/0.9.4/) |
| **libucontext** | 1.2 | ✅ 已编译 |  | Makefile | - | - | [📄](archives/l/libucontext/1.2/) |
| **libudev-zero** | 1.0.4 | ✅ 已发布 |  |  | 3 | - | [📄](archives/l/libudev-zero/1.0.4/) |
| **libunibreak** | 7.0 | ✅ 已发布 |  | Autotools | - | - | [📄](archives/l/libunibreak/7.0/) |
| **libunicode** | 0.9.0 | ✅ 已编译 |  | CMake | 1 | [] | [📄](archives/l/libunicode/0.9.0/) |
| **libunistring** | 1.0、1.4.2 | ✅ 已发布 |  | Autotools | 2 | - | [📄](archives/l/libunistring/1.4.2/) |
| **libunwind** | 1.6.2 | ✅ 已编译 |  |  | 48 | - | [📄](archives/l/libunwind/1.6.2/) |
| **libupnp** | 1.18.5 | ✅ 已编译 |  |  | 2 | - | [📄](archives/l/libupnp/1.18.5/) |
| **libupnpp** | 1.0.4 | ✅ 已编译 |  | Meson | 5 | - | [📄](archives/l/libupnpp/1.0.4/) |
| **liburing** | 2.7 | ✅ 已编译 |  | configure-make | - | - | [📄](archives/l/liburing/2.7/) |
| **liburiparser** | 1.0.2 | ✅ 已编译 |  | CMake | - | [] | [📄](archives/l/liburiparser/1.0.2/) |
| **libusb** | 1.0.27 | uploaded |  | unknown | 0 | - | [📄](archives/l/libusb/1.0.27/) |
| **libusb-compat** | 0.1.7 | ✅ 已编译 |  | CMake | 3 | - | [📄](archives/l/libusb-compat/0.1.7/) |
| **libusbgx** | 0.3.0 | ✅ 已发布 |  |  | - | - | [📄](archives/l/libusbgx/0.3.0/) |
| **libusbmuxd** | 2.1.0 | ✅ 已发布 |  | Autotools | - | - | [📄](archives/l/libusbmuxd/2.1.0/) |
| **libusrsctp** | 0.9.5.0 | success |  | CMake | 5 | - | [📄](archives/l/libusrsctp/0.9.5.0/) |
| **libutempter** | 1.2.3 | ✅ 已编译 |  |  | 2 | - | [📄](archives/l/libutempter/1.2.3/) |
| **libuv** | 1.52.1 | uploaded |  | Autotools | 0 | - | [📄](archives/l/libuv/1.52.1/) |
| **libva** | 2.23.0 | partial |  |  | - | - | [📄](archives/l/libva/2.23.0/) |
| **libva-utils** | 2.23.0 | ✅ 已编译 |  |  | - | - | [📄](archives/l/libva-utils/2.23.0/) |
| **libverto** | 0.3.2 | ✅ 已编译 |  |  | 3 | - | [📄](archives/l/libverto/0.3.2/) |
| **libvfn** | 5.1.0 | ✅ 已编译 |  | Meson | 2 | - | [📄](archives/l/libvfn/5.1.0/) |
| **libvirt** | 10.1.0 | ✅ 已编译 |  |  | - | - | [📄](archives/l/libvirt/10.1.0/) |
| **libvirt-glib** | 5.0.0 | ✅ 已编译 |  |  | - | - | [📄](archives/l/libvirt-glib/5.0.0/) |
| **libvirt-python** | 10.1.0 | ✅ 已编译 |  | custom | 1 | - | [📄](archives/l/libvirt-python/10.1.0/) |
| **libvmaf** | 2.3.1 | ✅ 已编译 |  | Meson | 2 | - | [📄](archives/l/libvmaf/2.3.1/) |
| **libvo-aacenc** | 0.1.3 | ✅ 已编译 |  |  | 3 | - | [📄](archives/l/libvo-aacenc/0.1.3/) |
| **libvolk** | 1.4.350 | ✅ 已编译 |  |  | - | - | [📄](archives/l/libvolk/1.4.350/) |
| **libvorbis** | 1.3.7 | ✅ 已编译 |  | Autotools | - | - | [📄](archives/l/libvorbis/1.3.7/) |
| **libvpx** | 1.14.1 | ✅ 已编译 |  |  | 2 | - | [📄](archives/l/libvpx/1.14.1/) |
| **libvterm** | 0.3.3 | ✅ 已发布 |  |  | - | - | [📄](archives/l/libvterm/0.3.3/) |
| **libwapcaplet** | 0.4.3 | ✅ 已发布 |  | Makefile | 1 | - | [📄](archives/l/libwapcaplet/0.4.3/) |
| **libwebp** | 1.3.2 | uploaded |  | Autotools | 0 | - | [📄](archives/l/libwebp/1.3.2/) |
| **libwebsockets** | 4.3.5 | ✅ 已发布 |  |  | 2 | - | [📄](archives/l/libwebsockets/4.3.5/) |
| **libwmf** | 0.2.15 | ✅ 已编译 |  |  | - | - | [📄](archives/l/libwmf/0.2.15/) |
| **libwpe** | 1.16.0 | ✅ 已编译 |  | Meson | 2 | - | [📄](archives/l/libwpe/1.16.0/) |
| **libwpebackend-fdo** | 1.15.90 | ✅ 已编译 |  | Meson | - | - | [📄](archives/l/libwpebackend-fdo/1.15.90/) |
| **libx11** | 1.8.10 | ✅ 已发布 |  | Autotools | 30 | - | [📄](archives/l/libx11/1.8.10/) |
| **libxau** | 1.0.11 | ✅ 已发布 |  |  | - | - | [📄](archives/l/libxau/1.0.11/) |
| **libxcb** | 1.16 | ✅ 已发布 |  |  | - | - | [📄](archives/l/libxcb/1.16/) |
| **libxcrypt** | 4.4.36 | ✅ 已编译 |  |  | 3 | - | [📄](archives/l/libxcrypt/4.4.36/) |
| **libxcvt** | 0.1.3 | success |  | Meson | - | - | [📄](archives/l/libxcvt/0.1.3/) |
| **libxdg-basedir** | 1.2.3 | ✅ 已编译 |  |  | - | - | [📄](archives/l/libxdg-basedir/1.2.3/) |
| **libxdiff** | 0.23 | ✅ 已编译 |  | Autotools | 4 | - | [📄](archives/l/libxdiff/0.23/) |
| **libxdmcp** | 1.1.4 | ✅ 已发布 |  |  | - | - | [📄](archives/l/libxdmcp/1.1.4/) |
| **libxext** | 1.3.6 | ✅ 已发布 |  | Autotools | - | libX11,xproto,xextproto | [📄](archives/l/libXext/1.3.6/) |
| **libxfce4util** | 4.20.0 | ✅ 已编译 |  |  | 3 | - | [📄](archives/l/libxfce4util/4.20.0/) |
| **libxisf** | 0.2.13 | ✅ 已编译 |  |  | 1 | - | [📄](archives/l/libxisf/0.2.13/) |
| **libxkbcommon** | 1.6.0 | ✅ 已发布 |  |  | - | - | [📄](archives/l/libxkbcommon/1.6.0/) |
| **libxlsxwriter** | 1.2.4 | ✅ 已发布 |  |  | - | - | [📄](archives/l/libxlsxwriter/1.2.4/) |
| **libxml++** | 5.4.0 | ✅ 已编译 |  | Meson | - | name: libxml2 | [📄](archives/l/libxml++/5.4.0/) |
| **libxml2** | 2.15.3 | ✅ 已编译 |  | Meson | 2 | - | [📄](archives/l/libxml2/2.15.3/) |
| **libxmlb** | 0.3.19 | ✅ 已编译 |  |  | - | - | [📄](archives/l/libxmlb/0.3.19/) |
| **libxmp** | 4.6.0 | ✅ 已编译 |  | CMake | 2 | [] | [📄](archives/l/libxmp/4.6.0/) |
| **libxpresent** | 1.0.2 | ✅ 已编译 |  | Autotools | 3 | - | [📄](archives/l/libxpresent/1.0.2/) |
| **libxrandr** | 1.5.5 | ✅ 已编译 |  |  | 3 | - | [📄](archives/l/libxrandr/1.5.5/) |
| **libxshmfence** | 1.3.3 | success |  | Autotools | 2 | - | [📄](archives/l/libxshmfence/1.3.3/) |
| **libxslt** | 1.1.39、1.1.42 | ✅ 已编译 |  |  | - | - | [📄](archives/l/libxslt/1.1.42/) |
| **libxxhash** | 0.8.2 | ✅ 已编译 |  | Makefile | 1 | - | [📄](archives/l/libxxhash/0.8.2/) |
| **libyubikey** | 1.13 | ✅ 已发布 |  | Autotools | 2 | - | [📄](archives/l/libyubikey/1.13/) |
| **libzbar** | 0.23.93 | ✅ 已编译 |  |  | - | - | [📄](archives/l/libzbar/0.23.93/) |
| **libzeitgeist** | 0.3.18 | ✅ 已编译 |  | Autotools | 2 | - | [📄](archives/l/libzeitgeist/0.3.18/) |
| **libzen** | 0.4.41 | ✅ 已发布 |  |  | 1 | - | [📄](archives/l/libzen/0.4.41/) |
| **libzim** | 9.7.0 | ✅ 已发布 |  |  | - | - | [📄](archives/l/libzim/9.7.0/) |
| **libzip** | 1.10.1、1.11.4 | ✅ 已编译 |  | CMake | - | - | [📄](archives/l/libzip/1.11.4/) |
| **lighttpd** | 1.4.82 | unknown |  |  | - | openssl,zlib,pcre2 | [📄](archives/l/lighttpd/1.4.82/) |
| **lilv** | 0.26.5-git | ✅ 已发布 |  |  | - | - | [📄](archives/l/lilv/0.26.5-git/) |
| **links** | 2.30 | ✅ 已编译 |  |  | - | - | [📄](archives/l/links/2.30/) |
| **links-graphics** | 2.30 | ✅ 已编译 |  | Autotools | 3 | - | [📄](archives/l/links-graphics/2.30/) |
| **list-someutils-xs** | 0.58 | ✅ 已编译 |  | perl | - | - | [📄](archives/l/list-someutils-xs/0.58/) |
| **livekit** | 1.13.1 | ✅ 已发布 |  | custom | - | - | [📄](archives/l/livekit/1.13.1/) |
| **llhttp** | 9.3.1 | ✅ 已发布 |  |  | - | - | [📄](archives/l/llhttp/9.3.1/) |
| **llvm** | 17.0.0 | ✅ 已编译 |  |  | - | - | [📄](archives/l/llvm/17.0.0/) |
| **lm-sensors** | 3.6.0 | uploaded |  | Makefile | 0 | - | [📄](archives/l/lm-sensors/3.6.0/) |
| **lmdb** | 0.9.33、0.9.35 | uploaded |  | Autotools | 0 | - | [📄](archives/l/lmdb/0.9.35/) |
| **lmdbxx** | 0.9.14.0 | ✅ 已编译 |  |  | - | - | [📄](archives/l/lmdbxx/0.9.14.0/) |
| **lmfit** | 10.0 | ✅ 已发布 |  | CMake | - | - | [📄](archives/l/lmfit/10.0/) |
| **lockdev** | 1.0.3 | ✅ 已编译 |  |  | 2 | - | [📄](archives/l/lockdev/1.0.3/) |
| **lockrun** | 1.1.3 | ✅ 已发布 |  | manual | - | - | [📄](archives/l/lockrun/1.1.3/) |
| **log4shib** | 2.0.1 | ✅ 已发布 |  | Autotools | 3 | - | [📄](archives/l/log4shib/2.0.1/) |
| **log_proxy** | 0.7.4 | ✅ 已发布 |  |  | - | - | [📄](archives/l/log_proxy/0.7.4/) |
| **logbookd** | 0.2.6 | ✅ 已发布 |  | Meson | 1 | - | [📄](archives/l/logbookd/0.2.6/) |
| **logcli** | 3.7.2 | ✅ 已发布 |  | go | - | go >= 1.26 | [📄](archives/l/logcli/3.7.2/) |
| **lolcat** | 100.0.1 | ✅ 已发布 |  |  | - | - | [📄](archives/l/lolcat/100.0.1/) |
| **lolcode** | 0.10.5 | ✅ 已发布 |  |  | 1 | - | [📄](archives/l/lolcode/0.10.5/) |
| **lp_solve** | 5.5.2.14 | ✅ 已发布 |  | custom | 3 | - | [📄](archives/l/lp_solve/5.5.2.14/) |
| **lpeg** | 1.1.0 | ✅ 已编译 |  | Makefile | 1 | - | [📄](archives/l/lpeg/1.1.0/) |
| **lrdf** | 0.6.1 | ✅ 已编译 |  |  | - | - | [📄](archives/l/lrdf/0.6.1/) |
| **lrexlib** | 2.9.1 | ✅ 已编译 |  | custom | - | - | [📄](archives/l/lrexlib/2.9.1/) |
| **lrzip** | 0.651 | ✅ 已发布 |  |  | 26 | - | [📄](archives/l/lrzip/0.651/) |
| **lrzsz** | 0.12.20 | ✅ 已发布 |  | Autotools | - | - | [📄](archives/l/lrzsz/0.12.20/) |
| **lshw** | B.02.20 | ✅ 已编译 |  |  | 2 | - | [📄](archives/l/lshw/B.02.20/) |
| **lsof** | 4.99.0 | ✅ 已编译 |  |  | 2 | - | [📄](archives/l/lsof/4.99.0/) |
| **lsyncd** | 2.3.1 | ✅ 已发布 |  |  | 1 | - | [📄](archives/l/lsyncd/2.3.1/) |
| **lua** | 5.2.4、5.3.6、5.4.7、5.4.8 | ✅ 已编译 |  | Makefile | - | - | [📄](archives/l/lua/5.4.8/) |
| **lua-alt-getopt** | 0.8.0 | ✅ 已编译 |  | custom | - | - | [📄](archives/l/lua-alt-getopt/0.8.0/) |
| **lua-ansicolors** | 1.0.2 | ✅ 已发布 |  |  | - | - | [📄](archives/l/lua-ansicolors/1.0.2/) |
| **lua-jsonschema** | 0.9.13 | ✅ 已编译 |  |  | - | - | [📄](archives/l/lua-jsonschema/0.9.13/) |
| **lua-language-server** | 3.18.2 | ✅ 已编译 |  |  | 54 | - | [📄](archives/l/lua-language-server/3.18.2/) |
| **lua-lsqlite3** | 0.9.4 | ✅ 已编译 |  | custom | - | - | [📄](archives/l/lua-lsqlite3/0.9.4/) |
| **lua-microlight** | 1.0 | ✅ 已编译 |  |  | 0 | - | [📄](archives/l/lua-microlight/1.0/) |
| **lua-mimetypes** | 1.0 | ✅ 已编译 |  |  | 0 | - | [📄](archives/l/lua-mimetypes/1.0/) |
| **lua-net-url** | 0.1.0 | ✅ 已编译 |  |  | 0 | - | [📄](archives/l/lua-net-url/0.1.0/) |
| **lua-optarg** | 0.4 | ✅ 已编译 |  | custom | - | - | [📄](archives/l/lua-optarg/0.4/) |
| **lua-optparse** | 0.3 | ✅ 已编译 |  |  | - | - | [📄](archives/l/lua-optparse/0.3/) |
| **lua-pc** | 5.4.7 | ✅ 已编译 |  |  | 1 | - | [📄](archives/l/lua-pc/5.4.7/) |
| **lua-penlight** | 1.15.0 | ✅ 已编译 |  | lua | - | - | [📄](archives/l/lua-penlight/1.15.0/) |
| **lua-pgmoon** | 2.3.4.0 | ✅ 已编译 |  | custom | - | - | [📄](archives/l/lua-pgmoon/2.3.4.0/) |
| **lua-pty** | 1.1 | ✅ 已编译 |  |  | 2 | - | [📄](archives/l/lua-pty/1.1/) |
| **lua-rapidjson** | 0.6.0 | ✅ 已编译 |  |  | - | - | [📄](archives/l/lua-rapidjson/0.6.0/) |
| **lua-redis** | 2.0.4 | ✅ 已编译 |  |  | 1 | - | [📄](archives/l/lua-redis/2.0.4/) |
| **lua-resty-core** | v0.1.27 | ✅ 已编译 |  | Makefile | - | lua/5.4.7 | [📄](archives/l/lua-resty-core/v0.1.27/) |
| **lua-resty-dns** | v0.23 | ✅ 已编译 |  | Makefile | - | - | [📄](archives/l/lua-resty-dns/v0.23/) |
| **lua-resty-hmac** | v0.06 | ✅ 已编译 |  |  | - | - | [📄](archives/l/lua-resty-hmac/v0.06/) |
| **lua-resty-http** | 0.17.2 | ✅ 已编译 |  |  | - | - | [📄](archives/l/lua-resty-http/0.17.2/) |
| **lua-resty-jwt** | v0.1.11 | ✅ 已编译 |  | custom | - | - | [📄](archives/l/lua-resty-jwt/v0.1.11/) |
| **lua-resty-lock** | 0.09 | ✅ 已发布 |  | Makefile | - | - | [📄](archives/l/lua-resty-lock/0.09/) |
| **lua-resty-lrucache** | 0.15 | ✅ 已编译 |  | Makefile | - | lua/5.4.7 | [📄](archives/l/lua-resty-lrucache/0.15/) |
| **lua-resty-mail** | 1.2.0 | ✅ 已编译 |  |  | - | - | [📄](archives/l/lua-resty-mail/1.2.0/) |
| **lua-resty-openidc** | 1.7.6 | ✅ 已发布 |  |  | 1 | - | [📄](archives/l/lua-resty-openidc/1.7.6/) |
| **lua-resty-session** | 3.10 | ✅ 已发布 |  |  | 1 | - | [📄](archives/l/lua-resty-session/3.10/) |
| **lua-resty-string** | 0.16 | ✅ 已编译 |  |  | - | - | [📄](archives/l/lua-resty-string/0.16/) |
| **lua-say** | 1.3-1 | ✅ 已发布 |  | Makefile | - | - | [📄](archives/l/lua-say/1.3-1/) |
| **lua-sleep** | 1.0.0-4 | ✅ 已编译 |  |  | 1 | - | [📄](archives/l/lua-sleep/1.0.0-4/) |
| **lua-soap** | 4.0.1 | ✅ 已编译 |  | Makefile | 1 | - | [📄](archives/l/lua-soap/4.0.1/) |
| **lua-socket** | 3.1.0 | ✅ 已编译 |  |  | - | - | [📄](archives/l/lua-socket/3.1.0/) |
| **lua-sqlite** | 2.6.0 | ✅ 已编译 |  |  | 2 | - | [📄](archives/l/lua-sqlite/2.6.0/) |
| **lua-stacktraceplus** | 0.1.2 | ✅ 已编译 |  |  | - | - | [📄](archives/l/lua-stacktraceplus/0.1.2/) |
| **lua-stdlib** | 41.2.1 | ✅ 已编译 |  | Autotools | 7 | - | [📄](archives/l/lua-stdlib/41.2.1/) |
| **lua-stdlib-debug** | 41.2.1 | ✅ 已编译 |  |  | 1 | - | [📄](archives/l/lua-stdlib-debug/41.2.1/) |
| **lua-stdlib-normalize** | 2.0.3 | ✅ 已编译 |  |  | - | - | [📄](archives/l/lua-stdlib-normalize/2.0.3/) |
| **lua-stringy** | 0.7 | ✅ 已编译 |  |  | - | - | [📄](archives/l/lua-stringy/0.7/) |
| **lua-struct** | 0.9.2 | ✅ 已发布 |  | Makefile | - | - | [📄](archives/l/lua-struct/0.9.2/) |
| **lua-subprocess** | 0.02 | ✅ 已编译 |  | Makefile | - | - | [📄](archives/l/lua-subprocess/0.02/) |
| **lua-tableshape** | 2.7.0 | ✅ 已编译 |  | lua | - | - | [📄](archives/l/lua-tableshape/2.7.0/) |
| **lua-term** | 0.7 | ✅ 已编译 |  | Makefile | 1 | - | [📄](archives/l/lua-term/0.7/) |
| **lua-toml** | 1.0 | ✅ 已编译 |  | manual | - | - | [📄](archives/l/lua-toml/1.0/) |
| **lua-uuid** | 1.0.0 | ✅ 已编译 |  | manual | - | - | [📄](archives/l/lua-uuid/1.0.0/) |
| **luacheck** | 0.23.0 | ✅ 已编译 |  | luarocks | - | - | [📄](archives/l/luacheck/0.23.0/) |
| **luajit** | 2.1.rolling | ✅ 已编译 |  | Makefile | 4 | - | [📄](archives/l/luajit/2.1.rolling/) |
| **luajit-openresty** | 2.1-20260311 | ✅ 已编译 |  |  | - | - | [📄](archives/l/luajit-openresty/2.1-20260311/) |
| **luarocks** | 3.12.2 | ✅ 已编译 |  | Autotools | - | - | [📄](archives/l/luarocks/3.12.2/) |
| **luasql** | 2.3.5 | ✅ 已发布 |  |  | 1 | - | [📄](archives/l/luasql/2.3.5/) |
| **luassert** | 1.9.0 | ✅ 已编译 |  | lua-builtin | - | - | [📄](archives/l/luassert/1.9.0/) |
| **luau** | 0.689-r0 | ✅ 已编译 |  |  | - | [] | [📄](archives/l/luau/0.689-r0/) |
| **luaunit** | 3.5 | ✅ 已发布 |  | manual | - | lua >= 5.1 | [📄](archives/l/luaunit/3.5/) |
| **lub** | 1.1.0 | ✅ 已编译 |  | CMake | 1 | - | [📄](archives/l/lub/1.1.0/) |
| **luit** | 20250912 | ✅ 已发布 |  | Autotools | 2 | - | [📄](archives/l/luit/20250912/) |
| **lustache** | 1.3.1-0 | ✅ 已编译 |  |  | 1 | - | [📄](archives/l/lustache/1.3.1-0/) |
| **luufs** | 0.1 | ✅ 已编译 |  | Makefile | - | fuse,zlib | [📄](archives/l/luufs/0.1/) |
| **luv** | 1.52.1-0 | ✅ 已编译 |  | CMake | 2 | - | [📄](archives/l/luv/1.52.1-0/) |
| **lv** | 4.51-10 | ✅ 已编译 |  |  | 1 | - | [📄](archives/l/lv/4.51-10/) |
| **lv2** | 1.18.11-git | ✅ 已发布 |  |  | - | - | [📄](archives/l/lv2/1.18.11-git/) |
| **lxc-templates-legacy** | 3.0.4 | ✅ 已编译 |  | Autotools | 11 | - | [📄](archives/l/lxc-templates-legacy/3.0.4/) |
| **lyaml** | 6.2.8 | ✅ 已编译 |  |  | - | - | [📄](archives/l/lyaml/6.2.8/) |
| **lynx** | 2.9.2 | ✅ 已编译 |  |  | 1 | - | [📄](archives/l/lynx/2.9.2/) |
| **lz4** | 1.10.0 | uploaded |  | unknown | 0 | - | [📄](archives/l/lz4/1.10.0/) |
| **lz4jsoncat** | v2 | uploaded |  | Makefile | 0 | - | [📄](archives/l/lz4jsoncat/v2/) |
| **lzbench** | 2.2 | uploaded |  | Makefile | 0 | - | [📄](archives/l/lzbench/2.2/) |
| **lzfse** | 1.0 | ✅ 已编译 |  |  | - | - | [📄](archives/l/lzfse/1.0/) |
| **lzip** | 1.25、1.26 | uploaded |  | Autotools | 0 | - | [📄](archives/l/lzip/1.26/) |
| **lzlib** | 1.15、1.9 | uploaded |  | Autotools | 0 | - | [📄](archives/l/lzlib/1.9/) |
| **lzma** | 5.6.2 | uploaded |  | Autotools | 0 | - | [📄](archives/l/lzma/5.6.2/) |
| **lzo** | 2.10 | uploaded |  | Autotools | 0 | - | [📄](archives/l/lzo/2.10/) |
| **lzo2** | 2.10 | uploaded |  | unknown | 0 | - | [📄](archives/l/lzo2/2.10/) |
| **lzop** | 1.04 | uploaded |  | Autotools | 0 | - | [📄](archives/l/lzop/1.04/) |
| **m17n-lib** | 1.8.6 | ✅ 已发布 |  | Autotools | 6 | - | [📄](archives/m/m17n-lib/1.8.6/) |
| **m4** | 1.4.19 | uploaded |  | Autotools | 0 | - | [📄](archives/m/m4/1.4.19/) |
| **mac** | 12.60 | ✅ 已发布 |  | CMake | - | - | [📄](archives/m/mac/12.60/) |
| **macchanger** | 1.7.0-r3 | ✅ 已编译 |  |  | 1 | - | [📄](archives/m/macchanger/1.7.0-r3/) |
| **mackup** | 0.10.3 | ✅ 已发布 |  |  | - | - | [📄](archives/m/mackup/0.10.3/) |
| **magic-wormhole** | 0.24.0 | ✅ 已发布 |  |  | - | - | [📄](archives/m/magic-wormhole/0.24.0/) |
| **make** | 4.4.1 | ✅ 已编译 |  | Autotools | 2 | [] | [📄](archives/m/make/4.4.1/) |
| **makedepend** | 1.0.9 | ✅ 已编译 |  |  | 2 | - | [📄](archives/m/makedepend/1.0.9/) |
| **makefile2graph** | 1.5.0 | ✅ 已编译 |  | Makefile | - | - | [📄](archives/m/makefile2graph/1.5.0/) |
| **man-db** | 2.13.1 | verified |  | Autotools | 0 | - | [📄](archives/m/man-db/2.13.1/) |
| **man-pages** | 6.18 | ✅ 已编译 |  |  | 15 | - | [📄](archives/m/man-pages/6.18/) |
| **mandoc** | 1.14.6 | success |  | custom-configure | 1 | - | [📄](archives/m/mandoc/1.14.6/) |
| **mandown** | 1.0.5.2 | ✅ 已编译 |  |  | 1 | libxml2 (2.15.3),libconfig (1.7.3),ncursesw (6.4, static) | [📄](archives/m/mandown/1.0.5.2/) |
| **mangohud** | 0.8.4 | ✅ 已发布 |  |  | 2 | - | [📄](archives/m/mangohud/0.8.4/) |
| **manticore** | 6.7.0 | ✅ 已发布 |  |  | 2 | - | [📄](archives/m/manticore/6.7.0/) |
| **mariadb-connector-c** | 3.4.8 | success |  |  | 1 | - | [📄](archives/m/mariadb-connector-c/3.4.8/) |
| **mask** | 0.11.7 | ✅ 已编译 |  | cargo | - | - | [📄](archives/m/mask/0.11.7/) |
| **masscan** | 1.3.9 | ✅ 已编译 |  | Makefile | 6 | - | [📄](archives/m/masscan/1.3.9/) |
| **massdns** | 1.1.0 | ✅ 已编译 |  | Makefile | - | - | [📄](archives/m/massdns/1.1.0/) |
| **mate-menus** | 1.28.0 | ✅ 已编译 |  |  | 3 | - | [📄](archives/m/mate-menus/1.28.0/) |
| **matio** | 1.5.23 | ✅ 已编译 |  |  | 2 | - | [📄](archives/m/matio/1.5.23/) |
| **matplotplusplus** | 1.2.0 | ✅ 已编译 |  | CMake | - | - | [📄](archives/m/matplotplusplus/1.2.0/) |
| **mawk** | 1.3.4-20260302 | ✅ 已编译 |  |  | 4 | - | [📄](archives/m/mawk/1.3.4-20260302/) |
| **mbedtls** | 2.28.8、3.6.6、4.1.0、2.28.10、3.6.0 | ✅ 已编译 |  | CMake | - | - | [📄](archives/m/mbedtls/3.6.0/) |
| **mc** | 4.8.30 | ✅ 已发布 |  | Autotools | - | glib 2.88.0,ncurses 6.4,libintl,pcre2 | [📄](archives/m/mc/4.8.30/) |
| **mcfly** | 0.9.4 | ✅ 已发布 |  |  | - | - | [📄](archives/m/mcfly/0.9.4/) |
| **mcpp** | 2.7.2 | ✅ 已编译 |  |  | 3 | - | [📄](archives/m/mcpp/2.7.2/) |
| **mcron** | 1.2.3 | ✅ 已发布 |  |  | 2 | - | [📄](archives/m/mcron/1.2.3/) |
| **md2pdf** | 3.1.1 | ✅ 已编译 |  | custom | - | - | [📄](archives/m/md2pdf/3.1.1/) |
| **md5sha1sum** | homebrew | ✅ 已发布 |  |  | - | - | [📄](archives/m/md5sha1sum/homebrew/) |
| **mdbook-mermaid** | 0.17.0 | ✅ 已发布 |  | cargo | - | - | [📄](archives/m/mdbook-mermaid/0.17.0/) |
| **mdbtools** | 1.0.1 | ✅ 已发布 |  | Autotools | 2 | glib,bison,flex | [📄](archives/m/mdbtools/1.0.1/) |
| **mdf2iso** | 0.3.1 | ✅ 已发布 |  | Autotools | 1 | - | [📄](archives/m/mdf2iso/0.3.1/) |
| **mdflib** | v2.1 | ✅ 已发布 |  | CMake | 1 | - | [📄](archives/m/mdflib/v2.1/) |
| **mdns-scan** | 0.5 | ✅ 已发布 |  |  | - | - | [📄](archives/m/mdns-scan/0.5/) |
| **mecab** | 0.996 | partial |  | Autotools | 3 | libc++ (替换 libstdc++) | [📄](archives/m/mecab/0.996/) |
| **mecab-ko** | 0.996-ko-0.9.2 | ✅ 已编译 |  |  | 8 | - | [📄](archives/m/mecab-ko/0.996-ko-0.9.2/) |
| **mecab-ko-dic** | 2.1.1-20180720 | ✅ 已编译 |  | none | - | mecab-ko | [📄](archives/m/mecab-ko-dic/2.1.1-20180720/) |
| **mediamtx** | 1.11.3 | ✅ 已发布 |  | go | - | - | [📄](archives/m/mediamtx/1.11.3/) |
| **melange** | 0.23.4、0.53.2、v0.53.2 | ✅ 已编译 |  |  | - | - | [📄](archives/m/melange/v0.53.2/) |
| **memcached** | 1.6.42 | partial |  |  | - | - | [📄](archives/m/memcached/1.6.42/) |
| **mender-artifact** | 4.4.0 | ✅ 已编译 |  |  | - | - | [📄](archives/m/mender-artifact/4.4.0/) |
| **mercury** | 22.01.8 | compiled |  | autoconf | 2 | - | [📄](archives/m/mercury/22.01.8/) |
| **meson** | 1.11.0、1.11.1、1.5.1 | ✅ 已编译 |  |  | - | - | [📄](archives/m/meson/1.5.1/) |
| **metis** | 5.1.0 | success |  | CMake | - | - | [📄](archives/m/metis/5.1.0/) |
| **mg** | 7.3 | ✅ 已发布 |  | Autotools | 5 | - | [📄](archives/m/mg/7.3/) |
| **mgis** | 3.2 | ✅ 已编译 |  | CMake | 4 | tfel >= 5.0 | [📄](archives/m/mgis/3.2/) |
| **micro** | 2.0.15 | ✅ 已编译 |  | go | - | - | [📄](archives/m/micro/2.0.15/) |
| **micropython** | 1.27.0 | success |  | custom | - | - | [📄](archives/m/micropython/1.27.0/) |
| **microsocks** | 1.0.5 | ✅ 已发布 |  | Makefile | 1 | - | [📄](archives/m/microsocks/1.0.5/) |
| **middleclass** | 4.1.1 | ✅ 已编译 |  |  | 0 | - | [📄](archives/m/middleclass/4.1.1/) |
| **midicsv** | 1.1 | ✅ 已发布 |  | Makefile | 1 | - | [📄](archives/m/midicsv/1.1/) |
| **mihomo** | 1.19.8 | ✅ 已发布 |  | go | - | - | [📄](archives/m/mihomo/1.19.8/) |
| **miller** | 6.15.0-r7 | ✅ 已发布 |  | Makefile | 3 | - | [📄](archives/m/miller/6.15.0-r7/) |
| **mimalloc** | 3.2.8 | ✅ 已编译 |  | CMake | - | - | [📄](archives/m/mimalloc/3.2.8/) |
| **mini_httpd** | 1.30 | ✅ 已编译 |  | Makefile | 3 | - | [📄](archives/m/mini_httpd/1.30/) |
| **minicom** | 2.10 | success |  | Autotools | 11 | libtinfo.so.6,make 4.4.1,autoconf 2.72,automake 1.16.5 | [📄](archives/m/minicom/2.10/) |
| **minify** | 2.24.13 | ✅ 已发布 |  |  | - | - | [📄](archives/m/minify/2.24.13/) |
| **minijinja-cli** | 2.20.0 | ✅ 已编译 |  | cargo | - | - | [📄](archives/m/minijinja-cli/2.20.0/) |
| **minimap2** | 2.30 | ✅ 已发布 |  | Makefile | - | - | [📄](archives/m/minimap2/2.30/) |
| **minio** | latest | ✅ 已编译 |  | go | - | - | [📄](archives/m/minio/latest/) |
| **minio-mc** | RELEASE.2024-11-21T17-21-54Z | ✅ 已编译 |  | custom | - | - | [📄](archives/m/minio-mc/RELEASE.2024-11-21T17-21-54Z/) |
| **minisat** | 2.2.1 | ✅ 已发布 |  | CMake | 1 | - | [📄](archives/m/minisat/2.2.1/) |
| **minisign** | 0.12-r1 | ✅ 已发布 |  | CMake | - | - | [📄](archives/m/minisign/0.12-r1/) |
| **miniupnpc** | 2.3.2、2.3.3 | success |  | Makefile | - | - | [📄](archives/m/miniupnpc/2.3.3/) |
| **minizip** | 1.3.1 | uploaded |  | unknown | 0 | - | [📄](archives/m/minizip/1.3.1/) |
| **minizip-ng** | 4.1.1 | uploaded |  | unknown | 0 | - | [📄](archives/m/minizip-ng/4.1.1/) |
| **mkclean** | 0.9.0 | ✅ 已发布 |  | CMake | 1 | - | [📄](archives/m/mkclean/0.9.0/) |
| **mkinitfs** | 3.4.5 | ✅ 已编译 |  |  | 1 | - | [📄](archives/m/mkinitfs/3.4.5/) |
| **mkvalidator** | 0.6.0 | ✅ 已编译 |  | CMake | 2 | - | [📄](archives/m/mkvalidator/0.6.0/) |
| **mockery** | homebrew、v2.46.0 | ✅ 已发布 |  | go | - | go >= 1.26,libc (musl) | [📄](archives/m/mockery/v2.46.0/) |
| **moderncli** | 1.4.1 | ✅ 已编译 |  |  | - | - | [📄](archives/m/moderncli/1.4.1/) |
| **mokutil** | 0.7.2 | ✅ 已发布 |  | Autotools | 5 | - | [📄](archives/m/mokutil/0.7.2/) |
| **mold** | 2.39.1 | ✅ 已编译 |  | CMake | 2 | - | [📄](archives/m/mold/2.39.1/) |
| **monero** | 0.18.4.4-r0 | ❌ 编译失败 |  | CMake | - | boost >= 1.66,openssl,libunbound >= 1.4.16,libsodium,libzmq >= 4.2.0... | [📄](archives/m/monero/0.18.4.4-r0/) |
| **mongo-php-library** | 2.3.0 | ✅ 已发布 |  | Script | - | - | [📄](archives/m/mongo-php-library/2.3.0/) |
| **mongoc-driver** | 1.29.0 | partial |  | cmake-ninja | - | openssl 1.1.1w,zlib 1.3.1 (bundled),zstd 1.5.7,snappy | [📄](archives/m/mongoc-driver/1.29.0/) |
| **mongodb-tools** | r4.3.2 | ✅ 已发布 |  | Makefile | 2 | - | [📄](archives/m/mongodb-tools/r4.3.2/) |
| **mongoose** | 7.21 | ✅ 已编译 |  |  | - | - | [📄](archives/m/mongoose/7.21/) |
| **mongooseim** | 6.7.0 | ✅ 已发布 |  |  | 7 | - | [📄](archives/m/mongooseim/6.7.0/) |
| **mono** | 6.12.0.122 | ✅ 已编译 |  | Autotools | 3 | - | [📄](archives/m/mono/6.12.0.122/) |
| **mosh** | 1.4.0 | ✅ 已编译 |  |  | 1 | protobuf/21.12,ncurses/6.4 | [📄](archives/m/mosh/1.4.0/) |
| **mosquitto** | 2.0.18 | uploaded |  | Autotools | 0 | - | [📄](archives/m/mosquitto/2.0.18/) |
| **mozjpeg** | 4.1.1 | ✅ 已编译 |  |  | 2 | - | [📄](archives/m/mozjpeg/4.1.1/) |
| **mp3info** | 0.8.5a | ✅ 已发布 |  | Makefile | 2 | - | [📄](archives/m/mp3info/0.8.5a/) |
| **mp3splt** | 2.6.2 | ✅ 已编译 |  | Autotools | 6 | - | [📄](archives/m/mp3splt/2.6.2/) |
| **mp3splt-gtk** | 0.9.2 | ✅ 已编译 |  |  | - | - | [📄](archives/m/mp3splt-gtk/0.9.2/) |
| **mp3val** | 0.1.8 | ✅ 已编译 |  | Makefile | 2 | - | [📄](archives/m/mp3val/0.1.8/) |
| **mp4v2** | 2.1.3 | ✅ 已编译 |  |  | 7 | - | [📄](archives/m/mp4v2/2.1.3/) |
| **mpack** | 1.6 | ✅ 已编译 |  | Autotools | 1 | [] | [📄](archives/m/mpack/1.6/) |
| **mpc** | 1.3.1 | ✅ 已编译 |  |  | 4 | - | [📄](archives/m/mpc/1.3.1/) |
| **mpdecimal** | 4.0.1 | ✅ 已发布 |  | Autotools | 2 | - | [📄](archives/m/mpdecimal/4.0.1/) |
| **mpfr** | 4.2.1、4.2.2 | ✅ 已发布 |  |  | 2 | - | [📄](archives/m/mpfr/4.2.2/) |
| **mpg123** | 1.33.5 | ✅ 已发布 |  | Autotools | 3 | - | [📄](archives/m/mpg123/1.33.5/) |
| **mpvpaper** | 1.8 | ✅ 已编译 |  |  | 1 | - | [📄](archives/m/mpvpaper/1.8/) |
| **mruby** | 3.3.0 | ✅ 已发布 |  |  | 1 | - | [📄](archives/m/mruby/3.3.0/) |
| **mscgen** | 0.20 | ✅ 已发布 |  | Autotools | 1 | - | [📄](archives/m/mscgen/0.20/) |
| **msgpack-c** | 7.0.0 | ✅ 已编译 |  |  | - | - | [📄](archives/m/msgpack-c/7.0.0/) |
| **msgpack-cxx** | 7.0.0 | ✅ 已编译 |  | CMake | - | - | [📄](archives/m/msgpack-cxx/7.0.0/) |
| **msgsl** | 4.0.0 | ✅ 已编译 |  |  | 3 | - | [📄](archives/m/msgsl/4.0.0/) |
| **msmtp** | 1.8.32 | ✅ 已编译 |  | Autotools | 3 | - | [📄](archives/m/msmtp/1.8.32/) |
| **msolve** | 0.9.5 | ✅ 已编译 |  | Autotools | - | - | [📄](archives/m/msolve/0.9.5/) |
| **mtdev** | 1.1.7 | pending |  | Autotools | 1 | - | [📄](archives/m/mtdev/1.1.7/) |
| **mtools** | 4.0.49 | ✅ 已发布 |  | Autotools | 1 | - | [📄](archives/m/mtools/4.0.49/) |
| **mtr** | 0.96 | ✅ 已发布 |  | Autotools | 7 | [] | [📄](archives/m/mtr/0.96/) |
| **mu** | 1.14.1 | ✅ 已编译 |  | Meson | - | glib/2.84.0,gmime/3.2.7,xapian-core/1.4.26 | [📄](archives/m/mu/1.14.1/) |
| **mujs** | 1.3.9 | success |  | Makefile | - | - | [📄](archives/m/mujs/1.3.9/) |
| **multitime** | 1.5 | ✅ 已编译 |  | Autotools | 3 | - | [📄](archives/m/multitime/1.5/) |
| **mummer** | 4.0.1 | ✅ 已编译 |  |  | 1 | autoconf >= 2.72,automake >= 1.16.5,libtool >= 2.4.7,yaggo >= 1.5.10,perl | [📄](archives/m/mummer/4.0.1/) |
| **mupdf** | 1.27.2 | ✅ 已编译 |  | Makefile | 6 | - | [📄](archives/m/mupdf/1.27.2/) |
| **mupdf-tools** | 1.27.2 | ✅ 已编译 |  |  | - | - | [📄](archives/m/mupdf-tools/1.27.2/) |
| **musl** | 1.2.5 | ✅ 已编译 |  |  | - | - | [📄](archives/m/musl/1.2.5/) |
| **musl-fts** | 1.2.7 | uploaded |  | unknown | 0 | - | [📄](archives/m/musl-fts/1.2.7/) |
| **musl-obstack** | 1.2.3 | uploaded |  | unknown | 0 | - | [📄](archives/m/musl-obstack/1.2.3/) |
| **mutagen** | 1.47.0 | ✅ 已编译 |  |  | - | - | [📄](archives/m/mutagen/1.47.0/) |
| **mutt** | 2.2.16 | ✅ 已编译 |  | Autotools | 20 | - | [📄](archives/m/mutt/2.2.16/) |
| **mxml** | 4.0.4 | ✅ 已发布 |  |  | 3 | - | [📄](archives/m/mxml/4.0.4/) |
| **mycli** | 1.74.0 | ✅ 已编译 |  |  | 1 | - | [📄](archives/m/mycli/1.74.0/) |
| **mypy** | 2.1.0 | ✅ 已编译 |  |  | - | - | [📄](archives/m/mypy/2.1.0/) |
| **n** | 10.2.0 | ✅ 已编译 |  | Makefile | - | - | [📄](archives/n/n/10.2.0/) |
| **n2n** | 3.1.1 | ✅ 已编译 |  | CMake | 3 | - | [📄](archives/n/n2n/3.1.1/) |
| **nano** | 7.2 | ✅ 已编译 |  | Autotools | 2 | - | [📄](archives/n/nano/7.2/) |
| **nanomsg** | 1.2 | ✅ 已编译 |  |  | 1 | - | [📄](archives/n/nanomsg/1.2/) |
| **nasm** | 2.16.03 | ✅ 已编译 |  | Autotools | 3 | - | [📄](archives/n/nasm/2.16.03/) |
| **nats-server** | v2.12.6 | ✅ 已编译 |  | go | - | - | [📄](archives/n/nats-server/v2.12.6/) |
| **nauty** | 2.9.3 | ✅ 已发布 |  |  | 2 | - | [📄](archives/n/nauty/2.9.3/) |
| **navi** | 2.24.0 | ✅ 已编译 |  | cargo | - | - | [📄](archives/n/navi/2.24.0/) |
| **nbd** | 3.26.1 | ✅ 已发布 |  |  | - | - | [📄](archives/n/nbd/3.26.1/) |
| **ncftp** | 3.3.0-r0 | ✅ 已编译 |  | autoconf | - | ncurses | [📄](archives/n/ncftp/3.3.0-r0/) |
| **ncpamixer** | 1.3.11 | ✅ 已编译 |  |  | 1 | - | [📄](archives/n/ncpamixer/1.3.11/) |
| **ncurses** | 6.4、6.5 | ✅ 已发布 |  |  | - | - | [📄](archives/n/ncurses/6.5/) |
| **ndisc6** | 1.0.8 | ✅ 已发布 |  |  | - | - | [📄](archives/n/ndisc6/1.0.8/) |
| **neon** | 0.35.0 | ✅ 已发布 |  | Autotools | 2 | - | [📄](archives/n/neon/0.35.0/) |
| **net-cpp** | 3.2.0-r0 | ✅ 已编译 |  |  | - | - | [📄](archives/n/net-cpp/3.2.0-r0/) |
| **net-snmp** | 5.9.5 | ✅ 已编译 |  | Autotools | 1 | - | [📄](archives/n/net-snmp/5.9.5/) |
| **netcat** | 0.7.1 | ✅ 已发布 |  | Autotools | - | - | [📄](archives/n/netcat/0.7.1/) |
| **netcat-openbsd** | 1.234.1 | ✅ 已发布 |  |  | - | - | [📄](archives/n/netcat-openbsd/1.234.1/) |
| **netcdf** | 4.9.2 | ✅ 已编译 |  | Autotools | 2 | - | [📄](archives/n/netcdf/4.9.2/) |
| **netcf** | 0.1.7 | ✅ 已发布 |  | Autotools | - | - | [📄](archives/n/netcf/0.1.7/) |
| **netdata** | 1.47.5 | ✅ 已编译 |  |  | 2 | - | [📄](archives/n/netdata/1.47.5/) |
| **nethogs** | 0.8.8、0.8.8-r0 | ✅ 已编译 |  |  | 2 | - | [📄](archives/n/nethogs/0.8.8-r0/) |
| **netpbm** | 10.73.42 | ✅ 已编译 |  |  | - | - | [📄](archives/n/netpbm/10.73.42/) |
| **nettle** | 3.10.2、3.10、4.0 | ✅ 已编译 |  |  | 3 | - | [📄](archives/n/nettle/4.0/) |
| **newrelic** | v0.0.0-20260603111055 | ✅ 已编译 |  | go | - | [] | [📄](archives/n/newrelic/v0.0.0-20260603111055/) |
| **nfdump** | 1.7.7 | ✅ 已编译 |  | Autotools | 4 | - | [📄](archives/n/nfdump/1.7.7/) |
| **nfpm** | 2.44.0 | ✅ 已发布 |  | go | - | - | [📄](archives/n/nfpm/2.44.0/) |
| **nghttp2** | 1.69.0 | ✅ 已编译 |  |  | 1 | - | [📄](archives/n/nghttp2/1.69.0/) |
| **nghttp3** | 1.15.0 | success |  | CMake | 1 | [] | [📄](archives/n/nghttp3/1.15.0/) |
| **nginx** | 1.26.2 | partial |  | Autotools | - | - | [📄](archives/n/nginx/1.26.2/) |
| **ngrep** | 1.49.0 | ✅ 已编译 |  | Autotools | - | "libc.so","libpcap","pcre2" | [📄](archives/n/ngrep/1.49.0/) |
| **ngspice** | 42 | unknown |  |  | 2 | - | [📄](archives/n/ngspice/42/) |
| **ngtcp2** | 1.22.1 | ✅ 已发布 |  |  | - | - | [📄](archives/n/ngtcp2/1.22.1/) |
| **nickle** | 2.108 | ✅ 已编译 |  | Meson | 4 | gmp 6.3.0,readline 8.2,ncurses | [📄](archives/n/nickle/2.108/) |
| **nikto** | 2.6.0 | ✅ 已编译 |  |  | - | - | [📄](archives/n/nikto/2.6.0/) |
| **nim** | 2.2.8 | success |  | custom | - | - | [📄](archives/n/nim/2.2.8/) |
| **ninja** | 1.12.1 | uploaded |  | Makefile | 0 | - | [📄](archives/n/ninja/1.12.1/) |
| **nkf** | 2.1.5 | ✅ 已发布 |  | Makefile | 1 | - | [📄](archives/n/nkf/2.1.5/) |
| **nload** | 0.7.4 | ✅ 已发布 |  | Autotools | 3 | - | [📄](archives/n/nload/0.7.4/) |
| **nlohmann-json** | 3.11.2 | uploaded |  | CMake | 0 | - | [📄](archives/n/nlohmann-json/3.11.2/) |
| **nlopt** | 2.10.1 | ✅ 已编译 |  |  | - | - | [📄](archives/n/nlopt/2.10.1/) |
| **nmap** | 7.95、7.97 | ✅ 已编译 |  | Autotools | 2 | - | [📄](archives/n/nmap/7.97/) |
| **nng** | 1.11 | ✅ 已发布 |  | CMake | - | - | [📄](archives/n/nng/1.11/) |
| **nnn** | 5.0 | partial |  | Makefile | - | name: ncursesw,name: readline,name: musl-fts | [📄](archives/n/nnn/5.0/) |
| **node_exporter** | 1.11.1 | ✅ 已编译 |  | go | - | - | [📄](archives/n/node_exporter/1.11.1/) |
| **nodeenv** | 1.10.0 | ✅ 已编译 |  |  | - | - | [📄](archives/n/nodeenv/1.10.0/) |
| **nodenv** | 1.6.2 | ✅ 已编译 |  |  | 1 | - | [📄](archives/n/nodenv/1.6.2/) |
| **nomacs** | 3.22.1 | ✅ 已编译 |  |  | 9 | - | [📄](archives/n/nomacs/3.22.1/) |
| **notcurses** | 3.0.17 | uploaded |  | unknown | 0 | ncursesw-6.4,libunistring,libdeflate | [📄](archives/n/notcurses/3.0.17/) |
| **notmuch** | 0.38.3 | ✅ 已编译 |  |  | - | - | [📄](archives/n/notmuch/0.38.3/) |
| **nox** | 2026.4.10 | ✅ 已编译 |  |  | - | argcomplete>=1.9.4,<4,attrs>=24.1,colorlog>=2.6.1,<7,dependency-groups>=1.1,humanize>=4... | [📄](archives/n/nox/2026.4.10/) |
| **npd6** | 1.1.0 | ✅ 已发布 |  |  | - | - | [📄](archives/n/npd6/1.1.0/) |
| **npm-check-updates** | 22.2.3 | ✅ 已发布 |  | npm | - | - | [📄](archives/n/npm-check-updates/22.2.3/) |
| **npth** | 1.8 | uploaded |  | Autotools | 0 | name: pthread | [📄](archives/n/npth/1.8/) |
| **nrg2iso** | 0.4.1 | ✅ 已发布 |  | Makefile | 1 | - | [📄](archives/n/nrg2iso/0.4.1/) |
| **nspr** | 4.37 | ✅ 已发布 |  |  | 1 | [] | [📄](archives/n/nspr/4.37/) |
| **nss** | 3.118.1、3.118.1-r0 | ✅ 已发布 |  | make | 3 | name: nspr,libnspr4.so (268KB),libnspr4.a (424KB),libplc4.so (35KB),libplc4.a (25KB)... | [📄](archives/n/nss/3.118.1-r0/) |
| **nsxiv** | 34 | ✅ 已编译 |  |  | 2 | - | [📄](archives/n/nsxiv/34/) |
| **ntfy** | 2.15.0-r5 | ✅ 已发布 |  | custom | - | [] | [📄](archives/n/ntfy/2.15.0-r5/) |
| **nuclei** | 3.8.0 | ✅ 已发布 |  | custom | - | - | [📄](archives/n/nuclei/3.8.0/) |
| **numactl** | 2.0.18 | partial |  | Autotools | - | - | [📄](archives/n/numactl/2.0.18/) |
| **nuttcp** | 8.2.2 | ✅ 已发布 |  |  | - | - | [📄](archives/n/nuttcp/8.2.2/) |
| **nxp-mfgtools** | 1.5.243 | ✅ 已编译 |  |  | - | - | [📄](archives/n/nxp-mfgtools/1.5.243/) |
| **nymphcast** | 0.2-alpha0 | ✅ 已编译 |  |  | 2 | - | [📄](archives/n/nymphcast/0.2-alpha0/) |
| **nymphrpc** | v0.1.1 | ✅ 已发布 |  |  | 1 | - | [📄](archives/n/nymphrpc/v0.1.1/) |
| **oath-toolkit** | 2.6.13-r0 | ✅ 已发布 |  |  | 9 | - | [📄](archives/o/oath-toolkit/2.6.13-r0/) |
| **objconv** | 2.57 | ✅ 已发布 |  |  | 0 | - | [📄](archives/o/objconv/2.57/) |
| **ocrmypdf** | 17.4.2 | ✅ 已编译 |  |  | - | - | [📄](archives/o/ocrmypdf/17.4.2/) |
| **octave** | 8.3.0 | ✅ 已编译 |  |  | 12 | - | [📄](archives/o/octave/8.3.0/) |
| **odbc-cpp-wrapper** | 1.6 | ✅ 已编译 |  | CMake | - | - | [📄](archives/o/odbc-cpp-wrapper/1.6/) |
| **ode** | 0.16.4 | ✅ 已发布 |  |  | - | - | [📄](archives/o/ode/0.16.4/) |
| **odt2txt** | 0.5 | ✅ 已发布 |  |  | - | - | [📄](archives/o/odt2txt/0.5/) |
| **oidn** | 2.5.0 | ✅ 已发布 |  | CMake | 2 | - | [📄](archives/o/oidn/2.5.0/) |
| **oksh** | 7.8 | ✅ 已发布 |  | Autotools | - | - | [📄](archives/o/oksh/7.8/) |
| **olm** | 3.2.16 | uploaded |  | unknown | 0 | - | [📄](archives/o/olm/3.2.16/) |
| **ompl** | 2.0.0 | ✅ 已编译 |  | CMake | - | boost >= 1.68,cmake >= 3.12,eigen >= 3.3 | [📄](archives/o/ompl/2.0.0/) |
| **onigmo** | 6.2.0 | ✅ 已编译 |  |  | 19 | - | [📄](archives/o/onigmo/6.2.0/) |
| **oniguruma** | 6.9.10 | ✅ 已发布 |  | CMake | 2 | - | [📄](archives/o/oniguruma/6.9.10/) |
| **opa** | 0.70.0 | ✅ 已发布 |  | custom | - | - | [📄](archives/o/opa/0.70.0/) |
| **open-adventure** | 1.20 | ✅ 已发布 |  | Makefile | 7 | - | [📄](archives/o/open-adventure/1.20/) |
| **open-mpi** | 5.0.10 | ✅ 已发布 |  |  | 2 | - | [📄](archives/o/open-mpi/5.0.10/) |
| **open-ocd** | 0.12.0 | ✅ 已编译 |  |  | 4 | - | [📄](archives/o/open-ocd/0.12.0/) |
| **open_jtalk** | 1.11 | ✅ 已发布 |  | Autotools | 3 | - | [📄](archives/o/open_jtalk/1.11/) |
| **openal-soft** | 1.24.3 | partial |  | Autotools | - | - | [📄](archives/o/openal-soft/1.24.3/) |
| **openapv** | 0.2.1.2 | ✅ 已发布 |  | CMake | - | - | [📄](archives/o/openapv/0.2.1.2/) |
| **openblas** | 0.3.33 | partial |  | Autotools | - | - | [📄](archives/o/openblas/0.3.33/) |
| **opencc** | 1.1.9 | ✅ 已编译 |  | CMake | - | [] | [📄](archives/o/opencc/1.1.9/) |
| **opencl-icd-loader** | v2024.05.08 | ✅ 已编译 |  |  | 1 | - | [📄](archives/o/opencl-icd-loader/v2024.05.08/) |
| **opencolorio** | 2.5.1 | ✅ 已编译 |  | CMake | - | pystring,yaml-cpp,minizip-ng,expat,zlib... | [📄](archives/o/opencolorio/2.5.1/) |
| **opencore-amr** | 0.1.6 | ✅ 已编译 |  | Autotools | 2 | - | [📄](archives/o/opencore-amr/0.1.6/) |
| **opencv** | 4.9.0 | ✅ 已编译 |  | CMake | 1 | - | [📄](archives/o/opencv/4.9.0/) |
| **openexr** | 2.2.1、3.1.5 | ✅ 已编译 |  | CMake | - | - | [📄](archives/o/openexr/3.1.5/) |
| **openfa** | 20231011.0.3 | ✅ 已发布 |  | CMake | - | - | [📄](archives/o/openfa/20231011.0.3/) |
| **openfortivpn** | 1.24.1 | ✅ 已发布 |  |  | 2 | - | [📄](archives/o/openfortivpn/1.24.1/) |
| **openfst** | 1.8.4 | ✅ 已发布 |  | Autotools | 3 | - | [📄](archives/o/openfst/1.8.4/) |
| **openh264** | 2.4.1 | ✅ 已编译 |  | Meson | 1 | meson >= 0.52,ninja,clang,pthread,libm | [📄](archives/o/openh264/2.4.1/) |
| **openimageio** | 3.1.13.1 | ✅ 已发布 |  |  | - | - | [📄](archives/o/openimageio/3.1.13.1/) |
| **openimageio-plugin-osl** | 1.15.4.0 | ✅ 已编译 |  |  | - | - | [📄](archives/o/openimageio-plugin-osl/1.15.4.0/) |
| **openjpeg** | 2.5.0 | uploaded |  | unknown | 0 | - | [📄](archives/o/openjpeg/2.5.0/) |
| **openldap** | 2.6.7 | ✅ 已发布 |  | Autotools | 3 | - | [📄](archives/o/openldap/2.6.7/) |
| **opensc** | 0.27.1 | partial |  | Autotools | 2 | - | [📄](archives/o/opensc/0.27.1/) |
| **openscap** | 1.4.3、1.4.3-r1 | ✅ 已编译 |  |  | 6 | - | [📄](archives/o/openscap/1.4.3-r1/) |
| **openscenegraph** | 3.6.5 | ✅ 已编译 |  |  | 3 | - | [📄](archives/o/openscenegraph/3.6.5/) |
| **opensmtpd-filter-dkimsign** | 0.6-r2 | ✅ 已编译 |  |  | - | - | [📄](archives/o/opensmtpd-filter-dkimsign/0.6-r2/) |
| **opensmtpd-filter-senderscore** | 0.1.2-r27 | ✅ 已编译 |  |  | - | - | [📄](archives/o/opensmtpd-filter-senderscore/0.1.2-r27/) |
| **opensmtpd-table-passwd** | 1.0.2-r0 | ✅ 已编译 |  |  | - | - | [📄](archives/o/opensmtpd-table-passwd/1.0.2-r0/) |
| **opensmtpd-table-redis** | 1.0.1-r0 | ✅ 已编译 |  |  | - | - | [📄](archives/o/opensmtpd-table-redis/1.0.1-r0/) |
| **opensmtpd-table-socketmap** | 1.1.1-r0 | ✅ 已编译 |  |  | - | - | [📄](archives/o/opensmtpd-table-socketmap/1.1.1-r0/) |
| **opensmtpd-table-sqlite** | 1.0.1-r0 | ✅ 已编译 |  |  | - | - | [📄](archives/o/opensmtpd-table-sqlite/1.0.1-r0/) |
| **openssh** | 10.0p1 | ✅ 已编译 |  | Autotools | 3 | openssl 1.1.1w (local build) | [📄](archives/o/openssh/10.0p1/) |
| **openssl** | 1.1.1w、3.5.6 | partial | 🟢 高 | openssl-perl | 0 | - | [📄](archives/o/openssl/3.5.6/) |
| **opensubdiv** | 3.7.0 | ✅ 已发布 |  |  | - | - | [📄](archives/o/opensubdiv/3.7.0/) |
| **openttd-opengfx** | 8.0 | ✅ 已发布 |  | custom | - | - | [📄](archives/o/openttd-opengfx/8.0/) |
| **openxr** | 1.1.60 | ✅ 已编译 |  |  | 2 | - | [📄](archives/o/openxr/1.1.60/) |
| **operator-sdk** | 1.39.2 | ✅ 已编译 |  |  | - | - | [📄](archives/o/operator-sdk/1.39.2/) |
| **optipng** | 7.9.1 | uploaded |  | unknown | 0 | - | [📄](archives/o/optipng/7.9.1/) |
| **opus** | 1.4 | ✅ 已发布 |  | Meson | 1 | - | [📄](archives/o/opus/1.4/) |
| **opus-tools** | 0.2 | ✅ 已发布 |  | Autotools | 6 | - | [📄](archives/o/opus-tools/0.2/) |
| **opusfile** | 0.12 | ✅ 已编译 |  | Autotools | 1 | - | [📄](archives/o/opusfile/0.12/) |
| **ortp** | 5.2.0 | ✅ 已发布 |  |  | 1 | - | [📄](archives/o/ortp/5.2.0/) |
| **osinfo-db** | 20250124 | ✅ 已发布 |  | Script | - | - | [📄](archives/o/osinfo-db/20250124/) |
| **osmfilter** | 0.9 | ✅ 已编译 |  | Autotools | - | - | [📄](archives/o/osmfilter/0.9/) |
| **osslsigncode** | 2.13 | uploaded |  | unknown | 0 | - | [📄](archives/o/osslsigncode/2.13/) |
| **ostree** | 2026.1 | ✅ 已编译 |  | Autotools | 2 | - | [📄](archives/o/ostree/2026.1/) |
| **otel-cli** | 0.4.5 | ✅ 已发布 |  | go | - | - | [📄](archives/o/otel-cli/0.4.5/) |
| **otf2bdf** | 3.1 | ✅ 已发布 |  |  | 4 | - | [📄](archives/o/otf2bdf/3.1/) |
| **oxipng** | v10.1.1 | ✅ 已编译 |  |  | - | - | [📄](archives/o/oxipng/v10.1.1/) |
| **p11-kit** | 0.25.5 | uploaded |  | Autotools | 0 | - | [📄](archives/p/p11-kit/0.25.5/) |
| **p7zip** | 17.05 | uploaded |  | unknown | 0 | - | [📄](archives/p/p7zip/17.05/) |
| **p8-platform** | 2.1.0 | ✅ 已编译 |  |  | - | - | [📄](archives/p/p8-platform/2.1.0/) |
| **pacman** | 7.1 | ✅ 已发布 |  | Meson | - | - | [📄](archives/p/pacman/7.1/) |
| **pacparser** | 1.5.0 | ✅ 已编译 |  | Makefile | 3 | - | [📄](archives/p/pacparser/1.5.0/) |
| **pacvim** | 1.1.1 | ✅ 已编译 |  |  | 3 | - | [📄](archives/p/pacvim/1.1.1/) |
| **paho-mqtt-c** | 1.3.13 | partial |  | CMake | - | openssl (1.1.1w, 预编译包已安装) | [📄](archives/p/paho-mqtt-c/1.3.13/) |
| **pamixer** | 1.6 | ✅ 已编译 |  | Makefile | - | - | [📄](archives/p/pamixer/1.6/) |
| **pango** | 1.50.14 | ✅ 已发布 |  | Meson | 1 | - | [📄](archives/p/pango/1.50.14/) |
| **paperkey** | 1.6 | ✅ 已发布 |  | Autotools | 1 | - | [📄](archives/p/paperkey/1.6/) |
| **papilo** | 3.0.0 | ✅ 已编译 |  |  | - | - | [📄](archives/p/papilo/3.0.0/) |
| **par** | 1.53.0 | ✅ 已发布 |  | Makefile | - | - | [📄](archives/p/par/1.53.0/) |
| **parallel** | 20260522 | ✅ 已编译 |  |  | 1 | - | [📄](archives/p/parallel/20260522/) |
| **pari** | 2.17.3 | ✅ 已编译 |  |  | - | - | [📄](archives/p/pari/2.17.3/) |
| **parole** | 4.20.0 | ❌ 编译失败 |  | Meson | - | - | [📄](archives/p/parole/4.20.0/) |
| **partclone-utils** | 0.4.3 | ✅ 已编译 |  | Autotools | 3 | - | [📄](archives/p/partclone-utils/0.4.3/) |
| **partimage** | 0.6.9 | ✅ 已发布 |  | Autotools | 46 | - | [📄](archives/p/partimage/0.6.9/) |
| **pass** | 1.7.4 | ✅ 已编译 |  | shell | - | - | [📄](archives/p/pass/1.7.4/) |
| **pass-otp** | 1.2.0 | ✅ 已编译 |  |  | - | - | [📄](archives/p/pass-otp/1.2.0/) |
| **patch** | 2.7.6 | verified |  | Autotools | 0 | - | [📄](archives/p/patch/2.7.6/) |
| **patchelf** | 0.18.0 | ✅ 已发布 |  | Autotools | 4 | - | [📄](archives/p/patchelf/0.18.0/) |
| **patchutils** | 0.4.4、0.4.5 | ✅ 已发布 |  |  | 3 | - | [📄](archives/p/patchutils/0.4.5/) |
| **pavucontrol** | 6.2 | ❌ 编译失败 |  | Meson | - | - | [📄](archives/p/pavucontrol/6.2/) |
| **pavucontrol-qt** | 2.4.0 | ✅ 已编译 |  | CMake | - | - | [📄](archives/p/pavucontrol-qt/2.4.0/) |
| **pax** | 20240817 | uploaded |  | unknown | 0 | - | [📄](archives/p/pax/20240817/) |
| **pbzip2** | 1.1.13 | uploaded |  | Makefile | 0 | bzip2 | [📄](archives/p/pbzip2/1.1.13/) |
| **pcapmirror** | 0.6.1 | ✅ 已编译 |  | Makefile | - | - | [📄](archives/p/pcapmirror/0.6.1/) |
| **pcaudiolib** | 1.3 | ✅ 已编译 |  | Autotools | 1 | - | [📄](archives/p/pcaudiolib/1.3/) |
| **pciutils** | 3.13.0 | uploaded |  | Makefile | 0 | - | [📄](archives/p/pciutils/3.13.0/) |
| **pcre** | 8.45 | uploaded |  | Autotools | 0 | - | [📄](archives/p/pcre/8.45/) |
| **pcre2** | 10.40、10.45 | ✅ 已发布 |  | Autotools | 3 | - | [📄](archives/p/pcre2/10.45/) |
| **pcsc-lite** | 2.4.0 | ✅ 已发布 |  | Meson | 1 | libusb-1.0 >= 1.0.27 | [📄](archives/p/pcsc-lite/2.4.0/) |
| **pdf-diff** | 0.9.3 | ✅ 已编译 |  | custom | 1 | - | [📄](archives/p/pdf-diff/0.9.3/) |
| **pdf2image** | 1.17.0 | ✅ 已编译 |  |  | - | - | [📄](archives/p/pdf2image/1.17.0/) |
| **pdf2json** | 0.71 | ✅ 已发布 |  | Autotools | 3 | - | [📄](archives/p/pdf2json/0.71/) |
| **pdf4qt** | 1.5.3.1 | ✅ 已编译 |  | CMake | - | - | [📄](archives/p/pdf4qt/1.5.3.1/) |
| **pdfalyzer** | 1.19.6 | ✅ 已发布 |  |  | - | - | [📄](archives/p/pdfalyzer/1.19.6/) |
| **pdfarranger** | 1.14.0 | ✅ 已编译 |  | custom | - | - | [📄](archives/p/pdfarranger/1.14.0/) |
| **pdfcpu** | 0.12.1 | ✅ 已编译 |  | go | 1 | [] | [📄](archives/p/pdfcpu/0.12.1/) |
| **pdfcrack** | 0.21 | ✅ 已编译 |  | Makefile | 2 | - | [📄](archives/p/pdfcrack/0.21/) |
| **pdfgrep** | 2.2.0 | ✅ 已编译 |  | Autotools | 3 | - | [📄](archives/p/pdfgrep/2.2.0/) |
| **pdfjs** | 6.0.227 | ✅ 已编译 |  | custom | - | - | [📄](archives/p/pdfjs/6.0.227/) |
| **pdfly** | 0.5.1 | ✅ 已编译 |  | python | - | - | [📄](archives/p/pdfly/0.5.1/) |
| **pdfpc** | 4.7.0 | ✅ 已编译 |  | CMake | - | - | [📄](archives/p/pdfpc/4.7.0/) |
| **pdfposter** | 0.9.1 | ✅ 已编译 |  | custom | 2 | - | [📄](archives/p/pdfposter/0.9.1/) |
| **pdfsandwich** | 0.1.7 | ✅ 已编译 |  | Autotools | 1 | - | [📄](archives/p/pdfsandwich/0.1.7/) |
| **peek** | 1.5.1 | ✅ 已编译 |  |  | 1 | - | [📄](archives/p/peek/1.5.1/) |
| **pegtl** | 4.0.0 | ✅ 已编译 |  |  | - | - | [📄](archives/p/pegtl/4.0.0/) |
| **perf** | 6.6.9 | ✅ 已编译 |  |  | - | - | [📄](archives/p/perf/6.6.9/) |
| **perl** | 5.42.2 | uploaded |  | Autotools | 0 | - | [📄](archives/p/perl/5.42.2/) |
| **perl-crypt-cast5** | 0.05-r14 | ✅ 已编译 |  | perl | - | - | [📄](archives/p/perl-crypt-cast5/0.05-r14/) |
| **perl-crypt-openssl-dsa** | 0.20 | ✅ 已发布 |  | custom | - | - | [📄](archives/p/perl-crypt-openssl-dsa/0.20/) |
| **perl-dbd-pg** | 3.18.0 | ✅ 已编译 |  |  | 1 | - | [📄](archives/p/perl-dbd-pg/3.18.0/) |
| **perl-dbd-sqlite** | 1.78 | ✅ 已编译 |  |  | 1 | - | [📄](archives/p/perl-dbd-sqlite/1.78/) |
| **perl-dbi** | 1.637 | ✅ 已编译 |  |  | - | - | [📄](archives/p/perl-dbi/1.637/) |
| **perl-devel-lexalias** | 0.05 | ✅ 已编译 |  |  | 1 | - | [📄](archives/p/perl-devel-lexalias/0.05/) |
| **perl-digest-md5** | 2.59 | ✅ 已发布 |  |  | - | - | [📄](archives/p/perl-digest-md5/2.59/) |
| **perl-digest-sha1** | 2.13 | ✅ 已编译 |  | Autotools | 1 | - | [📄](archives/p/perl-digest-sha1/2.13/) |
| **perl-digest-sha3** | 1.01 | ✅ 已编译 |  | perl_xs | - | - | [📄](archives/p/perl-digest-sha3/1.01/) |
| **perl-encode-hanextra** | 0.23 | ✅ 已编译 |  | Makefile | - | - | [📄](archives/p/perl-encode-hanextra/0.23/) |
| **perl-encode-jis2k** | 0.05-r2 | ✅ 已编译 |  | perl_xs | - | - | [📄](archives/p/perl-encode-jis2k/0.05-r2/) |
| **perl-ev** | 4.35 | ✅ 已编译 |  |  | 1 | - | [📄](archives/p/perl-ev/4.35/) |
| **perl-extutils-cchecker** | 0.12 | ✅ 已发布 |  | perl-build | - | - | [📄](archives/p/perl-extutils-cchecker/0.12/) |
| **perl-html-parser** | 3.83-r1 | ✅ 已编译 |  |  | - | - | [📄](archives/p/perl-html-parser/3.83-r1/) |
| **perl-http-parser-xs** | 0.17-r9 | ✅ 已编译 |  | perl | - | - | [📄](archives/p/perl-http-parser-xs/0.17-r9/) |
| **perl-io-html** | 1.004 | ✅ 已发布 |  | perl | - | - | [📄](archives/p/perl-io-html/1.004/) |
| **perl-io-multiplex** | 1.16 | ✅ 已编译 |  | perl | - | - | [📄](archives/p/perl-io-multiplex/1.16/) |
| **perl-io-prompt-tiny** | 0.003 | ✅ 已发布 |  | perl | - | - | [📄](archives/p/perl-io-prompt-tiny/0.003/) |
| **perl-io-prompter** | 0.005004-r0 | ✅ 已编译 |  | perl | - | - | [📄](archives/p/perl-io-prompter/0.005004-r0/) |
| **perl-io-socket-inet6** | 2.73-r2 | ✅ 已发布 |  |  | 1 | - | [📄](archives/p/perl-io-socket-inet6/2.73-r2/) |
| **perl-io-socket-timeout** | 0.32-r2 | ✅ 已编译 |  | perl | - | - | [📄](archives/p/perl-io-socket-timeout/0.32-r2/) |
| **perl-io-string** | 1.08 | ✅ 已发布 |  |  | - | - | [📄](archives/p/perl-io-string/1.08/) |
| **perl-io-tee** | 0.66 | ✅ 已发布 |  |  | - | - | [📄](archives/p/perl-io-tee/0.66/) |
| **perl-io-tty** | 1.20-r2 | ✅ 已发布 |  |  | 1 | - | [📄](archives/p/perl-io-tty/1.20-r2/) |
| **perl-ipc-run** | 20260402.0 | ✅ 已编译 |  |  | - | - | [📄](archives/p/perl-ipc-run/20260402.0/) |
| **perl-ipc-run3** | 0.049-r1 | ✅ 已发布 |  |  | - | - | [📄](archives/p/perl-ipc-run3/0.049-r1/) |
| **perl-ipc-sharelite** | 0.17-r14 | ✅ 已编译 |  |  | 1 | - | [📄](archives/p/perl-ipc-sharelite/0.17-r14/) |
| **perl-ipc-signal** | 1.00 | ✅ 已编译 |  |  | - | - | [📄](archives/p/perl-ipc-signal/1.00/) |
| **perl-iptables-chainmgr** | 1.6 | ✅ 已发布 |  |  | - | - | [📄](archives/p/perl-iptables-chainmgr/1.6/) |
| **perl-iptables-parse** | 1.6.1-r4 | ✅ 已发布 |  |  | - | - | [📄](archives/p/perl-iptables-parse/1.6.1-r4/) |
| **perl-json** | 4.10 | ✅ 已发布 |  |  | - | - | [📄](archives/p/perl-json/4.10/) |
| **perl-json-any** | 1.40-r0 | ✅ 已发布 |  | perl | - | - | [📄](archives/p/perl-json-any/1.40-r0/) |
| **perl-json-maybexs** | 1.004008-r0 | ✅ 已发布 |  | perl-extutils-makemaker | - | - | [📄](archives/p/perl-json-maybexs/1.004008-r0/) |
| **perl-json-path** | 1.0.6-r0 | ✅ 已编译 |  | perl-extutils-makemaker | - | - | [📄](archives/p/perl-json-path/1.0.6-r0/) |
| **perl-json-webtoken** | 0.10-r5 | ✅ 已发布 |  | perl | 1 | - | [📄](archives/p/perl-json-webtoken/0.10-r5/) |
| **perl-json-xs** | 4.04 | ✅ 已编译 |  | perl | - | - | [📄](archives/p/perl-json-xs/4.04/) |
| **perl-ldap** | 0.68-r2 | ✅ 已发布 |  |  | - | - | [📄](archives/p/perl-ldap/0.68-r2/) |
| **perl-libwww** | 6.81-r0 | ✅ 已发布 |  |  | - | - | [📄](archives/p/perl-libwww/6.81-r0/) |
| **perl-libxml-perl** | 0.08 | ✅ 已发布 |  |  | - | - | [📄](archives/p/perl-libxml-perl/0.08/) |
| **perl-lingua-en-inflect** | 1.905-r1 | ✅ 已发布 |  |  | - | - | [📄](archives/p/perl-lingua-en-inflect/1.905-r1/) |
| **perl-lingua-en-numbers-ordinate** | 1.05-r2 | ✅ 已发布 |  |  | - | - | [📄](archives/p/perl-lingua-en-numbers-ordinate/1.05-r2/) |
| **perl-lingua-preferred** | 0.2.4-r5 | ✅ 已发布 |  |  | - | - | [📄](archives/p/perl-lingua-preferred/0.2.4-r5/) |
| **perl-lingua-translit** | 0.29-r1 | ✅ 已发布 |  | perl | 1 | - | [📄](archives/p/perl-lingua-translit/0.29-r1/) |
| **perl-list-allutils** | 0.19 | ✅ 已发布 |  | perl | - | List::SomeUtils >= 0.58,List::Util >= 1.56,List::UtilsBy >= 0.11 | [📄](archives/p/perl-list-allutils/0.19/) |
| **perl-list-compare** | 0.55 | ✅ 已发布 |  | perl | - | - | [📄](archives/p/perl-list-compare/0.55/) |
| **perl-list-moreutils** | 0.430-r1 | ✅ 已编译 |  |  | - | - | [📄](archives/p/perl-list-moreutils/0.430-r1/) |
| **perl-list-moreutils-xs** | 0.430-r6 | ✅ 已编译 |  |  | 1 | - | [📄](archives/p/perl-list-moreutils-xs/0.430-r6/) |
| **perl-list-someutils** | 0.59-r1 | ✅ 已编译 |  | perl | - | - | [📄](archives/p/perl-list-someutils/0.59-r1/) |
| **perl-list-utilsby** | 0.12 | ✅ 已发布 |  | perl | - | - | [📄](archives/p/perl-list-utilsby/0.12/) |
| **perl-local-lib** | 2.000029-r0 | ✅ 已编译 |  |  | - | - | [📄](archives/p/perl-local-lib/2.000029-r0/) |
| **perl-locale-codes** | 3.85-r0 | ✅ 已发布 |  | perl_makemaker | - | - | [📄](archives/p/perl-locale-codes/3.85-r0/) |
| **perl-locale-gettext** | 1.07-r2 | ✅ 已编译 |  |  | 1 | - | [📄](archives/p/perl-locale-gettext/1.07-r2/) |
| **perl-locale-maketext-fuzzy** | 0.11-r5 | ✅ 已编译 |  | perl | - | - | [📄](archives/p/perl-locale-maketext-fuzzy/0.11-r5/) |
| **perl-locale-maketext-lexicon** | 1.00-r6 | ✅ 已发布 |  |  | - | - | [📄](archives/p/perl-locale-maketext-lexicon/1.00-r6/) |
| **perl-locale-msgfmt** | 0.15-r2 | ✅ 已编译 |  |  | - | - | [📄](archives/p/perl-locale-msgfmt/0.15-r2/) |
| **perl-log-any** | 1.718-r0 | ✅ 已发布 |  | perl | - | - | [📄](archives/p/perl-log-any/1.718-r0/) |
| **perl-log-any-adapter-screen** | 0.141 | ✅ 已发布 |  |  | - | - | [📄](archives/p/perl-log-any-adapter-screen/0.141/) |
| **perl-log-any-adapter-tap** | 0.003003-r0 | ✅ 已发布 |  |  | - | - | [📄](archives/p/perl-log-any-adapter-tap/0.003003-r0/) |
| **perl-log-dispatch** | 2.71 | published   |  | perl_makefile | - | perl-Carp,perl-Devel-GlobalDestruction,perl-Dist-CheckConflicts (>= 0.02),perl-Encode,perl-Module-Runtime... | [📄](archives/p/perl-log-dispatch/2.71/) |
| **perl-log-dispatch-config** | 1.04-r5 | published   |  | perl_makefile | - | perl-Log-Dispatch (>= 2.00),perl-AppConfig (optional) | [📄](archives/p/perl-log-dispatch-config/1.04-r5/) |
| **perl-log-dispatch-configurator-any** | 1.122640-r4 | published   |  | perl_makefile | - | perl-Carp,perl-Config-Any (>= 0.15),perl-Log-Dispatch (>= 2.23),perl-Log-Dispatch-Configurator,perl-Sys-Syslog (>= 0.25)... | [📄](archives/p/perl-log-dispatch-configurator-any/1.122640-r4/) |
| **perl-lv** | 0.006 | ✅ 已编译 |  |  | - | - | [📄](archives/p/perl-lv/0.006/) |
| **perl-lwp-online** | 1.08-r0 | ✅ 已发布 |  | perl | - | - | [📄](archives/p/perl-lwp-online/1.08-r0/) |
| **perl-lwp-useragent-determined** | 1.07-r4 | ✅ 已发布 |  |  | - | - | [📄](archives/p/perl-lwp-useragent-determined/1.07-r4/) |
| **perl-mail-authenticationresults** | 2.20250709-r0 | ✅ 已发布 |  | Perl-Makefile.PL | - | Test::Exception 0.43,Sub::Uplevel 0.2800 | [📄](archives/p/perl-mail-authenticationresults/2.20250709-r0/) |
| **perl-mail-dkim** | 1.20240923 | published   |  | perl_makefile | - | perl (>= 5.008),Crypt::OpenSSL::RSA 0.33 (签名功能必需，已编译XS模块),Crypt::OpenSSL::Random 0.11 (RSA依赖，已编译XS模块),Crypt::OpenSSL::Guess 0.15 (配置依赖，已编译可加载),Crypt::PK::Ed25519 (ed25519 签名，可选)... | [📄](archives/p/perl-mail-dkim/1.20240923/) |
| **perl-mail-domainkeys** | 1.0 | ✅ 已编译 |  |  | - | - | [📄](archives/p/perl-mail-domainkeys/1.0/) |
| **perl-mail-imapclient** | 3.43 | ✅ 已发布 |  | perl | - | perl-io-socket-ip,perl-authen-ntlm,perl-authen-sasl,perl-digest-hmac,perl-io-socket-ssl | [📄](archives/p/perl-mail-imapclient/3.43/) |
| **perl-mail-sendmail** | 0.82 | ✅ 已发布 |  | perl_makefile | 1 | perl (>= 5.008),Socket (core),Time::Local (core),Sys::Hostname (core),Sys::Hostname::Long... | [📄](archives/p/perl-mail-sendmail/0.82/) |
| **perl-mail-spamassassin** | 4.0.2 | ✅ 已发布 |  | perl-makefile | 13 | - | [📄](archives/p/perl-mail-spamassassin/4.0.2/) |
| **perl-mail-spf** | 3.20250505 | published   |  | perl_makefile | - | perl (>= 5.10),perl-net-dns,perl-uri,perl,clang | [📄](archives/p/perl-mail-spf/3.20250505/) |
| **perl-mailtools** | 2.22 | ✅ 已发布 |  | perl-module | 1 | perl,perl-net-domain,perl-io-handle | [📄](archives/p/perl-mailtools/2.22/) |
| **perl-match-simple** | 0.012 | ✅ 已编译 |  | perl-makefile | - | Exporter::Tiny >= 0.026 (已安装),List::Util >= 1.33 (Perl 内置),Scalar::Util (Perl 内置),Sub::Infix >= 0.004 (已安装 v0.004),ExtUtils::MakeMaker >= 6.17... | [📄](archives/p/perl-match-simple/0.012/) |
| **perl-match-simple-xs** | 0.002 | ✅ 已编译 |  | perl_xs | - | - | [📄](archives/p/perl-match-simple-xs/0.002/) |
| **perl-math-basecnv** | 1.14 | ✅ 已发布 |  | perl | - | - | [📄](archives/p/perl-math-basecnv/1.14/) |
| **perl-math-pari** | 2.030528-r1 | ✅ 已编译 |  |  | - | perl >= 5.42.0,pari >= 2.3.5 (embedded),clang >= 18.1.8,make | [📄](archives/p/perl-math-pari/2.030528-r1/) |
| **perl-math-random-isaac** | 1.004-r0 | ✅ 已发布 |  | perl | - | perl >= 5.006 | [📄](archives/p/perl-math-random-isaac/1.004-r0/) |
| **perl-math-random-mt-auto** | 6.23-r10 | ✅ 已发布 |  |  | 1 | - | [📄](archives/p/perl-math-random-mt-auto/6.23-r10/) |
| **perl-math-round** | 0.08-r1 | ✅ 已发布 |  | perl | - | - | [📄](archives/p/perl-math-round/0.08-r1/) |
| **perl-meta** | 0.015-r0 | ✅ 已发布 |  | module-build | 1 | - | [📄](archives/p/perl-meta/0.015-r0/) |
| **perl-metacpan-client** | 2.033000 | ✅ 已编译 |  |  | - | - | [📄](archives/p/perl-metacpan-client/2.033000/) |
| **perl-metrics-any** | 0.10-r1 | ✅ 已发布 |  |  | - | - | [📄](archives/p/perl-metrics-any/0.10-r1/) |
| **perl-mime-base32** | 1.303 | ✅ 已编译 |  |  | - | - | [📄](archives/p/perl-mime-base32/1.303/) |
| **perl-mime-base64** | 3.16 | ✅ 已发布 |  | perl-xs | - | - | [📄](archives/p/perl-mime-base64/3.16/) |
| **perl-mime-charset** | 1.013.1 | ✅ 已发布 |  | perl | - | - | [📄](archives/p/perl-mime-charset/1.013.1/) |
| **perl-mime-construct** | 1.11 | ✅ 已编译 |  | perl-module | - | - | [📄](archives/p/perl-mime-construct/1.11/) |
| **perl-mime-lite** | 3.033 | ✅ 已编译 |  | perl | - | - | [📄](archives/p/perl-mime-lite/3.033/) |
| **perl-mime-tools** | 5.515 | ✅ 已编译 |  | perl | - | - | [📄](archives/p/perl-mime-tools/5.515/) |
| **perl-mime-types** | 2.29 | ✅ 已发布 |  | perl | - | - | [📄](archives/p/perl-mime-types/2.29/) |
| **perl-mixin-event-dispatch** | 2.000 | ✅ 已发布 |  | perl | - | - | [📄](archives/p/perl-mixin-event-dispatch/2.000/) |
| **perl-mixin-linewise** | 0.111 | ✅ 已编译 |  | perl | - | - | [📄](archives/p/perl-mixin-linewise/0.111/) |
| **perl-module-build** | 0.4234 | ✅ 已编译 |  | perl-module-build | - | - | [📄](archives/p/perl-module-build/0.4234/) |
| **perl-module-build-tiny** | 0.052 | ✅ 已编译 |  |  | - | - | [📄](archives/p/perl-module-build-tiny/0.052/) |
| **perl-module-build-using-pkgconfig** | 0.03 | ✅ 已发布 |  | module-build | - | - | [📄](archives/p/perl-module-build-using-pkgconfig/0.03/) |
| **perl-module-build-xsutil** | 0.19 | ✅ 已发布 |  | perl-modulebuild | 1 | - | [📄](archives/p/perl-module-build-xsutil/0.19/) |
| **perl-module-cpanfile** | 1.1004 | ✅ 已发布 |  | perl-makemaker | - | - | [📄](archives/p/perl-module-cpanfile/1.1004/) |
| **perl-module-cpmfile** | 0.006 | ✅ 已发布 |  | perl-build-tiny | - | - | [📄](archives/p/perl-module-cpmfile/0.006/) |
| **perl-module-find** | 0.17 | ✅ 已发布 |  | perl | - | - | [📄](archives/p/perl-module-find/0.17/) |
| **perl-module-implementation** | 0.09 | ✅ 已发布 |  |  | - | - | [📄](archives/p/perl-module-implementation/0.09/) |
| **perl-module-install** | 1.21 | ✅ 已发布 |  | perl | - | - | [📄](archives/p/perl-module-install/1.21/) |
| **perl-module-install-authorrequires** | 0.02 | ✅ 已发布 |  | perl | - | - | [📄](archives/p/perl-module-install-authorrequires/0.02/) |
| **perl-module-install-authortests** | 0.002 | ✅ 已发布 |  | perl | - | - | [📄](archives/p/perl-module-install-authortests/0.002/) |
| **perl-module-loader** | 0.04 | ✅ 已发布 |  | perl-makemaker | - | - | [📄](archives/p/perl-module-loader/0.04/) |
| **perl-module-metadata** | 1.000038 | ✅ 已发布 |  | Custom Perl | - | - | [📄](archives/p/perl-module-metadata/1.000038/) |
| **perl-module-pluggable** | 6.3 | ✅ 已发布 |  |  | - | - | [📄](archives/p/perl-module-pluggable/6.3/) |
| **perl-module-refresh** | 0.18 | ✅ 已发布 |  | perl | - | - | [📄](archives/p/perl-module-refresh/0.18/) |
| **perl-module-runtime** | 0.018 | ✅ 已发布 |  | Makefile | - | - | [📄](archives/p/perl-module-runtime/0.018/) |
| **perl-module-runtime-conflicts** | 0.003 | ✅ 已发布 |  | perl | - | - | [📄](archives/p/perl-module-runtime-conflicts/0.003/) |
| **perl-module-scandeps** | 1.37 | ✅ 已发布 |  | perl | - | - | [📄](archives/p/perl-module-scandeps/1.37/) |
| **perl-module-versions-report** | 1.06 | ✅ 已发布 |  | perl-makefile-pl | - | - | [📄](archives/p/perl-module-versions-report/1.06/) |
| **perl-mojo-pg** | 4.28 | ✅ 已发布 |  | perl-makemaker | - | - | [📄](archives/p/perl-mojo-pg/4.28/) |
| **perl-mojolicious** | 9.42 | ✅ 已发布 |  | Makefile | 3 | - | [📄](archives/p/perl-mojolicious/9.42/) |
| **perl-mojolicious-plugin-i18n** | 1.6 | ✅ 已发布 |  |  | - | - | [📄](archives/p/perl-mojolicious-plugin-i18n/1.6/) |
| **perl-moo** | 2.005005 | ✅ 已发布 |  |  | - | - | [📄](archives/p/perl-moo/2.005005/) |
| **perl-moose** | 2.4000 | ✅ 已编译 |  | perl_makefile | 3 | - | [📄](archives/p/perl-moose/2.4000/) |
| **perl-moosex** | 0.002 | ✅ 已发布 |  | perl | - | - | [📄](archives/p/perl-moosex/0.002/) |
| **perl-moosex-test-role** | 0.08 | ✅ 已发布 |  |  | - | - | [📄](archives/p/perl-moosex-test-role/0.08/) |
| **perl-moosex-types** | 0.51 | ✅ 已发布 |  | perl | - | - | [📄](archives/p/perl-moosex-types/0.51/) |
| **perl-moosex-types-common** | 0.001015 | ✅ 已编译 |  | perl | - | - | [📄](archives/p/perl-moosex-types-common/0.001015/) |
| **perl-moosex-types-datetime** | 0.13 | ✅ 已编译 |  |  | - | - | [📄](archives/p/perl-moosex-types-datetime/0.13/) |
| **perl-moosex-types-path-class** | 0.09 | ✅ 已发布 |  | perl | - | - | [📄](archives/p/perl-moosex-types-path-class/0.09/) |
| **perl-moosex-types-uri** | 0.10 | ✅ 已发布 |  | perl | - | - | [📄](archives/p/perl-moosex-types-uri/0.10/) |
| **perl-moox-types-mooselike** | 0.29-r4 | ✅ 已发布 |  | perl | - | - | [📄](archives/p/perl-moox-types-mooselike/0.29-r4/) |
| **perl-moox-types-mooselike-numeric** | 1.03-r2 | ✅ 已发布 |  | perl | - | - | [📄](archives/p/perl-moox-types-mooselike-numeric/1.03-r2/) |
| **perl-mouse** | 2.6.0-r0 | ✅ 已编译 |  |  | - | - | [📄](archives/p/perl-mouse/2.6.0-r0/) |
| **perl-mozilla-ca** | 20250602-r0 | ✅ 已发布 |  | perl-makefile-pl | - | - | [📄](archives/p/perl-mozilla-ca/20250602-r0/) |
| **perl-mro-compat** | 0.15-r2 | ✅ 已发布 |  | perl-extutils | - | - | [📄](archives/p/perl-mro-compat/0.15-r2/) |
| **perl-namespace-autoclean** | 0.31 | ✅ 已发布 |  | Makefile | - | - | [📄](archives/p/perl-namespace-autoclean/0.31/) |
| **perl-namespace-clean** | 0.27-r4 | ✅ 已发布 |  | perl | - | - | [📄](archives/p/perl-namespace-clean/0.27-r4/) |
| **perl-net-appliance-session** | 4.300005-r5 | ✅ 已发布 |  |  | - | - | [📄](archives/p/perl-net-appliance-session/4.300005-r5/) |
| **perl-net-async-http** | 0.50-r0 | ✅ 已发布 |  | perl | - | - | [📄](archives/p/perl-net-async-http/0.50-r0/) |
| **perl-net-async-http-server** | 0.15-r0 | ✅ 已发布 |  | perl | - | - | [📄](archives/p/perl-net-async-http-server/0.15-r0/) |
| **perl-net-async-irc** | 0.12-r0 | ✅ 已发布 |  |  | - | - | [📄](archives/p/perl-net-async-irc/0.12-r0/) |
| **perl-net-async-xmpp** | 0.003-r0 | ✅ 已编译 |  |  | - | - | [📄](archives/p/perl-net-async-xmpp/0.003-r0/) |
| **perl-net-cidr** | 0.27-r0 | ✅ 已发布 |  |  | - | - | [📄](archives/p/perl-net-cidr/0.27-r0/) |
| **perl-net-cidr-lite** | 0.23-r0 | ✅ 已编译 |  |  | - | - | [📄](archives/p/perl-net-cidr-lite/0.23-r0/) |
| **perl-net-dns** | 1.53-r0 | ✅ 已发布 |  |  | - | - | [📄](archives/p/perl-net-dns/1.53-r0/) |
| **perl-net-dns-resolver-mock** | 1.20230216-r1 | ✅ 已编译 |  |  | - | - | [📄](archives/p/perl-net-dns-resolver-mock/1.20230216-r1/) |
| **perl-net-dns-resolver-programmable** | 0.009-r4 | ✅ 已发布 |  |  | - | - | [📄](archives/p/perl-net-dns-resolver-programmable/0.009-r4/) |
| **perl-net-dns-sec** | 1.26-r1 | ✅ 已编译 |  |  | - | - | [📄](archives/p/perl-net-dns-sec/1.26-r1/) |
| **perl-net-domain-tld** | 1.75-r0 | ✅ 已发布 |  | Makefile | - | - | [📄](archives/p/perl-net-domain-tld/1.75-r0/) |
| **perl-net-http** | 6.24-r0 | ✅ 已编译 |  |  | - | - | [📄](archives/p/perl-net-http/6.24-r0/) |
| **perl-net-ip** | 1.26-r7 | ✅ 已发布 |  | Makefile | - | - | [📄](archives/p/perl-net-ip/1.26-r7/) |
| **perl-net-iptrie** | 0.7-r5 | ✅ 已编译 |  |  | 2 | - | [📄](archives/p/perl-net-iptrie/0.7-r5/) |
| **perl-net-ipv4addr** | 0.10-r7 | ✅ 已编译 |  |  | - | - | [📄](archives/p/perl-net-ipv4addr/0.10-r7/) |
| **perl-net-jabber** | 2.0-r0 | ✅ 已发布 |  | Makefile | - | - | [📄](archives/p/perl-net-jabber/2.0-r0/) |
| **perl-net-jabber-bot** | 2.1.7-r0 | ✅ 已发布 |  |  | - | - | [📄](archives/p/perl-net-jabber-bot/2.1.7-r0/) |
| **perl-net-libidn** | 0.12-r17 | ✅ 已发布 |  |  | 1 | - | [📄](archives/p/perl-net-libidn/0.12-r17/) |
| **perl-net-libresolv** | 0.03-r2 | ✅ 已编译 |  |  | 2 | - | [📄](archives/p/perl-net-libresolv/0.03-r2/) |
| **perl-net-mpd** | 0.07-r3 | ✅ 已发布 |  |  | - | - | [📄](archives/p/perl-net-mpd/0.07-r3/) |
| **perl-net-mqtt** | 1.163170-r0 | ✅ 已发布 |  |  | 1 | - | [📄](archives/p/perl-net-mqtt/1.163170-r0/) |
| **perl-net-mqtt-simple** | 1.33-r0 | ✅ 已编译 |  |  | - | - | [📄](archives/p/perl-net-mqtt-simple/1.33-r0/) |
| **perl-net-ntp** | 1.5-r1 | ✅ 已发布 |  |  | 1 | - | [📄](archives/p/perl-net-ntp/1.5-r1/) |
| **perl-net-openssh** | 0.84-r1 | ✅ 已发布 |  |  | - | - | [📄](archives/p/perl-net-openssh/0.84-r1/) |
| **perl-net-pcap** | 0.21-r2 | ✅ 已编译 |  |  | 1 | - | [📄](archives/p/perl-net-pcap/0.21-r2/) |
| **perl-net-rblclient** | 0.5-r8 | ✅ 已编译 |  |  | 1 | - | [📄](archives/p/perl-net-rblclient/0.5-r8/) |
| **perl-net-server** | 2.014-r2 | ✅ 已发布 |  |  | - | - | [📄](archives/p/perl-net-server/2.014-r2/) |
| **perl-net-sftp-foreign** | 1.93-r0 | ✅ 已编译 |  | custom | - | - | [📄](archives/p/perl-net-sftp-foreign/1.93-r0/) |
| **perl-netaddr-ip** | 4.079 | ✅ 已发布 |  |  | - | - | [📄](archives/p/perl-netaddr-ip/4.079/) |
| **perl-padwalker** | 2.5-r5 | ✅ 已编译 |  |  | - | - | [📄](archives/p/perl-padwalker/2.5-r5/) |
| **perl-parallel-prefork** | 0.18 | ✅ 已编译 |  |  | 2 | - | [📄](archives/p/perl-parallel-prefork/0.18/) |
| **perl-pdf-api2** | 2.048 | ✅ 已发布 |  | perl | - | - | [📄](archives/p/perl-pdf-api2/2.048/) |
| **perl-perlio-utf8_strict** | 0.010 | ✅ 已编译 |  | perl-extutils | - | - | [📄](archives/p/perl-perlio-utf8_strict/0.010/) |
| **perl-perlio-via-timeout** | 0.32 | ✅ 已编译 |  | perl-extutils-makemaker | - | - | [📄](archives/p/perl-perlio-via-timeout/0.32/) |
| **perl-php-serialization** | 0.34 | ✅ 已编译 |  | perl-extutils | - | - | [📄](archives/p/perl-php-serialization/0.34/) |
| **perl-plack** | 1.0051-r0 | ✅ 已编译 |  |  | - | - | [📄](archives/p/perl-plack/1.0051-r0/) |
| **perl-pod-coverage** | 0.23 | ✅ 已发布 |  | perl | - | - | [📄](archives/p/perl-pod-coverage/0.23/) |
| **perl-pod-spell** | 1.27 | ✅ 已发布 |  | perl-eumm | - | - | [📄](archives/p/perl-pod-spell/1.27/) |
| **perl-pod-wrap** | 0.01 | ✅ 已发布 |  | perl | - | - | [📄](archives/p/perl-pod-wrap/0.01/) |
| **perl-posix-strftime-compiler** | 0.46 | ✅ 已发布 |  | perl | 2 | - | [📄](archives/p/perl-posix-strftime-compiler/0.46/) |
| **perl-power-tools** | 1.053 | ✅ 已发布 |  | perl-eumm | - | - | [📄](archives/p/perl-power-tools/1.053/) |
| **perl-ppix-quotelike** | 0.023 | ✅ 已编译 |  | perl-eumm | - | - | [📄](archives/p/perl-ppix-quotelike/0.023/) |
| **perl-ppix-regexp** | 0.091 | ✅ 已发布 |  |  | - | - | [📄](archives/p/perl-ppix-regexp/0.091/) |
| **perl-ppix-utils** | 0.004 | ✅ 已发布 |  | perl-eumm | - | - | [📄](archives/p/perl-ppix-utils/0.004/) |
| **perl-probe-perl** | 0.03 | ✅ 已发布 |  | perl-eumm | - | - | [📄](archives/p/perl-probe-perl/0.03/) |
| **perl-proc-forksafe** | 0.001 | ✅ 已发布 |  | perl-eumm | - | - | [📄](archives/p/perl-proc-forksafe/0.001/) |
| **perl-proc-processtable** | 0.637 | ✅ 已发布 |  |  | 1 | - | [📄](archives/p/perl-proc-processtable/0.637/) |
| **perl-proc-wait3** | 0.05 | ✅ 已发布 |  |  | - | - | [📄](archives/p/perl-proc-wait3/0.05/) |
| **perl-proc-waitstat** | 1.00 | ✅ 已发布 |  | perl-eumm | - | - | [📄](archives/p/perl-proc-waitstat/1.00/) |
| **perl-protocol-http2** | 1.11 | ✅ 已发布 |  |  | - | - | [📄](archives/p/perl-protocol-http2/1.11/) |
| **perl-protocol-irc** | 0.13 | ✅ 已发布 |  |  | - | - | [📄](archives/p/perl-protocol-irc/0.13/) |
| **perl-protocol-websocket** | 0.26 | ✅ 已发布 |  | perl-eumm | - | - | [📄](archives/p/perl-protocol-websocket/0.26/) |
| **perl-protocol-xmpp** | 0.006 | ✅ 已发布 |  |  | - | - | [📄](archives/p/perl-protocol-xmpp/0.006/) |
| **perl-provide** | 0.03 | ✅ 已发布 |  |  | - | - | [📄](archives/p/perl-provide/0.03/) |
| **perl-readonly** | 2.05 | ✅ 已发布 |  |  | - | - | [📄](archives/p/perl-readonly/2.05/) |
| **perl-redis** | 2.000 | ✅ 已发布 |  |  | - | - | [📄](archives/p/perl-redis/2.000/) |
| **perl-ref-util** | 0.204 | ✅ 已发布 |  |  | - | - | [📄](archives/p/perl-ref-util/0.204/) |
| **perl-regexp-common** | 2024080801 | ✅ 已发布 |  |  | - | - | [📄](archives/p/perl-regexp-common/2024080801/) |
| **perl-regexp-common-net-cidr** | 0.03 | ✅ 已发布 |  |  | - | - | [📄](archives/p/perl-regexp-common-net-cidr/0.03/) |
| **perl-regexp-grammars** | 1.058 | ✅ 已发布 |  | perl | - | - | [📄](archives/p/perl-regexp-grammars/1.058/) |
| **perl-regexp-ipv6** | 0.03 | ✅ 已发布 |  | perl | - | - | [📄](archives/p/perl-regexp-ipv6/0.03/) |
| **perl-regexp-tr** | 0.05 | ✅ 已发布 |  |  | - | - | [📄](archives/p/perl-regexp-tr/0.05/) |
| **perl-reply** | 0.42 | ✅ 已发布 |  |  | 4 | - | [📄](archives/p/perl-reply/0.42/) |
| **perl-role-basic** | 0.16 | ✅ 已发布 |  | perl | - | - | [📄](archives/p/perl-role-basic/0.16/) |
| **perl-role-tiny** | 2.002004 | ✅ 已发布 |  |  | - | - | [📄](archives/p/perl-role-tiny/2.002004/) |
| **perl-rpc-xml** | 0.82 | ✅ 已发布 |  |  | - | - | [📄](archives/p/perl-rpc-xml/0.82/) |
| **perl-rt-extension-commandbymail** | 3.02 | ✅ 已发布 |  |  | 1 | - | [📄](archives/p/perl-rt-extension-commandbymail/3.02/) |
| **perl-safe-isa** | 1.000010 | ✅ 已发布 |  |  | - | - | [📄](archives/p/perl-safe-isa/1.000010/) |
| **perl-scope-guard** | 0.21 | ✅ 已发布 |  |  | - | - | [📄](archives/p/perl-scope-guard/0.21/) |
| **perl-spiffy** | 0.46 | ✅ 已编译 |  | perl | - | - | [📄](archives/p/perl-spiffy/0.46/) |
| **perl-sql-abstract** | 2.000001 | ✅ 已发布 |  |  | - | - | [📄](archives/p/perl-sql-abstract/2.000001/) |
| **perl-tk** | 804.036 | ✅ 已编译 |  |  | 1 | - | [📄](archives/p/perl-tk/804.036/) |
| **perl-xml-parser** | 2.59 | ✅ 已发布 |  |  | - | - | [📄](archives/p/perl-xml-parser/2.59/) |
| **perltidy** | 20260204 | ✅ 已发布 |  | Custom Perl | 1 | - | [📄](archives/p/perltidy/20260204/) |
| **pg_cron** | 1.6.7 | ✅ 已编译 |  |  | - | - | [📄](archives/p/pg_cron/1.6.7/) |
| **pg_partman** | 5.4.3 | ✅ 已编译 |  |  | - | - | [📄](archives/p/pg_partman/5.4.3/) |
| **pg_roaringbitmap** | 1.1.0 | ✅ 已编译 |  |  | - | - | [📄](archives/p/pg_roaringbitmap/1.1.0/) |
| **pgbadger** | 13.2 | ✅ 已编译 |  |  | - | - | [📄](archives/p/pgbadger/13.2/) |
| **pgbouncer** | 1.22.1 | ✅ 已编译 |  |  | 3 | - | [📄](archives/p/pgbouncer/1.22.1/) |
| **pgcli** | 4.5.0 | ✅ 已编译 |  |  | - | - | [📄](archives/p/pgcli/4.5.0/) |
| **pgexporter** | 0.8.0 | ✅ 已发布 |  |  | 4 | - | [📄](archives/p/pgexporter/0.8.0/) |
| **pgimportdoc** | 0.1.4 | ✅ 已发布 |  | Makefile | 1 | - | [📄](archives/p/pgimportdoc/0.1.4/) |
| **pgpdump** | 0.37 | ✅ 已编译 |  | Autotools | 1 | - | [📄](archives/p/pgpdump/0.37/) |
| **pgpool** | 4.5.0 | ✅ 已编译 |  |  | 3 | - | [📄](archives/p/pgpool/4.5.0/) |
| **pgpool-II** | 4.7.2 | ✅ 已发布 |  | Autotools | 4 | - | [📄](archives/p/pgpool-II/4.7.2/) |
| **pgsanity** | 0.3.0 | ✅ 已发布 |  | python | - | - | [📄](archives/p/pgsanity/0.3.0/) |
| **pgtcl** | 3.1.1 | ✅ 已发布 |  |  | 1 | - | [📄](archives/p/pgtcl/3.1.1/) |
| **phodav** | 2.5 | ✅ 已发布 |  | Meson | 1 | - | [📄](archives/p/phodav/2.5/) |
| **phoon** | 14Aug2014、20140814 | ✅ 已编译 |  | Makefile | 1 | - | [📄](archives/p/phoon/20140814/) |
| **php** | 8.2.28、8.3.11 | ✅ 已编译 |  | Autotools | 1 | [] | [📄](archives/p/php/8.3.11/) |
| **php-pecl-memcache** | 8.2 | ✅ 已发布 |  | phpize | - | - | [📄](archives/p/php-pecl-memcache/8.2/) |
| **php-pecl-memcached** | 3.4.0 | ✅ 已发布 |  |  | 2 | - | [📄](archives/p/php-pecl-memcached/3.4.0/) |
| **php83** | 8.3.30 | ✅ 已编译 |  |  | 2 | - | [📄](archives/p/php83/8.3.30/) |
| **php83-pecl-memcache** | 2.3.3 | ✅ 已发布 |  |  | 8 | - | [📄](archives/p/php83-pecl-memcache/2.3.3/) |
| **php83-pecl-mongodb** | 2.3.3 | ✅ 已编译 |  |  | - | - | [📄](archives/p/php83-pecl-mongodb/2.3.3/) |
| **php83-pecl-timezonedb** | 3.4.0 | ✅ 已发布 |  |  | 2 | - | [📄](archives/p/php83-pecl-timezonedb/3.4.0/) |
| **php84** | 8.4.10 | ✅ 已编译 |  |  | 1 | - | [📄](archives/p/php84/8.4.10/) |
| **php84-pecl-memcache** | 2.3.3 | ✅ 已编译 |  |  | - | - | [📄](archives/p/php84-pecl-memcache/2.3.3/) |
| **php84-pecl-mongodb** | 2.3.3 | ✅ 已编译 |  |  | - | - | [📄](archives/p/php84-pecl-mongodb/2.3.3/) |
| **php85-pecl-memcache** | 2.3.3 | ✅ 已发布 |  |  | 5 | - | [📄](archives/p/php85-pecl-memcache/2.3.3/) |
| **phrase-cli** | 2.63.0、homebrew | ✅ 已发布 |  | go | 12 | - | [📄](archives/p/phrase-cli/homebrew/) |
| **physfs** | 3.2.0 | uploaded |  | unknown | 0 | - | [📄](archives/p/physfs/3.2.0/) |
| **picat** | 3.9.7 | ✅ 已发布 |  | Makefile | 2 | - | [📄](archives/p/picat/3.9.7/) |
| **picocom** | 2024.07 | ✅ 已发布 |  | Makefile | - | - | [📄](archives/p/picocom/2024.07/) |
| **picolisp** | 26.3 | ✅ 已编译 |  | Makefile | 1 | - | [📄](archives/p/picolisp/26.3/) |
| **picoruby** | 3.0.2 | ✅ 已发布 |  | custom | 1 | - | [📄](archives/p/picoruby/3.0.2/) |
| **pigz** | 2.8 | uploaded |  | Makefile | 0 | zlib | [📄](archives/p/pigz/2.8/) |
| **piknik** | 0.10.2-r12 | ✅ 已编译 |  |  | - | - | [📄](archives/p/piknik/0.10.2-r12/) |
| **pinentry** | 1.3.2 | ✅ 已编译 |  |  | 3 | - | [📄](archives/p/pinentry/1.3.2/) |
| **pinfo** | 0.6.13 | ✅ 已编译 |  | Autotools | 5 | - | [📄](archives/p/pinfo/0.6.13/) |
| **pix** | 3.4.10 | ✅ 已编译 |  |  | 3 | - | [📄](archives/p/pix/3.4.10/) |
| **pixi** | homebrew | ✅ 已编译 |  |  | - | - | [📄](archives/p/pixi/homebrew/) |
| **pixman** | 0.46.4 | uploaded |  | Autotools | 0 | - | [📄](archives/p/pixman/0.46.4/) |
| **pjproject** | 2.17 | ✅ 已编译 |  |  | - | - | [📄](archives/p/pjproject/2.17/) |
| **pkcs11-helper** | 1.30.0 | partial |  | Autotools | 9 | - | [📄](archives/p/pkcs11-helper/1.30.0/) |
| **pkcs11-tools** | 2.6.0 | ✅ 已发布 |  |  | - | - | [📄](archives/p/pkcs11-tools/2.6.0/) |
| **pkg-config** | 0.29.2 | uploaded |  | Makefile | 0 | - | [📄](archives/p/pkg-config/0.29.2/) |
| **pkgconf** | 2.5.1 | ✅ 已发布 |  | Meson | 3 | - | [📄](archives/p/pkgconf/2.5.1/) |
| **playwright-cli** | 0.1.13 | ✅ 已编译 |  |  | 1 | - | [📄](archives/p/playwright-cli/0.1.13/) |
| **plpgsql_check** | 2.9.1 | ✅ 已编译 |  |  | - | - | [📄](archives/p/plpgsql_check/2.9.1/) |
| **plymouth** | 24.2.122 | ✅ 已编译 |  | Meson | 7 | - | [📄](archives/p/plymouth/24.2.122/) |
| **plzip** | 1.13 | uploaded |  | Makefile | 0 | lzlib | [📄](archives/p/plzip/1.13/) |
| **pmccabe** | 2.8 | ✅ 已发布 |  |  | - | - | [📄](archives/p/pmccabe/2.8/) |
| **pmix** | 5.0.10 | ✅ 已编译 |  | Autotools | - | - | [📄](archives/p/pmix/5.0.10/) |
| **pnetcdf** | 1.14.1 | ✅ 已编译 |  |  | 1 | - | [📄](archives/p/pnetcdf/1.14.1/) |
| **pngcheck** | 4.0.1 | ✅ 已编译 |  | CMake | - | - | [📄](archives/p/pngcheck/4.0.1/) |
| **pngquant** | 2.18.0 | ✅ 已发布 |  | Autotools | 3 | - | [📄](archives/p/pngquant/2.18.0/) |
| **po4a** | 0.74 | ✅ 已发布 |  | perl-module-build | 1 | Module::Build >= 0.42,Locale::gettext >= 1.01,Pod::Parser,SGMLS,Term::ReadKey... | [📄](archives/p/po4a/0.74/) |
| **pocketbase** | 0.26.6 | ✅ 已编译 |  | go | - | - | [📄](archives/p/pocketbase/0.26.6/) |
| **pocketsphinx** | 5.1.1 | ✅ 已发布 |  |  | 2 | - | [📄](archives/p/pocketsphinx/5.1.1/) |
| **poco** | 1.14.2 | ✅ 已发布 |  | CMake | 1 | - | [📄](archives/p/poco/1.14.2/) |
| **pod2man** | 6.0.2 | ✅ 已编译 |  |  | 0 | - | [📄](archives/p/pod2man/6.0.2/) |
| **podman** | 5.8.3 | ✅ 已编译 |  | golang | 1 | - | [📄](archives/p/podman/5.8.3/) |
| **podman-tui** | 1.9.0 | ✅ 已编译 |  |  | - | - | [📄](archives/p/podman-tui/1.9.0/) |
| **podofo** | 0.9.5 | ✅ 已编译 |  | CMake | - | - | [📄](archives/p/podofo/0.9.5/) |
| **polipo** | 1.1.1 | ✅ 已发布 |  | Makefile | - | - | [📄](archives/p/polipo/1.1.1/) |
| **poppler** | 25.12.0 | ✅ 已编译 |  | CMake | - | - | [📄](archives/p/poppler/25.12.0/) |
| **popt** | 1.16 | uploaded |  | unknown | 0 | [] | [📄](archives/p/popt/1.16/) |
| **portable-libyaml** | 0.2.5 | ✅ 已发布 |  |  | - | - | [📄](archives/p/portable-libyaml/0.2.5/) |
| **portable-ruby** | 4.0.2 | ✅ 已发布 |  | Autotools | 3 | - | [📄](archives/p/portable-ruby/4.0.2/) |
| **portaudio** | 19.7.0 | ✅ 已编译 |  |  | 5 | - | [📄](archives/p/portaudio/19.7.0/) |
| **portmidi** | 2.0.8 | ✅ 已编译 |  |  | 1 | - | [📄](archives/p/portmidi/2.0.8/) |
| **postgis** | 3.4.2 | ✅ 已编译 |  |  | 1 | - | [📄](archives/p/postgis/3.4.2/) |
| **postgresql** | 18.3 | ✅ 已编译 |  |  | - | - | [📄](archives/p/postgresql/18.3/) |
| **postgresql-hll** | 2.19 | ✅ 已编译 |  |  | - | - | [📄](archives/p/postgresql-hll/2.19/) |
| **postgresql-hypopg** | 1.4.2 | ✅ 已编译 |  | pgxs | - | - | [📄](archives/p/postgresql-hypopg/1.4.2/) |
| **postgresql-login_hook** | 1.5 | ✅ 已发布 |  |  | 1 | - | [📄](archives/p/postgresql-login_hook/1.5/) |
| **postgresql-orafce** | 4.16.0 | ✅ 已编译 |  |  | - | - | [📄](archives/p/postgresql-orafce/4.16.0/) |
| **postgresql-pllua version: REL_2_0_12 status: built** | REL_2_0_12 | unknown |  |  | - | - | [📄](archives/p/postgresql-pllua/REL_2_0_12/) |
| **postgresql-rum** | 1.3.15 | ✅ 已发布 |  |  | - | - | [📄](archives/p/postgresql-rum/1.3.15/) |
| **postgresql-sequential-uuids** | 1.0.3 | ✅ 已编译 |  | pgxs | - | - | [📄](archives/p/postgresql-sequential-uuids/1.0.3/) |
| **postgresql-shared_ispell** | 1.1.0 | ✅ 已编译 |  | pgxs | - | - | [📄](archives/p/postgresql-shared_ispell/1.1.0/) |
| **postgresql-temporal_tables** | 1.2.2 | ✅ 已编译 |  |  | - | - | [📄](archives/p/postgresql-temporal_tables/1.2.2/) |
| **postgresql-topn** | 2.7.0 | ✅ 已编译 |  |  | - | - | [📄](archives/p/postgresql-topn/2.7.0/) |
| **postgresql-tsearch-czech** | latest | ✅ 已编译 |  | custom | - | - | [📄](archives/p/postgresql-tsearch-czech/latest/) |
| **postgresql-uint** | 3.0.0 | ✅ 已编译 |  |  | - | - | [📄](archives/p/postgresql-uint/3.0.0/) |
| **postgresql-url_encode** | 1.2.3 | ✅ 已发布 |  |  | 1 | - | [📄](archives/p/postgresql-url_encode/1.2.3/) |
| **potrace** | 1.16 | ✅ 已发布 |  |  | 3 | - | [📄](archives/p/potrace/1.16/) |
| **pound** | 4.22 | ✅ 已发布 |  |  | 1 | - | [📄](archives/p/pound/4.22/) |
| **ppp** | 2.5.2 | unknown |  |  | - | name: openssl,name: glibc,name: openssl-dev | [📄](archives/p/ppp/2.5.2/) |
| **precious** | 0.10.2 | ✅ 已编译 |  | rust | - | [] | [📄](archives/p/precious/0.10.2/) |
| **premake** | 5.0.0-beta8 | ✅ 已编译 |  | custom | 4 | - | [📄](archives/p/premake/5.0.0-beta8/) |
| **prettier** | 3.8.4 | ✅ 已编译 |  | custom | - | - | [📄](archives/p/prettier/3.8.4/) |
| **privoxy** | 4.0.0-r0 | ✅ 已编译 |  |  | 5 | - | [📄](archives/p/privoxy/4.0.0-r0/) |
| **prodigal** | 2.6.3 | ✅ 已发布 |  | Makefile | - | - | [📄](archives/p/prodigal/2.6.3/) |
| **progress** | 0.17 | ✅ 已发布 |  | Makefile | 2 | - | [📄](archives/p/progress/0.17/) |
| **proj** | 9.3.1 | ✅ 已发布 |  |  | - | - | [📄](archives/p/proj/9.3.1/) |
| **prometheus** | 3.12.0 | ✅ 已编译 |  | prebuilt/go | - | - | [📄](archives/p/prometheus/3.12.0/) |
| **prometheus-postgres-exporter** | 0.19.1 | ✅ 已发布 |  |  | - | - | [📄](archives/p/prometheus-postgres-exporter/0.19.1/) |
| **protobuf** | 34.1、21.12、21.9、29.6、33.6 | ✅ 已编译 |  | CMake | 2 | - | [📄](archives/p/protobuf/33.6/) |
| **protobuf-c** | 1.5.2 | ✅ 已发布 |  |  | 1 | - | [📄](archives/p/protobuf-c/1.5.2/) |
| **protoc-gen-go** | 1.36.11 | ✅ 已发布 |  | custom | - | - | [📄](archives/p/protoc-gen-go/1.36.11/) |
| **protoc-gen-go-grpc** | 1.6.2 | ✅ 已发布 |  | go | - | go >= 1.25.0 | [📄](archives/p/protoc-gen-go-grpc/1.6.2/) |
| **proxychains-ng** | 4.16 | ✅ 已编译 |  | Autotools | - | - | [📄](archives/p/proxychains-ng/4.16/) |
| **psftools** | 1.0.14 | ✅ 已发布 |  |  | 3 | - | [📄](archives/p/psftools/1.0.14/) |
| **psmisc** | 23.6 | partial |  | Autotools | - | ncurses | [📄](archives/p/psmisc/23.6/) |
| **psql2csv** | 1.1.4 | ✅ 已编译 |  |  | - | - | [📄](archives/p/psql2csv/1.1.4/) |
| **psqlodbc** | 16.00.0000 | partial |  |  | 2 | - | [📄](archives/p/psqlodbc/16.00.0000/) |
| **ptex** | 2.5.2 | ✅ 已编译 |  | CMake | 4 | - | [📄](archives/p/ptex/2.5.2/) |
| **pulseaudio** | 17.0 | ✅ 已编译 |  | Meson | 4 | - | [📄](archives/p/pulseaudio/17.0/) |
| **pulseaudio-ctl** | 1.70 | ✅ 已发布 |  | Makefile | 2 | - | [📄](archives/p/pulseaudio-ctl/1.70/) |
| **pulsemixer** | 1.5.1 | ✅ 已编译 |  | python | - | - | [📄](archives/p/pulsemixer/1.5.1/) |
| **pumba** | 1.1.2 | ✅ 已编译 |  |  | - | - | [📄](archives/p/pumba/1.1.2/) |
| **pure** | 1.23.0 | ✅ 已编译 |  | custom | - | - | [📄](archives/p/pure/1.23.0/) |
| **pure-ftpd** | 1.0.52-r0 | ✅ 已编译 |  |  | 2 | - | [📄](archives/p/pure-ftpd/1.0.52-r0/) |
| **putty** | 0.84 | ✅ 已编译 |  |  | 1 | - | [📄](archives/p/putty/0.84/) |
| **pv** | 1.7.24 | ✅ 已编译 |  | Autotools | 2 | - | [📄](archives/p/pv/1.7.24/) |
| **pwgen** | 2.08 | partial |  | Autotools | - | - | [📄](archives/p/pwgen/2.08/) |
| **pwsafe** | 1.24.0 | ✅ 已发布 |  |  | 9 | - | [📄](archives/p/pwsafe/1.24.0/) |
| **py3-alembic** | 1.18.4 | ✅ 已发布 |  |  | - | - | [📄](archives/p/py3-alembic/1.18.4/) |
| **py3-librelingo-audios** | 1.3.0 | ✅ 已编译 |  | custom | - | - | [📄](archives/p/py3-librelingo-audios/1.3.0/) |
| **py3-pypdf** | 6.12.2 | ✅ 已编译 |  | python3 | - | - | [📄](archives/p/py3-pypdf/6.12.2/) |
| **pycxx** | 6.2.3 | ✅ 已编译 |  | none | 1 | python3-dev | [📄](archives/p/pycxx/6.2.3/) |
| **pylint** | 4.0.5 | ✅ 已发布 |  |  | 1 | - | [📄](archives/p/pylint/4.0.5/) |
| **pyright** | 1.1.410 | ✅ 已发布 |  | npm | - | node (>=14.0.0) | [📄](archives/p/pyright/1.1.410/) |
| **pytest** | 9.0.3 | ✅ 已编译 |  | python-pip | - | iniconfig>=1.0.1,packaging>=22,pluggy>=1.5,<2,pygments>=2.7.2,setuptools>=77... | [📄](archives/p/pytest/9.0.3/) |
| **python** | 3.12.9、3.9.0、3.9.25 | verified |  | Autotools | 0 | - | [📄](archives/p/python/3.9.25/) |
| **python-gssapi** | 1.8.3 | ✅ 已编译 |  | python_wheel | - | krb5 1.22.2 (MIT Kerberos),cffi 1.17.1,six 1.17.0,pyasn1 0.6.1 | [📄](archives/p/python-gssapi/1.8.3/) |
| **qdbm** | 1.8.78 | ✅ 已发布 |  | Autotools | 3 | - | [📄](archives/q/qdbm/1.8.78/) |
| **qman** | 1.5.1 | ✅ 已编译 |  | Meson | 4 | - | [📄](archives/q/qman/1.5.1/) |
| **qpdf** | 11.6.3 | ✅ 已编译 |  |  | - | - | [📄](archives/q/qpdf/11.6.3/) |
| **qrencode** | 4.1.1 | ✅ 已编译 |  | CMake | - | - | [📄](archives/q/qrencode/4.1.1/) |
| **qsv** | homebrew | ✅ 已编译 |  |  | - | - | [📄](archives/q/qsv/homebrew/) |
| **qt-libiodbc** | 5.15.2 | ✅ 已编译 |  |  | - | - | [📄](archives/q/qt-libiodbc/5.15.2/) |
| **qt-mariadb** | 5.15.2 | ✅ 已编译 |  |  | - | - | [📄](archives/q/qt-mariadb/5.15.2/) |
| **qt-mysql** | 5.15.2 | ✅ 已编译 |  |  | 1 | - | [📄](archives/q/qt-mysql/5.15.2/) |
| **qt-unixodbc** | 5.15.2 | ✅ 已编译 |  |  | 1 | - | [📄](archives/q/qt-unixodbc/5.15.2/) |
| **qt5-qt3d** | 5.15.2 | ✅ 已编译 |  | qmake | - | qt5-qtbase 5.15.2,qt5-qtdeclarative 5.15.2 | [📄](archives/q/qt5-qt3d/5.15.2/) |
| **qt5-qtcharts** | 5.15.2 | ✅ 已编译 |  | qmake | - | qt5-qtbase 5.15.2,qt5-qtdeclarative 5.15.2 | [📄](archives/q/qt5-qtcharts/5.15.2/) |
| **qt5-qtgraphicaleffects** | 5.15.2 | ✅ 已编译 |  |  | - | - | [📄](archives/q/qt5-qtgraphicaleffects/5.15.2/) |
| **qt5-qtimageformats** | 5.15.2 | ✅ 已编译 |  | qmake | - | - | [📄](archives/q/qt5-qtimageformats/5.15.2/) |
| **qt5-qtsvg** | 5.15.2 | ✅ 已编译 |  |  | - | - | [📄](archives/q/qt5-qtsvg/5.15.2/) |
| **qtimageformats** | 6.11.1 | ✅ 已编译 |  | CMake | - | - | [📄](archives/q/qtimageformats/6.11.1/) |
| **qtshadertools** | 6.11.1 | ✅ 已编译 |  | CMake | 1 | - | [📄](archives/q/qtshadertools/6.11.1/) |
| **quilt** | 0.69 | ✅ 已发布 |  | autoconf | 1 | GNU patch >= 2.5,bash,gawk,sed (GNU),diff (GNU) | [📄](archives/q/quilt/0.69/) |
| **qxlsx** | 1.4.7 | ✅ 已编译 |  |  | - | - | [📄](archives/q/qxlsx/1.4.7/) |
| **rabbitmq-c** | 0.13.0、0.15.0 | ✅ 已编译 |  | CMake | - | openssl/1.1.1w | [📄](archives/r/rabbitmq-c/0.15.0/) |
| **radare2** | 6.0.7 | ✅ 已编译 |  | Autotools | 3 | name: capstone | [📄](archives/r/radare2/6.0.7/) |
| **radsecproxy** | 1.11.2 | ✅ 已发布 |  |  | - | - | [📄](archives/r/radsecproxy/1.11.2/) |
| **raft** | 0.22.1 | ✅ 已编译 |  | Autotools | - | - | [📄](archives/r/raft/0.22.1/) |
| **raft-cowsql** | 0.22.1 | ✅ 已发布 |  | Autotools | 17 | - | [📄](archives/r/raft-cowsql/0.22.1/) |
| **ragel** | 6.10 | uploaded |  | unknown | 0 | - | [📄](archives/r/ragel/6.10/) |
| **rain** | 1.24.4 | ✅ 已编译 |  |  | - | - | [📄](archives/r/rain/1.24.4/) |
| **raku-dbiish** | 0.6.8 | ✅ 已发布 |  | custom | 1 | - | [📄](archives/r/raku-dbiish/0.6.8/) |
| **rancher-cli** | 2.9.0 | ✅ 已发布 |  | go | - | - | [📄](archives/r/rancher-cli/2.9.0/) |
| **ranger** | 1.9.4 | ✅ 已编译 |  |  | 1 | - | [📄](archives/r/ranger/1.9.4/) |
| **rapidjson** | 1.1.0 | uploaded |  | CMake | 0 | - | [📄](archives/r/rapidjson/1.1.0/) |
| **raylib** | 6.0 | ✅ 已发布 |  |  | 1 | - | [📄](archives/r/raylib/6.0/) |
| **rbenv-bundler** | 1.0.1 | ✅ 已编译 |  | Makefile | - | - | [📄](archives/r/rbenv-bundler/1.0.1/) |
| **rc** | 1.7.4 | ✅ 已发布 |  | Autotools | 6 | - | [📄](archives/r/rc/1.7.4/) |
| **rclone** | 1.72.1 | ✅ 已发布 |  |  | - | - | [📄](archives/r/rclone/1.72.1/) |
| **re2** | 2024-04-01、2024-07-01 | partial |  | unknown | - | - | [📄](archives/r/re2/2024-07-01/) |
| **re2c** | 4.3.1 | uploaded |  | unknown | 0 | - | [📄](archives/r/re2c/4.3.1/) |
| **readline** | 8.2、8.3 | ✅ 已发布 |  |  | 1 | - | [📄](archives/r/readline/8.3/) |
| **readosm** | 1.1.0a | ✅ 已编译 |  |  | 1 | - | [📄](archives/r/readosm/1.1.0a/) |
| **readpe** | 0.81 | ✅ 已编译 |  |  | 3 | - | [📄](archives/r/readpe/0.81/) |
| **recode** | 3.7.12 | ✅ 已编译 |  | Autotools | 3 | - | [📄](archives/r/recode/3.7.12/) |
| **recutils** | 1.9 | ✅ 已编译 |  |  | 2 | - | [📄](archives/r/recutils/1.9/) |
| **redict** | 7.3.0 | ✅ 已发布 |  | Makefile | - | - | [📄](archives/r/redict/7.3.0/) |
| **redis** | 7.4.2、8.6.0 | ✅ 已编译 |  | Makefile | 4 | - | [📄](archives/r/redis/8.6.0/) |
| **redo** | 0.42d | ✅ 已发布 |  |  | - | - | [📄](archives/r/redo/0.42d/) |
| **redocly-cli** | 2.31.6 | ✅ 已发布 |  |  | - | - | [📄](archives/r/redocly-cli/2.31.6/) |
| **redsocks** | 0.5 | ✅ 已发布 |  |  | - | - | [📄](archives/r/redsocks/0.5/) |
| **rename** | 1.601 | ✅ 已发布 |  |  | - | - | [📄](archives/r/rename/1.601/) |
| **renderdoc** | 1.44 | ✅ 已编译 |  | CMake | 2 | - | [📄](archives/r/renderdoc/1.44/) |
| **renovate** | 39.238.1 | ✅ 已编译 |  |  | - | - | [📄](archives/r/renovate/39.238.1/) |
| **repo** | 2 | ✅ 已编译 |  | python | - | - | [📄](archives/r/repo/2/) |
| **reproc** | 14.2.5 | ✅ 已编译 |  |  | - | - | [📄](archives/r/reproc/14.2.5/) |
| **rest-server** | 0.14.0-r9 | ✅ 已编译 |  |  | - | - | [📄](archives/r/rest-server/0.14.0-r9/) |
| **resterm** | 0.42.1 | ✅ 已发布 |  | go | - | - | [📄](archives/r/resterm/0.42.1/) |
| **restic** | 0.18.1 | ✅ 已编译 |  | custom | - | - | [📄](archives/r/restic/0.18.1/) |
| **resvg** | 0.47.0 | ✅ 已编译 |  | cargo | - | [] | [📄](archives/r/resvg/0.47.0/) |
| **retawq** | 0.2.6c | ✅ 已发布 |  |  | - | - | [📄](archives/r/retawq/0.2.6c/) |
| **rex** | 1.16.1 | ✅ 已发布 |  | perl-makefile-pl | - | - | [📄](archives/r/rex/1.16.1/) |
| **rhash** | 1.4.4、1.4.6 | ✅ 已编译 |  |  | - | - | [📄](archives/r/rhash/1.4.6/) |
| **rich-cli** | 1.8.0 | ✅ 已编译 |  | cargo | - | - | [📄](archives/r/rich-cli/1.8.0/) |
| **rig** | 1.11 | ✅ 已编译 |  |  | 1 | - | [📄](archives/r/rig/1.11/) |
| **rinetd** | 0.73 | ✅ 已编译 |  | Autotools | 1 | - | [📄](archives/r/rinetd/0.73/) |
| **ripgrep** | 15.1.0 | ✅ 已编译 |  | cargo | - | - | [📄](archives/r/ripgrep/15.1.0/) |
| **ripmime** | 1.4.1.0 | ✅ 已发布 |  | Makefile | 4 | - | [📄](archives/r/ripmime/1.4.1.0/) |
| **ristretto** | 0.13.2 | ✅ 已编译 |  |  | 15 | - | [📄](archives/r/ristretto/0.13.2/) |
| **rlwrap** | 0.47.1 | ✅ 已编译 |  | Autotools | 1 | readline (8.2),ncurses (6.4) | [📄](archives/r/rlwrap/0.47.1/) |
| **robin-map** | 1.4.1 | uploaded |  | CMake | 0 | - | [📄](archives/r/robin-map/1.4.1/) |
| **rocksdb** | 9.10.0、6.4.6 | ✅ 已发布 |  |  | 4 | - | [📄](archives/r/rocksdb/6.4.6/) |
| **rogue** | 5.4.4 | ✅ 已发布 |  | Autotools | 4 | - | [📄](archives/r/rogue/5.4.4/) |
| **rom-tools** | 0.288 | ✅ 已编译 |  | custom | 53 | - | [📄](archives/r/rom-tools/0.288/) |
| **rpki-client** | 9.6 | ✅ 已发布 |  |  | 3 | - | [📄](archives/r/rpki-client/9.6/) |
| **rpm2cpio** | 1.4-r3 | ✅ 已编译 |  | Makefile | 1 | - | [📄](archives/r/rpm2cpio/1.4-r3/) |
| **rsync** | 3.3.0 | verified |  | Autotools | 0 | - | [📄](archives/r/rsync/3.3.0/) |
| **rsyslog** | 8.2404.0 | ✅ 已编译 |  |  | 6 | - | [📄](archives/r/rsyslog/8.2404.0/) |
| **rtmpdump** | 2.3 | ✅ 已编译 |  |  | 5 | openssl 1.1.1w,zlib | [📄](archives/r/rtmpdump/2.3/) |
| **rtptools** | 1.22 | ✅ 已编译 |  |  | 2 | - | [📄](archives/r/rtptools/1.22/) |
| **rubberband** | 3.3.0 | ✅ 已编译 |  | Meson | 1 | - | [📄](archives/r/rubberband/3.3.0/) |
| **ruby-build** | 20260512 | ✅ 已发布 |  | Script | - | - | [📄](archives/r/ruby-build/20260512/) |
| **ruby-install** | 0.10.2 | ✅ 已编译 |  | Makefile | - | - | [📄](archives/r/ruby-install/0.10.2/) |
| **ruby-webrick** | 1.9.1-r0 | ✅ 已编译 |  |  | - | - | [📄](archives/r/ruby-webrick/1.9.1-r0/) |
| **runme** | 3.16.11 | ✅ 已编译 |  | go | - | - | [📄](archives/r/runme/3.16.11/) |
| **s2geometry** | 0.10.0 | ✅ 已编译 |  | CMake | 1 | - | [📄](archives/s/s2geometry/0.10.0/) |
| **s2n** | 1.7.3 | ✅ 已编译 |  | CMake | - | - | [📄](archives/s/s2n/1.7.3/) |
| **s2n-tls** | 1.7.2 | uploaded |  | unknown | 0 | libcrypto (OpenSSL or AWS libcrypto) | [📄](archives/s/s2n-tls/1.7.2/) |
| **s3cmd** | 2.4.0 | ✅ 已编译 |  | python | 1 | - | [📄](archives/s/s3cmd/2.4.0/) |
| **s3fs-fuse** | 1.94 | ✅ 已发布 |  |  | 1 | - | [📄](archives/s/s3fs-fuse/1.94/) |
| **s6-dns** | 2.4.1.0 | ✅ 已发布 |  |  | - | - | [📄](archives/s/s6-dns/2.4.1.0/) |
| **salesforce-mcp** | 0.30.13 | ✅ 已编译 |  |  | - | - | [📄](archives/s/salesforce-mcp/0.30.13/) |
| **saml2aws** | homebrew | ✅ 已发布 |  |  | 1 | - | [📄](archives/s/saml2aws/homebrew/) |
| **samtools** | 1.21 | ✅ 已发布 |  | Autotools | - | - | [📄](archives/s/samtools/1.21/) |
| **samurai** | 1.2 | uploaded |  | unknown | 0 | - | [📄](archives/s/samurai/1.2/) |
| **scapy** | 2.6.1-r0 | ✅ 已编译 |  |  | - | - | [📄](archives/s/scapy/2.6.1-r0/) |
| **scc** | 3.6.0-r5 | ✅ 已发布 |  | custom | 1 | - | [📄](archives/s/scc/3.6.0-r5/) |
| **scdoc** | 1.11.0、1.11.3 | partial |  | Autotools | - | - | [📄](archives/s/scdoc/1.11.3/) |
| **scheme48** | 1.9.3 | ✅ 已发布 |  | Autotools | 4 | - | [📄](archives/s/scheme48/1.9.3/) |
| **scintilla** | 5.6.1 | device_testing |  |  | 10 | - | [📄](archives/s/scintilla/5.6.1/) |
| **scip** | 10.0.2 | ✅ 已编译 |  | CMake | - | - | [📄](archives/s/scip/10.0.2/) |
| **scmpuff** | 0.7.0 | ✅ 已发布 |  |  | - | - | [📄](archives/s/scmpuff/0.7.0/) |
| **scons** | 4.10.0 | uploaded |  | custom | 0 | - | [📄](archives/s/scons/4.10.0/) |
| **scrcpy** | 2.3.1 | ✅ 已编译 |  |  | - | - | [📄](archives/s/scrcpy/2.3.1/) |
| **scream** | 4.0-r0 | ✅ 已编译 |  |  | - | - | [📄](archives/s/scream/4.0-r0/) |
| **screen** | 5.0.0 | uploaded |  | Makefile | 0 | - | [📄](archives/s/screen/5.0.0/) |
| **scsi-tgt** | v1.0 | ✅ 已编译 |  | Makefile | 10 | - | [📄](archives/s/scsi-tgt/v1.0/) |
| **scudo-malloc** | 19.1.6 | ✅ 已编译 |  |  | - | - | [📄](archives/s/scudo-malloc/19.1.6/) |
| **scummvm** | 2026.2.0 | ✅ 已编译 |  | configure+make | 2 | - | [📄](archives/s/scummvm/2026.2.0/) |
| **scw** | 2.56.1 | ✅ 已编译 |  | go | - | - | [📄](archives/s/scw/2.56.1/) |
| **sd** | 1.0.0-r0 | ✅ 已发布 |  |  | - | - | [📄](archives/s/sd/1.0.0-r0/) |
| **sd-tools** | 0.99.0 | ✅ 已发布 |  | Meson | 11 | - | [📄](archives/s/sd-tools/0.99.0/) |
| **sdl12-compat** | 1.2.68-r1 | ✅ 已发布 |  | CMake | - | - | [📄](archives/s/sdl12-compat/1.2.68-r1/) |
| **sdl2** | 2.30.10 | ✅ 已发布 |  | Autotools | 1 | - | [📄](archives/s/SDL2/2.30.10/) |
| **sdl2-compat** | 2.32.68 | ✅ 已编译 |  |  | - | - | [📄](archives/s/sdl2-compat/2.32.68/) |
| **sdl2_gfx** | 1.0.4 | ✅ 已编译 |  |  | 2 | - | [📄](archives/s/sdl2_gfx/1.0.4/) |
| **sdl2_net** | 2.2.0 | ✅ 已编译 |  |  | 2 | - | [📄](archives/s/sdl2_net/2.2.0/) |
| **sdl2_pango** | 2.1.5 | ✅ 已编译 |  |  | 2 | - | [📄](archives/s/sdl2_pango/2.1.5/) |
| **sdl3** | 3.4.8 | ✅ 已编译 |  |  | 4 | - | [📄](archives/s/sdl3/3.4.8/) |
| **sdl3_image** | 3.4.4 | ✅ 已编译 |  | CMake | - | - | [📄](archives/s/sdl3_image/3.4.4/) |
| **sdl3_mixer** | 3.2.4 | ✅ 已发布 |  | CMake | - | - | [📄](archives/s/sdl3_mixer/3.2.4/) |
| **sdl3_ttf** | 3.2.2 | ✅ 已发布 |  |  | - | - | [📄](archives/s/sdl3_ttf/3.2.2/) |
| **seatd** | 0.9.1 | ✅ 已编译 |  |  | - | - | [📄](archives/s/seatd/0.9.1/) |
| **secureboot-hook** | 0.2 | ✅ 已编译 |  |  | 1 | - | [📄](archives/s/secureboot-hook/0.2/) |
| **sed** | 4.10、4.9 | verified |  | Autotools | 0 | - | [📄](archives/s/sed/4.9/) |
| **sentry-native** | 0.13.3 | ✅ 已发布 |  | CMake | - | - | [📄](archives/s/sentry-native/0.13.3/) |
| **serd** | 0.32.9-git | ✅ 已发布 |  |  | - | - | [📄](archives/s/serd/0.32.9-git/) |
| **serverless** | 4.37.0 | ✅ 已编译 |  | npm | - | - | [📄](archives/s/serverless/4.37.0/) |
| **sesh** | v1.2.0 | ✅ 已编译 |  | go | - | [] | [📄](archives/s/sesh/v1.2.0/) |
| **sevenzip** | 26.00 | success |  | custom-makefile | 1 | - | [📄](archives/s/sevenzip/26.00/) |
| **sfml** | 2.6.1 | partial |  |  | 3 | - | [📄](archives/s/sfml/2.6.1/) |
| **sfsexp** | 1.4.1 | ✅ 已编译 |  | Autotools | 4 | - | [📄](archives/s/sfsexp/1.4.1/) |
| **sha2** | 1.0.1 | ✅ 已编译 |  |  | 2 | - | [📄](archives/s/sha2/1.0.1/) |
| **shairport-sync** | 5.0.4 | ✅ 已编译 |  |  | 15 | - | [📄](archives/s/shairport-sync/5.0.4/) |
| **shapelib** | 1.5.0 | ✅ 已编译 |  | CMake | 4 | - | [📄](archives/s/shapelib/1.5.0/) |
| **shared-mime-info** | 2.4 | ✅ 已发布 |  | Meson | 2 | - | [📄](archives/s/shared-mime-info/2.4/) |
| **shc** | 4.0.3 | ✅ 已发布 |  | Autotools | 1 | - | [📄](archives/s/shc/4.0.3/) |
| **sheldon** | 0.8.5 | ✅ 已发布 |  |  | 1 | - | [📄](archives/s/sheldon/0.8.5/) |
| **shellspec** | 0.28.1 | ✅ 已发布 |  | Makefile | 2 | - | [📄](archives/s/shellspec/0.28.1/) |
| **shfmt** | 3.13.1 | ✅ 已编译 |  |  | - | - | [📄](archives/s/shfmt/3.13.1/) |
| **shntool** | 3.0.10 | ✅ 已发布 |  | Autotools | 4 | - | [📄](archives/s/shntool/3.0.10/) |
| **shorewall** | 5.2.8-r1 | success |  | shell | 1 | - | [📄](archives/s/shorewall/5.2.8-r1/) |
| **sigrok-cli** | 0.7.2 | ✅ 已编译 |  | Autotools | - | - | [📄](archives/s/sigrok-cli/0.7.2/) |
| **simdjson** | 4.6.3 | uploaded |  | CMake | 0 | - | [📄](archives/s/simdjson/4.6.3/) |
| **sipcalc** | 1.1.6 | ✅ 已发布 |  | Autotools | 1 | - | [📄](archives/s/sipcalc/1.1.6/) |
| **sipsak** | 0.9.7 | ✅ 已发布 |  | Autotools | 6 | name: openssl,name: gnutls,name: c-ares,name: check | [📄](archives/s/sipsak/0.9.7/) |
| **sl** | 5.02-r1 | ✅ 已发布 |  | Makefile | 1 | - | [📄](archives/s/sl/5.02-r1/) |
| **slackdump** | v4.0.0 | ✅ 已编译 |  | go | - | [] | [📄](archives/s/slackdump/v4.0.0/) |
| **sleef** | 3.6.1 | ✅ 已编译 |  |  | 1 | - | [📄](archives/s/sleef/3.6.1/) |
| **sleuthkit** | 4.12.1 | ✅ 已发布 |  | Autotools | 5 | - | [📄](archives/s/sleuthkit/4.12.1/) |
| **slim** | 1.3.6 | ✅ 已编译 |  |  | 9 | - | [📄](archives/s/slim/1.3.6/) |
| **sloccount** | 2.26 | ✅ 已编译 |  |  | 3 | - | [📄](archives/s/sloccount/2.26/) |
| **sloci-image** | 0.1.1 | ✅ 已编译 |  |  | - | - | [📄](archives/s/sloci-image/0.1.1/) |
| **slowhttptest** | 1.9.0 | ✅ 已发布 |  |  | 1 | - | [📄](archives/s/slowhttptest/1.9.0/) |
| **smartmontools** | 7.4 | uploaded |  | Makefile | 0 | - | [📄](archives/s/smartmontools/7.4/) |
| **smartypants** | 2.0.2 | ✅ 已编译 |  |  | - | - | [📄](archives/s/smartypants/2.0.2/) |
| **smenu** | 1.5.0 | ✅ 已发布 |  |  | 3 | - | [📄](archives/s/smenu/1.5.0/) |
| **snapcast** | 0.35.0 | ✅ 已编译 |  |  | 4 | - | [📄](archives/s/snapcast/0.35.0/) |
| **snappy** | 1.2.2 | uploaded |  | CMake | 0 | - | [📄](archives/s/snappy/1.2.2/) |
| **sndio** | 1.10.0 | ✅ 已编译 |  |  | 3 | - | [📄](archives/s/sndio/1.10.0/) |
| **socat** | 1.7.4.4、1.8.0.3 | partial |  | Autotools | 1 | - | [📄](archives/s/socat/1.8.0.3/) |
| **softhsm** | 2.6.1 | ✅ 已编译 |  | Autotools | - | - | [📄](archives/s/softhsm/2.6.1/) |
| **sord** | 0.16.22-git | ✅ 已发布 |  |  | - | - | [📄](archives/s/sord/0.16.22-git/) |
| **sound-juicer** | 3.40.0 | ✅ 已编译 |  |  | 7 | - | [📄](archives/s/sound-juicer/3.40.0/) |
| **sound-touch** | 2.4.0 | ✅ 已发布 |  | Autotools | 3 | - | [📄](archives/s/sound-touch/2.4.0/) |
| **source-to-image** | 1.6.1 | ✅ 已编译 |  | go | - | - | [📄](archives/s/source-to-image/1.6.1/) |
| **sox** | 14.4.2 | ✅ 已编译 |  | CMake | 3 | - | [📄](archives/s/sox/14.4.2/) |
| **spaceship** | 4.22.3 | ✅ 已发布 |  |  | - | - | [📄](archives/s/spaceship/4.22.3/) |
| **sparse** | 0.6.4 | ✅ 已编译 |  | Makefile | - | - | [📄](archives/s/sparse/0.6.4/) |
| **sparsehash** | 2.0.4 | uploaded |  | CMake | 0 | - | [📄](archives/s/sparsehash/2.0.4/) |
| **spawn-fcgi** | 1.6.6 | ✅ 已发布 |  | Meson | - | - | [📄](archives/s/spawn-fcgi/1.6.6/) |
| **spdlog** | 1.17.0 | uploaded |  | unknown | 0 | - | [📄](archives/s/spdlog/1.17.0/) |
| **speex** | 1.2.1 | uploaded |  | Autotools | 0 | - | [📄](archives/s/speex/1.2.1/) |
| **speexdsp** | 1.2.1 | uploaded |  | Autotools | 0 | - | [📄](archives/s/speexdsp/1.2.1/) |
| **sphinx** | 7.2.6 | ✅ 已编译 |  |  | - | - | [📄](archives/s/sphinx/7.2.6/) |
| **spice-protocol** | 0.14.5 | ✅ 已发布 |  |  | - | - | [📄](archives/s/spice-protocol/0.14.5/) |
| **spicetify-cli** | 2.43.2 | ✅ 已发布 |  | custom | - | - | [📄](archives/s/spicetify-cli/2.43.2/) |
| **spim** | 9.1.24 | ✅ 已发布 |  | Makefile | 1 | - | [📄](archives/s/spim/9.1.24/) |
| **spirv-cross** | 1.4.341.0 | ✅ 已发布 |  | CMake | - | - | [📄](archives/s/spirv-cross/1.4.341.0/) |
| **spirv-headers** | vulkan-sdk-1.3.290.0 | ✅ 已编译 |  | CMake | - | - | [📄](archives/s/spirv-headers/vulkan-sdk-1.3.290.0/) |
| **spirv-tools** | vulkan-sdk-1.3.290.0 | ✅ 已编译 |  |  | 1 | - | [📄](archives/s/spirv-tools/vulkan-sdk-1.3.290.0/) |
| **sponge** | 0.70 | ✅ 已发布 |  |  | - | - | [📄](archives/s/sponge/0.70/) |
| **spotify_player** | 0.22.1、0.23.0、homebrew | ❌ 编译失败 |  |  | - | - | [📄](archives/s/spotify_player/homebrew/) |
| **sqlcipher** | 4.16.0 | ✅ 已编译 |  | autosetup | 3 | name: openssl | [📄](archives/s/sqlcipher/4.16.0/) |
| **sqlcmd** | 1.10.0 | ✅ 已编译 |  |  | - | - | [📄](archives/s/sqlcmd/1.10.0/) |
| **sqldiff** | 3.51.3 | ✅ 已编译 |  |  | - | - | [📄](archives/s/sqldiff/3.51.3/) |
| **sqlite** | 3.46.0 | ✅ 已编译 |  |  | 2 | - | [📄](archives/s/sqlite/3.46.0/) |
| **sqlite-rsync** | 3.51.3 | ✅ 已发布 |  |  | - | - | [📄](archives/s/sqlite-rsync/3.51.3/) |
| **sqlite3** | 3.49.1 | uploaded |  | Autotools | 0 | - | [📄](archives/s/sqlite3/3.49.1/) |
| **sqlite3pp** | 1.0.8 | ✅ 已编译 |  |  | - | - | [📄](archives/s/sqlite3pp/1.0.8/) |
| **sqlmap** | 1.10 | ✅ 已发布 |  | python | - | - | [📄](archives/s/sqlmap/1.10/) |
| **sqlpage** | 0.44.0 | ✅ 已编译 |  |  | 9 | - | [📄](archives/s/sqlpage/0.44.0/) |
| **squashfs** | 4.7.5 | ✅ 已编译 |  |  | 3 | - | [📄](archives/s/squashfs/4.7.5/) |
| **squashfs-tools** | 4.6.1 | uploaded |  | unknown | 0 | zlib | [📄](archives/s/squashfs-tools/4.6.1/) |
| **squashfs-tools-ng** | 1.3.2 | ✅ 已编译 |  |  | 1 | - | [📄](archives/s/squashfs-tools-ng/1.3.2/) |
| **squid** | 7.3-r0 | unknown |  |  | 1 | name: openssl,name: krb5,name: libxml2,name: libcap,name: nettle... | [📄](archives/s/squid/7.3-r0/) |
| **squirrel-lang** | 3.2 | ✅ 已发布 |  | CMake | 1 | - | [📄](archives/s/squirrel-lang/3.2/) |
| **sratom** | 0.6.22-git | ✅ 已发布 |  |  | - | - | [📄](archives/s/sratom/0.6.22-git/) |
| **srt** | 1.5.5 | ✅ 已编译 |  |  | 1 | - | [📄](archives/s/srt/1.5.5/) |
| **ssh-copy-id** | 9.9p1 | packaged |  | Script | - | openssh-client | [📄](archives/s/ssh-copy-id/9.9p1/) |
| **sshpass** | 1.10 | success |  | Autotools | 2 | [] | [📄](archives/s/sshpass/1.10/) |
| **ssl-cert-check** | 4.14 | ✅ 已编译 |  | custom | 1 | - | [📄](archives/s/ssl-cert-check/4.14/) |
| **ssldump** | 1.9 | ✅ 已编译 |  |  | - | - | [📄](archives/s/ssldump/1.9/) |
| **sslh** | 1.22 | ✅ 已发布 |  |  | 1 | - | [📄](archives/s/sslh/1.22/) |
| **sslmate** | 1.10.0 | ✅ 已发布 |  | Makefile | - | - | [📄](archives/s/sslmate/1.10.0/) |
| **sslscan** | 2.2.0-r0 | ✅ 已编译 |  |  | - | - | [📄](archives/s/sslscan/2.2.0-r0/) |
| **ssmtp** | 2.64 | ✅ 已发布 |  |  | - | - | [📄](archives/s/ssmtp/2.64/) |
| **step** | 25.08.3-r0 | ✅ 已发布 |  | go | - | - | [📄](archives/s/step/25.08.3-r0/) |
| **stlink** | 1.8.0-r1 | ✅ 已编译 |  |  | 7 | [] | [📄](archives/s/stlink/1.8.0-r1/) |
| **stm32flash** | 0.7 | ✅ 已编译 |  |  | 5 | - | [📄](archives/s/stm32flash/0.7/) |
| **stockfish** | 17.1 | ✅ 已发布 |  | Makefile | - | - | [📄](archives/s/stockfish/17.1/) |
| **stormlib** | 9.25 | ✅ 已发布 |  | CMake | - | - | [📄](archives/s/stormlib/9.25/) |
| **strace** | 6.19、6.10 | partial |  | Autotools | 67 | - | [📄](archives/s/strace/6.10/) |
| **streamlink** | 8.4.0 | ✅ 已发布 |  |  | - | - | [📄](archives/s/streamlink/8.4.0/) |
| **stress-ng** | 0.21.01 | ✅ 已编译 |  |  | 11 | musl | [📄](archives/s/stress-ng/0.21.01/) |
| **stunnel** | 5.73 | partial |  | Autotools | - | - | [📄](archives/s/stunnel/5.73/) |
| **stuntman** | 1.2.16 | ✅ 已发布 |  | Makefile | 1 | - | [📄](archives/s/stuntman/1.2.16/) |
| **stylua** | 2.5.2 | ✅ 已编译 |  | custom | 0 | - | [📄](archives/s/stylua/2.5.2/) |
| **subfinder** | homebrew | ✅ 已发布 |  |  | - | - | [📄](archives/s/subfinder/homebrew/) |
| **subversion** | 1.14.5 | ✅ 已发布 |  | Autotools | 4 | - | [📄](archives/s/subversion/1.14.5/) |
| **sundials** | 4.0.0 | ✅ 已编译 |  | CMake | - | - | [📄](archives/s/sundials/4.0.0/) |
| **superfile** | 1.5.0 | ✅ 已编译 |  |  | - | - | [📄](archives/s/superfile/1.5.0/) |
| **superlu** | 5.3.0 | ✅ 已编译 |  |  | 1 | - | [📄](archives/s/superlu/5.3.0/) |
| **surfraw** | 2.3.0 | ✅ 已编译 |  | Autotools | 4 | - | [📄](archives/s/surfraw/2.3.0/) |
| **svgo** | 4.0.1 | ✅ 已编译 |  | npm | 0 | node >=16,npm,rollup | [📄](archives/s/svgo/4.0.1/) |
| **svt-av1** | 4.1.0 | ✅ 已编译 |  |  | - | - | [📄](archives/s/svt-av1/4.1.0/) |
| **swftools** | 0.9.2 | ✅ 已编译 |  | Autotools | 2 | - | [📄](archives/s/swftools/0.9.2/) |
| **swig** | 4.4.0 | uploaded |  | unknown | 0 | - | [📄](archives/s/swig/4.4.0/) |
| **swtpm** | 0.10.1 | ✅ 已发布 |  |  | - | - | [📄](archives/s/swtpm/0.10.1/) |
| **symlinks** | 1.4.3 | ✅ 已发布 |  | Makefile | 2 | - | [📄](archives/s/symlinks/1.4.3/) |
| **sysbench** | 1.0.20 | ✅ 已编译 |  |  | 53 | - | [📄](archives/s/sysbench/1.0.20/) |
| **sysfsutils** | 2.1.0 | uploaded |  | Makefile | 0 | - | [📄](archives/s/sysfsutils/2.1.0/) |
| **sysstat** | 12.7.9 | ✅ 已发布 |  | Autotools | - | - | [📄](archives/s/sysstat/12.7.9/) |
| **systemc** | 2.3.4 | ✅ 已编译 |  |  | - | - | [📄](archives/s/systemc/2.3.4/) |
| **ta-lib** | 0.6.4 | success |  | Autotools | 3 | - | [📄](archives/t/ta-lib/0.6.4/) |
| **taglib** | 2.3 | ✅ 已发布 |  |  | 1 | - | [📄](archives/t/taglib/2.3/) |
| **tailscale** | 1.90.9 | ✅ 已发布 |  |  | - | - | [📄](archives/t/tailscale/1.90.9/) |
| **tailwindcss** | 4.3.0 | ✅ 已编译 |  |  | - | - | [📄](archives/t/tailwindcss/4.3.0/) |
| **talhelper** | 1.17.1 | ✅ 已编译 |  | go | 2 | - | [📄](archives/t/talhelper/1.17.1/) |
| **talloc** | 2.4.4 | ✅ 已编译 |  | waf | 1 | [] | [📄](archives/t/talloc/2.4.4/) |
| **taplo** | 0.10.0 | ✅ 已编译 |  |  | 1 | - | [📄](archives/t/taplo/0.10.0/) |
| **tar** | 1.35 | verified |  | Autotools | 0 | - | [📄](archives/t/tar/1.35/) |
| **task** | 2.6.2 | ✅ 已编译 |  | CMake | - | libuuid (static),ncurses | [📄](archives/t/task/2.6.2/) |
| **taskflow** | 4.0.0 | ✅ 已编译 |  |  | - | - | [📄](archives/t/taskflow/4.0.0/) |
| **taskwarrior-tui** | 0.27.0 | ✅ 已编译 |  |  | - | - | [📄](archives/t/taskwarrior-tui/0.27.0/) |
| **tass64** | 1.60.3243 | ✅ 已发布 |  |  | - | - | [📄](archives/t/tass64/1.60.3243/) |
| **tbb** | 2023.0.0 | ✅ 已编译 |  | CMake | - | - | [📄](archives/t/tbb/2023.0.0/) |
| **tcc** | 0.9.27mob | ✅ 已编译 |  | Autotools | - | - | [📄](archives/t/tcc/0.9.27mob/) |
| **tcl** | 8.6.14、9.0.3.1 | built             |  | autotools  # 标准 conan Autotools（CI 原生 clang） | - | - | [📄](archives/t/tcl/9.0.3.1/) |
| **tcping** | 2.1.0 | ✅ 已编译 |  | Makefile | 1 | - | [📄](archives/t/tcping/2.1.0/) |
| **tcpkali** | 1.1.1 | ✅ 已发布 |  | Autotools | 2 | - | [📄](archives/t/tcpkali/1.1.1/) |
| **tcpstat** | 0.1 | ✅ 已发布 |  | Makefile | 2 | - | [📄](archives/t/tcpstat/0.1/) |
| **tcptrace** | 6.6.7 | ✅ 已发布 |  | Autotools | 8 | - | [📄](archives/t/tcptrace/6.6.7/) |
| **tcptraceroute** | 1.5beta7 | ✅ 已编译 |  |  | 11 | [] | [📄](archives/t/tcptraceroute/1.5beta7/) |
| **tcsh** | 6.24.16 | ✅ 已编译 |  |  | 3 | - | [📄](archives/t/tcsh/6.24.16/) |
| **teal** | 0.24.5 | ✅ 已发布 |  | lua | - | - | [📄](archives/t/teal/0.24.5/) |
| **teem** | 1.11.0 | ✅ 已发布 |  |  | 1 | - | [📄](archives/t/teem/1.11.0/) |
| **teensy_loader_cli** | 2.3 | ✅ 已编译 |  | Makefile | 3 | - | [📄](archives/t/teensy_loader_cli/2.3/) |
| **tenv** | 4.12.2 | ✅ 已发布 |  |  | - | - | [📄](archives/t/tenv/4.12.2/) |
| **terminator** | 2.1.5 | ✅ 已发布 |  |  | - | - | [📄](archives/t/terminator/2.1.5/) |
| **terraform-ls** | v0.38.7 | ✅ 已编译 |  | go | - | [] | [📄](archives/t/terraform-ls/v0.38.7/) |
| **terratag** | 0.7.6 | ✅ 已发布 |  | go | - | - | [📄](archives/t/terratag/0.7.6/) |
| **tesseract** | 5.3.3 | success |  |  | 1 | leptonica | [📄](archives/t/tesseract/5.3.3/) |
| **testdisk** | 7.1 | ✅ 已编译 |  |  | 4 | - | [📄](archives/t/testdisk/7.1/) |
| **testssl** | 3.2.3 | uploaded |  | unknown | 0 | - | [📄](archives/t/testssl/3.2.3/) |
| **texinfo** | 7.3 | verified |  | Autotools | 0 | - | [📄](archives/t/texinfo/7.3/) |
| **tf-summarize** | v0.3.20 | ✅ 已编译 |  | go | - | [] | [📄](archives/t/tf-summarize/v0.3.20/) |
| **tfel** | 5.2 | ✅ 已编译 |  |  | - | - | [📄](archives/t/tfel/5.2/) |
| **tftp-hpa** | 5.2 | ✅ 已发布 |  |  | - | - | [📄](archives/t/tftp-hpa/5.2/) |
| **tgenv** | latest | ✅ 已发布 |  |  | - | - | [📄](archives/t/tgenv/latest/) |
| **the_silver_searcher** | 2.2.0 | ✅ 已编译 |  | Autotools | 1 | - | [📄](archives/t/the_silver_searcher/2.2.0/) |
| **thrift** | 0.23.0 | ✅ 已编译 |  |  | - | - | [📄](archives/t/thrift/0.23.0/) |
| **thttpd** | 2.29 | ✅ 已发布 |  |  | - | - | [📄](archives/t/thttpd/2.29/) |
| **tidy-html5** | 5.8.0 | ✅ 已发布 |  | CMake | 1 | - | [📄](archives/t/tidy-html5/5.8.0/) |
| **tig** | 2.6.0 | ✅ 已编译 |  | Autotools | 1 | - | [📄](archives/t/tig/2.6.0/) |
| **time** | 1.9 | ✅ 已发布 |  |  | 1 | - | [📄](archives/t/time/1.9/) |
| **timescaledb** | 2.27.2 | ✅ 已编译 |  |  | 3 | - | [📄](archives/t/timescaledb/2.27.2/) |
| **timewarrior** | 1.9.1 | ✅ 已编译 |  | CMake | - | - | [📄](archives/t/timewarrior/1.9.1/) |
| **timg** | 1.6.3 | ✅ 已编译 |  | CMake | - | - | [📄](archives/t/timg/1.6.3/) |
| **timidity** | 2.13.2 | ✅ 已发布 |  | Autotools | 2 | libc.so (musl) | [📄](archives/t/timidity/2.13.2/) |
| **tin** | 2.6.4 | ✅ 已编译 |  | Autotools | 3 | - | [📄](archives/t/tin/2.6.4/) |
| **tinc-pre** | 1.1.18-r2 | ✅ 已编译 |  |  | - | - | [📄](archives/t/tinc-pre/1.1.18-r2/) |
| **tini** | 0.19.0 | ✅ 已发布 |  |  | 2 | - | [📄](archives/t/tini/0.19.0/) |
| **tinycdb** | 0.81 | ✅ 已发布 |  | Makefile | - | - | [📄](archives/t/tinycdb/0.81/) |
| **tinymist** | 0.12.2 | ✅ 已编译 |  |  | - | - | [📄](archives/t/tinymist/0.12.2/) |
| **tinyproxy** | 1.11.2、1.11.3 | ✅ 已发布 |  | Autotools | 5 | - | [📄](archives/t/tinyproxy/1.11.3/) |
| **tinyssh** | 20260401 | uploaded |  | unknown | 0 | - | [📄](archives/t/tinyssh/20260401/) |
| **tinytoml** | 0.4.0 | ✅ 已发布 |  | CMake | 2 | - | [📄](archives/t/tinytoml/0.4.0/) |
| **tinyxml** | 2.6.2 | ✅ 已发布 |  |  | - | [] | [📄](archives/t/tinyxml/2.6.2/) |
| **tinyxml2** | 10.0.0 | ✅ 已发布 |  | CMake | - | - | [📄](archives/t/tinyxml2/10.0.0/) |
| **tio** | 3.9-r0 | ✅ 已编译 |  |  | - | [] | [📄](archives/t/tio/3.9-r0/) |
| **tipidee** | 0.0.6.0 | ✅ 已发布 |  |  | - | - | [📄](archives/t/tipidee/0.0.6.0/) |
| **tk** | 9.0.3.1 | built             |  | autotools  # 标准 conan Autotools（CI 原生 clang） | - | - | [📄](archives/t/tk/9.0.3.1/) |
| **tlx** | 0.6.1 | ✅ 已发布 |  | CMake | 1 | - | [📄](archives/t/tlx/0.6.1/) |
| **tmux** | 3.4 | ✅ 已发布 |  |  | 6 | - | [📄](archives/t/tmux/3.4/) |
| **tnftp** | 20260211 | ✅ 已发布 |  | Autotools | 5 | - | [📄](archives/t/tnftp/20260211/) |
| **tofrodos** | 1.8.3 | ✅ 已编译 |  |  | - | - | [📄](archives/t/tofrodos/1.8.3/) |
| **tokay** | 0.6.13 | ✅ 已编译 |  |  | - | - | [📄](archives/t/tokay/0.6.13/) |
| **tokyo-cabinet** | 1.4.48 | unknown |  |  | 1 | - | [📄](archives/t/tokyo-cabinet/1.4.48/) |
| **toml11** | 4.4.0 | ✅ 已编译 |  | CMake | - | - | [📄](archives/t/toml11/4.4.0/) |
| **tomlplusplus** | 3.4.0 | uploaded |  | CMake | 0 | - | [📄](archives/t/tomlplusplus/3.4.0/) |
| **tpix** | 1.0.3 | ✅ 已发布 |  | custom | - | - | [📄](archives/t/tpix/1.0.3/) |
| **traceroute** | 2.1.6 | ✅ 已编译 |  | Makefile | 1 | - | [📄](archives/t/traceroute/2.1.6/) |
| **tre** | 0.9.0 | ✅ 已发布 |  | Autotools | 2 | - | [📄](archives/t/tre/0.9.0/) |
| **tree** | 2.1.3 | uploaded |  | Makefile | 0 | - | [📄](archives/t/tree/2.1.3/) |
| **tree-sitter** | 0.25 | ✅ 已发布 |  |  | - | - | [📄](archives/t/tree-sitter/0.25/) |
| **tree-sitter-go** | 0.25.0 | ✅ 已编译 |  | make | - | [] | [📄](archives/t/tree-sitter-go/0.25.0/) |
| **tree-sitter-python** | 0.23.6 | ✅ 已发布 |  | CMake | - | - | [📄](archives/t/tree-sitter-python/0.23.6/) |
| **triehash** | 0.3 | uploaded |  | CMake | 0 | - | [📄](archives/t/triehash/0.3/) |
| **ttaenc** | 3.4.1 | uploaded |  | unknown | 0 | - | [📄](archives/t/ttaenc/3.4.1/) |
| **tty-clock** | 2.3 | ✅ 已发布 |  | Makefile | 1 | - | [📄](archives/t/tty-clock/2.3/) |
| **ttyplot** | 1.7.1 | ✅ 已发布 |  | Makefile | - | - | [📄](archives/t/ttyplot/1.7.1/) |
| **ttyrec** | 1.0.8 | ✅ 已编译 |  | Makefile | 1 | - | [📄](archives/t/ttyrec/1.0.8/) |
| **turbo** | 2.1.2 | ✅ 已编译 |  | Makefile | 2 | - | [📄](archives/t/turbo/2.1.2/) |
| **txr** | 302 | ✅ 已编译 |  | configure | - | - | [📄](archives/t/txr/302/) |
| **txt2man** | 1.7.1 | ✅ 已编译 |  | Makefile | 1 | - | [📄](archives/t/txt2man/1.7.1/) |
| **ty** | 0.0.40 | ✅ 已编译 |  | cargo | - | - | [📄](archives/t/ty/0.0.40/) |
| **uSockets** | 0.7.1 | ✅ 已编译 |  | Makefile | - | - | [📄](archives/u/uSockets/0.7.1/) |
| **uWebSockets** | 18 | ✅ 已编译 |  | Makefile | - | - | [📄](archives/u/uWebSockets/18/) |
| **ubertooth** | 2020-12-R1 | ✅ 已编译 |  | CMake | - | - | [📄](archives/u/ubertooth/2020-12-R1/) |
| **uchardet** | 0.0.7 | ✅ 已编译 |  |  | - | - | [📄](archives/u/uchardet/0.0.7/) |
| **ucl** | 1.03 | uploaded |  | unknown | 0 | - | [📄](archives/u/ucl/1.03/) |
| **ucon64** | 2.2.2 | ✅ 已发布 |  |  | 4 | - | [📄](archives/u/ucon64/2.2.2/) |
| **ucpp** | 1.3.5 | ✅ 已编译 |  | Autotools | 2 | - | [📄](archives/u/ucpp/1.3.5/) |
| **udpping** | 0.0.2 | ✅ 已编译 |  | CMake | 2 | - | [📄](archives/u/udpping/0.0.2/) |
| **udunits** | 2.2.28 | ✅ 已发布 |  | Autotools | 2 | - | [📄](archives/u/udunits/2.2.28/) |
| **ugrep** | 7.8.2 | ✅ 已发布 |  | Autotools | 2 | - | [📄](archives/u/ugrep/7.8.2/) |
| **umka-lang** | 1.5.5 | ✅ 已发布 |  |  | - | - | [📄](archives/u/umka-lang/1.5.5/) |
| **unac** | 1.8.0 | ✅ 已发布 |  | Autotools | - | - | [📄](archives/u/unac/1.8.0/) |
| **unarj** | 2.63a | uploaded |  | unknown | 0 | - | [📄](archives/u/unarj/2.63a/) |
| **unbound** | 1.22.0 | ✅ 已编译 |  |  | 3 | - | [📄](archives/u/unbound/1.22.0/) |
| **unixodbc** | 2.3.12 | ✅ 已编译 |  |  | 6 | - | [📄](archives/u/unixodbc/2.3.12/) |
| **unrar** | 6.2.4 | compiling |  | Makefile | 2 | - | [📄](archives/u/unrar/6.2.4/) |
| **unudhcpd** | 0.2.1-r2 | ✅ 已编译 |  |  | - | - | [📄](archives/u/unudhcpd/0.2.1-r2/) |
| **unzip** | 6.0 | ✅ 已发布 |  | Makefile | 1 | - | [📄](archives/u/unzip/6.0/) |
| **upower** | 0.99.20 | ✅ 已编译 |  | Meson | - | glib-2.0 >= 2.58,gobject-2.0 >= 2.58,gio-2.0 >= 2.58,gio-unix-2.0 >= 2.58,gudev-1.0 >= 235... | [📄](archives/u/upower/0.99.20/) |
| **upx** | 5.1.1 | success |  | CMake | - | - | [📄](archives/u/upx/5.1.1/) |
| **urlview-ng** | 1e | ✅ 已编译 |  |  | 5 | - | [📄](archives/u/urlview-ng/1e/) |
| **usage** | 3.4.0 | ✅ 已发布 |  | custom | - | rust/1.95.0,cargo/1.95.0 | [📄](archives/u/usage/3.4.0/) |
| **usbredir** | 0.15.0 | ✅ 已编译 |  |  | - | - | [📄](archives/u/usbredir/0.15.0/) |
| **usbutils** | 017 | uploaded |  | Makefile | 0 | - | [📄](archives/u/usbutils/017/) |
| **userspace-rcu** | 0.15.6 | success |  | Autotools | 1 | - | [📄](archives/u/userspace-rcu/0.15.6/) |
| **ustream-ssl** | 20260222-r0 | ✅ 已编译 |  |  | 2 | - | [📄](archives/u/ustream-ssl/20260222-r0/) |
| **utf8cpp** | 4.1.1 | ✅ 已编译 |  | CMake | - | - | [📄](archives/u/utf8cpp/4.1.1/) |
| **utf8proc** | 2.11.3、2.9.0 | uploaded |  | CMake | 0 | - | [📄](archives/u/utf8proc/2.9.0/) |
| **utftex** | 1.31 | ✅ 已发布 |  | Autotools | 6 | - | [📄](archives/u/utftex/1.31/) |
| **uthash** | 2.3.0 | uploaded |  | CMake | 0 | - | [📄](archives/u/uthash/2.3.0/) |
| **util-linux** | 2.39 | ✅ 已编译 |  |  | 3 | - | [📄](archives/u/util-linux/2.39/) |
| **uuid** | 2.40 | ✅ 已编译 |  | Autotools | 10 | - | [📄](archives/u/uuid/2.40/) |
| **uvicorn** | 0.49.0 | ✅ 已编译 |  |  | - | - | [📄](archives/u/uvicorn/0.49.0/) |
| **uwsgi** | 2.0.24 | ✅ 已发布 |  |  | 4 | - | [📄](archives/u/uwsgi/2.0.24/) |
| **v2ray** | 5.37.0 | ✅ 已发布 |  | go | - | go-runtime | [📄](archives/v/v2ray/5.37.0/) |
| **vala** | 0.56.18 | uploaded |  | Meson | 0 | - | [📄](archives/v/vala/0.56.18/) |
| **valijson** | 1.1.1 | ✅ 已发布 |  |  | 2 | - | [📄](archives/v/valijson/1.1.1/) |
| **vampire** | 5.0.1 | ✅ 已发布 |  |  | - | - | [📄](archives/v/vampire/5.0.1/) |
| **varnish** | 7.5.0 | ✅ 已编译 |  | Autotools | 3 | - | [📄](archives/v/varnish/7.5.0/) |
| **vde2** | 2.3.3 | ✅ 已发布 |  |  | - | - | [📄](archives/v/vde2/2.3.3/) |
| **vectorscan** | 5.4.12 | ✅ 已编译 |  | CMake | - | - | [📄](archives/v/vectorscan/5.4.12/) |
| **velero** | 1.14.0 | ✅ 已发布 |  |  | - | - | [📄](archives/v/velero/1.14.0/) |
| **verapdf** | 1.30.1 | ✅ 已编译 |  |  | - | - | [📄](archives/v/verapdf/1.30.1/) |
| **verilator** | 5.046 | ✅ 已编译 |  | Autotools | 3 | - | [📄](archives/v/verilator/5.046/) |
| **video-compare** | 20260502 | ✅ 已编译 |  |  | - | - | [📄](archives/v/video-compare/20260502/) |
| **vifm** | 0.14.3 | ✅ 已发布 |  | Autotools | 6 | - | [📄](archives/v/vifm/0.14.3/) |
| **vim** | 9.1.1000 | ✅ 已编译 |  | Autotools | 6 | - | [📄](archives/v/vim/9.1.1000/) |
| **vips** | 8.14.1、8.18.2 | ✅ 已编译 |  | Meson | 5 | - | [📄](archives/v/vips/8.18.2/) |
| **virtualenvwrapper** | 6.1.1 | ✅ 已发布 |  | python_wheel | - | - | [📄](archives/v/virtualenvwrapper/6.1.1/) |
| **vis** | 0.9 | ✅ 已编译 |  | configure | - | name: libtermkey,name: unibilium | [📄](archives/v/vis/0.9/) |
| **visp** | 3.7.0 | ✅ 已编译 |  | CMake | 2 | - | [📄](archives/v/visp/3.7.0/) |
| **vitetris** | 0.59、0.59.1 | ✅ 已发布 |  | Makefile | 3 | - | [📄](archives/v/vitetris/0.59.1/) |
| **viu** | v1.6.1 | ✅ 已编译 |  | cargo | - | - | [📄](archives/v/viu/v1.6.1/) |
| **vkmark** | 2025.01 | ✅ 已编译 |  | Meson | - | - | [📄](archives/v/vkmark/2025.01/) |
| **vmdktool** | 1.4 | ✅ 已发布 |  |  | 1 | - | [📄](archives/v/vmdktool/1.4/) |
| **vmtouch** | 1.3.1 | ✅ 已发布 |  | Makefile | - | - | [📄](archives/v/vmtouch/1.3.1/) |
| **vnstat** | 2.13 | ✅ 已编译 |  |  | 2 | - | [📄](archives/v/vnstat/2.13/) |
| **volk** | 1.4.350、3.3.0 | ✅ 已编译 |  | CMake | - | - | [📄](archives/v/volk/3.3.0/) |
| **volta** | 2.0.2 | ✅ 已编译 |  |  | - | - | [📄](archives/v/volta/2.0.2/) |
| **vorbis-tools** | 1.4.2 | ✅ 已编译 |  | Autotools | 3 | - | [📄](archives/v/vorbis-tools/1.4.2/) |
| **vpnc** | 0.5.3 | ✅ 已发布 |  |  | - | - | [📄](archives/v/vpnc/0.5.3/) |
| **vsearch** | 2.30.5 | ✅ 已发布 |  | Autotools | - | - | [📄](archives/v/vsearch/2.30.5/) |
| **vtk** | 9.4.1 | ✅ 已编译 |  |  | - | - | [📄](archives/v/vtk/9.4.1/) |
| **vtsls** | 0.3.0 | ✅ 已发布 |  |  | - | - | [📄](archives/v/vtsls/0.3.0/) |
| **vulkan-extensionlayer** | 1.4.350 | ✅ 已编译 |  | CMake | 1 | VulkanHeaders vulkan-sdk-1.4.350.0,VulkanUtilityLibraries vulkan-sdk-1.4.350.0,VulkanVolk 1.4.350 | [📄](archives/v/vulkan-extensionlayer/1.4.350/) |
| **vulkan-headers** | 1.3.295 | partial |  | Autotools | 1 | - | [📄](archives/v/vulkan-headers/1.3.295/) |
| **vulkan-loader** | 1.3.295 | ✅ 已编译 |  | CMake | 1 | vulkan-headers/1.3.295 | [📄](archives/v/vulkan-loader/1.3.295/) |
| **vulkan-tools** | 1.3.290 | ✅ 已发布 |  |  | - | - | [📄](archives/v/vulkan-tools/1.3.290/) |
| **vulkan-utility-libraries** | vulkan-sdk-1.4.350.0 | ✅ 已编译 |  |  | - | - | [📄](archives/v/vulkan-utility-libraries/vulkan-sdk-1.4.350.0/) |
| **vulkan-validationlayers** | vulkan-sdk-1.4.350.0 | ✅ 已发布 |  | CMake | - | - | [📄](archives/v/vulkan-validationlayers/vulkan-sdk-1.4.350.0/) |
| **vulkan-volk** | 1.4.350 | ✅ 已编译 |  | CMake | 2 | VulkanHeaders vulkan-sdk-1.4.350.0 | [📄](archives/v/vulkan-volk/1.4.350/) |
| **vvdec** | 3.1.0 | ✅ 已发布 |  | CMake | 1 | - | [📄](archives/v/vvdec/3.1.0/) |
| **w3m** | 0.5.3 | ✅ 已发布 |  |  | 40 | - | [📄](archives/w/w3m/0.5.3/) |
| **wabt** | 1.0.41 | ✅ 已编译 |  | CMake | - | - | [📄](archives/w/wabt/1.0.41/) |
| **waf** | 2.1.9 | uploaded |  | custom | 0 | - | [📄](archives/w/waf/2.1.9/) |
| **wait4ports** | 0.3.3-r1 | ✅ 已编译 |  |  | - | - | [📄](archives/w/wait4ports/0.3.3-r1/) |
| **wakeonlan** | 0.42 | ✅ 已发布 |  | Custom Perl | - | - | [📄](archives/w/wakeonlan/0.42/) |
| **wal2json** | 2.6 | ✅ 已发布 |  | custom | - | - | [📄](archives/w/wal2json/2.6/) |
| **wangle** | v2026.05.18.00 | ✅ 已编译 |  | CMake | 1 | - | [📄](archives/w/wangle/v2026.05.18.00/) |
| **wasm-micro-runtime** | 2.4.4 | ✅ 已编译 |  | CMake | - | - | [📄](archives/w/wasm-micro-runtime/2.4.4/) |
| **wasmtime** | 45.0.0 | ✅ 已编译 |  |  | - | - | [📄](archives/w/wasmtime/45.0.0/) |
| **watchdog** | 5.16 | success |  | Autotools | - | - | [📄](archives/w/watchdog/5.16/) |
| **watcher** | 0.14.5 | ✅ 已发布 |  | CMake | 1 | - | [📄](archives/w/watcher/0.14.5/) |
| **watchexec** | 2.3.2-r0 | ✅ 已发布 |  | prebuilt-musl | - | - | [📄](archives/w/watchexec/2.3.2-r0/) |
| **wavemon** | 0.9.6 | ✅ 已发布 |  |  | 13 | - | [📄](archives/w/wavemon/0.9.6/) |
| **wavpack** | 5.7.0、5.8.1 | uploaded |  | unknown | 0 | - | [📄](archives/w/wavpack/5.8.1/) |
| **wayland-protocols** | 1.27 | ✅ 已发布 |  |  | - | - | [📄](archives/w/wayland-protocols/1.27/) |
| **wcslib** | 8.4 | ✅ 已编译 |  |  | 4 | - | [📄](archives/w/wcslib/8.4/) |
| **weasyprint** | 68.1 | ✅ 已编译 |  |  | - | - | [📄](archives/w/weasyprint/68.1/) |
| **webalizer** | 2.23.08 | ✅ 已编译 |  | Autotools | - | - | [📄](archives/w/webalizer/2.23.08/) |
| **webp-pixbuf-loader** | 0.2.7 | ✅ 已编译 |  | Meson | - | - | [📄](archives/w/webp-pixbuf-loader/0.2.7/) |
| **webrtc-audio-processing-1** | 1.3 | ✅ 已编译 |  | Meson | 1 | - | [📄](archives/w/webrtc-audio-processing-1/1.3/) |
| **webrtc-audio-processing-2** | 2.1 | ✅ 已编译 |  | Meson | 1 | - | [📄](archives/w/webrtc-audio-processing-2/2.1/) |
| **websocketpp** | 0.8.2 | ✅ 已发布 |  | CMake | - | - | [📄](archives/w/websocketpp/0.8.2/) |
| **weex** | 2.8.4.4-r0 | ✅ 已编译 |  |  | - | - | [📄](archives/w/weex/2.8.4.4-r0/) |
| **wget** | 1.19.1 | verified |  | Autotools | 0 | - | [📄](archives/w/wget/1.19.1/) |
| **wget2** | 2.2.0-r1 | ✅ 已编译 |  |  | 2 | - | [📄](archives/w/wget2/2.2.0-r1/) |
| **wgetpaste** | 2.34-r0 | ✅ 已编译 |  |  | - | - | [📄](archives/w/wgetpaste/2.34-r0/) |
| **when** | 1.1.45 | ✅ 已发布 |  | Makefile | 1 | - | [📄](archives/w/when/1.1.45/) |
| **which** | 2.21 | partial |  | Autotools | 2 | - | [📄](archives/w/which/2.21/) |
| **whois** | 5.6.6 | ✅ 已编译 |  |  | - | - | [📄](archives/w/whois/5.6.6/) |
| **whosthere** | v0.0.0-20260612222631 | ✅ 已编译 |  | go | - | [] | [📄](archives/w/whosthere/v0.0.0-20260612222631/) |
| **wiiuse** | 0.15.7 | ✅ 已编译 |  | CMake | 5 | - | [📄](archives/w/wiiuse/0.15.7/) |
| **wimlib** | 1.14.5 | uploaded |  | unknown | 0 | - | [📄](archives/w/wimlib/1.14.5/) |
| **wireguard-tools** | 1.0.20250521 | ✅ 已发布 |  | Makefile | 1 | - | [📄](archives/w/wireguard-tools/1.0.20250521/) |
| **wireless-regdb** | 2026.05.30 | ✅ 已发布 |  |  | - | - | [📄](archives/w/wireless-regdb/2026.05.30/) |
| **wireshark** | 4.4.16 | ❌ 编译失败 |  | CMake | - | glib/2.x (>= 2.50.0),libpcap/x.x,libgcrypt/x.x,cmake/3.5+,python3/x.x... | [📄](archives/w/wireshark/4.4.16/) |
| **wla-dx** | 10.6 | ✅ 已发布 |  |  | - | - | [📄](archives/w/wla-dx/10.6/) |
| **woff2** | 1.0.2 | ✅ 已编译 |  | CMake | 1 | - | [📄](archives/w/woff2/1.0.2/) |
| **wolfssl** | 5.9.0 | ✅ 已发布 |  | Autotools | - | - | [📄](archives/w/wolfssl/5.9.0/) |
| **woodpecker-cli** | 3.15.0 | ✅ 已编译 |  |  | - | - | [📄](archives/w/woodpecker-cli/3.15.0/) |
| **wpa_supplicant** | 2.11 | ✅ 已发布 |  |  | - | - | [📄](archives/w/wpa_supplicant/2.11/) |
| **wrk** | 4.2.0 | ✅ 已编译 |  |  | - | - | [📄](archives/w/wrk/4.2.0/) |
| **wxWidgets** | 3.2.6 | ✅ 已发布 |  |  | 1 | - | [📄](archives/w/wxWidgets/3.2.6/) |
| **wys** | 0.1.12 | ✅ 已编译 |  | Meson | - | - | [📄](archives/w/wys/0.1.12/) |
| **x264** | master、r3190 | ✅ 已发布 |  | Autotools | 3 | - | [📄](archives/x/x264/r3190/) |
| **x265** | 4.2 | ✅ 已编译 |  |  | - | - | [📄](archives/x/x265/4.2/) |
| **x2goserver** | 4.1.0.6 | ✅ 已编译 |  | Autotools | - | - | [📄](archives/x/x2goserver/4.1.0.6/) |
| **xapian-core** | 2.0.0 | ✅ 已发布 |  |  | - | - | [📄](archives/x/xapian-core/2.0.0/) |
| **xboard** | 4.9.1 | ✅ 已编译 |  | Autotools | 4 | - | [📄](archives/x/xboard/4.9.1/) |
| **xcaddy** | 0.4.5-r0 | ✅ 已编译 |  |  | - | - | [📄](archives/x/xcaddy/0.4.5-r0/) |
| **xcb-util-image** | 0.4.1 | ✅ 已编译 |  |  | 2 | - | [📄](archives/x/xcb-util-image/0.4.1/) |
| **xcb-util-renderutil** | 0.3.10 | ✅ 已编译 |  |  | 9 | - | [📄](archives/x/xcb-util-renderutil/0.3.10/) |
| **xclip** | 0.13 | ✅ 已编译 |  |  | 2 | - | [📄](archives/x/xclip/0.13/) |
| **xcur2png** | 0.7.1 | ✅ 已编译 |  | Autotools | 8 | - | [📄](archives/x/xcur2png/0.7.1/) |
| **xcursorgen** | 1.0.9 | ✅ 已编译 |  | Autotools | - | - | [📄](archives/x/xcursorgen/1.0.9/) |
| **xdg-dbus-proxy** | 0.1.7 | ✅ 已发布 |  |  | - | - | [📄](archives/x/xdg-dbus-proxy/0.1.7/) |
| **xf86-video-amdgpu** | 23.0.0 | unknown |  | Autotools | - | xorg-server >= 21.1.15,libdrm >= 2.4.133,libdrm_amdgpu >= 2.4.133,gbm (stub),xproto >= 7.0.33... | [📄](archives/x/xf86-video-amdgpu/23.0.0/) |
| **xf86-video-ati** | 22.0.0 | ✅ 已编译 |  | Autotools | 29 | - | [📄](archives/x/xf86-video-ati/22.0.0/) |
| **xf86-video-dummy** | 0.4.1 | unknown |  | Autotools | - | xorg-server >= 21.1.15,pixman-1 >= 0.46.4,xproto >= 7.0.31,randrproto >= 1.6.0,renderproto >= 0.11.1 | [📄](archives/x/xf86-video-dummy/0.4.1/) |
| **xf86-video-fbdev** | 0.5.1 | unknown |  | Autotools | - | xorg-server >= 21.1.15,pixman-1 >= 0.46.4 | [📄](archives/x/xf86-video-fbdev/0.5.1/) |
| **xf86-video-nouveau** | 1.0.18 | ✅ 已编译 |  | Autotools | - | - | [📄](archives/x/xf86-video-nouveau/1.0.18/) |
| **xf86-video-nv** | 2.1.24 | unknown |  | Autotools | - | xorg-server >= 21.1.15,pixman-1 >= 0.46.4,xproto >= 7.0.31,randrproto >= 1.6.0,renderproto >= 0.11.1... | [📄](archives/x/xf86-video-nv/2.1.24/) |
| **xf86-video-r128** | 6.13.0 | ✅ 已编译 |  | Autotools | 4 | - | [📄](archives/x/xf86-video-r128/6.13.0/) |
| **xf86-video-savage** | 2.4.1 | ✅ 已编译 |  | Autotools | 5 | - | [📄](archives/x/xf86-video-savage/2.4.1/) |
| **xfce4-pulseaudio-plugin** | 0.5.1 | ✅ 已编译 |  | Autotools | 33 | - | [📄](archives/x/xfce4-pulseaudio-plugin/0.5.1/) |
| **xinit** | 1.4.4 | ✅ 已编译 |  | Autotools | 3 | - | [📄](archives/x/xinit/1.4.4/) |
| **xkbcomp** | 1.4.7 | ✅ 已编译 |  |  | 7 | - | [📄](archives/x/xkbcomp/1.4.7/) |
| **xmake** | 3.0.5 | ✅ 已编译 |  |  | - | - | [📄](archives/x/xmake/3.0.5/) |
| **xmlrpc-c** | 1.64.03 | ✅ 已编译 |  | Autotools | 2 | - | [📄](archives/x/xmlrpc-c/1.64.03/) |
| **xmlsec1** | 1.3.11 | ✅ 已编译 |  | Autotools | 8 | libxml2/2.11.9,libxslt/1.1.39,openssl/1.1.1w | [📄](archives/x/xmlsec1/1.3.11/) |
| **xmlstarlet** | 1.6.1 | ✅ 已编译 |  | Autotools | - | libxml2 >= 2.15.0,libxslt >= 1.1.42,clang,libxml2-dev,libxslt-dev | [📄](archives/x/xmlstarlet/1.6.1/) |
| **xmltoman** | 0.4 | ✅ 已发布 |  | Makefile | 2 | - | [📄](archives/x/xmltoman/0.4/) |
| **xmq** | 4.2.0 | ✅ 已发布 |  | Autotools | 3 | - | [📄](archives/x/xmq/4.2.0/) |
| **xonsh** | 0.19.2 | ✅ 已编译 |  | python | - | - | [📄](archives/x/xonsh/0.19.2/) |
| **xorg-server** | 21.1.14、21.1.15 | ✅ 已发布 |  |  | - | - | [📄](archives/x/xorg-server/21.1.15/) |
| **xorgproto** | 2024.1 | success |  | Meson | 2 | [] | [📄](archives/x/xorgproto/2024.1/) |
| **xorgrgb** | 1.1.1 | ✅ 已发布 |  | Autotools | 1 | - | [📄](archives/x/xorgrgb/1.1.1/) |
| **xorriso** | 1.5.8.pl02 | ✅ 已发布 |  |  | 4 | - | [📄](archives/x/xorriso/1.5.8.pl02/) |
| **xournalpp** | 1.3.4 | ✅ 已编译 |  | CMake | 6 | - | [📄](archives/x/xournalpp/1.3.4/) |
| **xplanet** | 1.3.0 | ✅ 已编译 |  | Autotools | 10 | - | [📄](archives/x/xplanet/1.3.0/) |
| **xq** | 1.3.0 | ✅ 已发布 |  | custom | - | - | [📄](archives/x/xq/1.3.0/) |
| **xray** | homebrew | ✅ 已发布 |  |  | - | - | [📄](archives/x/xray/homebrew/) |
| **xrdb** | 1.2.2 | ✅ 已发布 |  |  | 4 | - | [📄](archives/x/xrdb/1.2.2/) |
| **xsimd** | 13.0.0 | ✅ 已发布 |  | CMake | - | - | [📄](archives/x/xsimd/13.0.0/) |
| **xterm** | 410 | ✅ 已编译 |  |  | 5 | - | [📄](archives/x/xterm/410/) |
| **xvidcore** | 1.3.7 | ✅ 已编译 |  | Autotools | 4 | - | [📄](archives/x/xvidcore/1.3.7/) |
| **xvinfo** | 1.1.5 | ✅ 已编译 |  | Autotools | 3 | - | [📄](archives/x/xvinfo/1.1.5/) |
| **xwayland** | 24.1 | ✅ 已发布 |  |  | - | - | [📄](archives/x/xwayland/24.1/) |
| **xwd** | 1.0.9 | ✅ 已编译 |  |  | 2 | - | [📄](archives/x/xwd/1.0.9/) |
| **xxd** | 9.1.0 | success |  | simple_makefile | - | - | [📄](archives/x/xxd/9.1.0/) |
| **xxhash** | 0.8.3、0.8.2 | partial |  | Autotools | - | - | [📄](archives/x/xxhash/0.8.2/) |
| **xz** | 5.6.2、5.2.3 | ✅ 已发布 |  | Autotools | 3 | - | [📄](archives/x/xz/5.2.3/) |
| **yad** | 14.2 | ✅ 已编译 |  | Autotools | 7 | - | [📄](archives/y/yad/14.2/) |
| **yajl** | 2.1.0 | success |  | CMake | 2 | - | [📄](archives/y/yajl/2.1.0/) |
| **yaml-cpp** | 0.8.0 | uploaded |  | CMake | 0 | - | [📄](archives/y/yaml-cpp/0.8.0/) |
| **yamlfmt** | 0.21.0 | ✅ 已编译 |  | custom | - | - | [📄](archives/y/yamlfmt/0.21.0/) |
| **yamllint** | 1.37.1 | ✅ 已编译 |  | custom | 2 | - | [📄](archives/y/yamllint/1.37.1/) |
| **yara** | 4.5.5 | ✅ 已编译 |  | Autotools | 11 | - | [📄](archives/y/yara/4.5.5/) |
| **yasm** | 1.3.0、1.3.0-r4 | ✅ 已编译 |  | Autotools | 2 | - | [📄](archives/y/yasm/1.3.0-r4/) |
| **yazi** | 26.5.6 | ✅ 已发布 |  |  | 3 | - | [📄](archives/y/yazi/26.5.6/) |
| **yj** | 5.1.0 | ✅ 已编译 |  | custom | 0 | - | [📄](archives/y/yj/5.1.0/) |
| **ykpers** | 1.20.0 | ✅ 已编译 |  | Autotools | 2 | - | [📄](archives/y/ykpers/1.20.0/) |
| **yt-dlp** | 2026.03.17 | ✅ 已发布 |  | python-zipapp | 0 | python>=3.10 | [📄](archives/y/yt-dlp/2026.03.17/) |
| **ytfzf** | 2.6.2 | ✅ 已编译 |  | Makefile | - | - | [📄](archives/y/ytfzf/2.6.2/) |
| **yyjson** | 0.12.0 | uploaded |  | CMake | 0 | - | [📄](archives/y/yyjson/0.12.0/) |
| **z3** | 4.15.4 | ✅ 已编译 |  | CMake | - | - | [📄](archives/z/z3/4.15.4/) |
| **zam-plugins** | 4.5 | ✅ 已编译 |  | Makefile | 29 | - | [📄](archives/z/zam-plugins/4.5/) |
| **zathura-pdf-mupdf** | 2026.05.10 | ✅ 已编译 |  | Meson | - | - | [📄](archives/z/zathura-pdf-mupdf/2026.05.10/) |
| **zathura-pdf-poppler** | 0.3.4 | ✅ 已编译 |  | Meson | - | - | [📄](archives/z/zathura-pdf-poppler/0.3.4/) |
| **zenity** | 4.2.2 | ✅ 已编译 |  |  | - | - | [📄](archives/z/zenity/4.2.2/) |
| **zeromq** | 4.3.5 | uploaded |  | unknown | 0 | - | [📄](archives/z/zeromq/4.3.5/) |
| **zimg** | 3.0.6 | ✅ 已编译 |  | Autotools | - | [] | [📄](archives/z/zimg/3.0.6/) |
| **zint** | 2.16.0 | ✅ 已编译 |  |  | 1 | - | [📄](archives/z/zint/2.16.0/) |
| **zip** | 3.0 | partial |  | Makefile | 1 | - | [📄](archives/z/zip/3.0/) |
| **zix** | 0.8.1-git | ✅ 已发布 |  |  | - | - | [📄](archives/z/zix/0.8.1-git/) |
| **zlib** | 1.3.1、1.3.1.1 | ✅ 已编译 |  |  | - | - | [📄](archives/z/zlib/1.3.1.1/) |
| **zlib-ng** | 2.3.3 | uploaded |  | unknown | 0 | - | [📄](archives/z/zlib-ng/2.3.3/) |
| **zlib-ng-compat** | 2.3.3 | uploaded |  | unknown | 0 | - | [📄](archives/z/zlib-ng-compat/2.3.3/) |
| **zmap** | 4.4.0 | ✅ 已发布 |  | CMake | 4 | cmake,gmp/6.3.0,gengetopt/2.23,libpcap/1.10.6,flex... | [📄](archives/z/zmap/4.4.0/) |
| **znc** | 1.10.2 | ✅ 已编译 |  | CMake | 3 | - | [📄](archives/z/znc/1.10.2/) |
| **zola** | 0.19.2 | ✅ 已编译 |  |  | 2 | - | [📄](archives/z/zola/0.19.2/) |
| **zoneminder** | 1.38.3 | ✅ 已编译 |  | CMake | 12 | - | [📄](archives/z/zoneminder/1.38.3/) |
| **zonenotify** | 0.1 | ✅ 已发布 |  |  | - | - | [📄](archives/z/zonenotify/0.1/) |
| **zopfli** | 1.0.3 | uploaded |  | unknown | 0 | - | [📄](archives/z/zopfli/1.0.3/) |
| **zsh** | 5.9 | partial |  | Autotools | 431 | ncurses 6.4 | [📄](archives/z/zsh/5.9/) |
| **zsh-autocomplete** | 25.03.19、main | ✅ 已发布 |  | Script | - | zsh >= 5.8 (with zsh/param/private and zsh/system modules) | [📄](archives/z/zsh-autocomplete/main/) |
| **zsh-git-prompt** | 0.1.0.0 | ✅ 已编译 |  | none | - | - | [📄](archives/z/zsh-git-prompt/0.1.0.0/) |
| **zsh-history-substring-search** | 1.1.0 | ✅ 已编译 |  |  | - | - | [📄](archives/z/zsh-history-substring-search/1.1.0/) |
| **zstd** | 1.5.6、1.5.7 | ✅ 已发布 |  |  | - | - | [📄](archives/z/zstd/1.5.7/) |
| **zstd-jni** | 1.5.6-5 | uploaded |  | unknown | 0 | - | [📄](archives/z/zstd-jni/1.5.6-5/) |
| **zutils** | 1.15、1.16 | uploaded |  | unknown | 0 | - | [📄](archives/z/zutils/1.16/) |
| **zxc** | 0.9.1 | ✅ 已发布 |  |  | 2 | - | [📄](archives/z/zxc/0.9.1/) |
| **zziplib** | 0.13.78 | uploaded |  | unknown | 0 | - | [📄](archives/z/zziplib/0.13.78/) |

---

*本文档由 `ohc summary` 从编译档案自动生成，请勿手动编辑。*

Copyright (c) 2024-2026 OpenHarmony PC Developer社区