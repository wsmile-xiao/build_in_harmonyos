# DRAFT：out-of-tree(VPATH) 构建下上游 shell 用例用 `pwd` 拼绝对 `${top_srcdir}` 期望路径必失败

> 状态：草稿（待知识库主编 promote）
> 来源：libxdg-basedir 1.2.3 适配，`archives/l/libxdg/1.2.3`
> 类别：testing / autotools / build-system / portability / conan

## 错误特征

`make check` 稳定失败**固定数量的、与库功能无关的**用例，且失败集合只取决于
上游把哪些路径假设写死在测试脚本里。libxdg 1.2.3 的现场：

```
FAIL: tests/querycf.2
FAIL: tests/querydf.2
# TOTAL: 31
# PASS: 29
# FAIL: 2
```

失败用例本身会打印 `expected:` / `got:`——两者肉眼看着"几乎一样"，只多了一段重复
前缀：

```
expected:
/home/user/libxdg-basedir/tests//home/user/libxdg-basedir/tests/querycf.2
got:
/home/user/libxdg-basedir/tests/querycf.2
```

这个"路径被拼了两遍、第二遍还是绝对路径"的形态，是本条目最可靠的识别信号。

## 触发条件

- 构建系统是 autotools，`TESTS` 由一堆 shell 脚本组成（automake parallel-tests）。
- 上游脚本里出现 `pwd` 与 `${top_srcdir}`（或 `${top_builddir}`）**相乘**的路径拼接，
  典型的三种写法：
  ```sh
  wd="`pwd`"
  td="${top_srcdir}/tests"
  expected="$wd/$td/$basename"
  export XDG_CONFIG_DIRS="$wd/$td"
  ```
- configure 被**以绝对路径调用**（`<abs>/configure`）或构建目录与源码目录分离
  （out-of-tree / VPATH）。

三条同时成立 → 必然失败。libxdg 1.2.3 的 `tests/querycf.2`、`tests/querydf.2`
就是前两个 `query*.N` 用例（其余 28 个只用 `${top_srcdir}` 当相对前缀，
配上 `${top_builddir}/tests/testquery` 直接执行，不参与路径相乘，所以不受影响）。

## 根因分析

automake 的 `TESTS_ENVIRONMENT` 会把 `top_srcdir` / `top_builddir` 传进测试脚本：

```make
TESTS_ENVIRONMENT = env top_srcdir=$(top_srcdir) top_builddir=$(top_builddir)
```

而 `${top_srcdir}` 的**形态**由 configure 的调用方式决定：

| configure 调用方式 | `${top_srcdir}` | `"$(pwd)/${top_srcdir}/tests/x"` |
| --- | --- | --- |
| in-tree（`./configure`） | `.` | `$(pwd)/./tests/x` → 正确 |
| out-of-tree，相对（`cd b && ../configure`） | `..` | `$(pwd)/../tests/x` → 正确 |
| out-of-tree，绝对（`/abs/src/configure`） | `/abs/src` | `$(pwd)//abs/src/tests/x` → **错误** |

Conan 的 Autotools helper 固定用绝对路径：
`configure_cmd = "{}/configure".format(source_folder)`，且 `source_folder` 是绝对路径
（`conan/tools/gnu/autotools.py`）。于是同一个上游 tarball，在维护者机器上
（in-tree 或相对路径）31/31 全绿，在 Conan 里 29/31——**配方没做错任何事，
库代码也没错**，坏的是上游用例把"相对路径假设"当成了不变量。

对赛事而言这一点格外要命：rule4 要求声明"上游实测通过率"，而这 2 个用例会
把一个功能完好、31 个用例全可执行的库，永久钉在 29/31 的假象上；如果反过来
为了让数字好看去删/缩 `TESTS`，就变成少报。两条路都堵，只能修脚本。

## 解决方案

打一个只动 `tests/` 的补丁：把路径先解析成真实绝对目录再拼。

