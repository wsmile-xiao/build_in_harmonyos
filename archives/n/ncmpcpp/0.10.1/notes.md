# ncmpcpp 0.10.1 HarmonyOS PC adaptation notes

## Software
- Name: ncmpcpp
- Version: 0.10.1
- Description: Featureful ncurses-based MPD clien
- Source: https://github.com/arybczak/ncmpcpp (tag 0.10.1, commit 3e6d992b938de9ba3019302027bd64dbcab6f8c6)

## Build system
- Autotools. The upstream release tarball has no configure; running ./bootstrap
  requires aclocal/automake, which the OHOS CI does not provide.
- Therefore the Autotools output was pre-generated in WSL and shipped with the
  recipe as plain files under files/autotools-generated/ (copied in source()).

## Dependencies (all from the ohpcd package repository)
- boost/1.90.0.1 (shared; filesystem/program_options/date_time/thread/atomic/chrono
  compiled components + full headers; no locale/regex compiled libs)
- libmpdclient/2.23 (shared; pkg-config name libmpdclient)
- ncurses/6.5 (static; pkg-config name ncursesw)
- curl/8.15.0 (shared; pkg-config name libcurl; depends on openssl/3.5.6.1, zlib/1.3.1.1)

## Adaptation patches (5)
1. 0001-configure-ac-ohos.patch
   - configure.ac: remove BOOST_LOCALE/BOOST_REGEX macro checks (registry boos
     lacks the libs), remove optional ICU check, remove AX_LIB_READLINE check
     (registry has no readline; compatibility layer provides it)
   - m4/boost.m4: Boost.System is header-only since 1.69; for boost >= 1.69
     skip the libboost_system search and leave BOOST_SYSTEM_LIBS empty
2. 0002-readline-compat.patch
   - src/utility/readline.h replaced by a minimal GNU readline-compatible header
   - New src/curses/readline_compat.cpp: implements readline()/rl_insert_text()/
     rl_bind_key()/rl_resize_terminal() etc. on top of ncmpcpp's own ncurses
     input loop (rl_getc_function/rl_redisplay_function); rl_resize_terminal
     repaints through the redisplay callback since ncurses owns the size
3. 0003-std-regex.patch
   - boost::regex migrated to std::regex in regex_filter/scrollpad/option_parser/
     actions/lastfm_service/lyrics_fetcher/mpdpp/statusbar/settings/search_engine
   - "regular_expressions = none" implemented with RegexFlags::literal + escaping
   - scrollpad.cpp regexSearch call sites: OHOS std::regex::flag_type is an enum,
     so flags are passed with explicit static_cast<std::regex::flag_type>(flags);
     the Color overload also had its (id, flags) argument order corrected to
     (flags, id) (upstream's integral boost flag_type had silently masked it)
4. 0004-locale-and-encoding.patch
   - charset.cpp no longer uses boost::locale; built-in UTF-8/ISO-8859-1 codecs
   - New utility/encoding.h/.cpp (UTF-8 <-> wchar_t)
   - boost::locale::to_lower migrated to utility/string.h toLower() (ASCII)
   - utf_to_utf in functional.h/wide_string.h moved to the encoding implementation
   - ncmpcpp.cpp/browser.cpp etc. drop boost/locale headers
5. 0005-boost-cxx20-compat.patch
   - Boost 1.90's boost/range/detail/any_iterator_interface.hpp uses unqualified
     add_const but only includes remove_const.hpp (upstream bug); with C++20 and
     libc++ the name is not found. src/interfaces.h, src/curses/menu.h and
     src/song_list.h now include <boost/type_traits/add_const.hpp> before
     boost/range, so boost::add_const is visible (src/screens/search_engine.cpp
     gets the same include inside 0003).

## Vendored boost/forma
- OHOS boost/1.90.0.1 is built from a reduced BOOST_INCLUDE_LIBRARIES set and
  does not ship boost/format.hpp (the header-only boost::format library).
- files/vendor-boost/ carries the missing headers, taken from Boost 1.84
  (BSL-1.0; LICENSE_1_0.txt is included).
- source() copies them to vendor-boost/ and generate() appends
  -I<src>/vendor-boost to CPPFLAGS: configure's boost.m4 check and make both
  find boost/format.hpp there, while all other Boost headers still resolve
  from the registry package.

## OHOS build notes
- configure's umask 077 must be replaced with 022 (HMDFS config.status temp
  directory permission issues)
