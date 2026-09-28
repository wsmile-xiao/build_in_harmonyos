# E429-draft-VTK9：GLES 几何着色器显式深度与 32 位格式保持

这是 VTK 9.3.0 适配产生的待审知识草稿。编号和归档位置由 `ohc-run.py graph add E429 --draft` 生成，尚未进入正式知识图谱。没有跨库实测或专项认可的主张。

## 已复现的问题

在 HarmonyOS PC 的 Maleoon 916/B301 驱动上，含 geometry shader 且片段着色器写 `gl_FragDepth` 的路径，向 D16/D24 深度附件写出的结果与预期不一致。例如 0.510493875 读回约 0.0104938755，0.25 读回约 0.50000006。普通光栅深度、清除深度及相同场景的 D32F 附件正确。

独立 EGL 程序直接调用 GLES，绕开 VTK；三组结果为：ES 3.00 无几何阶段 36/36、ES 3.20 无几何阶段 36/36、ES 3.20 含几何阶段 28/36。最后一组的 8 个失败均落在 D16/D24 与四个显式深度值组合，D32F 正确。失败程序保留 exit 1，作为问题复现证据。

原始浮点位模式低 24 位可解释该设备上的读回值，并与分子遮挡错误图像的数值分析一致。这是对实测行为的诊断，不推定驱动内部实现，也不外推到所有 GLES 或所有 Maleoon 固件。

## 适用条件与处理

优先针对上层原本要求 32 位深度的路径处理：当 `GL_DEPTH_COMPONENT32` 缺失但支持 `GL_DEPTH_COMPONENT32F` 时，用 D32F 与 `GL_FLOAT` 保持请求精度，避免降级成 D24。纹理、renderbuffer、resolve/copy 中间目标须使用匹配格式。

VTK 的修复涉及 `vtkOpenGLFramebufferObject` 和 `vtkTextureObject` 的格式与类型选择；体渲染/MSAA 的中间深度格式同步。此方案不强行改写显式请求 16/24 位深度的应用语义，也不按设备字符串全局切换。

前置条件是实际支持可用的浮点深度附件。若应用要求精确的 UNORM 格式、外部共享纹理或某些多采样格式组合，应先验证其格式和拷贝约束。仅有扩展字符串或 FBO complete 不足以验证数值正确。

## 复现和验收步骤

1. 创建 EGL 离屏上下文，记录 GL vendor/renderer/version；固定 viewport，保存后续要改的 GL 状态。
2. 对 D16、D24、D32F 分别运行清除深度、普通光栅深度、显式 gl_FragDepth 三种情况，覆盖含/不含 geometry shader。
3. 将深度纹理采样到颜色输出并读回，比较原始期望值；使用近中远多个深度值，保留失败退出码。
4. 修改格式选择后重新比较数值，再验证非零视口、MSAA resolve/copy 及 GL 状态恢复。
5. 运行真实应用遮挡、深度剥离、体渲染和分子绘制的原始图像回归。

可消费的 VTK 回归入口：

```sh
conan create archives/v/vtk/9.3.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

`test_package/src/test_render.cpp` 中的 GS 深度和偏移 MSAA 断言随上述命令运行。独立探针位于本次任务交付目录 `upstream/probe-fragment-depth.cpp`、`probe-fragment-depth320.cpp`、`probe-fragment-depth-gs.cpp`，原始结果在 `upstream/depth-probes/`。

## 证据与边界

- VTK 全量 phase24：1830 通过、0 失败、2 个 AVI/MP4 后端条件跳过，JUnit SHA256 `0e4434ec4a3fdbd26f4cae8a20bcf848890528ab1aa5d6c1c34e410814da29a3`。
- phase29：受影响 36 项回归通过；29 项消费者正向断言、两个反向控制通过。
- 最终安装包 Conan/W3 正在执行；结果与构建树诊断分别记录。
- 新增价值为“显式片段深度数值探针 + 保持请求深度精度 + 匹配后续拷贝格式”的诊断链，现阶段验证限于上述设备和 VTK。
- 既有 `E321-draft-B1GL` 讨论桌面固定管线经 gl4es 兼容，不覆盖本次原生 GLES shader 深度数值问题；E019/E092 讨论加载与平台识别，也不覆盖此数值行为。

新增草稿服务于问题复用；是否扩充正式知识或申报 B2，由后续知识审核及申报流程判定。
