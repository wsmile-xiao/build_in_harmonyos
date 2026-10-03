# DRAFT: 2009 年代 C++ 的「迭代器遮蔽外层循环变量」硬错误

- **package**: plink/1.07（PLINK 1.07 适配）
- **context**: 交叉编译 2009 年的纯 C++ 程序（92 个 `.cpp`）到 OHOS aarch64
- **verdict**: 与 OHOS 无关；改名字即可，算法与输出零变化

## error_signature

```
sets.cpp:771:37: error: redefinition of 'i' with a different type:
    'vector<Individual *>::iterator' (aka '__wrap_iter<Individual **>') vs 'int'
      vector<Individual*>::iterator i = PP->sample.begin();
                                    ^
sets.cpp:703:12: note: previous definition is here
  for (int i=0; i<snpset.size(); i++)
           ^
```

## root_cause

`Set::profileTestScore()` 里先写了 `for (int i = 0; i < snpset.size(); i++)`，
循环体之后又在**同一作用域**声明 `vector<Individual*>::iterator i`。
2009 年的 gcc 3.x 之前接受这种嵌套声明；现代 clang/gcc 按 C++ 作用域规则判为
**硬错误**（不是 warning），整个 TU 直接编不过，于是 make 停在第一个错误文件上。

同型问题另见两处：

| 文件 | 行 | 被遮蔽的循环变量 | 迭代器声明 |
|---|---|---|---|
| `sets.cpp` | 771 | `for (int i=0; ...)` | `vector<Individual*>::iterator i` |
| `elf.cpp` | 1178 / 1192 | `int i` | `map<int,int>::iterator i` |
| `idhelp.cpp` | 775 | `for (int j = 0; ...)` | `set<IDField*>::iterator j` |

**这不是平台适配问题。** 同一份代码在 x86 Linux + 现代 clang 上同样失败。
把它记成「OHOS/musl 差异」是错误归因，会让知识库沉淀出假平台知识。

## rec_approach

- 只把被遮蔽的迭代器变量改名（`i → i_iter`、`j → j_iter`），**不动算法、控制流与输出**。
- 沿用发行版已验证的同一修复，不必自己造：PLINK 1.07 的 Debian 打包带
  `debian/patches/gcc-4.7.patch`（"Fix nested declaration which fails in gcc-4.7"，
  Bug-Closed bugs.debian.org/667325，2012-04-22，已转发上游 plink@chgr.mgh.harvard.edu）。
- 改动后要能说清输出等价：这三处循环分别喂给 set score 关联结果、按染色体统计的
  等位基因计数、joint field 名字列表，逐一核对即可。
- 落地验证：改完重新构建，确认 make 越过了这三个文件，且下游断言数值不变
  （本包 `--assoc` / `--freq` 的输出断言就是回归网）。

## forbid

| 模式 | 后果 |
|---|---|
| 把这类错误当 OHOS/musl 平台差异去"适配" | 归因错误，污染知识库，后人照抄错误方案 |
| 顺手用 `-std=gnu++98` 放宽整个工程 | 与仓内 `cppstd=17` 基线不一致，且 libc++ 已移除部分旧特性 |
| 为绕过编译删掉 R 插件 / zlib 支持 | 属于裁剪软件，违反红线；这两项上游默认开启且 OHOS 下都能链 |

## 附带发现：同源的另外两类老代码硬错误

1. **`less<>` 特化的 `operator()` 缺 `const`。** libc++ 用 `diagnose_if` 报
   `the specified comparator type does not provide a viable const call operator`
   （`-Wuser-defined-warnings`）。它是 warning 而非 error，但比较器缺 `const`
   在 libc++ 下属 ill-formed。Debian 有对应修复 `gcc11.patch`
   （bugs.debian.org/984293，给 `plink.h`/`homozyg.cpp`/`genogroup.h` 的 4 个
   `operator()` 加 `const`）。**先看是否真的阻断构建**：本包不带这个补丁也能
   编过并通过全部 37 项断言，故未纳入（保持最小改动）。
2. **`<endian.h>` 回退逻辑。** PLINK 的 `Rsrv.h` 在既没 `__LITTLE_ENDIAN__`
   也没 `__BIG_ENDIAN__` 时会 `#error "Cannot determine endianness"`，Debian 为此
   打了 `30_endiandetection.patch`。**实测 clang 对 aarch64 定义
   `__LITTLE_ENDIAN__`，不需要这个补丁**——别默认套用发行版补丁包，
   先确认编译器是否已定义。
