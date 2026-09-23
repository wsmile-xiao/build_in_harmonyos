# notes.md — kicad-symbols 10.0.4 适配笔记

## 1. 任务口径核对：本任务在平台上标注 lang=cpp，但上游没有 C/C++ 代码

平台任务 #12840（`kicad-symbols` / `10.0.4` / `lang=cpp`）在上游对应的唯一实体是
**KiCad 官方符号库仓库** <https://gitlab.com/kicad/libraries/kicad-symbols> 的 tag 10.0.4。
该 tag 的实测内容：

| 事实 | 证据 |
|---|---|
| 顶层 `CMakeLists.txt` 为 `project( kicad-symbols NONE )` | tag 10.0.4 原始文件 |
| 仓库内**没有任何 C/C++ 源文件** | `tar tzf` 23012 个条目：222 个 `*.kicad_symdir/` + `Simulation_SPICE.sp` + `sym-lib-table` + 文档；无 `.c/.cpp/.h` |
| 唯一的“构建”动作是 Python 打包 | `tools/kicad_lib_pack.py`（把 `*.kicad_symdir/` 合并为单文件 `<lib>.kicad_sym`） |
| 发行版把它当纯数据包 | Debian `kicad-symbols` 10.0.6-1 为 `Architecture: all`，`usr/share/kicad/symbols/*.kicad_sym` + `usr/share/kicad/template/sym-lib-table` |

同批次任务 `kicad-library` / `kicad-library-symbols` / `kicad-library-packages3d` /
`kicad-packages3d` 同样是数据包，平台一律标 `lang=cpp`，可确认 **lang 字段是平台按套件
批量赋值的，并不表示该包含 C++ 编译单元**。

因此本 PR 的口径是：**按上游真实形态做数据/资源型包的 HarmonyOS PC 适配**，产物是
可直接被 KiCad 消费的符号库资源包（与 Debian 官方包同构），而不是伪造一个 C++ 目标。
`reports/pr-body.md` 中对该差异有专门说明。

## 2. 为什么用上游 CMake 而不是自己 copy 文件

上游顶层 CMakeLists 已经把“打包 + 安装 + 库表改写”的完整语义写进 install() 规则：

```
project( kicad-symbols NONE )            # 无编译器
option( KICAD_PACK_SYM_LIBRARIES ON )    # 默认打包
find_package( Python3 COMPONENTS Interpreter )
→ custom_command: python3 tools/kicad_lib_pack.py --input <symdirs> --output <packed> --table sym-lib-table
→ install( DIRECTORY <packed> DESTINATION share/kicad/symbols )
→ install( FILES sym-lib-table DESTINATION share/kicad/template )
```

复用它可以保证：

1. 产物与上游/发行版**逐字节同构**（本地实测与 Debian 10.0.6 包布局一致）；
2. 上游的打包脚本成为**真实被执行的代码路径**，而不是被“抄一遍”的注释；
3. `project(... NONE)` 意味着不调用任何编译器 —— 交叉编译风险为零，OHOS 与原生
   构建产物完全相同。

代价是构建期需要 `python3`（上游脚本用 PEP 604 `str | None` 注解，需 ≥ 3.10；
OHOS PC 平台 Python 为 3.12）。配方在 `generate()` 里用
`shutil.which("python3")` 把解释器路径显式写入 `Python3_EXECUTABLE` 缓存变量，
不依赖构建机 PATH 的偶然状态（R33）。

## 3. 踩坑记录

1. **`package_type` 不能用 `"application"`**
   CI 门禁 L0k（R38）以 `package_type == "application"` 作为“本包含命令行工具”的
   判据之一，会强制要求在软件级目录放 `commands.json`。本包无 bin/，用
   `package_type = "unknown"` + `cpp_info.resdirs = ["share"]`（E255/E305 同类模式）。

2. **s-expression 括号配平不能直接计数**
   第一版消费者测试用 `text.count("(") == text.count(")")` 判定库文件完整性，
   在 5 个库上误报（如 `Connector_Generic.kicad_sym` 两个计数相差 60）。原因是
   属性字符串里含括号（`(descr "...")`、`(property "Description" "...(...)...")`）。
   改为**引号感知**扫描后 222/222 全部通过。

3. **`(body_styles demorgan)` 会让引脚数翻倍**
   最初按直觉断言 `74xx:74LS00` 有 14 个引脚，实测 26。该符号声明了 De Morgan
   body style，每个 unit 输出两套 body style、各含一份引脚：
   4 门 × 3 引脚 × 2 + 电源单元 2 = 26。断言已按实测值固定（源码 sha256 固定，
   结果确定）。

4. **库表 uri 的占位符解析**
   打包后 `sym-lib-table` 的 uri 形如 `${KICAD10_SYMBOL_DIR}/4xxx.kicad_sym`。
   校验“表项指向真实文件”时必须把占位符解析为包内 `share/kicad/symbols`
   （KiCad 运行时正是用该环境变量指向此处），直接按相对路径拼接会全部误判为缺失。

## 4. 上游测试的处置（见 test_package/MANIFEST.yml）

- `klc-check/check_lib_table.py`（库表 ↔ 库文件一致性）：判定逻辑已在
  `test_package/test_kicad_symbols.py` 中**自包含等价复现**，随每次 `conan create`
  在 CI 真实执行（对应 9 条断言）。
- `klc-check/comparelibs.py`（KLC 规则 + 版本对比）：**未纳入**。它需要 git 历史
  （对比上一版本符号库）并 clone `kicad-footprints` 仓库，离线 CI 无法复现；
  影响面已在 `reports/test-report.md` 中说明。
- 未直接把 kicad-library-utils 源码复制进 `test_package/`：`check_lib_table.py`
  的依赖链为 `junit.py → rulebase.py → print_color.py`（该仓库为 GPL-3.0），
  整体内联进本仓库（Apache-2.0）会引入许可与维护问题；故选择“等价复现 + 逐条对照
  上游检查名”的方式，既能被 CI 每次回归，又不引入第三方代码。
