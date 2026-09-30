# DRAFT — 只读根文件系统上 X11 默认路径查找必然 miss：断言「失败路径」的确定返回码

- **来源**: libxmu 1.3.1.1（X.Org libXmu，autotools，OHOS aarch64），source_pr 13894，2026-09-30
- **同 stem 草稿**: `DRAFT-libxmu-1.3.1.1-ohos-readonly-root-bitmap-lookup-degradation.kv`

## 问题

X11 库普遍按「系统根文件系统里有 X11 数据目录」的假设写代码：位图从
`/usr/share/X11/bitmaps`、光标从 cursorfont、键映射从 `/usr/share/X11/xkb` 之类的
**绝对路径**查找。鸿蒙 PC 上：

- HMFS 根文件系统是**只读**的；
- 而且不含 `/usr/share/X11/bitmaps` 这类目录。

于是**所有**按默认路径的查找都必然 miss。如果实现走的是「找不到就 `abort()` / `exit()`」
分支，那么任何只是想在界面上放一个图标的 X 应用，在只读根上都会**必现**整进程崩溃。

同时有一个测试盲区：上游测试通常只把自带的样例文件从**可写的源码目录**喂进去，
所以**永远覆盖不到失败路径**。以上游 libXmu 为例，`test/ReadBitmapData.c` 只测
`plaid` / `star` / `xlogo64` 三个自带位图，打开失败与内容畸形两条路一条都没走到。

## 根因

两个假设在 OHOS 上同时失效：

| 上游假设 | OHOS 现实 |
|---|---|
| X11 数据目录存在于根文件系统 | 根文件系统只读，且不含该目录 |
| 路径查找失败是异常情况 | 默认路径查找**必然**失败，是常态 |
| 上游测试覆盖了失败路径 | 上游测试只喂自带样例，失败路径零覆盖 |

## 方案（推荐，已实测）

在 `test_package` 里补一组**失败路径**断言，直接断言「确定的错误码 + 不 abort」。
以 libXmu 为例（`test_package/test_ohos.c`，3 条）：

| 断言 | 输入 | 期望 |
|------|------|------|
| A1 | 合法 8×8 X11 位图（写到可写路径） | `BitmapSuccess`，且 `width==8 && height==8 && data != NULL` |
| A2 | 畸形内容（`this is not an X11 bitmap`） | `BitmapFileInvalid`，不 abort，不写出参 |
| A3 | 根文件系统上不存在的路径 | `BitmapOpenFailed` |

写法要点：

1. **状态常量取公共头文件**（这里是 `<X11/Xutil.h>`：`BitmapSuccess=0` /
   `BitmapOpenFailed=1` / `BitmapFileInvalid=2`），不要硬编码数字。
2. **只断言可观测的运行时行为**：返回值、出参是否被写坏、进程是否存活。
   **不要** grep 二进制、不要用 `strings` / `tr`（OHOS 精简环境未必有）。
3. **上游源码依据要写进 PR 描述**，证明这些错误码确实来自上游实现而不是自己编的。
   本例：`src/RdBitF.c` 的 `XmuReadBitmapDataFromFile()` 在 `fopen` 失败时
   `return BitmapOpenFailed`；`XmuReadBitmapData()` 未解析出 `bits[]` 时
   `RETURN(BitmapFileInvalid)`，且其函数注释明确「非 `BitmapSuccess` 时不触碰任何出参」。
4. **A1 这条成功路径也要留着**——它证明失败码不是「因为功能整个坏了」才返回的。

## 验证

```bash
$ conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# test_package 两个消费者均编译、链接、运行通过：
#   test_libxmu       -> XmuCompareISOLatin1()（libXmuu 组件）
#   test_libxmu_ohos  -> 上述 3 条鸿蒙断言（libXmu 组件）
```

## 适用边界与反例

- **适用**：从系统绝对路径读取 X11 数据文件、且找不到时的行为在 OHOS 与 Linux 上
  分歧的库；上游测试只覆盖成功路径的情况。
- **不适用/反例**：库本身把数据文件路径做成了**可配置**参数，且测试已经覆盖
  「路径不存在」分支——此时失败路径已被覆盖，不需要重复补。
- **若上游根本没写错误码分支**（找不到直接 abort），不要把这个平台差异写进
  `patches/` 的平台宏里；应按仓库规则用 shim 头文件 + `generate()` 里 `-include`
  注入，或走 fallback 的最小补丁，并把原因写进 `notes.md`。

## 与既有知识的关系

- `similar_to DRAFT-lazperf-3.4.0-tests-hardcoded-var-tmp-readonly-rootfs`：那条讲
  「测试硬编码 `/var/tmp` 在只读根上失败」，对象是**测试代码的路径**；本条讲
  「被测库的默认查找路径必然 miss，要断言它的失败返回码」，对象是**库的行为契约**。
- `similar_to DRAFT-mecab-rcfile-ohos-consumer`：同属「OHOS 上默认配置文件/数据路径
  找不到」族，但那条是消费者侧的运行期表现，本条是适配侧要补的断言写法。

## 查重表（四范围）

| 范围 | 结果 |
|---|---|
| 正式知识 knowledge/graph | 未命中（`BitmapOpenFailed` 关键词零命中） |
| 图谱 index.tsv | 未命中 |
| 草稿 knowledge/drafts/ | 命中两条相关但主题不同的（见上「与既有知识的关系」） |
| recipes catalog | libxmu 无既有制品记录 |
