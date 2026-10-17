# libdb 5.3.35 — Meson 侧的代换表把宏槽位留成空串，`gen_header.py` 于是把宏整段抹掉（草稿）

**Category**: build, conan, meson, headers, substitution, portability · **Severity**: 3 · **Tool**: meson|gen_header|custom_target|cc

## 症状

`meson compile` 在**第一个**编译单元就炸，20 条同型错误后 `-ferror-limit` 截断：

```
[5/275] Compiling C object dist/libdb.a.p/.._src_btree_bt_compact.c.o
In file included from ../src/btree/bt_compact.c:11:
In file included from dist/db_int.h:88:
dist/db.h:529:14: error: expected ';' at end of declaration list
        int (*close) __P((DB_LOGC *, u_int32_t));
                    ^
                    ;
...
fatal error: too many errors emitted, stopping now [-ferror-limit=]
20 errors generated.
```

迷惑点：**报错在 `db.h` 里，但 `db.h` 是构建期由模板渲染出来的生成物**，源树里根本没有
这个文件（只有 `src/dbinc/db.in`）。而报错的那一行看着完全合法 —— 传统 C 写法
`int (*close) __P((DB_LOGC *, u_int32_t));`，clang 却在 `__P` 处要分号。
**那正是「`__P` 这个宏根本没被定义」的报错形态**：`__P` 变成了一个普通标识符，
clang 把它当成 `(*close)` 之后的意外 token。

而且 `dist/db_int.h:88` 包含 `db.h`，所以**每一个**编译单元都以同样方式失败，
不是「某几个文件的问题」。

## 根因

`db.h` 是模板渲染的产物：`src/dbinc/db.in` 里的 `@VAR@` 占位符，
由 `dist/meson/gen_header.py` 按 `dist/meson/db_subs.json` 的表逐项替换：

```python
# dist/meson/gen_header.py:19
return re.sub(r"@([A-Za-z0-9_]+)@",
              lambda m: subs.get(m.group(1), m.group(0)), text)
```

注意替换语义是 **`查表值 or 原样保留占位符`**，而表里给的是**空串**。

Berkeley DB 的头文件**故意不包含 `db_config.h`**（模板注释原文：*"db.h include file
layout"*，且 `db.h` 的 `__P` 用法来自 `db_185.h` 的传统），所以 `__P()` 这个原型包装宏
必须由模板自己给出。`db.in` 因此专门备了两个槽位：

```
@DB_CONST@
@DB_PROTO1@
@DB_PROTO2@
```

Autotools 线由 `dist/configure.ac:407-411` 按编译器类型算值：

```sh
DB_PROTO1="#undef __P"
if test "$ac_cv_prog_cc_c89" = "no"; then
	DB_PROTO2="#define	__P(protos)	()"
else
	DB_PROTO2="#define	__P(protos)	protos"
fi
```

而 Meson 线的 `dist/meson/db_subs.json` 把这三项留成了：

```json
"DB_CONST": "",
"DB_PROTO1": "",
"DB_PROTO2": "",
```

`gen_header.py` 拿到空串 → 替换成空 → 生成的 `db.h` 里那段「清掉并重定义 `__P`」的
代码**整段消失**，而文件后面 470 处 `__P((...))` 全在。`DB_CONST` 留空是**对的**
（configure.ac 只在 pre-ANSI 编译器下才给它赋值），但 `DB_PROTO1/2` 留空就是漏代换。

**判据：模板的某个占位符被留成空串时，要分清它到底是「该为空」还是「漏填」——
去另一条构建线（或树里随包发布的其它平台构建产物）看同一个占位符被代换成什么。**
本例树里 `build_android/db.h:39-40` 正好就是那两行，是现成的「正确输出」对照。

## 处置（可复用）

把两个槽位补成另一条构建线（`configure.ac`）对 ANSI C 编译器所选的值：

```json
"DB_PROTO1": "#undef __P",
"DB_PROTO2": "#define\t__P(protos)\tprotos",
```

