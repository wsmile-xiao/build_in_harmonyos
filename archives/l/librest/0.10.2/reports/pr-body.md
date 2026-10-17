## PR 信息

- **三方库名称**：librest
- **上游版本**：0.10.2
- **上游仓库地址**：https://gitlab.gnome.org/GNOME/librest
- **适配路径**：路径 A（基础适配） / 路径 B（贡献创新） / 路径 C（高难度挑战候选）
- **使用知识库**：E535、E468；新增 E605（跨主机 OHOS 测试执行、网络 fixture 确定性与 `test_package` 传递运行闭包边界）和 E6339（Conan override/force 的直接生成器依赖边界）

---

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| 单元测试 | 10 | 来源：Meson/GLib `tests/meson.build`，native host 清单逐项执行 |
| 集成测试 | 0 | 上游未单独注册集成测试入口 |
| 其他测试 | 0 | 无额外入口 |
| **合计** | **10** | `reports/upstream-test-inventory.txt`，`INVENTORY_COUNT=10` |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------:|------------|------|
| 单元测试 | 10 | 不变 | native host fixture run，10/10 PASS |
| 集成测试 | 0 | 不变 | 无额外上游集成入口 |
| 鸿蒙特有测试 | 1 | 新增 | HarmonyOS PC armv8 signed package consumer，1/1 PASS |
| **合计** | **11** | **+1** | W3 consumer 与上游清单分开计量 |

---

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [ ] **否**，未修改上游任何测试用例
- [x] **是**，存在对上游测试用例的修改（请在下方逐条说明）

正式 recipe 通过测试专用补丁把 Flickr 的外部 HTTPS endpoint 替换为任务内 loopback HTTP fixture；保留 `flickr.people.getInfo`、`flickr.auth.getFrob` 两次调用、两个已注册测试、请求参数、XML 解析路径和原断言。平台 CI #60629 已证明 Flickr 通过，同时暴露 `custom-serialize` 用原始线程加固定端口启动服务器时的 listen 竞态；同一补丁让它复用上游 `test-server` 的临时端口和 condition-variable readiness handshake，保留原 POST body、序列化和状态断言。补丁只修改测试源，不安装 fixture 到库包。

---

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

HarmonyOS PC consumer 是包边界测试，不把它描述为上游测试缺失补全。

---

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：10/10（100%）
- 新增测试用例通过率：1/1（100%）

上游命令：`PYTHONPATH=/mnt/f/HarmonyPC/librest-0.10.2-20260913/meson-runtime /usr/bin/python3 -m mesonbuild.mesonmain test -C /mnt/f/HarmonyPC/librest-0.10.2-20260913/host-native-build-r003 --no-rebuild --print-errorlogs --num-processes 2`。

Conan r103 已完成 graph、package_info、OHOS armv8 交叉编译、10 个上游测试 ELF 构建、打包、CMake consumer 构建和 test_package，返回码为 0，并把 55 个验证后的共享库名称物化到 consumer 的单一 runtime stage。当前候选为每个上游测试 ELF 保留 `libintl.so.8`、`libjson-glib-1.0.so.0` 的直接 `DT_NEEDED` 和 `DT_RPATH`，并在 worker 最终运行路径重新签名复制的运行时根；packaged consumer 同样使用冲突拒绝的 loader-first stage，并在 native worker 对两个关键根执行最终路径签名。平台 CI #60642 暴露传递路径缺失，#60661 则证明即使显式长路径已包含 json-glib 目录，loader 仍无法可靠解析后段间接 SONAME；本候选针对该精确边界改为单目录闭包。当前候选的精确 W3 successor 由任务外部的不可变合同证据绑定，生成后的 run id/receipt 不回写候选 tree；任何旧 W3 只作不可复用前驱。

---

## 补充说明

- 关联 Issue：#3070（https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/3070）
- 队伍名称：中国矿业大学鸿晕当头
- 申请人显示标识：2301_80739235
- 源分支：sawakage:feat/librest-0.10.2
- 目标分支：OpenHarmonyPCDeveloper/build_in_harmonyos:main
- 其他说明：直接依赖为 `glib/2.84.0.1.1`（`force=True` 统一版本）、`libsoup3/3.6.5-r3`、`json-glib/1.10.6`、`libxml2/2.15.3`、`libffi/3.4.4`、`pcre2/10.45`、`zlib/1.3.1.1`；`rest-1.0` 组件使用 `glib::glib`、libsoup3、json-glib、libxml2、pcre2 和 libffi。平台 CI #60610/#60616 验证上游目标 loader 闭包，#60642/#60661 证明 packaged consumer 需要独立的单目录运行闭包而非更长的 `LD_LIBRARY_PATH`。本候选保持 10 项上游测试分母不变，使用 test-only fixture 修复目标 TLS 能力差异，并为真实 consumer 物化、去重、冲突拒绝和最终路径签名其 host 传递闭包；最终 PR HEAD 仍需精确 W3、平台 CI PASS 与最新 AI Review 无真实代码问题后提审。新增知识草稿 E605、E6339、E6341 已完成全状态查重并绑定本候选证据。
