# Test Report — curtain 0.3

日期: 2026-09-15
包: `curtain/0.3@ohpcd/stable`（本地验证 profile: `ohos-aarch64-device`）

## 1. 上游测试清点（N=0）

Curtain 0.3 官方归档中无自动化测试：

- `configure.ac` 无 `AM_TESTS` / `AC_CONFIG_TESTDIR` / 测试宏；
- 根、`src/`、`desktop/`、`docs/` 的 `Makefile.am` 无 `TESTS`、无 `check_PROGRAMS`、
  无自定义 `check:` 目标；
- 源码树无 `test/`、`tests/` 目录及测试源文件。

结论：上游测试用例数 N=0（证据见 0.3/notes.md 与上游源码清点命令输出）。

## 2. 构建与消费者测试（本地复现）

`conan-verify curtain 0.3`（等价于 CI 门禁）结果：

| 门禁 | 结果 | 说明 |
| --- | --- | --- |
| G0 预构建风险 | PASS | 知识图谱预查询 |
| G1 配方完整性 | PASS | conanfile/conandata/test_package/MANIFEST 齐全 |
| G2 干净 conan create | PASS | 34 个补丁全部应用，CMake 构建成功 |
| G3 系统同名库隔离 | PASS | 无冲突 |
| G4 产物完整性 | PASS | lib/bin/include 产物存在 |

CI 门禁脚本（`ci/conan/build_and_test.sh`，增量模式）实测：

- L0（结构/依赖/质量门禁）PASS
- L1（上游测试 + test_package 执行证据）PASS；L1e 破坏性反证确认测试真实依赖被测包
- L2 smoke test PASS（`curtain_check --version` 正常执行）
- L4 patches 危险函数扫描 **warn**：`targets` 中误匹配 `gets`（CI 正则已知误报，非真实问题）
- L5 产物基线 + SONAME 质量门禁 PASS（`libcurtain.so` 含 DT_SONAME）

## 3. 适配回归测试（新增，替代上游 N=0）

`bin/curtain_check` 在构建机真实执行，28/28 断言通过，覆盖：

- 四边揭开与回盖几何（右揭 600/左揭 400/回盖 700/上揭 300/下揭 300）
- 最小尺寸 25px 钳制
- 关闭热区（按压右上角 25px 触发退出）
- 普通按压不误退出；释放返回变化标志
- 缩放：均匀色不变量、同尺寸逐字节一致、边缘镜像、非法输入拒绝

`test_package` 16/16 断言通过（含 `libcurtain.so` 的 `libace_napi.z.so` NEEDED、
harmony 适配树、rawfile 幕布图、许可证）。

## 4. 真机验证（2026-09-15，签名 HAP，HarmonyOS 6.1.0.117 / 3120x2080）

| 项目 | 结果 | 证据 |
| --- | --- | --- |
| 签名 HAP 构建 | PASS | entry-default-signed.hap（2179501 B） |
| HAP 安装 | PASS | install bundle successfully |
| 启动 + 全屏遮罩 | PASS | device-verify/01-launch.jpeg（整屏幕布覆盖） |
| 真实手指拖拽揭开 | PASS | device-verify/02-peel.jpeg（左侧露出浏览器） |
| 注入拖拽揭开（右缘） | PASS | 02-peel-right.jpeg；日志 rect=0,0,1700,2080 |
| 纵向揭开 | PASS | 02b-peel-top.jpeg；日志 rect=0,500,1700,2080 |
| 点击穿透 | PASS | 03-click-through.jpeg；点击露出区未产生应用触摸日志，桌面/浏览器收到点击 |
| 拖拽回盖 | PASS | 04-recover.jpeg；日志 applyRect (100,0,3020,2080) |
| 右上角 X 关闭 | PASS | 日志 quit requested，进程退出；关闭后 05-close.jpeg |
| 再次启动 | PASS | 重启后全屏遮罩与拖拽重现，日志完整 |
| 置顶权限 | 限制（已记录） | setWindowTopmost 返回 201；被点击拉起的其他窗口可盖住幕布，需重新启动应用置前 |

说明：初始阻塞原因（设备锁屏 10106102）在用户解锁后解除；未绕过锁屏。
自由窗口状态下点击幕布最顶部边缘可能被系统窗口热区/悬浮标题栏占用，缩放状态下建议点击 X 的靠内区域；
最大化/全屏状态下 X 点击实测正常（证据：quit requested 日志）。

## 5. 结论与边界

- 构建、配方、消费者测试、适配回归测试均已在本机实测通过。
- 真机 UI 行为已验证通过（见第 4 节，2026-09-15 完成），验证期间修复的
  external ArrayBuffer/释放顺序问题已包含在最终补丁中。
- 上游 N=0 已如实申报，未将适配回归测试冒充上游测试。

## 6. 真机日志摘录（设备 hilog，原样摘录）

```
CurtainHost: display 3120x2080
CurtainHost: freeWindowMode=true
CurtainHost: layoutFullScreen OK / systemBarEnable OK / bgTransparent OK / decorInvisible OK / maximize OK
CurtainHost: topmost ERR {"code":201}
CurtainPage: core init=true
CurtainPage: setSource=true 1024x768
CurtainPage: getPixels=true expect=25958400
CurtainPage: pixelMap=true
CurtainPage: window rect=(0,0,3120,2080)
CurtainPage: down 3000,1000 -> up 1700,1000 changed=1 -> applyRect (0,0,1700,2080)
CurtainPage: down 800,100 -> up 800,500 changed=1 -> applyRect (0,500,1700,1580)
CurtainPage: down 1200,1000 -> up 100,1000 changed=1 -> applyRect (100,0,3020,2080)
CurtainPage: quit requested
```
