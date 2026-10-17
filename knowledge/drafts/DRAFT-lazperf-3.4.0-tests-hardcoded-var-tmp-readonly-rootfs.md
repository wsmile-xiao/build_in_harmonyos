# DRAFT：测试夹具硬编码 `/var/tmp` 且忽略 `mkstemp()` 返回值 → 只读根文件系统上成组用例以「数据不匹配」失败

> 状态：草稿（待知识库主编 promote）
> 来源：lazperf 3.4.0 适配，`archives/l/lazperf/3.4.0`
> 类别：testing / cmake / conan / portability / filesystem

## 错误特征

在一台根文件系统只读、且没有可写 `/var/tmp` 的机器上，`ctest` 里**同一个测试
二进制**稳定失败**固定的一组**用例，而它们看起来毫无共同点——一个是 extrabytes
（额外维度）、一个是 variable_chunks（变长分块）、一个是 bbox 回写：

```
[  FAILED  ] io_tests.extrabytes
[  FAILED  ] io_tests.issue44
[  FAILED  ] io_tests.can_encode_large_files
[  FAILED  ] io_tests.variable_chunks
[  FAILED  ] io_tests.compression_decompression_is_symmetric
[  FAILED  ] io_tests.writes_bbox_to_header
[  FAILED  ] io_tests.write_laz_with_no_points_and_read_back
[==========] 21 tests from 1 test suite ran.
[  PASSED  ] 14 tests.
[  FAILED  ] 7 tests, listed below:
```

**这个「失败的用例名集合」本身就是最强的识别信号**：把它和「凡是自己造临时文件
的那个 helper 的调用点」求交集，如果完全重合，那就是本条。

还有两个次要信号：

- 失败用例的报错内容指向**数据**（点坐标/属性不相等），而不是文件系统；
- 单独跑失败的用例时，如果**恰好**当前目录可写、并且手工 `export TMPDIR=<可写目录>`
  却**毫无效果** —— 说明 $TMPDIR 根本没被读，路径是写死的。

## 触发条件

三条同时成立：

1. 上游测试源码里有**硬编码的绝对临时路径**，典型是 `/tmp/…` 或 `/var/tmp/…`；
2. 创建临时文件的调用（`mkstemp` / `mkstemps` / `tmpfile` / `open(O_CREAT)`）
   **返回值被丢弃**，失败不报错；
3. 运行环境是只读根文件系统（HarmonyOS/OHOS 的 `/` 是 erofs 只读挂载，
   `/var/tmp` 甚至不存在；只读容器镜像、CI 沙箱同理）。

lazperf 3.4.0 的现场是 `cpp/test/io_tests.cpp`：

```cpp
std::string makeTempFileName()
{
    std::string filename;
#ifdef _WIN32
    ...
#else
    std::string s("/var/tmp/fnXXXXXX");   // ← (1) 写死
    mkstemp(const_cast<char *>(s.data())); // ← (2) 返回值丢弃
    filename = s;
#endif
    return filename;
}
```

## 根因分析

### (1) `/var/tmp` 不是「临时目录」，`$TMPDIR` 才是

`/var/tmp` 在 FHS 里是「跨重启保留的临时目录」，`/tmp` 是「随时可清空的临时
目录」，而 POSIX/`mktemp` 约定里**唯一**由运行环境指定的 scratch 位置是
`$TMPDIR`（未设时退回 `/tmp`）。写死 `/var/tmp` 同时踩两个坑：

| 环境 | 现象 |
| --- | --- |
| HarmonyOS/OHOS | `/` 是 erofs 只读挂载，`/var/tmp` 可能**不存在** → `mkstemp` 报 `ENOENT`/`EROFS` |
| 只读容器镜像 / CI 沙箱 | `/var/tmp` 存在但只读 → `EROFS` |
| 普通 Linux 开发机 | 一切正常 —— **所以上游维护者看不到这个 bug** |

### (2) 静默失败把「路径问题」伪装成「数据问题」

