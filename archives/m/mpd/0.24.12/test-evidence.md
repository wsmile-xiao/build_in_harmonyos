# mpd 0.24.12 上游测试全量执行证据（轮 B：16/18 注册）

> 采集时间: 2026-10-01（轮 B W3 复验轮）
> 采集方式: `meson test -v -j4 -t 10` 于 conan 构建树全量重跑，输出原文收录，未删节
> 构建树: ~/.conan2/p/b/mpd8f22b09807afb/b/build-release/meson-build（轮 B 配方构建产物，21:50 完成编译打包）
> 环境: OHOS aarch64（host=target，HarmonyOS PC 原生执行），meson 1.12.0 + ninja，conan 2.29.1
> 说明: test_archive_bzip2 为 shell 套件，其 bzip2 程序由 tool_requires bzip2/1.0.8.2 注入 PATH

## 汇总（实测）

| 项 | 结果 |
|---|---|
| 注册套件 | **16/18**（未注册 2：test_archive_iso9660 [libiso9660 未发布]、test_archive_zzip [zip 未发布]——上游环境依赖，非适配裁剪） |
| 套件通过率 | **Ok: 16 / Fail: 0（100%）** |
| gtest 用例 `[ OK ]` | 170（15 个 gtest 套件；test_archive_bzip2 为 shell 套件，不产 gtest 行） |
| 消费者测试（test_package） | C1-C4 全过（C4 = null 输出播放闭环状态机，配方 build()/conan-verify 内真实执行） |

以下为 meson test -v 完整输出：

