# glad 2.0.8 适配笔记

## 编译环境
- 构建系统: cmake（conanfile 内调用官方生成器产出 C loader 后 CMake 编译）
- 编译日期: 2026-09-10
- 编译器: clang/clang++（aarch64-linux-ohos，OHOS SDK 26.0.0.18）
- 状态: built

## 编译步骤

```bash
# 1. 官方源 v2.0.8（conandata.yml: github.com/Dav1dde/glad，sha256=44f06f91…eb2d0fc）
# 2. conan create（E017 临时注入 ghfast.top 镜像下载，完成后恢复官方 URL）
python3 scripts/ohc-run.py conan-verify glad 2.0.8      # G1/G0/G2/G3/G4+L2/L4/L5 全 PASS
python3 scripts/ohc-run.py finish glad 2.0.8 built        # 含 W2 结构/W3 本地 CI（1/1 Success）
```

配方 build() 内部：
1. `python3 -m glad --api=gl:core=4.6 --out-path=<gen> --reproducible c`（离线，内置 specs）
2. CMake 编译 `<gen>/src/gl.c` → libglad.a，install 头文件（glad/gl.h + KHR/khrplatform.h）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | github.com 直连超时 | 网络对 github 直连不可达 | conan-verify E017 自动注入 ghfast.top 镜像下载；conandata.yml 保持官方 URL（R39），验证后恢复并清理 .ghfast-bak |
| 2 | W3 L0d stub_test_method | test_package test() 用 cmake.test() 无 self.run | 改为显式 `self.run(<test_bin>, env="conanrun")` 逐项运行 test_glad 与 harmonyos_specific_test |
| 3 | glad2 GLADloadfunc 签名 | 返回 `GLADapiproc`（`void(*)(void)`）而非 `void*` | 测试 stub 按真实签名实现，glGetString 返回"4.6.0"驱动版本解析 |

## 依赖版本

- 运行时依赖：无（libglad.a 纯 C 静态库）
- 构建期：python3 3.12.9 + jinja2 3.1.4（随 conan 环境）、clang 15.0.4、cmake 4.1.2

## 验证结果

```bash
# 上游测试全量尝试（C 口径）：parse 4/4 + compile 76/76 = 80/80 PASS
# run 11 硬阻塞（无 libglfw/mingw/wine/GPU），rust 8 组无 cargo（语言口径外）
# HarmonyOS 专项（本机原生运行）：
./test_glad                # rc=0: loader init executed, version=4.6, table populated
./harmonyos_specific_test  # rc=0: platform=OHOS(aarch64), GL_VERSION_4_6, table populated
# 全量通过率：80/91 = 87.9%（C 口径）；当前配置可执行集合 80/80 = 100%
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py + conandata.yml | 官方源 + 生成→静态库配方 |
| CMakeLists.txt | 生成 loader 编译/安装 |
| test_package/ | 消费者测试 + HarmonyOS 专项（ctest 双用例） |
| reports/upstream-test-ledger.md | 上游测试完整枚举台账 + 双口径统计 |
| reports/test-report.md | 测试报告（80/91=87.9%，80/80=100%） |

## 注意事项

- 生成器内置 Khronos XML specs（glad/files/*.xml），`--reproducible` 离线可复现，CI 无需联网拉取
- 上游 release 无预生成 loader；交付形态为生成器产出的 C loader 库本体（任务允许形态）
- 禁止提交 .ghfast-bak/.orig 残留（W3 JC1 拦截），提交前清理

## 发现与知识

- ✅ 知识1: glad 2.0.x 官方仓库是 Python 生成器工具（glad2），可交付形态=构建期用内置 Khronos XML specs 生成 C loader（glad/gl.h + KHR/khrplatform.h + gl.c），再用 OHOS 工具链编译为 libglad.a；语言预检不应直接 env_unsupported 终态，应评估生成器产物的 C 交付形态（knowledge_ref: R47 边界，glad 2.0.8 实证）
- ✅ 知识2: glad2 GLADloadfunc 返回类型为 GLADapiproc（`void(*)(void)`）而非 `void*`；C 测试 stub 需按此签名实现并让 glGetString 返回版本串驱动 glad_gl_find_core_gl 版本解析，才能在无 GPU/EGL 上下文的 CI 上真实执行 loader 初始化路径（knowledge_ref: test_package/test_glad.c 实证）
---

**编译结束**: 2026-09-10 21:59
**最终状态**: built
