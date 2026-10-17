# DRAFT-E2175：静态库 Conan 包的鸿蒙特有测试——归档直接验证 + 消费者链接产物断言

> Contributor: goblinrs | Status: Draft (rev 2, 2026-09-09) | Updated: 2026-09-09
> Source: libsvg-cairo 0.1.6 PR rule12 修复（本地 conan test 全链路通过）

## 背景

libsvg-cairo 0.1.6 只产出静态库 `libsvg-cairo.a`（上游无 shared 选项，R26 例外）。
web-review 指出 test_package 只验证了消费者 API（L0k），缺 rule12 鸿蒙特有测试：
没有以最终 Conan 包产物为输入的 OHOS 属性验证与真实流程验证。R1 修复建立了
"从包产物链接出 .so + 可执行文件再断言"的链路，但 rev 1 草稿与 manifest 的
技术边界表述不准确：把 DT_SONAME、PT_INTERP、.code_signature 说成静态包/静态
归档的属性。rev 2 修订为严格区分三类对象，并把每个断言只施加在适用的对象上。

## 三类对象（本条知识的核心边界）

| 记号 | 对象 | 身份 | 可施加的断言 |
|------|------|------|--------------|
| [P] | `libsvg-cairo.a` | 最终 Conan 包产物（conan cache `package_folder`） | 归档身份 + 成员架构（ar magic / 非空 / 成员 ELF64 LE AArch64 REL） |
| [S] | `libsvg-cairo-ohos.so.0` | 测试派生的共享库（消费者打包场景模拟） | ELF64/AArch64、DT_SONAME、导出符号、NEEDED 洁净性 |
| [E] | `ohos_svg_check` | OHOS 运行时消费者产物（可执行文件） | PT_INTERP、.code_signature、NEEDED/RUNPATH 洁净性、真实 SVG 解析+渲染 |

静态归档是 ar 容器而非动态 ELF：SONAME/INTERP/.code_signature 段在 .a 上
**不存在**，只存在于消费者链接生成的动态对象上。宣称"静态库本身具有
SONAME/INTERP/code_signature"是边界错误；对 .a 唯一直接可验的是归档身份
（`!<arch>` 魔数）与成员目标文件的 ELF 头。

## 错误链（R1→R2 实测踩坑）

### 坑 1：CONAN_LIB_DIRS_* 未导出

Conan 2.x VirtualRunEnv 生成的 conanrun 环境只有 PATH/LD_LIBRARY_PATH 等，
不导出 `CONAN_LIB_DIRS_<PKG>` 变量，测试脚本无法从 env 拿到被测包目录。必须
在 test() 中用 `self.dependencies[self.tested_reference_str].package_folder`
取包目录，经 env（`OHOS_PKG_LIBDIR=` 等）显式传给脚本。

### 坑 2：不用 --whole-archive 产出空壳 .so

ld 默认按需抽取归档成员；消费者只引用 `svg_cairo_create` 时，未被直接引用的
成员被丢弃，产出零导出的空壳 .so（动态符号表 svg_cairo 符号数为 0）。
`--whole-archive` 的用途**仅是**确认归档成员确实进入派生产物（防零导出空壳），
不是给静态库"赋予".so 属性。断言 `readelf --dyn-syms | grep -c svg_cairo ≥ 5`
验证成员真实进入。

### 坑 3：--whole-archive 生成 .so 的 PIC 前提

用 `-shared --whole-archive` 生成共享库要求归档成员满足 PIC。非 PIC 归档成员
链接时实测报错：

```text
relocation R_AARCH64_ABS32 cannot be used against symbol ...; recompile with -fPIC
```

此时**不能强行生成共享库**，应改为构建直接引用包公开 API 的可执行消费者
（可执行文件对成员 PIC 无要求）。本包 fPIC=True，走共享库路径；脚本在链接
失败信息中注明回退形态。

### 坑 4：INTERP 断言 grep 假失败

`readelf -l` 的 INTERP 信息在 `Requesting program interpreter: /lib/ld-musl-aarch64.so.1`
行；`grep "INTERP"` 只命中 segment 标题行 `INTERP`，永远取不到解释器路径。
必须 grep `"Requesting program interpreter"`。

### 坑 5：RUNPATH 方括号假通过（R2 新发现）

rev 1 脚本链接时注入 `-Wl,-rpath,$OUT`，断言用 `grep -E "\[(RPATH|RUNPATH)\]"`
排除宿主路径。但 readelf 实际输出是圆括号 `(RUNPATH) Library runpath: [...]`，
方括号模式**永远失配**——上次"通过"是模式失配的假通过，而 rpath 本身会把本机
输出目录（`/storage/...`）写成 DT_RUNPATH 宿主路径。修正：链接时不注入 rpath，
运行期用 LD_LIBRARY_PATH 定位派生库；断言改 `grep -E '\((RPATH|RUNPATH)\)'`。

### 坑 6：.codesign 段名

OHOS lld 对消费者链接生成的动态对象注入的签名段，readelf -SW 实测段名为
`.codesign`（即 code signature 段），不是 `.code_signature`。断言统一为
实际验证的精确段名：`grep -qE "\.code_signature|\.codesign"`（两种写法都接受，
实测命中 `.codesign`）。

### 坑 7：toybox grep 不支持 BRE \| 交替（R2 新发现）

