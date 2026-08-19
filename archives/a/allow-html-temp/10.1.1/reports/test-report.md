# allow-html-temp 10.1.1 测试报告

## 上游测试

- 上游自动化测试：0
- 原因：10.1.1 源码归档没有测试目录、测试框架或测试命令。
- 上游通过率：0/0（不适用），不记为 100%。

## 适配后补全测试

上游无测试用例，本适配新增 18 项测试，全部由 Conan `test_package` 执行。

### XPI 集成测试

`test_package/test_xpi.py` 对 Conan 安装后的 XPI 执行 10 项断言：

1. XPI 已安装；
2. XPI 非空；
3. ZIP CRC 完整；
4. 条目顺序确定；
5. 根目录含 `manifest.json`；
6. 版本为 10.1.1；
7. manifest 规范版本为 2；
8. Gecko 扩展 ID 正确；
9. 脚本、API、locale、选项页和图标均存在；
10. ZIP 条目时间戳固定，可复现。

结果：10/10 PASS。

### 核心策略单元测试

`test_package/test_button_policy.py` 从安装后的 XPI 读取上游 `scripts/background.js`，验证 `getButtonPolicy()` 的 8 条核心功能契约：

1. Shift 选择纯文本模式；
2. Ctrl 选择原始 HTML 并临时允许远程内容；
3. Command 与 Ctrl 行为一致；
4. Ctrl+Shift 选择净化 HTML；
5. 远程内容按钮选择原始 HTML、远程内容和内联附件；
6. 默认纯文本配置保留远程内容限制；
7. 默认净化 HTML 配置可临时允许远程内容；
8. 默认 HTML 配置可启用内联附件。

结果：8/8 PASS。

## 汇总

- 上游测试：0/0（不适用）
- 新增单元测试：8/8 PASS（100%）
- 新增集成测试：10/10 PASS（100%）
- 新增测试合计：18/18 PASS（100%）

## 限制

未在 Conan Worker 中执行 Thunderbird UI 交互测试；该行为依赖 Thunderbird 128–145、邮件账户和消息显示上下文，不计为通过。
