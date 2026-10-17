# msgpuck 2.0 适配笔记

## 编译环境

- 构建系统: CMake（上游声明最低 2.8.5 → 补丁提升到 3.15）
- 平台任务: contrib-9002（msgpuck 2.0），claimer Ember5843，认领 2026-09-18T02:30Z
- 目标平台: HarmonyOS PC arm64（clang 15 / musl），本机原生构建；设备 CMake 4.4.3
- 依赖: **无外部依赖**（纯 C99，仅 libc）
- 上游: https://github.com/tarantool/msgpuck （tarantool 官方，tag 2.0）
- 源码 sha256: `01e6aa55d4d52a5b19f7ce9a9845506d9ab3f5abcf844a75e880b8378150a63d`
- 语言实测（R47 lang-preflight）: C（msgpuck.c/hints.c + 头）

## 源码面貌（摸底结论）

- 交付形态: `libmsgpuck.a` + `msgpuck.h`（API 全是头内 inline，库体提供 mp_check 等非 inline 实现）
- 上游测试: `test/msgpuck.c`（约 177 项断言）+ `test/test.c` 支撑，构建为单个二进制
  `msgpuck.test`，由 `test/CMakeLists.txt` 的自定义目标运行（**未用 ctest 注册**）
- CMake 版本声明 2.8.5：CMake 4.x 已移除对 <3.5 的兼容，直接报错

## 移植要点

1. **补丁 0001（CMake 4 兼容）**：① 顶层 `cmake_minimum_required` 2.8.5→3.15；② `test/CMakeLists.txt` 去掉 `cmake_policy(SET CMP0037 OLD)` 与其依赖的自定义目标（CMake 4.4.3 对这两项都直接报错），测试二进制目标名与源文件未改
2. 上游测试不是 ctest 目标：配方在 build() 里直接执行 `test/msgpuck.test`，
   以退出码为判据（失败即配方失败）
3. **补丁 0002（平台差异）**：`test_mp_print` 用 `tmpfile()` 建临时文件，而
   本平台 /tmp 只读 → `tmpfile()` 返回 NULL → test_mp_print 计划 10 项只跑 8 项、
   子测试判失败。改为在 TMPDIR 下 `fopen`（配方运行时把 TMPDIR 指向构建目录内
   `.tmp`），断言数量与语义均未改。与 gtest 的 TMPDIR 补丁同源
3. 构建环境显式清空 LD_LIBRARY_PATH（lld/libxml2 防护，同 libodfgen 系）
4. 消费者测试走公共 API：编码 uint/str/int/double 数组 → mp_check 接受 →
   逐值解码比对 → mp_check 拒绝截断缓冲

## 状态

- [x] 配方四件套
- [ ] 设备实机 conan create + conan-verify + 上游测试 + 消费者测试
- [ ] push / PR / 平台绑定 / 提审
