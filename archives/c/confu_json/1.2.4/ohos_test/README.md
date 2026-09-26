# HarmonyOS 专项测试 — confu_json 1.2.4

`main.cxx` 是 confu_json 1.2.4 的 HarmonyOS (OHOS aarch64) 专项测试用例，
仅通过库已安装/导出的公开头文件 `<confu_json/confu_json.hxx>` 与公开 API
`to_json` / `to_object` 使用该库（不包含库私有头文件、不调用内部符号）。

## 覆盖点
- enum 序列化（magic_enum）往返
- std::optional / std::vector / 嵌套结构体往返
- `unique_ptr<Base>` + `BaseToDerivedMapping` 映射往返（动态派发 round-trip），
  对应本适配为严格 C++20（clang 15）补充的 `typename` 修复
  （`to_json.hxx` / `to_object.hxx` 中 `boost::mpl::at<...>::type` 依赖类型）

## 构建命令（OHOS aarch64, clang 15）
```bash
clang++ -std=c++20 -O2 -fPIC main.cxx -o run-ohos-test \
  -I<安装前缀>/include \                    # confu_json 已安装公开头文件（include/confu_json/）
  -I<magic_enum 头文件目录> \               # magic_enum/magic_enum.hpp 所在 include 目录
  -I<boost 头文件目录>                      # boost/algorithm/string.hpp 所在 include 目录
```
boost::json 实现以 header-only 方式由 `#include <boost/json/src.hpp>` 编入本 TU
（与上游 test/main.cxx 一致），无需链接 boost 静态库。

## 运行
```bash
TMPDIR=<可写临时目录> ./run-ohos-test
```
退出码 0 = 全部通过；每项检查输出 `[PASS]/[FAIL]` 行与往返 JSON 摘要。

## 本轮实测记录
- 构建：`clang++ -std=c++20 -O2 -fPIC`（clang 15.0.4, aarch64-linux-ohos），exit 0
- 运行：全部检查 `[PASS]`，输出 `ALL OHOS TESTS PASSED (0 failures)`，exit 0
- 日志与 SHA-256 见主任务最终回报
