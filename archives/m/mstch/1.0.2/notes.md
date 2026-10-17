# mstch 1.0.2 编译进度

## 2026-08-31 初始化

### Phase 1: 上游核实
- [x] 官方仓库: https://github.com/no1msd/mstch
- [x] tag: 1.0.2（官方正式 tag，非 fork）
- [x] 源码 tarball: https://github.com/no1msd/mstch/archive/refs/tags/1.0.2.tar.gz
- [x] SHA256: `811ed61400d4e9d4f9ae0f7679a2ffd590f0b3c06b16f2798e1f89ab917cba6c`（实测下载校验）
- [x] License: MIT（tarball 内 LICENSE，Copyright (c) 2015 Daniel Sipka）
- [x] 版本真实性: tarball 与 tag 1.0.2 一一对应，未发现伪造版本号

### Phase 2: 上游测试核查
- [x] `test/CMakeLists.txt`: `enable_testing()` + `add_subdirectory(test)`，开关 `option(WITH_UNIT_TESTS ...)` 上游默认关闭
- [x] 测试框架: Catch v1.12.2（git submodule `vendor/Catch`，pinned SHA `35f4266d...`）
- [x] 测试主程序: `test/test_main.cpp`，注册 `mstch_test` 可执行目标，Catch 单可执行文件跑全部用例
- [x] 测试构成（逐项核实）:
  - 50 个 `MSTCH_TEST` + 8 个 `MSTCH_PARTIAL_TEST` = 58 个 data 测试（对应 `test/data/` 58 个 .hpp）
  - 7 个 `SPECS_TEST`（`vendor/spec/specs/` 下 7 个 .json）
  - 合计 **65 个 ctest 目标**
- [x] CI workflow: `.travis.yml`（上游用 Travis 跑 `make check`，即 ctest）

### Phase 3: 依赖核查
- [x] Boost（`boost::variant`/`boost::variant`/`boost::optional`）— 库的真实依赖，registry 已有
- [x] Catch v1.12.2 / rapidjson / headerize / mustache/spec — 仅上游测试用（submodule），不打包
- [x] 本包已加入依赖: `boost/1.84.0`（registry 现存版本）
- [x] `test_package` 无第三方依赖（纯 mstch 公共 API）

### Phase 4: 构建与测试（OHOS AArch64）
- [x] 工具链: OHOS SDK clang15, target triple `aarch64-unknown-linux-ohos`, libc++/musl
- [x] 上游测试完整执行: `ctest --output-on-failure` → **65/65 通过, 0 失败, 0 跳过**
- [x] test_package 编译链接运行成功（OHOS AArch64 ELF, musl interpreter）
- [x] ELF 验证: `ELF64 / AArch64 / interpreter /lib/ld-musl-aarch64.so.1`

### Phase 5: patch 记录
- [x] `fix-cmake-minimum-version.patch`: `cmake_minimum_required` 3.0.2 → `3.5...3.31`
  - 原因: OHOS SDK CMake 3.22+ 对 `VERSION 3.0.2` 报错/警告，且低版本下
    CMakeToolchain 生成的 toolchain 文件用到了需要更高 cmake 版本的特性
  - 不改变任何模板渲染业务逻辑，仅构建系统兼容
- [x] 无其他 patch；`-DBOOST_SP_NO_PTHREAD_SETCANCELSTATE` 通过 conanfile
  `extra_cxxflags` 注入（非 patch）

## 备注
- mstch 是**编译型静态库**（非 header-only）: `libmstch.a`，源码 `src/mstch.cpp` 等多 TU 编译
- 上游 CMake 无 shared library 选项，只产 static
- GitHub tag tarball 不含 submodule 内容（gitlink 不物化），Catch/rapidjson/headerize/spec
  需在 recipe 的 build() 中按 pinned SHA 拉取并解压到 `vendor/`，仅用于编译测试
- musl 缺 `pthread_setcancelstate`，boost::shared_ptr 相关代码需 `BOOST_SP_NO_PTHREAD_SETCANCELSTATE`

## 2026-08-31 修复: CI 改写 conandata URL 未恢复 + 文档计数错误

### 现象
1. CI 的 pre-download 机制把 conandata.yml 中全部 11 处 URL 改写为
   CI 曾临时改写源码地址，且前次会话结束时未恢复官方 HTTPS URL
   （相关本地缓存已清理）
2. 1.0.2/README.md 与 manifest.yaml 中上游测试计数写作 "64 个 MSTCH_TEST/MSTCH_PARTIAL_TEST"，
   与实测不符

### 修复
1. conandata.yml: 通过 predl 文件名前缀 = md5(原URL)[:8] 离线反推全部 11 个原始 URL，
   恢复为官方 GitHub HTTPS 地址，并重新下载实测 SHA256 一致
2. 文档计数修正为实测值: 50 MSTCH_TEST + 8 MSTCH_PARTIAL_TEST（58 data）+ 7 SPECS_TEST = 65
3. manifest.yaml 中测试开关笔误修正为开启状态（与 recipe 实际行为一致）
4. patch 文件 trailing whitespace 清理（git diff --check 干净），
   并实测 `patch --dry-run` 可干净应用于上游 tarball
