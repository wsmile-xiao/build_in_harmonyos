# 手写 Makefile.in autotools 库（qlibc 模式）OHOS Conan 适配组合

> 草稿编号：DRAFT-qlibc-2.5.1-in-source-relative-dt-needed（正式编号待主编确认）
> 来源：qlibc 2.5.1 OHOS PC 适配（任务 qlibc-2.5.1-r01-pc5-12-20260907T150504Z，分支 feat/qlibc-2.5.1）
> 作者：pc5-12，2026-09-07

## 问题

qlibc 是手写 `Makefile.in`（非 automake 生成、无 VPATH、无 subdir-objects）的 autotools
C 库，上游同时构建静态与共享产物。在 OHOS PC（arm64, musl, Conan 2）适配中出现两个
独立、可复现的错误面：

1. **构建期**：Conan 2 `basic_layout`（out-of-source，build 目录为 build-release/ 子目录）下，
   `configure` 成功生成 Makefile，但 `make` 报
   `make[1]: *** No rule to make target 'containers/qtreetbl.o', needed by 'qlibc'.  Stop.`
2. **运行期**：消费者链接共享库后运行报
   `Error loading shared library ../lib/libqlibc.so.2: (needed by .../lib/libqlibcext.so)`

## 根因

1. **相对对象路径**：上游手写 `src/Makefile.in` 用相对子目录对象路径
   （`containers/qtreetbl.o`、`utilities/qstring.o` 等），make 靠隐式规则在**源码树**内
   查找 `.c`。out-of-source 布局下 make 在 build-release/src 中找不到源码 → 无规则可循。
   configure 成功并不代表 make 成功——这是与 DRAFT-audacious（configure 产物缺失、
   `No targets specified and no makefile found`）不同的错误面。
2. **字面相对 DT_NEEDED**：上游 `src/Makefile.in` 用
   `clang -shared -o libqlibcext.so.2 obj... ../lib/libqlibc.so.2` 直接链接兄弟库，
   未用 libtool/soname，DT_NEEDED 记录的是**字面相对路径** `../lib/libqlibc.so.2`。
   该路径只在上游源码树结构（build 目录 = 源码树内）下成立；脱离源码树后任何
   安装/打包目录结构都无法解析。此问题与 HMDFS 无关——Linux 原生环境同样损坏
   （区别于 E073：E073 是 HMDFS 上 .so 存在但不可加载，本问题是链接期字面路径）。

## 方案

```python
def layout(self):
    basic_layout(self)
    self.folders.build = "."          # (1) 强制 in-source，使隐式规则找到相对对象路径

def package(self):
    ...
    if not self.options.shared:       # (2) shared=False 时只交付静态库，绕开字面相对 DT_NEEDED
        for _so in glob(lib/*.so*):
            os.remove(_so)
```

- 修复 (1) 后 conan create G2 通过（含 test_package 构建运行）。
- 修复 (2) 后消费者 CTest 运行全部通过；conan-verify G4 产物完整性通过。
- 若确实需要共享交付，必须为上游补充 libtool/soname 或改链接命令（`-Wl,-soname` +
  按 soname 链接），非同仓库配方职责。

## 验证

| 步骤 | 命令 | 结果 |
|---|---|---|
| 复现构建期错误 | conan create（basic_layout，无补丁） | `No rule to make target 'containers/qtreetbl.o'` |
| 布局修复 | `self.folders.build = "."` | conan create G2 PASS |
| 复现运行期错误 | CTest 运行（有 .so） | `Error loading shared library ../lib/libqlibc.so.2` |
| 静态兜底 | package() 移除 *.so* | CTest 2/2 PASS，G4 PASS |
| 上游测试 | tests/launcher.sh 10 程序 | 74/74 通过（12,183,893 断言） |
| 消费者测试 | test_ohos / test_qlibc | ALL PASS |

日志：`archives/q/qlibc/2.5.1/reports/conan-create.log`、`reports/conan-verify-report.md`、
`reports/test-run-full.log`（SHA-256 见台账与最终回报）。

## 适用边界与反例

- **适用**：autotools 生成 configure、但 Makefile.in 为手写且对象路径为相对子目录、
  无 libtool 的 C/C++ 库；尤其是静态+共享双构建的库。
- **不适用**：automake 正式生成（VPATH/subdir-objects 完备）的项目——out-of-source 正常；
  libtool 管理的共享库——DT_NEEDED 为 soname，正常加载。

## 查重差异（摘要）

- similar_to：DRAFT-audacious-buildsys-in-source-static-chain（同 in-source 补救，
  不同错误面/签名）；E073（同静态兜底，不同根因：HMDFS vs 链接期字面路径）；E011
  （configure tmpdir，本任务另复用，未重复建草稿）。
- 新增差异：`No rule to make target '.../xxx.o'` 与 `Error loading shared library ../lib/...`
  两个识别签名；"configure 成功≠make 成功"边界；DT_NEEDED 字面相对路径与 HMDFS 无关的反例。
- 完整七轴查重与覆盖/新增差异见 `archives/q/qlibc/2.5.1/reports/knowledge-candidate-ledger.md`。

*由执行端 pc5-12 起草（知识库扩展路径 B），随 qlibc 三方库归档 PR 一并提交。*