OHOS PC 的 `/usr/bin/grep` 是 toybox 0.8.x：`grep -q "A\|B"` **恒失配**（即使
B 存在），得到假失败。`grep -qE "A|B"` 正常。所有含交替的断言必须用 `-E`。
（本坑由 conan test 实测复现：坑 6 的修复第一版用 `\|` 写法，.codesign 明明
存在却断言失败。）

### 坑 8：conanrun LD_LIBRARY_PATH 污染宿主工具（CI #42924，R3 新发现）

test() 以 `self.run(..., env="conanrun")` 调 test_ohos.sh 时，VirtualRunEnv
的 LD_LIBRARY_PATH **前置了目标依赖包 lib/ 目录**。脚本内的宿主 clang/lld/
llvm-ar/readelf 若直接继承该变量，宿主 lld 会从目标目录加载目标包
libxml2.so.16（而非 SDK llvm/lib 下的宿主版），符号重定位失败崩溃。该崩溃
曾被链接失败信息误报为"non-PIC members"——**宿主工具加载器错误会伪装成链接/
PIC 错误，必须先看真实工具闭包输出再定性**。

修复模式（环境分裂）：
- conanfile.py 单独计算宿主工具运行所需的 LD_LIBRARY_PATH（E429 恢复目录 +
  VirtualBuildEnv 组合出的 conanbuild LD_LIBRARY_PATH，剔除目标依赖目录），
  经 `OHOS_TOOL_LD_LIBRARY_PATH` 传给脚本。注意：`Environment().vars()` 只含
  该对象自身的值，**取不到 profile [buildenv]**；必须用
  `VirtualBuildEnv(self).vars()`（与 conanbuild.sh 同一组合逻辑）。
- 脚本内所有宿主工具调用统一 `env LD_LIBRARY_PATH="$OHOS_TOOL_LD_LIBRARY_PATH"`
  包装（run_tool 函数）；目标依赖只在链接行经 -L/绝对路径解析。
- 仅在真正**运行目标消费者**时，才临时 `LD_LIBRARY_PATH=$OUT:依赖目录`。
- `set -e` 下 `cmd; rc=$?` 是死代码（cmd 非零退出直接终止脚本，诊断信息
  丢失）；捕获退出码必须写 `rc=0; cmd || rc=$?`。

## 修订后的测试链路（test_ohos.sh）

1. **[P] 归档直接验证**：`head -c 8` 验 `!<arch>` 魔数；`ar t` 非空；
   `ar p` 逐成员提取，`readelf -h` 验成员 Class=ELF64、Data=little endian、
   Type=REL、Machine=AArch64。
2. **[S] 链接派生共享库**：`clang -shared -Wl,-soname,... -Wl,--whole-archive
   $SVGC_A -Wl,--no-whole-archive` + 静态 libsvg.a/libjpeg.a 并入 + 共享依赖；
   断言 ELF64/AArch64、SONAME 与文件名一致、svg_cairo 导出符号 ≥5、
   NEEDED 无宿主机路径。
3. **[E] 链接消费者可执行文件**：不注入 rpath；断言 ELF64/AArch64、
   INTERP=/lib/ld-musl-aarch64.so.1、.code_signature/.codesign 段存在、
   NEEDED 含 libsvg-cairo-ohos.so.0 且无宿主机路径、无宿主 RUNPATH。
4. **运行**：LD_LIBRARY_PATH 定位派生库后在 OHOS PC 运行 ohos_svg_check，
   完成真实 SVG 解析 + cairo 渲染（ARGB32 surface、像素断言），非零退出即失败。

manifest 口径（harmonyos_specific_tests 描述）统一为：
"以最终 Conan 包中的静态归档为输入，验证归档成员架构，并链接生成消费者 ELF，
对消费者产物执行 OHOS 属性和运行验证。"

## 查重结论（rev 2，2026-09-09）

对七组语义在 knowledge/ 全库查重，均为部分重叠、无完整链路覆盖：

| 语义 | 最近条目 | 差异 |
|------|----------|------|
| static archive member architecture | E236 | 仅 thin archive 成员场景 |
| ar archive ELF object | E371 | 仅提及 ar，无验证链路 |
| consumer-linked artifact | E234 | whole-archive→fPIC 映射，无消费者产物分层断言 |
| whole-archive empty shared object | E234 | 不含空壳检测链路 |
| PIC boundary | E539 | 共享目标捕获非 PIC，无回退形态 |
| static Conan package OHOS test | E541 | zlib 静态 PIC 策略 |
| package_folder artifact validation | E241 | 数据清单 hash，非测试断言 |

故保留 DRAFT-E2175 并申报路径 B。

## 关联

- similar_to: E234（whole-archive 链接）、E298（conanrun 显式运行）、
  E236（thin archive 成员）、E241（package_folder 数据清单）、
  DRAFT-libharu-2.3.0-missing-dt-soname（SONAME 缺失）
- 对应实现：`archives/l/libsvg-cairo/0.1.6/test_package/test_ohos.sh`、
  `ohos_svg_check.c`、`conanfile.py test()`
- CI 案例链：#42924（conanrun LD_LIBRARY_PATH 污染宿主 lld，坑 8）→
  修复见 test() 的 OHOS_TOOL_LD_LIBRARY_PATH 注入与脚本 run_tool 环境分裂