（JSON 里写 `\t`，`json.load` 后即真实制表符 —— 与 configure.ac/sed 线写进 `db.h`
的内容逐字节一致。）

### 怎么提前发现

1. **空串占位符审查**：列出替换表里所有值为 `""` 的键，逐个去模板里 grep 该占位符的
   用法，判断「空」是语义还是缺漏：

   ```sh
   python -c "import json;d=json.load(open('dist/meson/db_subs.json'));print([k for k,v in d.items() if v==''])" |
     tr ',' '\n' | sed 's/[][ \x27]//g' | while read k; do grep -c "@$k@" src/dbinc/*.in; done
   ```

   注意 `DB_VERSION_UNIQUE_NAME`、`int16_decl` 这类**确实该为空**（类型已由系统头提供、
   或该构建线不需要符号重命名），不能一刀切。

2. **有第二条构建线时先比对该占位符的取值**：`grep -n 'DB_PROTO' dist/configure`
   直接给出定值；树里有别的平台构建产物（`build_*/`）更好，直接 diff 生成的头。

3. **生成物的头文件报语法错，先怀疑宏没定义**：clang 对「未知标识符出现在声明列表里」
   的报错就是 `expected ';' at end of declaration list`，光标停在那个标识符上并提示
   补 `;`。**不要顺着这个报错去改 `db.h`**（它是生成物），也不要怀疑 `-std=` 或
   系统头 —— 去模板里找那个标识符该由谁定义。

## 退路

- **不改上游、只在配方侧兜底**：在 `generate()`/`build()` 里把
  `-D__P(x)=x`（或 `#define __P(protos) protos` 拼进 CFLAGS）塞进命令行。
  能编过，但把「上游 Meson 路径漏代换」这个事实藏进了消费者配方，且一旦上游补齐
  就变成重复定义告警。**仅在无法打补丁时使用。**
- **换回 Autotools 线**：`dist/configure.ac` 的线代换是对的 —— 但那要付
  HMDFS 上 `print -r --` / `umask 077` / 老 `config.guess` 三类坑的代价
  （见同批草稿 `DRAFT-6818-libdb-5.3.35-meson-sidesteps-autotools-hmdfs-pits`），
  为了省一个 2 行补丁而放弃整条 Meson 线不划算。

## 验证

- **本地复现**：`python dist/meson/gen_header.py out.h dist/meson/db_subs.json
  src/dbinc/db.in src/dbinc_auto/api_flags.in src/dbinc_auto/ext_def.in
  src/dbinc_auto/ext_prot.in`，未打补丁时 `out.h` 第 529 行即
  `int (*close) __P((DB_LOGC *, u_int32_t));`（与 CI 报错行号逐字一致）。
- **补丁实测**：`patch_ng.fromfile(p).apply(strip=0, root=<src>)` ——
  注意 Conan 的 `conandata.yml` 补丁默认 `strip=0`，靠 patch_ng 的
  `a/`/`b/` 前缀回退找到文件；本包两条补丁依次返回 `True`。
- **端到端**：补丁后重跑 `gen_header.py`，渲染出的 `db.h` 在版本宏之前出现

  ```
  #undef __P
  #define	__P(protos)	protos
  ```

  与其后 470 处 `__P((...))` 用法配套。
- 提交后由 CI 实跑 `conan create` 验证（`libdb.a.p/.../bt_compact.c.o` 不再 FAILED）。

## 关联

- `archives/l/libdb/5.3.35/patches/0002-meson-db-subs-proto-macros.patch`
- `archives/l/libdb/5.3.35/notes.md`（「补丁：patches/0002-…」一节）
- `DRAFT-6818-libdb-5.3.35-fork-version-strings-drift-from-release`
  （同一张表、同一批行的另一半问题：版本串漂移。两条补丁改相邻行，
  0002 的上下文行特意避开 0001 改动的行，故必须按 0001 → 0002 顺序应用）
- `DRAFT-6818-libdb-5.3.35-meson-sidesteps-autotools-hmdfs-pits`
  （为什么本包走 Meson —— 也正是「两条构建线并存」这个前提本身）
