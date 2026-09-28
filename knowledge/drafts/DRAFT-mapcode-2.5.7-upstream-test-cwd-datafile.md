# DRAFT — 上游单测依赖工作目录：2.45 亿断言全过却报 1 error

> Status: **Draft**（待主编 promote） | severity: `2` | category: `testing` | Updated: 2026-09-26
> 源文件：`knowledge/drafts/DRAFT-mapcode-2.5.7-upstream-test-cwd-datafile.kv`
> 来源：mapcode 2.5.7 适配（`feat/mapcode-2.5.7`）

---

**关键词**：working directory, WORKING_DIRECTORY, cwd, ctest, add_test, territories.csv

## 现象（error_signature）

```text
*** ERROR *** Can't read file territories.csv
0
 lines tested from territories.csv
...
Executed 245633397 tests, found 1 errors
UNIT TESTS FAILED!
```

**这个签名极具误导性**：2.45 亿条断言全部通过，仅仅因为工作目录不对就产生了 1 个 error。

## 根因（root_cause）

`test/unittest.c` 用**相对路径**读取同目录的 `territories.csv`（533 行）与
`alphabets.csv`。从 CMake 构建目录启动时文件打开失败，程序汇总成
`found 1 errors` 并返回非零。

容易被误判为「平台不兼容 / 浮点行为差异 / 字符集问题」而放弃适配，
实际上只需把工作目录指回源码 `test/`。

## 处方（rec_approach）

**两处都要固定，缺一不可：**

1. CMake 注册测试时显式声明：

   ```cmake
   add_test(NAME unittest COMMAND unittest
            WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/test)
   ```

2. conanfile 的 `build()` 里直接执行时传 `cwd=`（`self.run` 原生支持）：

   ```python
   self.run(f'"{unittest}"', env="conanbuild",
            cwd=os.path.join(self.source_folder, "test"))
   ```

只做 1) 而在 `build()` 里裸 `self.run` 仍会踩坑；只做 2) 则 ctest 入口不可用。

## 备选（fallback）

若上游把 fixture 路径写死在别处、无法靠 `WORKING_DIRECTORY` 规避，
可把数据文件复制到构建目录，或用 `configure_file` / `-D` 把数据目录注入测试程序。
侵入性更大，仅在 `WORKING_DIRECTORY` 不可行时使用。

## 反模式（forbid_1）

```text
self\.run\([^)]*unittest[^)]*\)(?![^)]*cwd[[:space:]]*=)
```

直接执行依赖数据文件的上游测试程序却不指定工作目录，会稳定复现
`found 1 errors` 并被误读为平台不兼容，排障方向被引向浮点/字符集/ABI 等无关假设。

## 验证

```bash
cd <source>/test && <unittest_binary>     # 期望 found 0 errors
cd <build>     && <unittest_binary>       # 复现 found 1 errors
```

---

*本条目为草稿。正式化请用 `ohc-run.py graph promote` 提升到 `knowledge/graph/`。*
