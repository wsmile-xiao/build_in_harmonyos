# Test Report — nymphcast 0.2-alpha0 (OHOS aarch64)

**Date**: 2026-09-03
**Profile**: ohos-aarch64 (clang 15.0.4, libc++, musl-like OHOS libc, armv8)
**Build**: conan create --build=missing（W3 本地 CI 模拟通过，.ci-result.json exit_code=0）

## 上游测试（src/test/Makefile，7 项）

| # | 测试 | 执行方式 | 实测 exit code | 结论 |
|---|------|---------|---------------|------|
| 1 | test_databuffer_mm | 手动镜像官方 Makefile 命令编译+运行（OHOS clang++，dummy env 不需要） | 0 | ✅ 通过（wrap-around/reset/seek 全过） |
| 2 | test_screensaver | build() 内编译+受控运行（SDL_VIDEODRIVER=dummy, timeout 120s） | 0 | ⚠️ 仅 abort 路径（"Found 0 wallpapers. Abort screensaver due to lack of images."），上游测试从不调用 setDataPath，无真渲染 |
| 3 | test_ffplay_local_file | build() 内编译+受控运行（dummy SDL + ffmpeg 生成测试媒体, timeout 150s） | 124 | ❌ 上游 teardown 挂起（完整播放流程完成后 "Terminating player..." 处 FUTEX 阻塞；上游 event loop quit push 被注释；SDL dummy/offscreen 双驱动均复现，非 OHOS 适配缺陷） |
| 4 | test_databuffer | 手动镜像官方 Makefile 命令编译 | 1（编译失败） | ❌ 上游缺陷：test_databuffer.cpp:32 调用 `DataBuffer::setDataRequestCondition()`，该方法在 v0.2-alpha0 与 master 的 databuffer.h 中均不存在 |
| 5 | test_databuffer_mport (test_db_mp) | 手动镜像官方 Makefile 命令编译 | 1（编译失败） | ❌ 上游缺陷：同上 setDataRequestCondition 缺失 + NymphLogger 未声明（nymph_logger.h 不在源码树）+ 官方 Makefile target 缺 -I../server |
| 6 | test_file_seeking.sh | build() 内受控运行（timeout 60s） | 1 | ❌ 上游 test_server build-blocked（stale pre-2021 nymphrpc API，NymphString/NymphBoolean 旧值类型已被官方移除，上游 NymphCastServer.cpp 已迁移新 API 独留 test_server 未更新）→ "inaccessible or not found" |
| 7 | test_file_transfer.sh | build() 内受控运行（timeout 60s） | 1 | ❌ 同上：test_server 缺失，"Connecting to remote server failed: 127.0.0.1:4004" |

**上游通过率：1/7（14.3%）**——唯一完整通过项为 test_databuffer_mm。其余 6 项失败均归因于上游源码缺陷或上游测试环境依赖（GitHub raw 双版本核验证据见 notes.md），非 OHOS 适配引入。

## 正向数据点（非官方测试项）

- nymphcast_client 编译+链接成功；localhost server+client 200KB blocks 端到端传输实测成功（前人 round-7 证据 + 本次 conanfile 内 client 构建链接 OK）

## 鸿蒙特有测试（test_package，1 项）

| 测试 | 内容 | 断言数 | 结果 |
|------|------|--------|------|
| test_package/test.cpp | 编译真实探针，popen 调用打包产物 nymphcast_server --version，断言 exit 0 + "NymphCast version:" 横幅 | 3 | ✅ PASS（conanrun env + OHOS 工具链 libc++ 运行时路径注入） |

**新增通过率：1/1（100%）**

## W3 本地 CI 模拟

- setup.sh: 通过
- build_and_test.sh: conan create + L1 测试执行验证 通过
- .ci-result.json: exit_code=0, integrity_hash=9931bda005bbb8a6, log_sha256=c13dda7371ba5cb618b7790f307faa012426d09e1c8b56c729ae5c0e57b06d71
