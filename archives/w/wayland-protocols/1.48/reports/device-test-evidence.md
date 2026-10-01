# 真机测试证据（conan-verify 第 6 轮，2026-09-30 03:56，ohos-aarch64，conan 2.29.1）

第 6 轮为最终干净构建（设备 conan 缓存已先 `conan remove -c` 清空 + test_package
构建残留已清理），配方与补丁为 MR 最终形态（fork `a59d747ec8`），完整构建日志
`conan-create.log`（242KB，含 701 个构建目标全量输出）留存设备，以下为关键摘录：

## 主包构建

- `built static libwayland-protocol.a (65 protocols)` — 64 个协议 + wayland.xml 核心
- `Apply patch (conan): OHOS HMDFS 禁止 exec 脚本文件（EACCES，chmod 无效）：
  tests/meson.build 中 replace.py（custom_target）与 scan.sh（meson test）的调用
  改为解释器前缀执行（python3 replace.py / sh scan.sh），测试逻辑零修改`
- `[701/701] Linking target tests/test-build-cxx-experimental_xx_zones_xx_zones_v1_xml`
  — meson 配置的 701 个构建目标全部产出

## 上游 191 项测试（构建期 meson test）

```
189/191 wayland-protocols:test-build-cxx-experimental_xx_text_input_xx_text_input_v3_xml   OK  0.07s
190/191 wayland-protocols:test-build-pedantic-experimental_xx_zones_xx_zones_v1_xml        OK  0.05s
191/191 wayland-protocols:test-build-cxx-experimental_xx_zones_xx_zones_v1_xml             OK  0.04s

Ok:                191
Fail:              0
```

scan 64 + pedantic-c99 64 + cxx 63 全量执行，零跳过。

## test_package 消费者 E2E（conan test）

```
TEST CASE stable/xdg-shell ... TEST PASS ×4
TEST CASE stable/viewporter ... TEST PASS ×4
TEST CASE staging/xdg-session-management(1.48新协议) ... TEST PASS ×4
TEST CASE staging/xdg-activation ... TEST PASS ×4
TEST CASE staging/xdg-dialog ... TEST PASS ×4
TEST CASE unstable/xdg-decoration ... TEST PASS ×4
TEST CASE unstable/xdg-output ... TEST PASS ×4
TEST SUMMARY: 28 passed, 0 failed
wayland-protocols/1.48@ohpcd/stable (test package): wayland-protocols consumer E2E PASS
(7 用例 × 4 检查点 = 28 项)
```

7 用例 × 4 检查点（接口名 / 版本号 / 请求计数 / 包内 XML 一致）= 28 项全部通过，
退出码 0（E2E 任一失败退出码 1）。

## 门禁总评

conan-verify 全门禁 PASS（G0/G1/G2/G3/G4 + L2/L4/L5），verdict 可标记 published。
