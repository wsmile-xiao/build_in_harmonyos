# qt5-qtsvgv 5.15.2.2 适配笔记

## 编译环境
- 构建系统: qmake
- 编译日期: 2026-09-03
- 目标工具链: clang/clang++（平台 CI 的 ohos-aarch64 profile）
- 本机辅助工具链: GCC 15.2（初始化检查发现 clang 不在主机 PATH）
- 状态: built（目标平台 W3 已完成；本机 finish 的 Conan create 受 Windows/AArch64 shell 边界限制）

## 适配场景与根因

任务是对 Qt SVG 模块的修复版本重新建立独立包身份。旧 qtsvg 先例的消费者测试与包名不能直接复用到 `qt5-qtsvgv`，否则 Conan 生成的 config/target 与任务引用不一致，平台 CI 无法按分支和包路径跟踪。

r1 真机日志进一步暴露：Windows Conan 生成的 qtbase `.pri` 文件可能携带
`F:\\...\\conan-home\\p\\qt5-q...\\p`，原先只匹配 Unix
`/.conan2/p/b/...` 的重定位逻辑会漏掉该路径，目标机 qmake 随后报告模块
`.pri` 不存在。配方现同时匹配两种路径，并在设备 runner 中再次绑定当前
远端 qtbase 根；r1 因输入闭包不完整而作废，不能用其 BUILD_PASS 代替本轮
完整 W3。

## 修复步骤

1. 保留 Qt 5.15.2 官方 qmake 构建入口和已发布的 `qt5-qtbase/5.15.2.2` 依赖。
2. 将配方、消费者 CMake target、MANIFEST 和版本 manifest 全部绑定到 `qt5-qtsvgv/5.15.2.2`。
3. 使用 `QSvgRenderer` 解析最小合法 SVG 并断言 `isValid()`，覆盖安装后的真实 SVG 解析路径。

## 验证记录

- W0：`qt5-qtbase/5.15.2.2` recipe 已由 `conan download --only-recipe` 精确确认发布。
- 初始化：官方 qtsvg 5.15.2 tarball SHA-256 为 `8bc3c2c1bc2671e9c67d4205589a8309b57903721ad14c60ea21a5d06acb585e`。
- r9-r11 为不可重放的单次 W3 失败：分别定位到缺失 `include/QtSvg`、qtbase `.prl/.la` 泄漏旧 Conan build 路径、provider ID 正则未匹配 `qt5-qa31db...`；均已保留 terminal 证据并清理各自远端根。
- r13 在 `10.62.195.15:8022` 唯一 launch：五组上游测试通过（`qsvgdevice` 2 passed/29 skipped，其余 13/13、15/15、7/7、55/55），`QSvgRenderer` 消费者 smoke 通过，AArch64 ELF、进程清零均 PASS；结果哈希为 `474e9e6bcb6eda4c5f6a8c2065722705b5913ffc5ea257b6a8276c09e7569535`。
- 本机正式 `conan create`/finish clean-verify 不能作为目标构建证据：Windows 无法执行 provider 内 AArch64 qmake，且 Conan 生成的 POSIX `conanbuild.sh` 与 Windows shell 不兼容；因此未生成、未修改 `.ci-result.json`。后续 CI 证据以发 PR 后平台 Buildbot 为准。
- W3 r4 证明 `qt5-qtbase/5.15.2` 仅提供 Core/Gui/Test（缺 Widgets/Xml）；
  W0 随后确认已发布的 `qt5-qtbase/5.15.2.2` 提供完整 Widgets/Xml，配方已
  绑定该 provider，避免把缺模块当作测试跳过理由。

## 安全边界

- 不把本机 GCC 可用性解释为 ohos-aarch64 目标通过；目标构建必须使用平台 profile/工具链。
- 旧 `qt5-qtsvg` 版本的 CI/W3 结果仅作先例，不能替代本版本的当前 HEAD 证据。
---

**编译结束**: 2026-09-03 07:44
**最终状态**: built
