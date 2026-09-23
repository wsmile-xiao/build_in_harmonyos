# DRAFT-crack-5.0a-knr-clang15: K&R 老 C 代码在 clang 15 下默认报 error，`-std=gnu89 -Wno-int-conversion` 组合恢复编译

> **Contributor**: 2404_87638649 | **Status**: Draft（pending editor review）| **Updated**: 2026-09-11
> **Source**: crack 5.0a HarmonyOS PC 适配（build_in_harmonyos，archives/c/crack/5.0a）
> **拟提升编号：由知识库主编确认** —— 本草稿为未提升草稿，尚未分配正式 E 编号

## 场景

把 1990s 的 K&R 风格 C 源码（本例：Alec Muffett 的 crack 5.0a，1996 年发布，Debian
归档 `crack_5.0a.orig.tar.gz`）搬到 OHOS PC（clang 15.0.4 + musl）上编译。此类老工具
普遍无 configure 脚本、手工 Makefile、函数无原型、用固定参数列表模拟变参。

## 问题

可复用问题签名（日志症状）：

```text
error: incompatible integer to pointer conversion passing 'int' to parameter
       of type 'char *' [-Wint-conversion]
warning: a function definition without a prototype is deprecated in all
       versions of C and is not supported in C2x [-Wdeprecated-non-prototype]
warning: passing arguments to 'Logger' without a prototype is deprecated ...
```

真实证据（crack 5.0a，src/util/cracker.c）：

```c
void
Logger(key, fmt, a, b, c, d, e, f)   /* K&R 定义：伪变参 */
char key;
char *fmt;
char *a, *b, *c, *d, *e, *f;
{ ... fprintf(stdout, fmt, a, b, c, d, e, f); ... }
```

调用侧把 `int`/`long`/`pid_t` 直接传给 `char *` 形参（K&R 时代指针整数同宽的惯用法）：

```c
Logger('S', "pid=%d ciphers=%ld ... srule=%d\n",
       getpid(), cstat_numciphers, ..., from_rule);
```

- **关键区分点**：crack 的 Makefile **没有启用 -Werror**（对照 E063 场景），
  但 clang 15 对 int→pointer 转换默认就是 error，`-std=gnu89` 单独不能解除；
- 无原型老式定义在默认 dialect 下报 deprecation（C2x 起变 error）。

## 根因

两类冲突叠加：

1. **伪变参 int/pointer 混传**：K&R 惯用法在 ANSI 原型化后的 clang 语义下是
   `-Wint-conversion` 硬错误（clang 15 默认开启，与 -std 档位无关）；
2. **老式函数定义无原型**：`-Wdeprecated-non-prototype`，C2x 移除支持。

## 修复（最小方案）

组合两个编译开关直传 make 变量（不动 1996 源码语义）：

```bash
XCFLAGS="-std=gnu89 -Wno-int-conversion -O2 -DUSE_STRING_H -DUSE_STDLIB_H \
         -DUSE_SIGNAL_H -DUSE_SYS_TYPES_H -DUSE_UNISTD_H -DUSE_PWD_H"
make -C src/lib  "XDIR=../../run/bin" "XCFLAGS=$XCFLAGS" "XCC=clang"
make -C src/util "XDIR=../../run/bin" "XCFLAGS=$XCFLAGS" "XCC=clang" \
     "../../run/bin/stdlib-cracker"
```

- `-std=gnu89` 恢复隐式 int / 老式定义合法地位；
- `-Wno-int-conversion` 把伪变参混传降回 warning；
- `-DUSE_*_H` 系列是 crack 上游 `Crack` 驱动脚本注释里写明的平台移植开关。

## 验证

- `conan create archives/c/crack/5.0a --profile:host=ci/conan/profiles/ohos-aarch64`
  全绿（exit 0），产出 cracker/dawg/xdawg/dictfilt/kickdict 五个 aarch64 OHOS ELF；
- 真机功能验证：dawg/xdawg 词典往返无损；cracker 经完整字典管线
  （mkdictgrps 全量 + 2312 规则）从 `crypt("123456","ab")` 密文恢复出明文。

## 可复用边界

- 适用：一切 1990s K&R C 老工具（无 configure、手工 Makefile、无原型）搬上
  clang 15/musl 的场景——报错签名全是 `-Wint-conversion` /
  `-Wdeprecated-non-prototype` 且项目 grep 不到 `-Werror` 时必中；
- 限制：`-Wno-int-conversion` 降级后 K&R 混传在 LP64 上依赖"指针/long 同宽"成立
  （arm64 成立）；若代码依赖 int==指针宽度（ILP32 假设）则需真改代码。

## 与现有条目的关系（查重）

- **E063**（-Werror 升级）不覆盖：crack 未启用 -Werror，错误来自 clang 15 对
  int→pointer 默认 error 的新行为，仅去 -Werror 无解；
- **E420**（隐式声明/头文件直含）不覆盖：本条是伪变参混传 + 老式定义的编译
  dialect 问题，非 API 可见性问题。