ninja: Entering directory `/storage/Users/currentUser/.conan2/p/b/mpd8f22b09807afb/b/build-release/meson-build'
ninja: no work to do.
 1/16 mpd:TestUtil              RUNNING       
>>> ASAN_OPTIONS=halt_on_error=1:abort_on_error=1:print_summary=1 MSAN_OPTIONS=halt_on_error=1:abort_on_error=1:print_summary=1:print_stacktrace=1 MESON_TEST_ITERATION=1 MALLOC_PERTURB_=32 MESON_EXE_WRAPPER=/storage/Users/currentUser/.conan2/p/b/mpd8f22b09807afb/b/build-release/mpd-exe-wrapper.sh /storage/Users/currentUser/.conan2/p/b/mpd8f22b09807afb/b/build-release/mpd-exe-wrapper.sh /storage/Users/currentUser/.conan2/p/b/mpd8f22b09807afb/b/build-release/meson-build/test/util/TestUtil

 2/16 mpd:TestNet               RUNNING       
>>> ASAN_OPTIONS=halt_on_error=1:abort_on_error=1:print_summary=1 MSAN_OPTIONS=halt_on_error=1:abort_on_error=1:print_summary=1:print_stacktrace=1 MALLOC_PERTURB_=8 MESON_TEST_ITERATION=1 MESON_EXE_WRAPPER=/storage/Users/currentUser/.conan2/p/b/mpd8f22b09807afb/b/build-release/mpd-exe-wrapper.sh /storage/Users/currentUser/.conan2/p/b/mpd8f22b09807afb/b/build-release/mpd-exe-wrapper.sh /storage/Users/currentUser/.conan2/p/b/mpd8f22b09807afb/b/build-release/meson-build/test/net/TestNet

 3/16 mpd:TestTime              RUNNING       
>>> ASAN_OPTIONS=halt_on_error=1:abort_on_error=1:print_summary=1 MSAN_OPTIONS=halt_on_error=1:abort_on_error=1:print_summary=1:print_stacktrace=1 MALLOC_PERTURB_=21 MESON_TEST_ITERATION=1 MESON_EXE_WRAPPER=/storage/Users/currentUser/.conan2/p/b/mpd8f22b09807afb/b/build-release/mpd-exe-wrapper.sh /storage/Users/currentUser/.conan2/p/b/mpd8f22b09807afb/b/build-release/mpd-exe-wrapper.sh /storage/Users/currentUser/.conan2/p/b/mpd8f22b09807afb/b/build-release/meson-build/test/time/TestTime

 4/16 mpd:TestMixRamp           RUNNING       
>>> MALLOC_PERTURB_=147 ASAN_OPTIONS=halt_on_error=1:abort_on_error=1:print_summary=1 MSAN_OPTIONS=halt_on_error=1:abort_on_error=1:print_summary=1:print_stacktrace=1 MESON_TEST_ITERATION=1 MESON_EXE_WRAPPER=/storage/Users/currentUser/.conan2/p/b/mpd8f22b09807afb/b/build-release/mpd-exe-wrapper.sh /storage/Users/currentUser/.conan2/p/b/mpd8f22b09807afb/b/build-release/mpd-exe-wrapper.sh /storage/Users/currentUser/.conan2/p/b/mpd8f22b09807afb/b/build-release/meson-build/test/tag/TestMixRamp

 2/16 mpd:TestNet               OK               0.08s
――――――――――――――――――――――――――――――――――――― ✀  ―――――――――――――――――――――――――――――――――――――
Running main() from /storage/Users/currentUser/.conan2/p/b/gtestddcd678b9dadc/b/googletest/src/gtest_main.cc
[==========] Running 24 tests from 5 test suites.
[----------] Global test environment set-up.
[----------] 5 tests from IPv4AddressTest
[ RUN      ] IPv4AddressTest.Basic
[       OK ] IPv4AddressTest.Basic (0 ms)
[ RUN      ] IPv4AddressTest.Port
[       OK ] IPv4AddressTest.Port (0 ms)
[ RUN      ] IPv4AddressTest.NumericAddress
[       OK ] IPv4AddressTest.NumericAddress (0 ms)
[ RUN      ] IPv4AddressTest.Mask
[       OK ] IPv4AddressTest.Mask (0 ms)
[ RUN      ] IPv4AddressTest.And
[       OK ] IPv4AddressTest.And (0 ms)
[----------] 5 tests from IPv4AddressTest (0 ms total)

[----------] 6 tests from IPv4Address
[ RUN      ] IPv4Address.Octets
[       OK ] IPv4Address.Octets (0 ms)
[ RUN      ] IPv4Address.Any
[       OK ] IPv4Address.Any (0 ms)
[ RUN      ] IPv4Address.Port
[       OK ] IPv4Address.Port (0 ms)
[ RUN      ] IPv4Address.Loopback
[       OK ] IPv4Address.Loopback (0 ms)
[ RUN      ] IPv4Address.MaskFromPrefix
[       OK ] IPv4Address.MaskFromPrefix (0 ms)
[ RUN      ] IPv4Address.Numeric
[       OK ] IPv4Address.Numeric (0 ms)
[----------] 6 tests from IPv4Address (0 ms total)

[----------] 4 tests from IPv6AddressTest
[ RUN      ] IPv6AddressTest.Basic
[       OK ] IPv6AddressTest.Basic (0 ms)
[ RUN      ] IPv6AddressTest.Port
[       OK ] IPv6AddressTest.Port (0 ms)
[ RUN      ] IPv6AddressTest.Mask
[       OK ] IPv6AddressTest.Mask (0 ms)
[ RUN      ] IPv6AddressTest.And
[       OK ] IPv6AddressTest.And (0 ms)
[----------] 4 tests from IPv6AddressTest (0 ms total)

[----------] 4 tests from IPv6Address
[ RUN      ] IPv6Address.Octets
[       OK ] IPv6Address.Octets (0 ms)
[ RUN      ] IPv6Address.Any
[       OK ] IPv6Address.Any (0 ms)
[ RUN      ] IPv6Address.Port
[       OK ] IPv6Address.Port (0 ms)
[ RUN      ] IPv6Address.MaskFromPrefix
[       OK ] IPv6Address.MaskFromPrefix (0 ms)
[----------] 4 tests from IPv6Address (0 ms total)

[----------] 5 tests from LocalSocketAddress
[ RUN      ] LocalSocketAddress.Path1
[       OK ] LocalSocketAddress.Path1 (0 ms)
[ RUN      ] LocalSocketAddress.Path2
[       OK ] LocalSocketAddress.Path2 (0 ms)
[ RUN      ] LocalSocketAddress.Path
[       OK ] LocalSocketAddress.Path (0 ms)
[ RUN      ] LocalSocketAddress.Abstract1
[       OK ] LocalSocketAddress.Abstract1 (0 ms)
[ RUN      ] LocalSocketAddress.Abstract
[       OK ] LocalSocketAddress.Abstract (0 ms)
[----------] 5 tests from LocalSocketAddress (0 ms total)

[----------] Global test environment tear-down
[==========] 24 tests from 5 test suites ran. (0 ms total)
[  PASSED  ] 24 tests.
――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――

 5/16 mpd:TestPlaylistPlugins   RUNNING       
>>> ASAN_OPTIONS=halt_on_error=1:abort_on_error=1:print_summary=1 MSAN_OPTIONS=halt_on_error=1:abort_on_error=1:print_summary=1:print_stacktrace=1 MALLOC_PERTURB_=130 MESON_TEST_ITERATION=1 MESON_EXE_WRAPPER=/storage/Users/currentUser/.conan2/p/b/mpd8f22b09807afb/b/build-release/mpd-exe-wrapper.sh /storage/Users/currentUser/.conan2/p/b/mpd8f22b09807afb/b/build-release/mpd-exe-wrapper.sh /storage/Users/currentUser/.conan2/p/b/mpd8f22b09807afb/b/build-release/meson-build/test/playlist/TestPlaylistPlugins

 3/16 mpd:TestTime              OK               0.09s
――――――――――――――――――――――――――――――――――――― ✀  ―――――――――――――――――――――――――――――――――――――
Running main() from /storage/Users/currentUser/.conan2/p/b/gtestddcd678b9dadc/b/googletest/src/gtest_main.cc
[==========] Running 3 tests from 2 test suites.
[----------] Global test environment set-up.
[----------] 2 tests from Time
[ RUN      ] Time.LocalTime
[       OK ] Time.LocalTime (0 ms)
[ RUN      ] Time.GmTime
[       OK ] Time.GmTime (0 ms)
[----------] 2 tests from Time (0 ms total)

[----------] 1 test from ISO8601
[ RUN      ] ISO8601.Parse
[       OK ] ISO8601.Parse (0 ms)
[----------] 1 test from ISO8601 (0 ms total)

[----------] Global test environment tear-down
[==========] 3 tests from 2 test suites ran. (0 ms total)
[  PASSED  ] 3 tests.
――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――

 6/16 mpd:TestRewindInputStream RUNNING       
>>> ASAN_OPTIONS=halt_on_error=1:abort_on_error=1:print_summary=1 MALLOC_PERTURB_=15 MSAN_OPTIONS=halt_on_error=1:abort_on_error=1:print_summary=1:print_stacktrace=1 MESON_TEST_ITERATION=1 MESON_EXE_WRAPPER=/storage/Users/currentUser/.conan2/p/b/mpd8f22b09807afb/b/build-release/mpd-exe-wrapper.sh /storage/Users/currentUser/.conan2/p/b/mpd8f22b09807afb/b/build-release/mpd-exe-wrapper.sh /storage/Users/currentUser/.conan2/p/b/mpd8f22b09807afb/b/build-release/meson-build/test/TestRewindInputStream

 4/16 mpd:TestMixRamp           OK               0.10s
――――――――――――――――――――――――――――――――――――― ✀  ―――――――――――――――――――――――――――――――――――――
Running main() from /storage/Users/currentUser/.conan2/p/b/gtestddcd678b9dadc/b/googletest/src/gtest_main.cc
[==========] Running 3 tests from 1 test suite.
[----------] Global test environment set-up.
[----------] 3 tests from MixRamp
[ RUN      ] MixRamp.Interpolate
[       OK ] MixRamp.Interpolate (0 ms)
[ RUN      ] MixRamp.Parser
[       OK ] MixRamp.Parser (0 ms)
[ RUN      ] MixRamp.VorbisParser
[       OK ] MixRamp.VorbisParser (0 ms)
[----------] 3 tests from MixRamp (0 ms total)

[----------] Global test environment tear-down
[==========] 3 tests from 1 test suite ran. (0 ms total)
[  PASSED  ] 3 tests.
――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――

 1/16 mpd:TestUtil              OK               0.13s
――――――――――――――――――――――――――――――――――――― ✀  ―――――――――――――――――――――――――――――――――――――
Running main() from /storage/Users/currentUser/.conan2/p/b/gtestddcd678b9dadc/b/googletest/src/gtest_main.cc
[==========] Running 55 tests from 17 test suites.
[----------] Global test environment set-up.
[----------] 1 test from CircularBuffer
[ RUN      ] CircularBuffer.Basic
[       OK ] CircularBuffer.Basic (0 ms)
[----------] 1 test from CircularBuffer (0 ms total)

[----------] 8 tests from ExceptionTest
[ RUN      ] ExceptionTest.RuntimeError
[       OK ] ExceptionTest.RuntimeError (0 ms)
[ RUN      ] ExceptionTest.DerivedError
[       OK ] ExceptionTest.DerivedError (0 ms)
[ RUN      ] ExceptionTest.GetFullMessageSanitize
[       OK ] ExceptionTest.GetFullMessageSanitize (0 ms)
[ RUN      ] ExceptionTest.FindNestedDirect
[       OK ] ExceptionTest.FindNestedDirect (0 ms)
[ RUN      ] ExceptionTest.FindNestedIndirect
[       OK ] ExceptionTest.FindNestedIndirect (0 ms)
[ RUN      ] ExceptionTest.FindRetrowNestedDirect
[       OK ] ExceptionTest.FindRetrowNestedDirect (0 ms)
[ RUN      ] ExceptionTest.FindRetrowNestedIndirect
[       OK ] ExceptionTest.FindRetrowNestedIndirect (0 ms)
[ RUN      ] ExceptionTest.FindRetrowNestedIndirectRuntimeError
[       OK ] ExceptionTest.FindRetrowNestedIndirectRuntimeError (0 ms)
[----------] 8 tests from ExceptionTest (0 ms total)

[----------] 3 tests from IntrusiveForwardList
[ RUN      ] IntrusiveForwardList.Basic
[       OK ] IntrusiveForwardList.Basic (0 ms)
[ RUN      ] IntrusiveForwardList.ConstantTimeSize
[       OK ] IntrusiveForwardList.ConstantTimeSize (0 ms)
[ RUN      ] IntrusiveForwardList.CacheLast
[       OK ] IntrusiveForwardList.CacheLast (0 ms)
[----------] 3 tests from IntrusiveForwardList (0 ms total)

[----------] 3 tests from IntrusiveHashSet
[ RUN      ] IntrusiveHashSet.Basic
[       OK ] IntrusiveHashSet.Basic (0 ms)
[ RUN      ] IntrusiveHashSet.Multi
[       OK ] IntrusiveHashSet.Multi (0 ms)
[ RUN      ] IntrusiveHashSet.Tag
[       OK ] IntrusiveHashSet.Tag (0 ms)
[----------] 3 tests from IntrusiveHashSet (0 ms total)

[----------] 8 tests from IntrusiveList
[ RUN      ] IntrusiveList.Basic
[       OK ] IntrusiveList.Basic (0 ms)
[ RUN      ] IntrusiveList.Track
[       OK ] IntrusiveList.Track (0 ms)
[ RUN      ] IntrusiveList.AutoUnlink
[       OK ] IntrusiveList.AutoUnlink (0 ms)
[ RUN      ] IntrusiveList.Tag
[       OK ] IntrusiveList.Tag (0 ms)
[ RUN      ] IntrusiveList.Merge
[       OK ] IntrusiveList.Merge (0 ms)
[ RUN      ] IntrusiveList.Sort
[       OK ] IntrusiveList.Sort (0 ms)
[ RUN      ] IntrusiveList.ClearDisposeUnlink
[       OK ] IntrusiveList.ClearDisposeUnlink (0 ms)
[ RUN      ] IntrusiveList.ClearDisposePush
[       OK ] IntrusiveList.ClearDisposePush (0 ms)
[----------] 8 tests from IntrusiveList (0 ms total)

[----------] 6 tests from IntrusiveTreeSet
[ RUN      ] IntrusiveTreeSet.Basic
[       OK ] IntrusiveTreeSet.Basic (0 ms)
[ RUN      ] IntrusiveTreeSet.RandomOrder
[       OK ] IntrusiveTreeSet.RandomOrder (0 ms)
[ RUN      ] IntrusiveTreeSet.LargeRandom
[       OK ] IntrusiveTreeSet.LargeRandom (14 ms)
[ RUN      ] IntrusiveTreeSet.ClearIsLinked
[       OK ] IntrusiveTreeSet.ClearIsLinked (0 ms)
[ RUN      ] IntrusiveTreeSet.ClearAndDisposeIsLinked
[       OK ] IntrusiveTreeSet.ClearAndDisposeIsLinked (0 ms)
[ RUN      ] IntrusiveTreeSet.Zero
[       OK ] IntrusiveTreeSet.Zero (5 ms)
[----------] 6 tests from IntrusiveTreeSet (19 ms total)

[----------] 1 test from MimeType
[ RUN      ] MimeType.Base
[       OK ] MimeType.Base (0 ms)
[----------] 1 test from MimeType (0 ms total)

[----------] 2 tests from UriUtil
[ RUN      ] UriUtil.Parameters
[       OK ] UriUtil.Parameters (0 ms)
[ RUN      ] UriUtil.RemoveAuth
[       OK ] UriUtil.RemoveAuth (0 ms)
[----------] 2 tests from UriUtil (0 ms total)

[----------] 2 tests from RingBuffer
[ RUN      ] RingBuffer.DirectReadWrite
[       OK ] RingBuffer.DirectReadWrite (0 ms)
[ RUN      ] RingBuffer.ReadFromWriteTo
[       OK ] RingBuffer.ReadFromWriteTo (0 ms)
[----------] 2 tests from RingBuffer (0 ms total)

[----------] 4 tests from SplitString
[ RUN      ] SplitString.Basic
[       OK ] SplitString.Basic (0 ms)
[ RUN      ] SplitString.Strip
[       OK ] SplitString.Strip (0 ms)
[ RUN      ] SplitString.NoStrip
[       OK ] SplitString.NoStrip (0 ms)
[ RUN      ] SplitString.Empty
[       OK ] SplitString.Empty (0 ms)
[----------] 4 tests from SplitString (0 ms total)

[----------] 3 tests from StringStrip
[ RUN      ] StringStrip.StripLeft
[       OK ] StringStrip.StripLeft (0 ms)
[ RUN      ] StringStrip.StripRight
[       OK ] StringStrip.StripRight (0 ms)
[ RUN      ] StringStrip.Strip
[       OK ] StringStrip.Strip (0 ms)
[----------] 3 tests from StringStrip (0 ms total)

[----------] 3 tests from TemplateString
[ RUN      ] TemplateString.FromChar
[       OK ] TemplateString.FromChar (0 ms)
[ RUN      ] TemplateString.FromLiteral
[       OK ] TemplateString.FromLiteral (0 ms)
[ RUN      ] TemplateString.Concat
[       OK ] TemplateString.Concat (0 ms)
[----------] 3 tests from TemplateString (0 ms total)

[----------] 2 tests from TerminatedArray
[ RUN      ] TerminatedArray.PointerArray
[       OK ] TerminatedArray.PointerArray (0 ms)
[ RUN      ] TerminatedArray.CSTring
[       OK ] TerminatedArray.CSTring (0 ms)
[----------] 2 tests from TerminatedArray (0 ms total)

[----------] 1 test from UriExtract
[ RUN      ] UriExtract.Suffix
[       OK ] UriExtract.Suffix (0 ms)
[----------] 1 test from UriExtract (0 ms total)

[----------] 1 test from UriQueryParser
[ RUN      ] UriQueryParser.UriFindRawQueryParameter
[       OK ] UriQueryParser.UriFindRawQueryParameter (0 ms)
[----------] 1 test from UriQueryParser (0 ms total)

[----------] 3 tests from UriRelative
[ RUN      ] UriRelative.IsChild
[       OK ] UriRelative.IsChild (0 ms)
[ RUN      ] UriRelative.ApplyBase
[       OK ] UriRelative.ApplyBase (0 ms)
[ RUN      ] UriRelative.ApplyRelative
[       OK ] UriRelative.ApplyRelative (0 ms)
[----------] 3 tests from UriRelative (0 ms total)

[----------] 4 tests from ByteReverse
[ RUN      ] ByteReverse.A
[       OK ] ByteReverse.A (0 ms)
[ RUN      ] ByteReverse.B
[       OK ] ByteReverse.B (0 ms)
[ RUN      ] ByteReverse.C
[       OK ] ByteReverse.C (0 ms)
[ RUN      ] ByteReverse.D
[       OK ] ByteReverse.D (0 ms)
[----------] 4 tests from ByteReverse (0 ms total)

[----------] Global test environment tear-down
[==========] 55 tests from 17 test suites ran. (21 ms total)
[  PASSED  ] 55 tests.
――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――

 7/16 mpd:test_protocol         RUNNING       
>>> ASAN_OPTIONS=halt_on_error=1:abort_on_error=1:print_summary=1 MSAN_OPTIONS=halt_on_error=1:abort_on_error=1:print_summary=1:print_stacktrace=1 MALLOC_PERTURB_=61 MESON_TEST_ITERATION=1 MESON_EXE_WRAPPER=/storage/Users/currentUser/.conan2/p/b/mpd8f22b09807afb/b/build-release/mpd-exe-wrapper.sh /storage/Users/currentUser/.conan2/p/b/mpd8f22b09807afb/b/build-release/mpd-exe-wrapper.sh /storage/Users/currentUser/.conan2/p/b/mpd8f22b09807afb/b/build-release/meson-build/test/test_protocol

 8/16 mpd:test_queue_priority   RUNNING       
>>> ASAN_OPTIONS=halt_on_error=1:abort_on_error=1:print_summary=1 MSAN_OPTIONS=halt_on_error=1:abort_on_error=1:print_summary=1:print_stacktrace=1 MALLOC_PERTURB_=238 MESON_TEST_ITERATION=1 MESON_EXE_WRAPPER=/storage/Users/currentUser/.conan2/p/b/mpd8f22b09807afb/b/build-release/mpd-exe-wrapper.sh /storage/Users/currentUser/.conan2/p/b/mpd8f22b09807afb/b/build-release/mpd-exe-wrapper.sh /storage/Users/currentUser/.conan2/p/b/mpd8f22b09807afb/b/build-release/meson-build/test/test_queue_priority

 6/16 mpd:TestRewindInputStream OK               0.06s
――――――――――――――――――――――――――――――――――――― ✀  ―――――――――――――――――――――――――――――――――――――
Running main() from /storage/Users/currentUser/.conan2/p/b/gtestddcd678b9dadc/b/googletest/src/gtest_main.cc
[==========] Running 1 test from 1 test suite.
[----------] Global test environment set-up.
[----------] 1 test from RewindInputStream
[ RUN      ] RewindInputStream.Basic
[       OK ] RewindInputStream.Basic (0 ms)
[----------] 1 test from RewindInputStream (0 ms total)

[----------] Global test environment tear-down
[==========] 1 test from 1 test suite ran. (0 ms total)
[  PASSED  ] 1 test.
――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――

 9/16 mpd:TestIcu               RUNNING       
>>> ASAN_OPTIONS=halt_on_error=1:abort_on_error=1:print_summary=1 MALLOC_PERTURB_=50 MSAN_OPTIONS=halt_on_error=1:abort_on_error=1:print_summary=1:print_stacktrace=1 MESON_TEST_ITERATION=1 MESON_EXE_WRAPPER=/storage/Users/currentUser/.conan2/p/b/mpd8f22b09807afb/b/build-release/mpd-exe-wrapper.sh /storage/Users/currentUser/.conan2/p/b/mpd8f22b09807afb/b/build-release/mpd-exe-wrapper.sh /storage/Users/currentUser/.conan2/p/b/mpd8f22b09807afb/b/build-release/meson-build/test/TestIcu

 5/16 mpd:TestPlaylistPlugins   OK               0.11s
――――――――――――――――――――――――――――――――――――― ✀  ―――――――――――――――――――――――――――――――――――――
Running main() from /storage/Users/currentUser/.conan2/p/b/gtestddcd678b9dadc/b/googletest/src/gtest_main.cc
[==========] Running 1 test from 1 test suite.
[----------] Global test environment set-up.
[----------] 1 test from PlaylistPlugins
[ RUN      ] PlaylistPlugins.Pls
[       OK ] PlaylistPlugins.Pls (0 ms)
[----------] 1 test from PlaylistPlugins (0 ms total)

[----------] Global test environment tear-down
[==========] 1 test from 1 test suite ran. (0 ms total)
[  PASSED  ] 1 test.
――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――

10/16 mpd:TestSongFilter        RUNNING       
>>> ASAN_OPTIONS=halt_on_error=1:abort_on_error=1:print_summary=1 MSAN_OPTIONS=halt_on_error=1:abort_on_error=1:print_summary=1:print_stacktrace=1 MALLOC_PERTURB_=71 MESON_TEST_ITERATION=1 MESON_EXE_WRAPPER=/storage/Users/currentUser/.conan2/p/b/mpd8f22b09807afb/b/build-release/mpd-exe-wrapper.sh /storage/Users/currentUser/.conan2/p/b/mpd8f22b09807afb/b/build-release/mpd-exe-wrapper.sh /storage/Users/currentUser/.conan2/p/b/mpd8f22b09807afb/b/build-release/meson-build/test/TestSongFilter

 7/16 mpd:test_protocol         OK               0.08s
――――――――――――――――――――――――――――――――――――― ✀  ―――――――――――――――――――――――――――――――――――――
Running main() from /storage/Users/currentUser/.conan2/p/b/gtestddcd678b9dadc/b/googletest/src/gtest_main.cc
[==========] Running 1 test from 1 test suite.
[----------] Global test environment set-up.
[----------] 1 test from ArgParser
[ RUN      ] ArgParser.Range
[       OK ] ArgParser.Range (0 ms)
[----------] 1 test from ArgParser (0 ms total)

[----------] Global test environment tear-down
[==========] 1 test from 1 test suite ran. (0 ms total)
[  PASSED  ] 1 test.
――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――

 8/16 mpd:test_queue_priority   OK               0.07s
――――――――――――――――――――――――――――――――――――― ✀  ―――――――――――――――――――――――――――――――――――――
Running main() from /storage/Users/currentUser/.conan2/p/b/gtestddcd678b9dadc/b/googletest/src/gtest_main.cc
[==========] Running 1 test from 1 test suite.
[----------] Global test environment set-up.
[----------] 1 test from QueuePriority
[ RUN      ] QueuePriority.Priority
[       OK ] QueuePriority.Priority (0 ms)
[----------] 1 test from QueuePriority (0 ms total)

[----------] Global test environment tear-down
[==========] 1 test from 1 test suite ran. (0 ms total)
[  PASSED  ] 1 test.
――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――

11/16 mpd:test_translate_song   RUNNING       
>>> ASAN_OPTIONS=halt_on_error=1:abort_on_error=1:print_summary=1 MSAN_OPTIONS=halt_on_error=1:abort_on_error=1:print_summary=1:print_stacktrace=1 MALLOC_PERTURB_=125 MESON_TEST_ITERATION=1 MESON_EXE_WRAPPER=/storage/Users/currentUser/.conan2/p/b/mpd8f22b09807afb/b/build-release/mpd-exe-wrapper.sh /storage/Users/currentUser/.conan2/p/b/mpd8f22b09807afb/b/build-release/mpd-exe-wrapper.sh /storage/Users/currentUser/.conan2/p/b/mpd8f22b09807afb/b/build-release/meson-build/test/test_translate_song

12/16 mpd:test_icy_parser       RUNNING       
>>> ASAN_OPTIONS=halt_on_error=1:abort_on_error=1:print_summary=1 MSAN_OPTIONS=halt_on_error=1:abort_on_error=1:print_summary=1:print_stacktrace=1 MALLOC_PERTURB_=105 MESON_TEST_ITERATION=1 MESON_EXE_WRAPPER=/storage/Users/currentUser/.conan2/p/b/mpd8f22b09807afb/b/build-release/mpd-exe-wrapper.sh /storage/Users/currentUser/.conan2/p/b/mpd8f22b09807afb/b/build-release/mpd-exe-wrapper.sh /storage/Users/currentUser/.conan2/p/b/mpd8f22b09807afb/b/build-release/meson-build/test/test_icy_parser

 9/16 mpd:TestIcu               OK               0.06s
――――――――――――――――――――――――――――――――――――― ✀  ―――――――――――――――――――――――――――――――――――――
Running main() from /storage/Users/currentUser/.conan2/p/b/gtestddcd678b9dadc/b/googletest/src/gtest_main.cc
[==========] Running 2 tests from 1 test suite.
[----------] Global test environment set-up.
[----------] 2 tests from IcuConverter
[ RUN      ] IcuConverter.InvalidCharset
[       OK ] IcuConverter.InvalidCharset (0 ms)
[ RUN      ] IcuConverter.Latin1
[       OK ] IcuConverter.Latin1 (0 ms)
[----------] 2 tests from IcuConverter (1 ms total)

[----------] Global test environment tear-down
[==========] 2 tests from 1 test suite ran. (1 ms total)
[  PASSED  ] 2 tests.
――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――

13/16 mpd:test_archive_bzip2    RUNNING       
>>> MESON_TEST_ITERATION=1 ASAN_OPTIONS=halt_on_error=1:abort_on_error=1:print_summary=1 MALLOC_PERTURB_=25 MSAN_OPTIONS=halt_on_error=1:abort_on_error=1:print_summary=1:print_stacktrace=1 /storage/Users/currentUser/.conan2/p/b/mpd8f22b09807afb/b/test/test_archive_bzip2.sh

11/16 mpd:test_translate_song   OK               0.07s
――――――――――――――――――――――――――――――――――――― ✀  ―――――――――――――――――――――――――――――――――――――
Running main() from /storage/Users/currentUser/.conan2/p/b/gtestddcd678b9dadc/b/googletest/src/gtest_main.cc
[==========] Running 6 tests from 1 test suite.
[----------] Global test environment set-up.
[----------] 6 tests from TranslateSongTest
[ RUN      ] TranslateSongTest.AbsoluteURI
[       OK ] TranslateSongTest.AbsoluteURI (0 ms)
[ RUN      ] TranslateSongTest.Insecure
[       OK ] TranslateSongTest.Insecure (0 ms)
[ RUN      ] TranslateSongTest.Secure
[       OK ] TranslateSongTest.Secure (0 ms)
[ RUN      ] TranslateSongTest.InDatabase
[       OK ] TranslateSongTest.InDatabase (0 ms)
[ RUN      ] TranslateSongTest.Relative
[       OK ] TranslateSongTest.Relative (0 ms)
[ RUN      ] TranslateSongTest.Backslash
[       OK ] TranslateSongTest.Backslash (0 ms)
[----------] 6 tests from TranslateSongTest (0 ms total)

[----------] Global test environment tear-down
[==========] 6 tests from 1 test suite ran. (0 ms total)
[  PASSED  ] 6 tests.
――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――

14/16 mpd:test_pcm              RUNNING       
>>> ASAN_OPTIONS=halt_on_error=1:abort_on_error=1:print_summary=1 MSAN_OPTIONS=halt_on_error=1:abort_on_error=1:print_summary=1:print_stacktrace=1 MALLOC_PERTURB_=124 MESON_TEST_ITERATION=1 MESON_EXE_WRAPPER=/storage/Users/currentUser/.conan2/p/b/mpd8f22b09807afb/b/build-release/mpd-exe-wrapper.sh /storage/Users/currentUser/.conan2/p/b/mpd8f22b09807afb/b/build-release/mpd-exe-wrapper.sh /storage/Users/currentUser/.conan2/p/b/mpd8f22b09807afb/b/build-release/meson-build/test/test_pcm

12/16 mpd:test_icy_parser       OK               0.08s
――――――――――――――――――――――――――――――――――――― ✀  ―――――――――――――――――――――――――――――――――――――
Running main() from /storage/Users/currentUser/.conan2/p/b/gtestddcd678b9dadc/b/googletest/src/gtest_main.cc
[==========] Running 1 test from 1 test suite.
[----------] Global test environment set-up.
[----------] 1 test from IcyMetadataParserTest
[ RUN      ] IcyMetadataParserTest.Basic
[       OK ] IcyMetadataParserTest.Basic (0 ms)
[----------] 1 test from IcyMetadataParserTest (0 ms total)

[----------] Global test environment tear-down
[==========] 1 test from 1 test suite ran. (0 ms total)
[  PASSED  ] 1 test.
――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――

15/16 mpd:TestFs                RUNNING       
>>> ASAN_OPTIONS=halt_on_error=1:abort_on_error=1:print_summary=1 MSAN_OPTIONS=halt_on_error=1:abort_on_error=1:print_summary=1:print_stacktrace=1 MALLOC_PERTURB_=175 MESON_TEST_ITERATION=1 MESON_EXE_WRAPPER=/storage/Users/currentUser/.conan2/p/b/mpd8f22b09807afb/b/build-release/mpd-exe-wrapper.sh /storage/Users/currentUser/.conan2/p/b/mpd8f22b09807afb/b/build-release/mpd-exe-wrapper.sh /storage/Users/currentUser/.conan2/p/b/mpd8f22b09807afb/b/build-release/meson-build/test/fs/TestFs

14/16 mpd:test_pcm              OK               0.06s
――――――――――――――――――――――――――――――――――――― ✀  ―――――――――――――――――――――――――――――――――――――
Running main() from /storage/Users/currentUser/.conan2/p/b/gtestddcd678b9dadc/b/googletest/src/gtest_main.cc
[==========] Running 36 tests from 2 test suites.
[----------] Global test environment set-up.
[----------] 2 tests from AudioFormatTest
[ RUN      ] AudioFormatTest.ToString
[       OK ] AudioFormatTest.ToString (0 ms)
[ RUN      ] AudioFormatTest.Parse
[       OK ] AudioFormatTest.Parse (0 ms)
[----------] 2 tests from AudioFormatTest (0 ms total)

[----------] 34 tests from PcmTest
[ RUN      ] PcmTest.Channels16
[       OK ] PcmTest.Channels16 (0 ms)
[ RUN      ] PcmTest.Channels32
[       OK ] PcmTest.Channels32 (0 ms)
[ RUN      ] PcmTest.Dither24
[       OK ] PcmTest.Dither24 (0 ms)
[ RUN      ] PcmTest.Dither32
[       OK ] PcmTest.Dither32 (0 ms)
[ RUN      ] PcmTest.ExportShift8
[       OK ] PcmTest.ExportShift8 (0 ms)
[ RUN      ] PcmTest.ExportPack24
[       OK ] PcmTest.ExportPack24 (0 ms)
[ RUN      ] PcmTest.ExportReverseEndian
[       OK ] PcmTest.ExportReverseEndian (0 ms)
[ RUN      ] PcmTest.ExportDsdU16
[       OK ] PcmTest.ExportDsdU16 (0 ms)
[ RUN      ] PcmTest.ExportDsdU32
[       OK ] PcmTest.ExportDsdU32 (0 ms)
[ RUN      ] PcmTest.ExportDop
[       OK ] PcmTest.ExportDop (0 ms)
[ RUN      ] PcmTest.ExportAlsaChannelOrder
[       OK ] PcmTest.ExportAlsaChannelOrder (0 ms)
[ RUN      ] PcmTest.Format8To16
[       OK ] PcmTest.Format8To16 (0 ms)
[ RUN      ] PcmTest.Format16To24
[       OK ] PcmTest.Format16To24 (0 ms)
[ RUN      ] PcmTest.Format16To32
[       OK ] PcmTest.Format16To32 (0 ms)
[ RUN      ] PcmTest.FormatFloat16
[       OK ] PcmTest.FormatFloat16 (0 ms)
[ RUN      ] PcmTest.FormatFloat32
[       OK ] PcmTest.FormatFloat32 (0 ms)
[ RUN      ] PcmTest.Interleave8
[       OK ] PcmTest.Interleave8 (0 ms)
[ RUN      ] PcmTest.Interleave16
[       OK ] PcmTest.Interleave16 (0 ms)
[ RUN      ] PcmTest.Interleave24
[       OK ] PcmTest.Interleave24 (0 ms)
[ RUN      ] PcmTest.Interleave32
[       OK ] PcmTest.Interleave32 (0 ms)
[ RUN      ] PcmTest.Interleave64
[       OK ] PcmTest.Interleave64 (0 ms)
[ RUN      ] PcmTest.Mix8
[       OK ] PcmTest.Mix8 (0 ms)
[ RUN      ] PcmTest.Mix16
[       OK ] PcmTest.Mix16 (0 ms)
[ RUN      ] PcmTest.Mix24
[       OK ] PcmTest.Mix24 (0 ms)
[ RUN      ] PcmTest.Mix32
[       OK ] PcmTest.Mix32 (0 ms)
[ RUN      ] PcmTest.Pack24
[       OK ] PcmTest.Pack24 (0 ms)
[ RUN      ] PcmTest.Unpack24
[       OK ] PcmTest.Unpack24 (0 ms)
[ RUN      ] PcmTest.Unpack24BE
[       OK ] PcmTest.Unpack24BE (0 ms)
[ RUN      ] PcmTest.Volume8
[       OK ] PcmTest.Volume8 (0 ms)
[ RUN      ] PcmTest.Volume16
[       OK ] PcmTest.Volume16 (0 ms)
[ RUN      ] PcmTest.Volume16to32
[       OK ] PcmTest.Volume16to32 (0 ms)
[ RUN      ] PcmTest.Volume24
[       OK ] PcmTest.Volume24 (0 ms)
[ RUN      ] PcmTest.Volume32
[       OK ] PcmTest.Volume32 (0 ms)
[ RUN      ] PcmTest.VolumeFloat
[       OK ] PcmTest.VolumeFloat (0 ms)
[----------] 34 tests from PcmTest (1 ms total)

[----------] Global test environment tear-down
[==========] 36 tests from 2 test suites ran. (1 ms total)
[  PASSED  ] 36 tests.
――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――

16/16 mpd:TestParsePath         RUNNING       
>>> ASAN_OPTIONS=halt_on_error=1:abort_on_error=1:print_summary=1 MSAN_OPTIONS=halt_on_error=1:abort_on_error=1:print_summary=1:print_stacktrace=1 MALLOC_PERTURB_=252 MESON_TEST_ITERATION=1 MESON_EXE_WRAPPER=/storage/Users/currentUser/.conan2/p/b/mpd8f22b09807afb/b/build-release/mpd-exe-wrapper.sh /storage/Users/currentUser/.conan2/p/b/mpd8f22b09807afb/b/build-release/mpd-exe-wrapper.sh /storage/Users/currentUser/.conan2/p/b/mpd8f22b09807afb/b/build-release/meson-build/test/fs/TestParsePath

15/16 mpd:TestFs                OK               0.06s
――――――――――――――――――――――――――――――――――――― ✀  ―――――――――――――――――――――――――――――――――――――
Running main() from /storage/Users/currentUser/.conan2/p/b/gtestddcd678b9dadc/b/googletest/src/gtest_main.cc
[==========] Running 14 tests from 3 test suites.
[----------] Global test environment set-up.
[----------] 6 tests from Glob
[ RUN      ] Glob.Basic
[       OK ] Glob.Basic (0 ms)
[ RUN      ] Glob.Asterisk
[       OK ] Glob.Asterisk (0 ms)
[ RUN      ] Glob.QuestionMark
[       OK ] Glob.QuestionMark (0 ms)
[ RUN      ] Glob.Wildcard
[       OK ] Glob.Wildcard (0 ms)
[ RUN      ] Glob.PrefixWildcard
[       OK ] Glob.PrefixWildcard (0 ms)
[ RUN      ] Glob.SuffixWildcard
[       OK ] Glob.SuffixWildcard (0 ms)
[----------] 6 tests from Glob (0 ms total)

[----------] 1 test from ArchiveTest
[ RUN      ] ArchiveTest.Lookup
[       OK ] ArchiveTest.Lookup (0 ms)
[----------] 1 test from ArchiveTest (0 ms total)

[----------] 7 tests from Path
[ RUN      ] Path.Basic
[       OK ] Path.Basic (0 ms)
[ RUN      ] Path.GetBase
[       OK ] Path.GetBase (0 ms)
[ RUN      ] Path.GetDirectoryName
[       OK ] Path.GetDirectoryName (0 ms)
[ RUN      ] Path.Relative
[       OK ] Path.Relative (0 ms)
[ RUN      ] Path.Extension
[       OK ] Path.Extension (0 ms)
[ RUN      ] Path.Suffix
[       OK ] Path.Suffix (0 ms)
[ RUN      ] Path.WithSuffix
[       OK ] Path.WithSuffix (0 ms)
[----------] 7 tests from Path (0 ms total)

[----------] Global test environment tear-down
[==========] 14 tests from 3 test suites ran. (0 ms total)
[  PASSED  ] 14 tests.
――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――

16/16 mpd:TestParsePath         OK               0.05s
――――――――――――――――――――――――――――――――――――― ✀  ―――――――――――――――――――――――――――――――――――――
Running main() from /storage/Users/currentUser/.conan2/p/b/gtestddcd678b9dadc/b/googletest/src/gtest_main.cc
[==========] Running 4 tests from 1 test suite.
[----------] Global test environment set-up.
[----------] 4 tests from ParsePath
[ RUN      ] ParsePath.Basic
[       OK ] ParsePath.Basic (0 ms)
[ RUN      ] ParsePath.Tilde
[       OK ] ParsePath.Tilde (0 ms)
[ RUN      ] ParsePath.Home
[       OK ] ParsePath.Home (0 ms)
[ RUN      ] ParsePath.XDG
[       OK ] ParsePath.XDG (0 ms)
[----------] 4 tests from ParsePath (0 ms total)

[----------] Global test environment tear-down
[==========] 4 tests from 1 test suite ran. (0 ms total)
[  PASSED  ] 4 tests.
――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――

13/16 mpd:test_archive_bzip2    OK               0.20s

10/16 mpd:TestSongFilter        OK               0.30s
――――――――――――――――――――――――――――――――――――― ✀  ―――――――――――――――――――――――――――――――――――――
Running main() from /storage/Users/currentUser/.conan2/p/b/gtestddcd678b9dadc/b/googletest/src/gtest_main.cc
[==========] Running 18 tests from 2 test suites.
[----------] Global test environment set-up.
[----------] 8 tests from StringFilterTest
[ RUN      ] StringFilterTest.ASCII
[       OK ] StringFilterTest.ASCII (25 ms)
[ RUN      ] StringFilterTest.Negated
[       OK ] StringFilterTest.Negated (14 ms)
[ RUN      ] StringFilterTest.StartsWith
[       OK ] StringFilterTest.StartsWith (13 ms)
[ RUN      ] StringFilterTest.IsIn
[       OK ] StringFilterTest.IsIn (12 ms)
[ RUN      ] StringFilterTest.Latin
[       OK ] StringFilterTest.Latin (11 ms)
[ RUN      ] StringFilterTest.Normalize
[       OK ] StringFilterTest.Normalize (11 ms)
[ RUN      ] StringFilterTest.Transliterate
[       OK ] StringFilterTest.Transliterate (10 ms)
[ RUN      ] StringFilterTest.FoldCase
[       OK ] StringFilterTest.FoldCase (11 ms)
[----------] 8 tests from StringFilterTest (110 ms total)

[----------] 10 tests from TagSongFilterTest
[ RUN      ] TagSongFilterTest.Basic
[       OK ] TagSongFilterTest.Basic (10 ms)
[ RUN      ] TagSongFilterTest.Empty
[       OK ] TagSongFilterTest.Empty (10 ms)
[ RUN      ] TagSongFilterTest.Substring
[       OK ] TagSongFilterTest.Substring (10 ms)
[ RUN      ] TagSongFilterTest.Startswith
[       OK ] TagSongFilterTest.Startswith (10 ms)
[ RUN      ] TagSongFilterTest.Negated
[       OK ] TagSongFilterTest.Negated (10 ms)
[ RUN      ] TagSongFilterTest.EmptyNegated
[       OK ] TagSongFilterTest.EmptyNegated (11 ms)
[ RUN      ] TagSongFilterTest.MultiNegated
[       OK ] TagSongFilterTest.MultiNegated (10 ms)
[ RUN      ] TagSongFilterTest.Fallback
[       OK ] TagSongFilterTest.Fallback (10 ms)
[ RUN      ] TagSongFilterTest.EmptyFallback
[       OK ] TagSongFilterTest.EmptyFallback (10 ms)
[ RUN      ] TagSongFilterTest.NegatedFallback
[       OK ] TagSongFilterTest.NegatedFallback (10 ms)
[----------] 10 tests from TagSongFilterTest (107 ms total)

[----------] Global test environment tear-down
[==========] 18 tests from 2 test suites ran. (217 ms total)
[  PASSED  ] 18 tests.
――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――


Ok:                16  
Fail:              0   

Full log written to /storage/Users/currentUser/.conan2/p/b/mpd8f22b09807afb/b/build-release/meson-build/meson-logs/testlog.txt
