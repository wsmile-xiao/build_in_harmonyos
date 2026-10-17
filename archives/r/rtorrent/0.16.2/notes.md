# rtorrent 0.16.2 — Adaptation Notes

## Software
- **Name**: rtorrent
- **Version**: 0.16.2
- **Description**: rTorrent BitTorrent client (ncurses-based)
- **Upstream**: https://github.com/rakshasa/rtorrent
- **License**: GPL-2.0-or-later

## Build System
- Autotools (configure + make)
- C++17 required (AX_CXX_COMPILE_STDCXX)
- API_VERSION: 18

## Dependencies
- **libtorrent/0.16.17** (rakshasa): BitTorrent library, found via pkg-config (libtorrent >= 0.16.2)
- **ncurses/6.5**: Terminal UI, found via AX_WITH_CURSES (ncursesw preferred)
- **cppunit/1.15.1** (test only): CppUnit test framework
- Transitive: curl/8.15.0, openssl/3.5.6.1, zlib/1.3.1.1 (via libtorrent)

## Patches
1. **0001-config.guess.patch**: Replace config.guess with version that detects HarmonyOS/OHOS (aarch64-unknown-linux-ohos)
2. **0003-config.sub.patch**: Replace config.sub with version that recognizes `ohos` as a valid OS
3. **0004-src-display-attributes.h.patch**: Undef curses macros (refresh, erase, clear) that conflict with C++ method names in src/display/attributes.h

Note: The historical 0002-config.h.patch (pre-generated config.h bypassing configure) is NOT used. Instead, configure runs properly with the OHOS compiler wrapper (signing conftest executables), following the proven pattern from libtorrent/0.16.17.

## OHOS-Specific Adaptations
- **Compiler wrapper**: Signs conftest executables during configure (same approach as libtorrent/0.16.17)
- **Autoreconf**: Regenerates configure from configure.ac with updated autoconf/automake
- **umask fix**: configure's `umask 077` changed to `umask 022` (HMDFS setgid semantics)
- **--disable-execinfo**: OHOS does not consistently expose execinfo.h
- **Explicit triplet**: --build/--host=aarch64-unknown-linux-ohos
- **Test environment**: TESTS_ENVIRONMENT set to explicit shell path (HMDFS rejects libtool wrapper shebangs)

## Build Commands
```bash
source .build-context-rtorrent-0.16.2
cd $BUILD_SRC_DIR
autoreconf --install --force --verbose
./configure --build=aarch64-unknown-linux-ohos --host=aarch64-unknown-linux-ohos --disable-execinfo --disable-debug
make -j1
make check
```

## Known Issues
- automake not found on device directly; provided via conan tool_requires
- cc/c++ not found; only clang/clang++ available
- rtorrent is an interactive ncurses application; test_package runs `-h`/`-n -h` which print help and exit(0)

## libtorrent 0.16.17 Functional Limitations (upstream API removals)
Verified against `torrent/tracker/dht_controller.h` and `torrent/runtime/proxy_manager.h` in libtorrent 0.16.17; fixes follow the approach of upstream rtorrent 0.16.23:
- **DHT bandwidth throttling**: `DhtController::set_upload/download_throttle` no longer exist. `dht.throttle.name` no longer applies a throttle to the DHT channel (patch 0006 removes the dead calls; the setting stays informational).
- **DHT byte counters**: `statistics_type` no longer carries `down_rate`/`up_rate`. `dht.statistics` reports `bytes_read`/`bytes_written` as 0 and the periodic log line omits the bytes fields — identical to upstream rtorrent 0.16.23.
- **Proxy address format**: proxy handling moved to `torrent::runtime::ProxyManager`. `network.proxy_address.set` / `network.http.proxy_address.set` now require URL form `socks5://host:port` / `http://host:port` (the old `host:port` form is rejected by libtorrent itself); commands are wired to the real `proxy_manager()` APIs, not stubs (patches 0010/0020).

---

**编译结束**: 2026-08-28 01:30
**最终状态**: built

**2026-09-18 修复轮**（PR CI failed: L0 no_test_sources）:
- test_package/ 新增 test.sh（L0c 测试源文件门禁）：`rtorrent -h` 验证 usage banner、`rtorrent -n -h` 验证跳过 rtorrent.rc，conanfile.py 经 bash 包装执行
- 删除误提交的 conandata.yml.ghfast-bak；源码 URL 恢复官方 github.com（R39，CI 自带镜像回退）
- 0006: 删除未使用 throttles 变量；日志去掉 bytes 字段、dht.statistics 置 0（对齐上游 0.16.23）
- 0009: retrieve_d_base_filename 改用局部 std::string 拷贝（对齐上游，消除取地址写法争议）
- 0010/0020: 代理命令接到 runtime::ProxyManager 真实实现（原为静默 stub），set_proxy_address 改为 set_proxy_url 透传
- 0005（增强）: SCgiTask 回调取消迁移到 libtorrent 0.16.17 的 callback_id 机制（close 时 cancel_callback_and_wait 等待 worker/main 两线程排队回调完成，receive_call 的 3 处 callback_interrupt 均携带 m_callback_id），保留原指针取消的 UAF 防护语义，对齐上游 0.16.23；print_help 改用 std::_Exit(0)——torrent::initialize() 在 -h 解析前已启动 disk/net/tracker 三个线程，exit(0) 的静态析构与在跑线程竞争导致 OHOS 上间歇性 SIGABRT（本地实测 30 次约 3 次崩溃，CI #50132 即此问题）
- 0022（增强）: 测试夹具 tearDown 不再销毁从未 start 的 TestMainThread（改为 release() 有意泄漏）——libtorrent 0.16.17 的 Thread 析构对"初始化但未启动"的线程存在竞态，OHOS 上约 15% 概率段错误（本地压测复现，修复后 0/100）；测试程序为短生命周期进程，泄漏无副作用（CI #50141 的 make check 失败即此问题）
- 0022: 上游 CppUnit 测试助手适配 libtorrent 0.16.17（移除 this_thread::event_* mock、Thread/NetworkConfig 命名空间迁移，对齐上游 0.16.23 方案）；conanfile 取消 OHOS 下的 make check 跳过（本机为原生构建非交叉编译），实测 rtorrent_Test_Rpc 23/23 + rtorrent_Test_Src 3/3 全部通过

