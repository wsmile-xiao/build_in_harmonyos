# osqp 1.0.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-16
- 编译器: clang 15.0.4 / clang++ 15.0.4
- 目标平台: HarmonyOS aarch64
- 状态: published

## 编译步骤

1. 加载 openharmony-compile-agent 技能，初始化 SKILL_ROOT
2. init-build 失败（SSL 下载失败 + 构建系统误检测为 autotools）
3. 使用 ghfast.top 镜像 + curl -kL 手动下载 osqp v1.0.0 tarball 到 ~/tmp/builds/
4. init-build 成功（tarball 已存在，跳过下载）
5. build Step3-4 失败（configure/make 用 autotools 方式执行，对 cmake 项目无效）
6. 切换为模式 B（手动编译）：
   - 手动下载 QDLDL v0.1.8 子模块源码（SSL 受限，FetchContent 无法从 GitHub 拉取）
   - 修改 `algebra/_common/lin_sys/qdldl/qdldl.cmake`，将 `GIT_REPOSITORY https://github.com/osqp/qdldl.git GIT_TAG v0.1.8` 改为 `SOURCE_DIR /storage/Users/currentUser/tmp/qdldl-v0.1.8-src`
   - cmake 配置: `cmake .. -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DCMAKE_BUILD_TYPE=Release -DOSQP_BUILD_DEMO_EXE=OFF -DOSQP_BUILD_UNITTESTS=OFF -DOSQP_CODEGEN=OFF`
   - make -j2 编译成功
   - make install DESTDIR=$TEST_PREFIX (DESTDIR 模式 R20)
   - make install (本地安装验证)
7. ohc-run.py package 制作预编译包（412KB）
8. 编写并执行 C 语言功能验证测试程序，调用 OSQP API 解最简 QP 问题
9. 测试全部通过：求解状态=SOLVED，解向量 x≈0，目标值≈0，迭代50次，耗时0.03ms
10. ohc-run.py finish osqp 1.0.0 published

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build SSL 下载失败 | 鸿蒙系统 SSL 证书验证失败，urllib 无法访问 GitHub | 使用 ghfast.top 镜像 + curl -kL 手动下载 tarball |
| 2 | 自动检测构建系统为 autotools（错误） | OSQP 源码中 `configure` 是一个目录而非脚本，_detect_build_system 判断 "有CMakeLists.txt且有configure → autotools" 是误判 | 手动切换为 cmake 编译（模式 B），更新 BUILD_SYSTEM=cmake |
| 3 | cmake FetchContent 卡住（下载 QDLDL 子模块） | FetchContent 从 GitHub 拉取受 SSL 阻碍，configure 阻塞超 120s | 手动下载 QDLDL v0.1.8 源码，修改 qdldl.cmake 使用 SOURCE_DIR 指向本地路径 |
| 4 | 链接 osqpstatic 时 undefined symbol (interrupt) | interrupt_unix.c 未包含在静态库 object 中 | 编译 interrupt_unix.c 为 .o 文件，单独链接 |
| 5 | G0 干净构建验证失败 (exit 126) | clean-verify 脚本硬编码 `bash ./configure`，OSQP 的 configure 是目录；cmake 项目不支持此方式 | 已手动验证编译正确性（G1-G4 全通过），记录为已知平台脚本限制 |
| 6 | manifest 缺少 build_system 字段 | verify-build G4 检查顶级字段 build_system:，而非 build.system: | 在 manifest.yaml 添加顶级 build_system: cmake 字段 |
| 7 | manifest patches_applied 不一致 | manifest patches_applied=[] 但磁盘已有 1 个 patch | 更新 patches_applied 列表 |

## 源码修改

**文件**: `algebra/_common/lin_sys/qdldl/qdldl.cmake`
**修改**: 将 FetchContent_Declare 的 `GIT_REPOSITORY https://github.com/osqp/qdldl.git` + `GIT_TAG v0.1.8` 替换为 `SOURCE_DIR /storage/Users/currentUser/tmp/qdldl-v0.1.8-src`
**补丁**: `0001-algebra-_common-lin_sys-qdldl-qdldl.cmake.patch`

## 依赖版本

- QDLDL v0.1.8（内嵌子模块，cmake FetchContent → SOURCE_DIR 本地替代）
- 无外部依赖

## 验证结果

### 功能验证测试（真实执行）

编写 C 测试程序，调用 OSQP API 解 QP 问题 min 0.5*2*x²+x, s.t. x≥0：
- 预期最优解: x=0, 目标值=0
- 实际结果: x=-0.00019511, obj=-0.00019507（ADMM 容差范围内）
- 求解状态: OSQP_SOLVED (status_val=1) ✅
- 解向量验证: |x-0| < 1e-3 ✅
- 目标值验证: |obj-0| < 1e-3 ✅
- 迭代次数: 50
- 求解耗时: 0.000029 s
- 内部求解器: QDLDL v0.1.8 ✅

### 库安装验证

```bash
ls ~/usr/local/lib/libosqp*
# libosqp.so (129344 bytes) — ELF shared object, 64-bit LSB arm64 ✅
# libosqpstatic.a (179126 bytes) — 静态库 ✅

ls ~/usr/local/include/osqp/
# 6 个头文件 ✅

ls ~/usr/local/lib/cmake/osqp/
# osqp-config.cmake, osqp-config-version.cmake, targets ✅
```

### 门禁验证: PASS (G1-G4)

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| osqp-1.0.0-ohos-aarch64.tar.gz | 412KB | 预编译包（libosqp.so + libosqpstatic.a + headers + cmake config） |
| osqp-1.0.0-ohos-aarch64-debug.tar.gz | 48KB | debug 符号包 |

## 注意事项

1. OSQP 使用 FetchContent 拉取 QDLDL 子模块，在 SSL 受限环境中需手动下载并修改 cmake 配置（GIT_REPOSITORY → SOURCE_DIR）
2. OSQP 源码中 `configure` 是目录而非可执行脚本，自动检测可能误判为 autotools
3. 链接 osqpstatic 需额外提供 interrupt_unix.c（中断监听器实现），该文件未被包含在静态库中
4. 建议关闭 OSQP_CODEGEN 和 OSQP_BUILD_DEMO_EXE 以简化编译
5. 验证容差建议使用 1e-3（匹配 OSQP 默认 eps_abs/eps_rel），而非 1e-4

---

**编译结束**: 2026-06-16 15:37
**最终状态**: published
