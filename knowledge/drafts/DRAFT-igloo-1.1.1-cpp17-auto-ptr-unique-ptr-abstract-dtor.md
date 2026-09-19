# DRAFT: C++17 auto_ptr→unique_ptr 迁移后：抽象基类缺虚析构触发 -Wdelete-abstract-non-virtual-dtor

> 草稿归属: igloo 1.1.1 适配（task igloo-1.1.1-r01-pc4-12）｜状态: UNMATCHED/待审核提升

## 问题

OHOS 平台 Conan profile 设定 `compiler.cppstd=17`。2013 年发布的旧 C++ 库（本实例 igloo 1.1.1）公共头与测试源直接使用 `std::auto_ptr`，C++17 已将其从标准移除，编译报：

```
error: no template named 'auto_ptr' in namespace 'std'
```

将 `std::auto_ptr` 直接替换为 `std::unique_ptr` 后，删除动作改经 `unique_ptr` 的 typed delete 进行，对"纯虚但析构非虚"的抽象基类指针删除时触发：

```
fatal error: delete called on 'igloo::TestResultsOutput' that is abstract but has non-virtual destructor [-Wdelete-abstract-non-virtual-dtor]
```

同一批 2013 年文件还暴露注释中 Latin-1 非法 UTF-8 字节（`-Winvalid-utf8`）。

## 根因

1. `std::auto_ptr` 自 C++17 起被标准移除（OHOS 统一 cppstd=17）。
2. `std::unique_ptr<T>` 的析构执行 typed delete；若 `T` 为抽象基类且析构非虚，clang 告警 `-Wdelete-abstract-non-virtual-dtor`，上游 `-Werror` 提升为 fatal。
3. 旧源码注释以 Latin-1 字节提交，clang 15（libcxx-ohos）默认检查注释编码。

## 方案（igloo 实测验证）

- header-only 库：公共头 + 测试源一并 `std::auto_ptr` → `std::unique_ptr`（`sed -i 's/std::auto_ptr/std::unique_ptr/g'`）。
- 对 unique_ptr 删除的抽象基类补充 `virtual ~T() {}`。
- 注释非法 UTF-8 字节：`d.replace(b'\xe4', 'ä'.encode('utf-8'))` 字节级修复；若 `refresh-patch --auto` 无法生成含非法字节的补丁（dry-run 必失败、补丁被删），改由配方 `build()` 内 `replace_in_file(..., encoding="latin-1")` 修复，不写入 patches/。
- 全部改动固化后 `conan create`（ohos-aarch64, cppstd=17）复验 test_package 消费者编译运行。

## 验证（igloo 1.1.1，OHOS arm64，clang 15）

- 上游自测：igloo-tests 114/114 通过，snowhouse-tests 177/177 通过（退出码 0）。
- 消费者 test_package：ctest 1/1 通过（`Assert::That(2+2, Is().EqualTo(4))` 等 2 条断言）。
- W3 本地 CI（build_and_test.sh）：Pass rate 100% (1/1)，`.ci-result.json` exit_code=0。
- 证据日志（含 SHA-256）：`archives/i/igloo/1.1.1/reports/igloo-tests-run.log` 等。

## 适用边界 / 反例

- 适用：header-only 或可无 ABI 顾虑直接改造的旧 C++ 库；抽象基类被 unique_ptr 删除且析构非虚。
- 反例：有 ABI 约束的库（公共头 auto_ptr 成员参与数据布局）必须用布局兼容 shim（参见 `DRAFT-bulletml-0.0.6-auto_ptr-cpp17-compat`），不能直接替换。
- 禁用：平台名分支（`#ifdef __OHOS__`）或全局压制 `-Wno-delete-abstract-non-virtual-dtor`——掩盖真实生命周期缺陷。

## 查重差异（vs 既有条目）

- 与 DRAFT-bulletml：同根因、trigger 重叠；方案差异 = header-only 直接替换 + 虚析构配套 + 测试源同批迁移（bulletml 走 shim 保 ABI）。
- 与 E293（legacy C++17 移除项）：E293 面向工具链 flag 侧（-Wregister 等），本条目面向源码侧 auto_ptr 迁移与虚析构。
- 与 E549（toybox sed Latin-1）：同为上游 Latin-1 工件兼容缺陷，机制不同（toybox sed 正则吞字节 vs clang 注释编码校验）；本条目补充 refresh-patch 无法表达非法字节补丁的配方级绕过。

## 关系

- similar_to: DRAFT-bulletml-0.0.6-auto_ptr-cpp17-compat, E293, E549
- caused_by: 上游 2013 年代 C++98/03 头文件 + OHOS cppstd=17 + clang 15 严格校验
- prerequisite_of: 无 ｜ conflicts_with: 无
