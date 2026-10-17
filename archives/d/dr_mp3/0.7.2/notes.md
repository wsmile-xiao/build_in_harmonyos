# dr_mp3 0.7.2 适配笔记

## 编译环境
- 构建系统: cmake（上游构建系统；本库 header-only，配方无 build 步骤）
- 编译日期: 2026-08-30
- 编译器: clang/clang++（OHOS 工具链 /data/service/hnp/bin/clang 15.0.4）
- 状态: built（conan-verify 通过后由 finish 定稿）

## 编译步骤

header-only 库，无 configure/make 步骤：

```bash
# 1. init-build 下载官方 tarball (tag mp3-0.7.2) 并解压
# 2. conan-init 生成骨架后按 header-only 形态改写配方
#    - conanfile.py: source() 拉 tarball, package() 拷 dr_mp3.h + LICENSE
#    - package_type = "header-library", cpp_info.libs = []
# 3. test_package: test.c 定义 DR_MP3_IMPLEMENTATION 后包含 dr_mp3.h,
#    解码源内构造的真实 MPEG1 Layer III 帧 (128kbps/44.1kHz/立体声, 417 字节),
#    低层 drmp3dec_decode_frame + 高层 drmp3_init_memory/read_pcm_frames_f32, 11 断言
# 4. conan-verify: conan create (-pr:h/-pr:b=ohos-aarch64) + G0-G4 + L2/L4/L5
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 按 autotools 模板跳过配方生成 | 模板库无 header-only 模板，且 manifest 模板默认 build_system 识别为 autotools | 参照同仓 abletonlink 3.1.2 header-only 配方手工改写 conanfile.py/conandata.yml/test_package |
| 2 | /tmp 只读，tarball 下载失败 (curl 23) | OHOS 平台 /tmp 只读（E002） | 改用 $HOME/tmp 存放 tarball 与构建中间产物 |
| 3 | 上游 CMake 测试 (mp3_basic 等) 无法运行 | 依赖 tests/testvectors 数据集，官方 tag tarball 不含（仅 .gitkeep） | 在 MANIFEST.yml 如实声明 upstream_tests 不可运行；test_package 用源内真实帧解码覆盖功能验证 |
| 4 | GitCode 镜像 tarball 与 GitHub 不一致 (sha256 不同, 3.5KB 错误页) | 镜像未同步/代理返回错误响应 | conandata.yml 采用官方 GitHub URL + 实测 sha256（fd94a133...） |

## 源码修改

无补丁。dr_mp3 为纯可移植 C89 单头文件，无平台分支代码，OHOS 直接可用。

## 依赖版本

- 编译/运行依赖: 无（零依赖库）
- 工具链: OHOS clang 15.0.4、CMake 4.1.2、Conan 2.29.1（OHOS 适配版）

## 验证结果

```bash
# conan-verify (W3 同源): 见 .ci_logs / reports 下 conan create 日志
# 本地预验证: test.c 以 OHOS clang 原生编译并运行, 11/11 断言通过
```
---

**编译结束**: 2026-08-31 10:27
**最终状态**: built