`mkstemp()` 失败返回 `-1`，而这里**没看返回值**；返回的路径仍然是一个不存在的
文件。下游 `writer::named_file f(makeTempFileName(), c)` 内部的 `ofstream` 打开
同样失败，写入全部**无声丢弃**。于是真实数据流是：

```
写 0 字节  →  读同一个（空）文件  →  与期望文件逐字节比对  →  失败
                                                              ↑
                                          gtest 报的是「点属性不相等」
```

用例名和报错内容都在指向编解码器，实际原因与编解码器毫无关系。这也是本条比
E002（`/tmp` 只读）更值得单独记一笔的地方：**E002 的失败信息直接说路径不可写，
本条不说。**

### (3) 数量要按「可执行集」数，不是按调用点数

`makeTempFileName()` 在该文件里共有 8 个调用点，但其中 `io_tests.fast` 被上游
用 `/** ... **/` 块注释掉了。所以：

- 受影响的**可执行**用例 = **7**；
- 若按调用点数会数成 8，属统计口径错误（与 rule4「未执行」的口径同源）。

## 解决方案

只改这一个 helper，把路径解析交给 `$TMPDIR`，并把失败显式化：

```diff
 #else
-    std::string s("/var/tmp/fnXXXXXX");
-    mkstemp(const_cast<char *>(s.data()));
+    // Scratch files belong in $TMPDIR, which is what POSIX prescribes. A
+    // hardcoded /var/tmp makes every test that writes a temporary LAS/LAZ
+    // file fail on systems whose root filesystem is read-only or which have
+    // no /var/tmp at all (HarmonyOS/OHOS, minimal containers, ...): mkstemp
+    // fails, its return value is ignored, and the subsequent ofstream open
+    // silently yields nothing. Try $TMPDIR, then the current directory, which
+    // is writable by definition.
+    const char *tmpdir = std::getenv("TMPDIR");
+    std::string s = (tmpdir && *tmpdir ? std::string(tmpdir) : std::string(".")) +
+        "/lazperf-fnXXXXXX";
+    int fd = mkstemp(const_cast<char *>(s.data()));
+    if (fd < 0 && tmpdir && *tmpdir)
+    {
+        s = "./lazperf-fnXXXXXX";
+        fd = mkstemp(const_cast<char *>(s.data()));
+    }
+    if (fd >= 0)
+        ::close(fd);
     filename = s;
 #endif
```

要点：

- **不动用例数、用例体、断言**，也不触碰被安装的库代码；
- `$TMPDIR` 优先、当前目录兜底 —— 两条都在 POSIX 语义内，不引入平台宏，
  与 HarmonyOS 无关 → **可直接向上游提交**（P005）；
- 顺手把 `mkstemp` 的 fd 关掉：临时文件本身是被写盘再读的，需要它留下；
  但 fd 泄漏会让「大量用例」场景撞上 fd 上限；
- 配方侧配套：`build()` 里在 `build_folder/tmp` 建可写目录，把
  `TMPDIR`/`TMP`/`TEMP` 注入给 `ctest`。这是必需的，因为上游
  `add_test()` 的 `WORKING_DIRECTORY "${CMAKE_RUNTIME_OUTPUT_DIRECTORY}/../.."`
  在 `CMAKE_RUNTIME_OUTPUT_DIRECTORY` 未设置时会解析成 `/` ——
  用例进程的 cwd 就是根目录，兜底的 `./` 也落不下去。

lazperf 3.4.0 的实测对照（`unshare -rm` + `mount -t tmpfs -o ro,size=4M tmpfs /var/tmp`，
唯一变量是补丁与 `TMPDIR`）：

| 条件 | 结果 |
| --- | --- |
| 未打补丁，`/var/tmp` 可写（基线） | 21 ran / **21 PASSED** |
| 未打补丁，`/var/tmp` 只读 | 21 ran / **14 PASSED / 7 FAILED** |
| 打补丁，`/var/tmp` 只读 + `TMPDIR` 指向可写目录 | 21 ran / **21 PASSED** |
| 打补丁，`/var/tmp` 只读 + `TMPDIR` 未设（退回当前目录） | 21 ran / **21 PASSED** |

