# lurlparser

轻量级 URL/URI 解析库（RFC 1738 / RFC 3986），C++11 实现。

- 上游: https://github.com/corporateshark/LUrlParser
- 版本: 1.1 (tag `release-1.1`)，MIT License
- 适配: HarmonyOS PC (aarch64, clang 15)

## 适配内容

- `1.1/`——CMake 静态库配方（conanfile.py + conandata.yml），
  补丁 0001 新增库目标/安装规则，0002 将上游 stale test 移植到
  release-1.1 公开 API。

## 功能

- `LUrlParser::ParseURL::parseURL(url)`：解析 scheme/host/port/path/
  query/fragment/userName/password；`isValid()`/`getPort()` 辅助接口。

## 验证

- conan create（OHOS aarch64, with_tests=True）通过
- 上游 gtest 8/8 PASSED；消费者与 OHOS 专项测试通过