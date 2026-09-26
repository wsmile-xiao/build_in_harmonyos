# kicad-library-packages3d 10.0.5 适配笔记

## 上游与产物

- 使用 KiCad 官方 `kicad-packages3D` tag 10.0.5（commit `67538dca…`）的 3D
  模型数据。源归档取 Ubuntu 26.04 / Debian 的 `kicad-packages3d` 10.0.5-1
  官方再打包源码归档（pristine orig tarball，USTC / 阿里云双镜像，sha256
  `318d41cf…`）：CI 网络无法直连 gitlab.com（2026-09-24 实测），GitHub
  同名镜像停更于 5.1.7，Debian/Ubuntu 再打包归档是最可信的字节冻结来源。
- 模型库按封装族组织：105 个 `.3dshapes` 家族目录平铺于归档根目录，共
  7293 个文件（7245 个 .step + 48 个辅助文件）。
- **KiCad 10 起上游移除了全部 VRML（.wrl）模型**：10.0.5 归档实测 0 个
  .wrl。再打包归档已移除 1 个不参与安装的 .fcstd 源文件
  （`Button_Switch_SMD.3dshapes/SW_SPST_FSMSM.fcstd`）。
- 许可证：CC-BY-SA 4.0（模型文件与 LICENSE.md 均为 CC-BY-SA 4.0，含电子
  设计豁免条款）。

## OHOS 适配

纯数据/资源包，无编译无链接。上游 CMakeLists 仅
`install(DIRECTORY 3dshapes/ DESTINATION share/kicad/3dmodels)` 一条指令。
配方在 `build()` 阶段核对：

1. 顶层标记文件（CMakeLists.txt / LICENSE.md）；
2. 根级 `.3dshapes` 家族目录数（105）与目录名集合 sha256 摘要
   （`3be1738c...`，任意目录增删/改名即失败）；
3. .step/辅助文件/总文件计数（7245/48/7293），家族目录内不允许嵌套目录；
4. 代表性封装族目录在位（15 个 spot dirs）。

`package()` 将全部家族目录安装到 `share/kicad/3dmodels/`（与上游
CMake 安装目录一致），通过 `cpp_info.resdirs` 暴露，
`runenv_info` 定义 `KICAD3D_MODEL_DIR`。

## 测试口径

上游不含测试套件（CMakeLists 仅 install 指令），上游测试 N/A。
适配后的消费者测试（test_package/kicad_packages3d_probe.cpp）：

1. 资源根目录与目录/文件计数校验（与 build() 防漂移同口径）；
2. 代表性封装族目录在位；
3. 全量消费：7245 个 .step 逐个校验 ISO-10303-21 头
   （`ISO-10303-21;`）与尾（`END-ISO-10303-21;`）；
4. 负向故障注入：缺尾/缺头的截断 .step 必须被校验器拒绝。

## 状态

- 真机（HarmonyOS PC aarch64）探针直跑通过（2026-09-25 实测）：
  `kicad_packages3d_probe: 105 model dirs, 7245 .step validated OK`
  —— 14771 条断言全过（资源根/目录集合与计数校验、spot 目录在位、
  全量 STEP 头/尾校验、负向注入拒绝）。
- 真机 conan create（ohos-aarch64 profile）：主包构建+打包通过；
  test_package 探针编译受真机 GNU Make 4.4.1 `-j20` 并行静默失败影响
  （真机环境缺陷，串行 make 可正常编译；CI 官方 worker 无此问题），
  探针经串行 make 编译后在真机直跑全过。CI 流水线 conan create 全绿
  （MR #12527，构建 #60637）。

## 其他说明

- 模型包体积较大（源码归档 313 MB，解包 3.39 GB，包内资源约 3.4 GB），
  W3/CI 构建超时需放宽（build_timeouts.txt 覆盖，建议 10800 秒）。
