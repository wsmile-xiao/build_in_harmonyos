## PR 信息

- **三方库名称**：MAdLib（网格自适应库，非 Apache MADlib）
- **上游版本**：1.3.0
- **上游仓库地址**：https://www.madlib.be/；权威源码发行包：https://deb.debian.org/debian/pool/main/m/madlib/madlib_1.3.0.orig.tar.gz
- **适配路径**：路径 A（基础适配）+ 路径 B（知识库扩展）
- **使用知识库**：E074、E129；本 PR 草稿 E2180-draft-2501（同一 FIFO 警告跨失败/成功运行的终态判读）

---

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| 单元测试 | 0 | 发行包所有 `Makefile.am` 均未声明 `TESTS` / `check_PROGRAMS` / `check_SCRIPTS`。 |
| 集成测试 | 0 | 没有注册的集成测试入口。 |
| 其他测试 | 0 | `make check -j1` 已在目标机完整执行，但无注册用例。 |
| **合计** | **0** | `reports/upstream-test-inventory.txt`。 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|---------------:|------------|------|
| 单元测试 | 0 | 不变 | 未篡改或伪造上游测试。 |
| 集成测试 | 0 | 不变 | 上游没有注册用例。 |
| 鸿蒙特有测试 | 1 | +1 | `test_package/test_madlib.cpp` 从安装包调用公开初始化/结束 API。 |
| **合计** | **1** | **+1** | 目标机 Conan 消费测试 1/1。 |

---

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

仅对 `config.sub`、`configure` 和一个缺失 POSIX 声明的源码文件做窄补丁；未修改测试入口。

---

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

补全范围：安装后的静态库、公开头与 Conan 依赖链的实际 C++ 编译、链接、运行。新增文件：`test_package/conanfile.py`、`test_package/CMakeLists.txt`、`test_package/test_madlib.cpp`、`test_package/MANIFEST.yml`。

---

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：0/0（不适用）
- 新增测试用例通过率：1/1（100%）
- HarmonyOS PC aarch64 上 `conan create` 返回 0；`make check -j1` 已执行，完整 Conan 日志 SHA-256 `4ca43c65ba0422dbacef04b2f5bc92d864fe7ea0234013ab50efa126a761abe1`。
- 冻结运行 `madlib-w3-20260929T043214Z` 单次 launch、精确传输/回读、release/postrelease，校验返回 `W3_VALIDATOR_PASS`；链头 SHA-256 `c6a25d379172dbf58bfddf8e61d614f1103849630c52b7eb4134940afab84fa7`。
- 当前尚未声称平台 CI、合并或制品仓发布通过。

---

## 补充说明

- 关联 Issue：#3572
- 队伍名称：诶，云朵
- 申请人显示标识：2501_91199785
- 源分支：2501_91199785:feat/madlib-1.3.0
- 目标分支：OpenHarmonyPCDeveloper/build_in_harmonyos:main
- 其他说明：本次 B 类知识草稿基于 E074 的真实反例增量，说明 GNU make 的 HMDFS FIFO 警告可能与成功制品、消费者并存；不能据警告推断终态，也不能因此忽略独立 fatal。查重和适用边界见 `reports/knowledge-dedup-result.json` 与配对草稿。真机校园网 IP 会变化，证据以设备和运行身份绑定。