- Timestamps: configure.ac/Makefile.am < aclocal.m4 < configure < Makefile.in so
  make never re-runs autotools
- Explicit --build/--host=aarch64-unknown-linux-ohos to avoid config.guess
  failing on HMDFS
- files/autotools-generated/ includes config.h.in (required by configure)
- autoconf 2.72/pkgconf pkg.m4 expansion emitted one stray "fi" after the
  libmpdclient PKG_CHECK_MODULES block; it was removed from the generated
  configure (bash -n clean; all other pkg blocks already balanced)

## Tests
- Upstream ncmpcpp 0.10.1 registers no TESTS/check_PROGRAMS; make check is a no-op
- test_package runs `ncmpcpp --version` and asserts the output contains 0.10.1

## Status
- Target: L0/L1/L4/L5 pass, L2 smoke --version/--help (OpenDesk device verification)
- 2026-08-09: r8 device build failed in src/curses/scrollpad.cpp at the
  regexSearch call sites; fixed with explicit flag_type casts + corrected
  argument order (see 0003).
- r9 passed scrollpad.cpp compilation but make tried to re-run aclocal:
  m4/boost.m4 (in am__aclocal_m4_deps) was newer than aclocal.m4 after
  patching, and the device has no aclocal. _fix_autotools_timestamps now
  pins every m4/*.m4 (and acinclude.m4) to base_time, so make never
  re-invokes aclocal.
- r10 compiled many objects then failed in screens/help.cpp: boost/range
  any_iterator_interface.hpp uses unqualified add_const (Boost 1.90 upstream
  bug). Patch 0005 fixed interfaces.h; r11 then hit the same bug through
  curses/menu.h and song_list.h, so 0005 covers all boost/range include
  sites (interfaces.h, menu.h, song_list.h; search_engine.cpp in 0003).
- r12 failed in search_engine.cpp: std::regex has no empty(); an rx_ok[]
  validity array now mirrors boost::regex::empty() semantics. The same scan
  found leftover boost::regex_match/regex_search calls (actions.cpp,
  lastfm_service.cpp, mpdpp.cpp, option_parser.cpp) which are now migrated
  to std::regex_match/regex_search.
- r13 compiled through all regex files and utility/*, then failed in
  actions.cpp: rl_resize_terminal() was missing from the readline compa
  layer. Added it to 0002 (repaints the prompt; ncurses owns dimensions).
  r14 device verification in progress.
- r14: package now builds (Package created, bin/ncmpcpp present); the only failure
  is test_package: "ncmpcpp: command not found". VirtualRunEnv only adds bin
  dirs of dependencies whose package_type is "application"; the recipe was
  still the default library type, so the packaged binary was not on PATH.
- r15: package_type = "application" added (same as abcmidi/aa3d/iputils in this repo); VirtualRunEnv then injects the package's own bindir into PATH. However the PowerShell edit that added it also wrote a UTF-8 BOM into conanfile.py, and the CI L0 dependency check (ast.parse on the recipe source) rejects U+FEFF, so L0 died silently (stderr is redirected to /dev/null). r15/r16diag confirmed via zsh -x trace + direct repro: SyntaxError: invalid non-printable character U+FEFF.
- r16: removed the BOM from conanfile.py/notes.md; device pipeline now fully green: L0/L1/L4/L5 = pass, Total 1 / Success 1 / Failed 0 (L2 skip: version/help failed, non-blocking). test_package runs `ncmpcpp --version` -> prints "ncmpcpp 0.10.1" and both assertions pass.


## 2026-09-05 复查完善 (lkyz)

- 独立复查tag 0.10.1 源码（gitcode 镜像，commit 3e6d992b938de9ba3019302027bd64dbcab6f8c6）：
  5 个补丁 dry-run 全部干净（0001 一处 fuzz 1）；conanfile.py / test_package/conanfile.py 字节编译通过。
- 修正 test_package/MANIFEST.yml：assertion_count 1 -> 2（脚本实际有 2 项断言：--version 成功退出 + 输出包含 0.10.1）。
- 补全软件级 README.md 与 reports/（build-report.md、test-report.md），固化官方流水线验证结果。
