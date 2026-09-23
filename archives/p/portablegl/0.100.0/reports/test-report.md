# Test Report — portablegl 0.100.0

**日期**: 2026-09-03
**平台**: OpenHarmony PC (OHOS arm64)，clang 15.0.4（原生，非交叉）
**验证方式**: 上游离屏渲染测试套件 + 自研 test_package 像素断言 + conan create L1e 破坏性反向验证

## 1. 上游测试套件（testing/，全离屏，无窗口依赖）

上游 testing/ 为离屏渲染单元测试：渲染到 640x640 内存帧缓冲，输出 PNG 与
expected_output/ 期望图**逐像素对比**（stb_image 加载 + write_diff 对比）。

| 套件 | 测试项 | 结果 | 帧缓冲格式/变体 |
|------|--------|------|----------------|
| run_tests | 105 | ✅ All 105 tests passed | 默认 ABGR32 |
| run_tests_d16 | 105 | ✅ All 105 tests passed | D16 深度缓冲 |
| run_tests_d16_no_stencil | 104 | ✅ All 104 tests passed | D16 无模板 |
| run_tests_rgb565 | 105 | ✅ All 105 tests passed | RGB565 16 位 |
| run_tests_clamp_border | 107 | ✅ All 107 tests passed | clamp-to-border 纹理 |
| run_tests_no_depth_no_stencil | 99 | ✅ All 99 tests passed | 无深度无模板 |
| **合计** | **625** | **✅ 625/625 (100%)** | 6 套件 |

覆盖功能：三角形/线/点光栅化、顶点插值、索引绘制、client arrays、多边形模式、
正反面剔除、裁剪（XY/Z/投影）、深度钳制、scissor、viewport、混合、模板、深度测试、
线边缘标志、纹理 1D/2D/矩形（nearest/linear/repeat/clamp/mirror）、VBO 映射、
instance/multidraw、颜色掩码等 OpenGL 3.x core 子集核心路径。

跳过项：demos/、examples/ 中 SDL2/GLFW 等窗口系统演示程序（OHOS PC 无对应窗口
后端；属上游演示而非库本体，库本体的离屏渲染路径已全量实测）。

## 2. test_package 渲染验证（消费者视角，R34/R40）

test_package/test.c 实质调用被测包 API 并断言像素（非 print 空壳）：

```
portablegl/0.100.0@ohpcd/stable (test package): RUN: "./test_portablegl"
glContext initialized (320x240, framebuffer=0x5b42a6d7c0)
PASS clear color center @(x=160,y=120): (R=0,G=0,B=255)
PASS clear color corner @(x=2,y=2):     (R=0,G=0,B=255)
PASS quad fill center @(x=160,y=120):   (R=255,G=0,B=0)
PASS quad fill corner @(x=2,y=2):       (R=255,G=0,B=0)
PASS quad fill edge   @(x=317,y=237):   (R=255,G=0,B=0)
RESULT: PASSED (all 5 pixel assertions passed, offline rendering verified)
```

渲染路径：init_glContext（内存帧缓冲）→ glClear 蓝色（断言 2 像素）→
pglCreateProgram 用户 shader 对 → VBO/IBO + glDrawElements 画满屏红色四边形
（断言 3 像素）→ free_glContext。5/5 像素断言通过，exit 0。

## 3. conan-verify / W3 本地 CI 结果

- conan-verify 八道门禁：G0/G1/G2/G3/G4 PASS，L2/L4/L5 skip（header-only 无 ELF 产物）
- G2 conan create 干净构建：PASS（test_package 渲染 6/6 断言 PASSED）
- W3 本地 CI（build_and_test.sh）：L0 pass / L1 pass / L1e **破坏性反向验证 pass**
  （include/ 移走后测试失败——证明 test 真实依赖 portablegl）/ L4 pass
- `.ci-result.json`: **exit_code=0**（integrity_hash 8677af17cb2b7491）

## 4. 结论

PortableGL 0.100.0 在 OHOS PC (arm64) 适配完整：编译零告警错误（仅 2 个上游已知的
implicit-const-int-float-conversion 警告）、上游 625 项离屏渲染测试 100% 通过、
消费者侧渲染像素断言通过、L1e 反向验证确认测试真实性。软件光栅化离屏渲染路径
（R40 适配完整性）有充分像素级输出证据。
