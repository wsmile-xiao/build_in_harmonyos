# CMake 的 `-o aslr` 不会开启 ASLR

## 错误特征

上游 `src/CMakeLists.txt` 第 34 行无条件执行下面这行，没有按编译器分叉。HarmonyOS 工具链是 Clang，Clang 把 `-o` 解析成输出文件名，所以 `aslr` 是文件名而不是 ASLR 开关。

```cmake
add_compile_options(-fstack-protector-strong -o aslr -fpie)
```

这类问题未必产生清晰的“ASLR 不支持”诊断：Clang 会按自身参数语义解析 `-o`。因此仅看 configure 成功或编译命令中出现字符串 `aslr`，不能证明 PIE、ASLR 或平台签名已经正确启用。

## 触发条件

- 项目使用 CMake `add_compile_options` 注入编译选项。
- 编译器为 Clang，或接受 GCC/Clang 驱动参数的兼容编译器。
- 上游把 `-o <名称>` 误当作安全属性、链接选项或输出类别。

## 根因与证据

| 证据 | 结果 | 含义 |
|---|---|---|
| tagutil 3.1 上游第 34 行 | `-fstack-protector-strong -o aslr -fpie` | 该行无条件存在；`-o` 后的 `aslr` 是输出文件名参数，不是 ASLR 开关 |
| HarmonyOS 适配补丁 | 删除 `-o aslr`，保留 `-fstack-protector-strong -fpie` | 仅纠正误用参数，不把 PIE 与 ELF 签名混为一谈 |
| 本任务 Conan 构建 | 2026-10-04 19:50 `51 scenarios (51 passed)`、`253 steps (253 passed)`；20:31:23 复用该包的 create 退出码 0，消费者 4/4 | 计数来自真机 `conan create` 日志，不是手工套件或旧脚本 |

`-o` 是编译器驱动的输出路径参数。它不能表达“生成 ASLR 程序”；即便目标构建命令后续另有输出参数，也不应依赖重复 `-o` 的排列来掩盖无效配置。安全属性应分别按工具链支持的 PIE 编译/链接选项配置，HarmonyOS 可执行文件还须执行平台签名流程。

## 解决方案

推荐对上游构建脚本做最小源码补丁，移除被误放进编译选项的 `-o <name>`。然后开启 verbose build，检查最终编译和链接命令中的输出参数，并对产物检查其 PIE/签名属性。不要把文件名 `aslr` 当作安全验证结果。

适用于 tagutil 的补丁：

```diff
-add_compile_options(-fstack-protector-strong -o aslr -fpie)
+add_compile_options(-fstack-protector-strong -fpie)
```

检查命令示例：

```sh
grep -nE 'add_compile_options.*-o[[:space:]]+aslr' src/CMakeLists.txt
cmake --build build --verbose 2>&1 | grep -E 'clang.*-o'
```

第一条命令应无命中；第二条用于人工确认编译器输出参数只指向 CMake 对象文件。HarmonyOS 的可执行文件签名应使用目标设备/构建环境提供的签名工具完成并单独验证。

## 禁止做法

1. 不要用 `-o aslr` 表达 ASLR，也不要因为产物或参数名含有 `aslr` 就宣称已启用 ASLR。
2. 不要把 PIE 编译选项与 ELF 签名当成可互换措施；它们解决不同阶段的问题。
3. 不要用重复输出参数顺序偶然生成目标文件作为配置正确性的证明。

## 查重反证

按 main tip `1262b4ac24a3244f254c3e8163fa35d04b48f7fb` 检索正式知识条目共 542 个。对 `knowledge/graph` 与 `knowledge/doc` 搜索 `-o aslr`、`add_compile_options.*-o`、`stack-protector-strong.*fpie`、`aslr`，没有同机制命中。

| 相邻条目 | 已覆盖内容 | 本草稿边界 |
|---|---|---|
| E077 / E128 / E179 / E295 | HarmonyOS ELF 的签名、签名工具或运行权限 | 本草稿诊断的是 CMake/Clang 参数语义；签名仍按这些条目的流程处理 |
| E222 | HarmonyOS 运行期崩溃的取证链 | 不涉及编译期 `-o` 参数，也不替代运行期崩溃诊断 |
| DRAFT-E662 | Build.sh 测试 harness 的 OHOS 环境适配；包含正确配置 PIE/链接选项的实例 | 说明正确的平台加固配置，不讨论把 `-o <名称>` 误作 ASLR 开关；本稿与它有安全选项主题重叠，需由主编复核边界 |

可复核检索：

```sh
git grep -in -E -- '-o[[:space:]]+aslr|add_compile_options.*-o|stack-protector-strong.*fpie|aslr' \
  1262b4ac24a3244f254c3e8163fa35d04b48f7fb -- knowledge/graph knowledge/doc
```

## 通用性范围

该机制来自 CMake 将编译选项传给编译器驱动的通用规则，不依赖 tagutil 的音频标签 API。其他 C/C++ 项目若把 `-o <名称>` 放入 `add_compile_options` 并试图借名称表达安全属性，也应按同一命令语义检查。当前证据以 tagutil 上游源、最小参数补丁和本任务 HarmonyOS 构建为主；尚无第二个独立上游项目的实测复现，列为草稿待补证据及主编评审边界。

## 元信息

- 关联任务：MAIN tagutil 3.1，任务 #11010。
- AtomGit ID：`iKalous_OscarP`。
- 状态：协作草稿，等待知识库主编复核。