## 验证命令

```bash
# 1) 复现：不需要改任何源码，只要让 /var/tmp 不可写
unshare -rm bash -c 'mount -t tmpfs -o ro,size=4M tmpfs /var/tmp && ./cpp/test/io_tests'
#    → 21 ran / 14 PASSED / 7 FAILED，失败名即那 7 个

# 2) 定位写死点（同时找绝对临时路径与返回值被丢弃的 mkstemp）
grep -rn '/var/tmp\|/tmp/' cpp/test/ | grep -v raw-sets
grep -n 'mkstemp' cpp/test/io_tests.cpp

# 3) 打补丁后，同一只读环境下
TMPDIR=<writable> ./cpp/test/io_tests      # → 21/21
TMPDIR=<writable> ctest --output-on-failure # → 3/3

# 4) 数「受影响用例数」时按可执行集，排除被块注释掉的调用点
grep -n 'makeTempFileName()' cpp/test/io_tests.cpp
sed -n '655,690p' cpp/test/io_tests.cpp     # io_tests.fast 在 /** **/ 里，不计
```

## 禁止策略

| 禁止 | 原因 | 后果 |
| --- | --- | --- |
| 用 `--gtest_filter=-…` / `SKIP_TESTS` / 自定义 skip 把失败用例摘掉 | 伪造通过率 | rule4 判少报/造假，PR 驳回返工 |
| `chmod 777 /var/tmp`、`mount -o remount,rw`、`mkdir -p /var/tmp` | 改变被测环境而非适配库；OHOS 上做不到，做得到也不是消费者视角 | 配方只在特权环境可用，真机/CI 行为不一致 |
| 把断言降级成告警（`always exit 0`、`FAIL() → WARN`、`GTEST_SKIP()`） | 这 7 个用例断言的是 LAZ 写-读的字节一致性，是真断言 | 测试假通过，编解码器回归失去保护 |
| 预造 `/var/tmp/fnXXXXXX` 让 `mkstemp` 失败后果被掩盖 | 模板名带 `XXXXXX`，只能覆盖单个确定名字；且等于承认「写不进去不要紧」 | 一旦用例真需要写盘就变成假通过 |

## 关联

- `similar_to` **E002**：鸿蒙 `/tmp` 是 erofs 只读挂载，通用方案是把 `TMPDIR`
  指向可写目录。本条目是它**更隐蔽的一面**：写死发生在*测试夹具*里，
  且失败信息指向数据不匹配而非路径不可写，所以很难一眼归到 E002。
- `similar_to` **E265**：上游测试硬编码 `/tmp` 路径导致 `mkdir` 失败。
  同属「上游把临时目录当不变量」家族；区别在 E265 直接报错，本条目静默产出空文件。
- `similar_to` **DRAFT-isutf8-cmake-configure-download-benchmarks**：同批 lazperf
  适配里的另一条知识——上游 `CMakeLists.txt` 在 configure 期 `file(DOWNLOAD)`
  外部资源须收进默认 OFF 的选项守卫（lazperf 的 `patches/0002`）。
  两条合起来是「上游把外部环境前提（可写临时目录 / 可直连 github.com）
  当不变量」的两个方向。
- 配套（本条目主题之外）：内置 gtest 的 `cmake_minimum_required(VERSION 2.8.12)`
  需 `CMAKE_POLICY_VERSION_MINIMUM=3.5`（cache 变量）才能被 CMake ≥ 4 配置；
  gtest 的 `-Werror` 遇上 OHOS clang driver 自报的
  `-Wunused-command-line-argument` 需有界地只关这一条。

## 上游可提交性

补丁只改测试夹具的临时路径解析，不引入平台宏、不依赖 HarmonyOS、不改任何用例
语义；可直接向上游提 issue/PR（"tests hardcode /var/tmp and ignore mkstemp's
return value, so they fail on a read-only root filesystem"）。上游 master 至今仍是
写死的 `/var/tmp`。
