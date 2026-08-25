# libnymphcast v0.2.1 适配笔记

## 编译环境
- 构建系统: Makefile（`make lib`，无 configure/CMake）
- 编译器: clang/clang++ 15.0.4 (aarch64-unknown-linux-ohos)
- 依赖: NymphRPC v0.1.1（头 `nymph/nymph.h` + `-lnymphrpc`）+ POCO 1.15.3（PocoNet/PocoUtil/PocoFoundation/PocoJSON）
- 版本状态: built（权威 CI 真机 PASS；conan verify 通过未 upload）

## 构建步骤（Conan 方式）
1. conandata.yml: `https://github.com/MayaPosch/libnymphcast/archive/refs/tags/v0.2.1.tar.gz`
   SHA-256 = `4a824b3aef22e1bc32d4b4fcc6158e7c0e0d674155b031c12a5bdd0c3e534cf0`
   （builder 于设备端经 gh-proxy 独立复核一致；scout 曾 codeload/双代理三路径一致）
2. patches/0001-Makefile-static-only.patch: 让 `make lib` 只构建静态库
   （libnymphrpc.a 为非 PIC 静态包，上游共享 .so 目标在 OHOS 链接报
   R_AARCH64_ADR_PREL_PG_HI21 relocation 错；本库只输出静态 .a）
3. `make lib -j1`，传入:
   - CXX=/data/service/hnp/bin/clang++（conan conf dict `tools.build:compiler_executables`）
   - AR=llvm-ar
   - CXXFLAGS: `-I src` + 依赖 include（nymphrpc/poco/libcxx）+ `-std=c++17`
   - LIBS: `-lnymphrpc -lPocoNet -lPocoUtil -lPocoFoundation -lPocoJSON -pthread`
4. 产物: `lib/aarch64-unknown-linux-ohos/libnymphcast.a`

## 关键点
- Makefile 的 `$(wildcard src/*.cpp)` + `$(notdir)` + `addprefix obj/static/$(ARCH)` 在 OHOS 实测与 nymphrpc 一致：对象落在 `obj/static/<arch>/src/*.o`（nymphrpc build 日志确认）。
- 公开头 `src/nymphcast_client.h` → `include/`；`#include <nymph/nymph.h>` 需 nymphrpc 包 include **根目录**（nymphrpc 的 cpp_info.includedirs=["include/nymph"]，父级 include/ 由 conanfile `_dep_includedirs()` 补全）。
- make `-j1`（OHOS SELinux 禁 FIFO）。

## 依赖协调（R2）
- ohpcd remote **无** `nymphrpc/*`（`conan list "nymphrpc/*" -r ohpcd` → 0）。
- 本地 conan cache 有 `nymphrpc/v0.1.1` 与 `nymphrpc/0.1.1`（同包 d427270a…）。
- 权威 CI 依赖解析：需 nymphrpc recipe 先合入官方 main 或上传 ohpcd，否则 L0i/R36 depchain_missing。
  已记录协调方案（见 round-1.md），不属本 implement 轮次处理范围。

## 上游测试
- 上游无 `test/` 目录、无 CI workflow；`make test` 悬空 target（test-client/test-server 子目录不存在）。
- 上游测试总数 = 0，验证走 test_package 消费层（9 断言，构造/setters/数据结构/枚举）。
