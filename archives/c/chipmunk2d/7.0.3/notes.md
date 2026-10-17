# chipmunk2d 7.0.3 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-03
- 编译器: clang 15.0.4 (OHOS aarch64)
- 状态: built

## 编译步骤

1. 官方源码: https://github.com/slembcke/Chipmunk2D 标签 Chipmunk-7.0.3（commit 87340c216bf9）
2. tarball SHA-256: 1e6f093812d6130e45bdf4cb80280cb3c93d1e1833d8cf989d554d7963b7899a
3. CMake 配置（探索性编译）:
   cmake .. -DCMAKE_INSTALL_PREFIX=$PREFIX -DBUILD_DEMOS=OFF -DINSTALL_DEMOS=OFF
            -DBUILD_SHARED=ON -DBUILD_STATIC=ON -DINSTALL_STATIC=ON -DCMAKE_BUILD_TYPE=Release
4. make -j4 && make install DESTDIR=$TEST_PREFIX（成功，产出 libchipmunk.so/.a 与 include/chipmunk/）
5. conan-init 生成配方 → 重写为 CMake 版 conanfile.py（生成器模板误判为 autotools）
6. conan-verify: G0-G4 + L2/L4/L5 全部 PASS（含 conan create 干净构建 + test_package 消费者测试）
7. finish built: W3 本地 CI（setup.sh + build_and_test.sh）通过，Pass rate 100%，.ci-result.json exit_code=0

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | src/cpHastySpace.c 编译失败 `fatal error: 'sys/sysctl.h' file not found` | OHOS/musl 无 BSD sysctl.h；上游无条件包含该头 | 补丁 0001：将 `#include <sys/sysctl.h>` 收敛到 `#ifdef __APPLE__` 分支（sysctlbyname 仅在 __APPLE__ 使用） |
| 2 | test_package 单步断言 cy1<cy0 失败 | Chipmunk 半隐式欧拉积分：速度先于位置更新，单步后位置未变 | 测试改为 60 步 1/60s 模拟后断言明显下落（60 步实测 pos.y=-49.17） |
| 3 | W3 JC 拦截 9 个其他库历史基线文件 | full 模式扫描整仓 tracked 文件，命中 embree/flatcv 等库遗留状态文件 | 按基线隔离规约：临时 git rm --cached 精确路径 → W3 复验通过 → 无条件 git add -f 恢复（恢复后对 HEAD 零差异） |

## 源码修改

- patches/0001-src-cpHastySpace.c.patch: sys/sysctl.h include 增加 __APPLE__ 守卫（portability）

## 依赖版本

无第三方依赖（纯 C 库，仅链接 libm）

## 验证结果

```bash
# 上游测试：Chipmunk2D 7.0.3 无独立单元测试套件（仅 xcode/ObjectiveChipmunkTests，Apple 平台专用，不适用 OHOS）
# 消费者测试（test_package，60 步模拟）：
space=... gravity=-100.0 pos0=(0.000,0.000) pos1=(0.000,-49.167) vel1=(0.000,-100.000)
chipmunk2d 7.0.3 consumer test: OK
# W3 本地 CI：Success: 1, Pass rate: 100.0% (1/1)
```

## 注意事项

- 上游 demo 依赖 GLFW/Sokol，库适配禁用 BUILD_DEMOS
- 版本号保持 7.0.3（首次适配，制品仓无同版本）
- 不生成 commands.json（纯库类型，无 bin 产物，R38 豁免）

---

**编译结束**: 2026-09-03 10:26
**最终状态**: built
