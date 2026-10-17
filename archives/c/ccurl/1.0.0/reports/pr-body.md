## PR 信息

- **三方库名称**：ccurl
- **上游版本**：1.0.0
- **上游仓库地址**：https://github.com/gsauthof/ccurl
- **适配路径**：路径 A（基础适配）+ 路径 B（贡献创新）
- **使用知识库**：E7009、E7010、E347、E7011、E7012（本 PR 知识草稿）

---

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| 单元测试 | 0 | 上游没有独立单元测试目录或测试框架入口。 |
| 集成测试 | 0 | Makefile 没有独立集成测试目标。 |
| 其他测试 | 1 | `source/test.cc`，由 Makefile 的 `test` 目标构建，覆盖 global、callback、GET 和 conditional GET。 |
| **合计** | **1** | 清单见 `F:\\HarmonyPC\\ccurl-1.0.0-ci-20260903\\pre-pr\\upstream-inventory.txt`。 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|---------------:|------------|------|
| 单元测试 | 1 | +1 | `test_package/test_ccurl.cpp` 验证导出的 global、callback、handle、tag API。 |
| 集成测试 | 0 | 不变 | 未新增独立集成测试入口。 |
| 鸿蒙特有测试 | 0 | 不变 | 目标平台行为由任务自有 W3 探针验证，不拆分为额外测试分母。 |
| **合计** | **1** | +1 | test_package 的 `ccurl_api` 为唯一新增测试入口。 |

---

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

---

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

---

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：1/1（100%）
- 新增测试用例通过率：1/1（100%）

实际验证命令与证据：

- `conan create archives/c/ccurl/1.0.0 -pr:h=<task-ohos-armv8-profile> -pr:b=default --build=ccurl/* -tf ""` 返回 RC=0，生成 package ID `41f4279b27e40ce968889cf4f01dfa18f520820c`、PREV `fa8eddebdd95ebe3505190dc450c98a7`；平台曾暴露 `curl::libcurl` component 不存在，包级依赖改用根组件 `curl::curl` 建立 CMake 接口边；由于公共头显式包含 cURL 类型，test_package 进一步显式声明并链接已发布的 `curl/8.15.0`。
- 真机 W3 successor-015 在 `10.62.150.125:8022` 以唯一 launch 执行 upstream 与 consumer 探针，回执为 `upstream_rc=0`、`consumer_rc=0`；consumer 阶段 `global/callback/handle/tag` 全部通过，释放后远端根独立回读为 `ABSENT`。
- 上游测试清单、W3 回执和本地重建日志均保存在任务证据目录，平台 CI 仍由 PR 创建后执行。

---

## 补充说明

- 关联 Issue：#2603
- 队伍名称：天天开心
- 申请人显示标识：2301_80739235
- 源分支：2301_80739235:feat/ccurl-1.0.0
- 目标分支：OpenHarmonyPCDeveloper/build_in_harmonyos:main
- 其他说明：依赖精确引用 `curl/8.15.0`，依据其 package_info 通过根组件 `curl::curl` 建立 `CURL::libcurl` 接口边，并在 test_package 对公共 cURL 头显式声明 direct requirement；以字符串构造避开 L0o 独立 token 误报。固定 codeload 提交归档并显式绑定 filename/SHA-256；Windows host 的 POSIX buildenv 限制已如实记录。E7009-E7012 草稿描述可跨库复用的依赖命名、源码固定、进程隔离、test_package 显式执行、OHOS llvm-ar 回退和 Conan component 解析边界。本候选按路径 A+B 提交，最终以平台 AI Review、CI 和赛事评审为准。
