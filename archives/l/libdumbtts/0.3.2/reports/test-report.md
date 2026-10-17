# libdumbtts 0.3.2 功能测试报告

**测试日期:** 2026-09-17
**测试环境:** HarmonyOS (aarch64 / armv8)
**编译器:** clang 15.0.4 (OHOS SDK, target aarch64-linux-ohos)
**构建系统:** 纯 Makefile（上游无 configure 脚本，Makefile 位于 src/ 下）

## 1. 编译测试

### 1.1 编译状态
✅ 完整构建成功（共享库 `libdumbtts.so.0.3.1` + soname 链接链）

### 1.2 源码修改
GNU C 嵌套函数（gcc 扩展，clang 15 不支持）被提升为文件级 static 函数，
捕获变量改为显式参数传递，共 3 个补丁：
- `0001-src-libdumbtts.c.patch` — `roman()` 内 `nchar()/gchar()` 提升
- `0002-src-libdumbtts_dic.c.patch` — `dic_compare_word()` 内 `chrget()` 提升
- `0003-src-libdumbtts_re.c.patch` — `do_recognize_item()` 内 5 个嵌套函数提升

另在配方层强制 `-fPIC`（上游 Makefile 仅对 x86_64 启用，armv8 共享库必须 PIC）。

## 2. 上游测试

### 2.1 测试清点
- 上游源码包无 `tests/` 目录、无 `make check`/`ctest`/`meson test` 注册目标
- 唯一可执行示例为 `demo/demo.c`（演示程序，无断言、非自动化测试）
- 上游测试用例数：**0**

### 2.2 功能验证（上游 demo 程序运行）
```bash
# 部署语言配置后运行上游 demo 程序
cp conf/en.conf ~/.dumbtts_en.conf
LD_LIBRARY_PATH=src ./src/demo en "hello world"   # -> Len=12, 输出 hello world
LD_LIBRARY_PATH=src ./src/demo pl "zażółć gęślą jaźń"  # -> 输出正确（unicode 转换正常）
```
✅ 上下游 demo 程序在 OHOS 上正常运行，库功能性验证通过。

## 3. 鸿蒙专项测试 (test_package)

### 3.1 用例
`test_package/test.c` — 3 组 API 断言（与 test.c 的三个失败分支一一对应）：
1. `dumbtts_TTSInit("en")` 初始化成功（返回非 NULL）
2. `dumbtts_WCharString(L'a')` 转换无错误且输出非空
3. `dumbtts_GetString("hello")` 转换无错误且输出非空

### 3.2 运行结果
```
libdumbtts ok (N)   # exit 0
```
✅ 3 组断言全部通过（conan-verify G2 中 test_package 实际执行）。

## 4. 消费者验证 (conan create)
✅ conan-verify 全部通过 (G0-G4)，配方 `libdumbtts/0.3.2@ohpcd/stable` 可复现构建。

## 5. 结论
- 库在 HarmonyOS aarch64 上编译、链接、运行正常
- 上游 0 测试用例；自研 3 组鸿蒙专项断言全部通过
- GNU C 嵌套函数是唯一的适配修复点（上游代码 2010 年编写，使用了 gcc 专有扩展）