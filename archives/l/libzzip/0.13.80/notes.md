# libzzip 0.13.80 — 适配笔记

## 平台
- 目标: OpenHarmony PC (aarch64, musl, clang 15)
- 构建系统: cmake (顶层 CMakeLists + zzip/ bins/ test/ 子目录)

## 上游身份
- **libzzip = zziplib**：gdraheim/zziplib v0.13.80，官方 URL
  https://github.com/gdraheim/zziplib (tarball refs/tags/v0.13.80.tar.gz)
- SHA256 `21f40d111c0f7a398cfee3b0a30b20c5d92124b08ea4290055fbfe7bdd53a22c` (1192948 字节)
- License: **MPL-1.1 OR LGPL-2.1-or-later**（核心库默认 MPL，LGPL 作为可选授权，
  见仓库根 COPYING.MPL / COPYING.LIB；CMake 版权字段写 "MPL-1.0-or-later"）

## 编译步骤
1. 依赖: zlib/1.3.1.1 (Conan 仓库 OHOS 包)
2. cmake 配置: ohos.toolchain.cmake + ZLIB_ROOT 指向 Conan zlib 包
   -DZZIPDOCS=OFF -DZZIPSDL=OFF -DZZIPBINS=ON -DZZIPTEST=ON
3. cmake --build --target <4 libs + 13 bins>（不跑 test/ 的 sfx ALL 目标, 见下）
4. cmake --install → 4 个 .so + bin/ 工具 (zzcat/unzzip/unzip-mem/…) + CMake config

## SONAME（关键适配）
- 现象: HarmonyOS 无 CMake Platform/HarmonyOS 模块 → `CMAKE_SHARED_LIBRARY_SONAME_C_FLAG`
  为空。上游 zzip/CMakeLists.txt 已设 `SOVERSION ${VERNUM}`(=13)，但链接器收不到
  `-Wl,-soname,` 标志 → 产物 `libzzip-0.so` 无 DT_SONAME（同 libharu E298 问题）。
- 修复: configure 期注入 `-DCMAKE_SHARED_LIBRARY_SONAME_C_FLAG=-Wl,-soname,`（零 patch）。
  注入后 4 个库都有 `SONAME libzzipX-0.so.13`；bins 的 DT_NEEDED 从相对路径
  `../zzip/libzzip-0.so` 变成规范 SONAME。

## 产物
- libzzip-0.so.13.0.80 (+ .so.13/.so 软链), 同规则 4 组
- include/zzip/*.h (20 个头文件)
- lib/cmake/zziplib/{zziplib-config.cmake,zziplibTargets.cmake}
- bin/: zzcat zzdir zzxorcat zzxordir zzxorcopy zzobfuscated zziptest
        unzzip unzzip-mix unzzip-big unzzip-mem unzip-mem zzip (13 个)
- CMake target: zziplib::libzzip (+ ::libzzipfseeko / ::libzzipmmapped / ::libzzipwrap)

## 官方测试 (上游 test/zziptests.py)
- python unittest，230 项；部分依赖宿主 infozip zip/unzip（生成 fixture 与期望输出）
- 运行约束（全部实测）:
  ① cwd 须为 <build>/test；`-b ../bins` **必须传相对路径** —— 用例 20595/65485/65486
    执行 `cd tmp.x && ../{exe}`，绝对路径会拼成 `..//abs/path` → 127
  ② bins DT_NEEDED 是 SONAME libzzip-0.so.13 → 运行测试须
    LD_LIBRARY_PATH=<build>/test/zzip（把版本化 .so 复制进去并补 .so.13/.so 软链）
  ③ **sfx ALL 目标**: 全量 `cmake --build` 会先 exec `zzipsetstub` 造自解压演示文件,
    SONAME 注入后其 DT_NEEDED 无路径且无 LD_LIBRARY_PATH → 127 中断 make。
    故 build 用 `--target` 只构建 4 库 + 13 bins, 不触发 test/ 目标
  ④ test_81000 (SFX): OHOS 内核拒绝 exec "非 ELF magic 开头" 的 zip-stub 拼接文件
    (exit 126/EPERM)——环境限制非库 bug。fnmatch 无补集语法, 按 `def test_<n>_` 枚举
    生成 229 个精确 pattern 显式排除
  ⑤ 联网 CVE 测试 134 项: `--downloads=OFF` 跳过（CI 无外网）
- 本机实跑结果: **Ran 229 tests — OK (skipped=134), 0 fail 0 error**

## Conan
- name: libzzip（目录名与任务要求一致；上游项目名 zziplib，cmake_file_name=zziplib）
- cpp_info.libs: zzip-0 zzipfseeko-0 zzipmmapped-0 zzipwrap-0
- cmake_target_name: zziplib::libzzip；pkg_config_name: zziplib
- 不创建 commands.json（纯 library，bin/ 工具为示例程序非 CLI 产品）

## 状态
built（CI conan create + test 通过）
