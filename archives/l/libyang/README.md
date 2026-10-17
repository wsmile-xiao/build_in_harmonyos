# libyang

## 简介
YANG data modeling language parser and toolkit (C library with yanglint/yangre CLI tools)

## OHOS 适配
- 构建系统: cmake
- 详见各版本 notes.md 获取适配详情
- 已适配版本：3.13.6、5.8.6

## 依赖
- pcre2（运行依赖，上游 find_package(PCRE2 REQUIRED)）
- cmocka（test_requires，仅上游测试套件使用）
- 5.8.6 实测所用版本：pcre2/10.47、cmocka/2.0.2

## 使用方必须知道的两点（5.8.6 实测）
**1. `ly_ctx_new()` 需要 libyang 自带的 YANG 模块目录。** 库内部的
`ietf-inet-types`、`ietf-yang-metadata`、`yang` 等模块位于包内
`share/yang/modules/libyang`。不传该目录会失败：

```c
ly_ctx_new(NULL, 0, &ctx);                       /* 失败: "module failed, not found" */
ly_ctx_new("/path/to/share/yang/modules/libyang", 0, &ctx);   /* 正常 */
```

`5.8.6/test_package/CMakeLists.txt` 给出了把包内路径接进去的写法。

**2. 校验用 `LYD_VALIDATE_PRESENT`。** 否则 `lyd_validate_all()` 会连带校验
内置的 `ietf-yang-library` 模块（调用方从未提供其强制节点）而报无关错误。

## 功能验证
- 上游 CTest 套件（tests/utests，cmocka）在真机执行
- test_package：C API 全链路消费者测试 + 打包的 yanglint --version 执行验证
- 5.8.6：上游 57 个 cmocka 用例真机 57/57；test_package 9 项断言（含 3 项负向）

## 各版本要点
### 3.13.6
- 详见 `3.13.6/notes.md`

### 5.8.6
- 上游 CMakeLists 对**静态构建直接关闭全部测试**（`if(NOT BUILD_SHARED_LIBS) →
  set(ENABLE_TESTS OFF)`），故本包默认 **shared** 构建，否则无测试可跑；
- `ENABLE_YANGLINT_INTERACTIVE=OFF`：交互式 yanglint 测试是 Tcl 脚本，设备无
  tclsh，而上游在无 tclsh 时仍会注册命令为 `PATH_TCLSH-NOTFOUND` 的测试项；
- 上游测试：57 个 `ly_add_utest()` 用例（`ctest -R '^utest_'`）；Tcl 驱动的
  `yangre` / 交互式 `yanglint` 套件在本目标上记为 **NOT_RUN**，如实申报而非计入通过；
- 详见 `5.8.6/notes.md` 与 `5.8.6/test_package/MANIFEST.yml`

## 参考
- https://github.com/CESNET/libyang
