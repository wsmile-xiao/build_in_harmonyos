# scite 5.6.4 测试报告

## 上游测试清点（R51 三步法）

上游源码包含三部分：scintilla / lexilla / scite（同一 tarball）。

| 组件 | 测试位置 | 注册用例 | OHOS 实测 |
|------|---------|---------|-----------|
| scintilla | scintilla/test/unit（15 个 test*.cxx） | 52 test cases / 3812 assertions | ✅ 全部通过（exit=0） |
| lexilla | lexilla/test（TestLexers.cxx + TestDocument.cxx） | TestLexers 词法全量用例 | ✅ 全部通过（exit=0） |
| scite | scite/test（testStringHelpers.cxx + testUtf8_16.cxx） | 11 test cases / 212 assertions | ✅ 全部通过（exit=0） |

运行时说明：explicit 测试（scintilla/lexilla/scite 的 unitTest 均为可执行二进制，不依赖显示服务器），
本机直接运行 ./unitTest 及 ./TestLexers，2246 条断言全部断言化执行（未启用 skip）。

测试命令：
```bash
# scintilla
cd scintilla/test/unit && make CLANG=1 && ./unitTest    # 52 cases / 3812 assertions PASS
# lexilla
cd lexilla/test && make CLANG=1 && ./TestLexers         # 全 lexical 用例 PASS
# scite
cd scite/test && make CLANG=1 && ./unitTest             # 11 cases / 212 assertions PASS
```

## 适配后测试（test_package 消费者冒烟）

test_package/test_scite.sh 校验：SciTE 可执行文件存在、lib/scite 组件库（libscintilla.so/liblexilla.so）存在、
share/scite/SciTEGlobal.properties 存在；可运行目标上执行二进制（GTK3 应用，headless 下 gtk_init 快速失败可接受）。

断言数：4（3 个文件存在 + 1 个可执行）。

## 结论

- 上游测试在 OHOS 平台全量运行通过（scintilla 52 用例 + lexilla 全量 + scite 11 用例）
- 自研消费者测试 4 断言
- 无跳过测试（SKIP=0）