# fftresampler 2.8 适配笔记

## 编译环境
- 构建系统: cmake（上游 CMakeLists.txt，project(FFTResampler LANGUAGES C)）
- 编译日期: 2026-09-26
- 编译器: clang 15.0.4 / clang++（aarch64 OHOS）
- 状态: built

## 编译步骤

1. `init-build fftresampler 2.8`：源码来自官方仓库提交 0a9720bc05105ccf11764be0d22721238306c793（2019-05-02，上游无正式 tag/release；GitHub tags/releases API 均为空，已核验）
2. `lang-preflight`：task=cpp，detected=c（c↔cpp 兼容族，通过）
3. 探索编译：
   - `cmake .. -DCMAKE_POLICY_VERSION_MINIMUM=3.5`（上游 cmake_minimum_required(2.8) 与 CMake 4.1.2 冲突，策略参数绕过，未改上游文件）
   - `make -j1`（HMDFS 上 make jobserver 不可用，须 -j1）
   - 产物 `FFTResampler` 可执行文件
4. 功能验证：生成 0.05~1s 44100Hz 正弦 WAV → `FFTResampler in.wav out.wav 8000` → exit 0，输出 IEEE float WAV（fmt=3, mono, rate=8000）有效
5. `conan-init` 生成配方骨架 → 重写为 CMake 应用型配方（R38：产物为可执行文件，软件级声明 commands.json）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 下载 github.com 仓库 URL 返回 HTML | 需归档 URL（master.zip 302 重定向） | `--url=<repo>/archive/refs/heads/master.zip` |
| 2 | cmake 配置失败 "Compatibility with CMake < 3.5 has been removed" | 上游 cmake_minimum_required(2.8)，本机 CMake 4.1.2 | 配方 generate() 注入 `CMAKE_POLICY_VERSION_MINIMUM=3.5`（最小可逆修复） |
| 3 | `make -j2` 报 jobserver mkfifo Operation not permitted | HMDFS 限制 | 一律 `-j1`（R9） |
| 4 | conan-init 生成 Autotools 模板 | 构建系统误判 | 重写为 CMakeToolchain 应用型配方 |

## 源码修改

无补丁。上游 CMakeLists.txt 无 install() 规则，配方 package() 直接 copy `FFTResampler` 二进制到包 bin/。

## 依赖版本

无第三方依赖（仅系统 libm，target_link_libraries 已含 -lm）。

## 验证结果

- 上游测试：无（上游无 tests/ 目录、无 ctest/pytest 注册，R51 清点：源码树仅 8 文件）
- test_package（conan create 内实跑）：生成 WAV → FFTResampler 重采样 → 校验退出码 + 输出 WAV 头，3/3 PASS

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | CMake 应用型配方 |
| conandata.yml | commit 固定官方源 + SHA-256 |
| test_package/ | 消费者验证（test.sh 真实调用二进制） |
| commands.json | 软件级命令行工具声明（R38） |

## 注意事项

- 上游仓库 cpuimage/FFTResampler 已多年未更新（最后一次提交 2019-05-02），无发布标签；版本 2.8 为任务头指定版本，源码固定到 master 最新提交
- HMDFS 大小写不敏感：本库路径 archives/f/fftresampler 无大小写冲突
---

**编译结束**: 2026-09-26 22:18
**最终状态**: built