```diff
 harness="${top_srcdir}/tests/query-harness.sh"
-wd="`pwd`"
-td="${top_srcdir}/tests"
+td="$(cd "${top_srcdir}/tests" && pwd -P)"
 
 export HOME=/home/test
-export XDG_CONFIG_DIRS="$wd/$td"
+export XDG_CONFIG_DIRS="$td"
 
 basename="`basename "$0"`"
 arguments="config find $basename"
-expected="$wd/$td/$basename"
+expected="$td/$basename"
```

要点：

- **`cd ... && pwd -P` 对相对/绝对两种 `top_srcdir` 都得到同一真实路径**，所以补丁在
  in-tree 与 out-of-tree 下都成立，不需要按构建方式分叉。
- 用子 shell `$( )` 包裹 `cd`，不改变脚本后续的相对路径语义。
- 只改 `tests/*.N` 两个用例，`query-harness.sh` 公共比对逻辑一行不动（动它会把
  其余 28 个用例的断言语义一起废掉）。
- 补丁与被安装的库代码零交集，属**通用可移植性修复，可直接向上游提交**（P005）。

libxdg 1.2.3 的实测对照（唯一变量是 configure 调用方式）：

| 条件 | 结果 |
| --- | --- |
| 相对路径 configure，不打补丁 | 31/31 |
| 绝对路径 configure，不打补丁 | 29/31（querycf.2、querydf.2 FAIL） |
| 绝对路径 configure，打补丁 | **31/31** |

## 验证命令

```bash
# 1) 定位可疑用例：同时出现 pwd / top_srcdir / expected 的测试脚本
grep -ln 'pwd' tests/*.[0-9] | xargs grep -ln 'top_srcdir'

# 2) 复现：把 configure 换成绝对路径调用即可，无需改任何库代码
cd /tmp/build-abs && /abs/src/configure && make -j1 check   # 29/31
cd /tmp/build-rel && cd /abs/src && ./configure --prefix=... \
  && cd /tmp/build-rel && make -j1 check                   # 31/31

# 3) 补丁后验证汇总行（automake parallel-tests 会写 <build>/tests/test-suite.log）
grep -E '^# (TOTAL|PASS|FAIL|SKIP|ERROR)' tests/test-suite.log
```

## 禁止策略

| 禁止 | 原因 | 后果 |
| --- | --- | --- |
| 删/缩 `TESTS = …` 让 make check 全绿 | 少报上游用例数 | rule4 判 FAIL，PR 驳回返工 |
| 给失败用例打 skip（`SKIP_TESTS`、`.skip`、条件跳过） | 伪造通过率 | 评审不可信 |
| 改 `query-harness.sh` 的比对逻辑 / `always exit 0` | 会同时废掉其余用例的断言 | 测试假通过，回归保护失效 |
| 让配方改成"相对路径调用 configure"来绕开 | 绕过而非降级（P013），依赖调用方协调，随 Conan 版本漂移 | 同一配方在不同环境行为不一致 |

## 关联

- `similar_to` **E434**：automake `copystamp` 在 in-tree 构建下 `cp` 同文件失败，
  必须 VPATH 构建——本条目方向相反：VPATH 构建让上游用例的路径假设失效。
  两条合起来说明"上游对 in-tree/out-of-tree 的假设"是两个方向都会爆的雷。
- `similar_to` **E041 / E071**：VPATH 构建触发的 autotools 时间戳/版本重生成，
  同属"VPATH 构建暴露上游假设"家族。
- 配套（本题另一条，非本条目主题）：`E007`（config.guess/config.sub 不认 HarmonyOS）、
  `E114/E011`（HMDFS setgid 使 configure 内 `umask 077` 临时目录不可写）、
  `E074`（SELinux 禁 jobserver FIFO，`-j1`）——三者均在 libxdg 配方中同步处理。

## 上游可提交性

补丁只改测试脚本的路径解析，不引入平台宏、不依赖 HarmonyOS，与构建设备无关；
可直接向上游提 issue/PR（"query tests fail out-of-tree with an absolute top_srcdir"）。
