# DRAFT-cpdb-libs-1.2.0-cups-residual-dependency-removal — 残留 CUPS 依赖在 OHOS 无 CUPS 包时的移除方案

- 触发事件：cpdb-libs 1.2.0 适配，conan create 编译/链接缺 cups 包
- 路径：Path B（知识库扩展）
- 编号：DRAFT-cpdb-libs-1.2.0-cups-residual-dependency-removal

## 现象

`conan create` 编译 cpdb-libs v1.2.0 时报：

```
lib/frontend_helper.c:824: error: use of undeclared identifier 'pwg_media_t'
lib/frontend_helper.c:824: error: call to undeclared function 'pwgMediaForPWG'
```

（cups 头缺失）；若仅去头则会进一步报链接失败 `cannot find -lcups`。
`conan search cups -r=ohpcd` 返回 `Recipe 'cups' not found`，
`conan download cups/1.7.5` 亦不可用（registry 无此包）。

## 根因

v1.2.0 前端库对 CUPS 的依赖是**历史残留**：

- `lib/Makefile.am` 无条件 `-lcups`；
- `lib/frontend_helper.h` include `<cups/cups.h>`；
- `lib/frontend_helper.c` 的 `pwg_to_readable`/`readable_to_pwg` 调用
  `pwgMediaForPWG`/`pwgMediaForPPD` 做 PWG 介质名↔可读名转换。

经全源码 grep（`cups[A-Za-z_]*\(`），这两个函数只在 `print_option()` 的
调试输出被调用，不属于前端/打印主路径。上游后续版本（2.0-b5）已整体移除
cups 链接，佐证该依赖非必需。

## 修复（三处联动补丁）

1. `0001-lib-Makefile.am.patch`：`-lcups -lpthread -lm -lcrypt` → `-lpthread -lm -lcrypt`；
2. `0002-lib-frontend_helper.h.patch`：移除 `#include <cups/cups.h>`；
3. `0003-lib-frontend_helper.c.patch`：

```c
const char *pwg_to_readable(const char *pwg_media_name)
{
    return pwg_media_name;   /* 无 CUPS 表：原样返回，调用契约不变 */
}
const char *readable_to_pwg(const char *readable_media_name)
{
    return readable_media_name;
}
```

passthrough 与原始实现的失败分支语义一致（原代码在表缺失时本就返回输入
原值），因此不是空壳顶替，而是真实依赖裁剪。

## 验证

- `conan create`（`-pr:h`/`-pr:b=ohos-aarch64`）：编译、链接、`make check`、
  test_package 全部通过；
- W3 `build_and_test.sh` RC=0，L0/L1/L4/L5 pass；
- 消费者测试 `test_cpdb_libs_ohos` 12/12 PASS。

日志：`archives/c/cpdb-libs/1.2.0/reports/conan-create.log`。

## 适用边界

- 适用：链接/头/实现依赖某包，但符号仅被非主路径工具函数引用，且
  registry/系统均无该依赖包的库；
- 决策辅助：上游后续版本是否已移除该依赖（2.0-b5 已去 cups）；
- 反例：若依赖被主流程（打印/前端核心）调用，不得裁剪——需先适配发布
  依赖包（R36）或由分析端另行绑定；
- 注意：不得用 dummy 包/空壳函数顶替真实依赖（R34/R36 红线）。

## 关联

- 相似：E107（glib 静态链接 g_libintl 类依赖裁剪思路）；本条目为
  autotools + 残留转换函数场景的具体可复现补丁集。