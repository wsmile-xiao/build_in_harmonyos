- **三方库名称**：libogg
- **上游版本**：v1.3.5
- **上游仓库地址**：https://github.com/xiph/ogg
- **适配路径**：路径 A（基础适配）
- **使用知识库**：有（E103 bump-cmake-minimum-version、E002 set-env-var、E346 OHOS make SHELL 拒绝，另参考 critnib/1.1 的 direct-cc 先例与本包 libogg/1.3.6.2 已验证配方）

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 2 | 来源：`CMakeLists.txt` 中 `if(BUILD_TESTING)` 注册 `test_bitwise`（src/bitwise.c）与 `test_framing`（src/framing.c），均以 `-D_V_SELFTEST` 编译；`src/Makefile.am` 的 `check_PROGRAMS` 声明同一批程序 |
| 集成测试 | 0 | 上游无集成测试目录，不存在 `tests/` |
| 其他测试 | 0 | 上游亦无 `pytest`/`ctest` 之外的测试框架 |
| **合计** | **2** | |

> 说明：上游 `BUILD_TESTING` 默认关闭，直接跑 `ctest` 会发现 0 条用例。因此本适配按上游同样的源文件、宏定义与头文件布局显式编译两个自测程序并直接执行，以真实退出码为准。

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 2 | 不变 | 上游 `test_bitwise` / `test_framing` 全部执行并通过 |
| 集成测试 | 0 | 不变 | 上游无，未新增同类 |
| 鸿蒙特有测试 | 1 | 新增 | 针对鸿蒙平台新增「安装后包」端到端验证：消费者的完整端到端工作流（流初始化 → 灌包 → flush 成页 → 解码还原 → 逐字节比对），4 个阶段，链接并使用 Conan 包实际产物 |
| **合计** | **3** | **+1** | |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

> 两个自测程序均使用上游未修改的源文件 `src/bitwise.c`、`src/framing.c`，沿用上游的 `-D_V_SELFTEST` 宏定义与 include 布局（`-Isrc -Iinclude -I<generated>`），未对上游源码与测试用例做任何改动，故本版本不引入 `patches/`。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

> - **补全的测试范围**：新增 1 个「安装后包」端到端验证用例（`test_package/test_package.c`），覆盖完整端到端消费者工作流，共 4 个阶段。
> - **补全原因**：上游的两个自测程序是把 `.c` 源码以 `_V_SELFTEST` 宏**自包含**编译后运行的，全程不链接 libogg 库，因此无法证明「Conan 打包并安装后的头文件和库是否真的可被下游消费者使用」。鸿蒙平台还需要额外验证动态库可加载执行，这部分上游完全没有覆盖。
> - **新增测试文件清单**：
>   1. `test_package/test_package.c` — 端到端消费者验证：链接安装后的 libogg，`ogg_stream_init` → `ogg_stream_packetin` + `ogg_stream_flush` 生成 Ogg 页 → `ogg_stream_pagein` + `ogg_stream_packetout` 由第二个流解码 → `memcmp` 逐字节比对还原结果；每阶段打印一条 `CHECK n OK`，任一阶段失败即以不同非零码退出。判定要求「退出码 0 且 4 条 CHECK 行齐全」，因此空输出桩无法伪造通过。

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：2/2（100%）
- 新增测试用例通过率：1/1（100%）

`conan-verify` 八道门禁全部 PASS：G0（预构建风险评估）、G1（配方完整性）、G2（conan create 干净构建）、G3（系统同名库隔离 R26）、G4（产物完整性）、L2、L4、L5。

```
HMBS_UPSTREAM_TEST_RESULT={"status":"passed","framework":"official-selftest-programs",
  "discovered":2,"executed":2,"passed":2,"failed":0,"skipped":0}

CHECK 1 OK: ogg_stream_init (encoder)
CHECK 2 OK: ogg_stream_packetin + ogg_stream_flush
CHECK 3 OK: ogg_stream_pagein + ogg_stream_packetout
CHECK 4 OK: payload round-trip identical (22 bytes)
libogg installed-package round trip passed (4/4 stage lines)
HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"discovered":1,"passedCount":1}
```

另设有可证伪性校验：同一 runner 下编译一个必然返回 1 的桩程序，必须被判定为失败。本轮该桩被正确识别为红灯，证明上述「全部通过」非空转结论。

## 补充说明

1. **版本号说明（R37）**：上游 `libogg 1.3.5` 在本仓库已有已发布配方，而制品仓不支持同版本多 revision 并存、修改已发布配方需递增版本号，因此本次以 `X.Y.Z.N` 形式落地为 **1.3.5.1**，构建对象仍是**同一份未经修改的上游 1.3.5 源码**（sha256 与已发布版本一致）。这与本包既有的 `1.3.6 → 1.3.6.1 → 1.3.6.2` 命名惯例一致。

2. **为何不走 CMake**：历史归档记录 1.3.5「cmake 配置成功」，但该结论产生于旧版 cmake 环境。当前 cmake 为 4.1.2，而上游 `CMakeLists.txt` 声明 `cmake_minimum_required(VERSION 2.8.12)`，低于其最低支持版本（对应 E103）；同时本包 1.3.6.2 已实测 CMake 的编译器识别探针在 OHOS clang 驱动上失败（同类问题另见 E346）。由于 libogg 仅有两个翻译单元（`src/bitwise.c`、`src/framing.c`），本配方沿用 critnib/1.1 与本包 1.3.6.2 已验证的 **direct-cc 路线**：绕过全部 CMake 探针，直接用 profile 编译器编译，因此比反复叠加 CMake 补丁标志更稳定。

3. **SONAME 不硬编码**：动态库 SONAME 在构建时从 `configure.ac` 解析 `LIB_CURRENT=8 / LIB_REVISION=5 / LIB_AGE=8`，得到 `SOVERSION = 8 - 8 = 0`，产物为 `libogg.so.0` 与 `libogg.so.0.8.5`。上游日后 bump  versioning 时无需修改配方。

4. **产物完整性**：除静态/动态库外，一并安装 `include/ogg/{ogg.h,os_types.h,config_types.h}`、`lib/pkgconfig/ogg.pc` 与 `lib/cmake/Ogg/{OggTargets,OggConfig,OggConfigVersion}.cmake`，对外提供 `Ogg::ogg` 目标与 `pkg_config_name=ogg`，接口与上游 CMake install 保持一致。`config_types.h` 由编译期类型探针生成，等价复现上游 `CheckSizes` + `check_include_files` 的结果。

5. **零第三方依赖**：已通过 `W0` 预检确认，本包仅依赖 libc，`dependencies: []`。

6. **已知限制**：Windows 仍保留遗留 CMake 消费者路线（MSVC 风格编译器需要 CMake 处理 flags），本次未在 Windows 上验证；目标是 OHOS aarch64。
