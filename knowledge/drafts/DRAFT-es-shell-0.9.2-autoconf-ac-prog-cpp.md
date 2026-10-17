# es-shell 0.9.2：configure.ac 使用 `$ac_cpp` 却未调用 `AC_PROG_CPP`，autoconf 2.72 下检测结果全空

> 草稿（DRAFT）— 来自 es-shell 0.9.2 HarmonyOS PC (aarch64) 第一轮适配的真实日志。
> 与 `.kv` 同 stem 配对，字段见 knowledge/drafts/DRAFT-es-shell-0.9.2-autoconf-ac-prog-cpp.kv

## 问题

es-shell 0.9.2（autotools）configure 阶段出现两级故障：

1. **configure 卡在自定义探测宏**：`./configure` 执行到 `AC_CMDSTDOUT_CPP` 时，
   直接把 `-I/storage/.../include: No such file or directory` 当作命令执行。
2. **rlimit 类型检测结果为空**：`checking for rlimit type ......`（点号后为空），
   config.h 生成 `#define LIMIT_T `（空值）→ 编译 prim-sys.c 报
   `error: expected expression`（`(LIMIT_T)n` 无法解析）。

## 根因

上游 `configure.ac` 自定义宏 `AC_CMDSTDOUT_CPP` 内部使用 `$ac_cpp` 做预处理探测：

```m4
AC_DEFUN([AC_CMDSTDOUT_CPP],
[cat > conftest.$ac_ext <<EOF
...
$1=`(eval "$ac_cpp conftest.$ac_ext") 2>&AS_MESSAGE_LOG_FD | $2`
...])
```

但脚本「Checks for programs」段只有 `AC_PROG_CC`，**从未调用 `AC_PROG_CPP`**。
autoconf 2.72 下 `ac_cpp` 在未运行 `AC_PROG_CPP` 时为空字符串：

- `eval "$ac_cpp conftest.c"` → `eval " conftest.c"` → shell 把 `-I<path>`（CPPFLAGS
  展开后的首词）当命令执行 → `-I...: No such file or directory`；
- 探测管道输出为空 → `es_cv_rlimit_t` 为空 → `AC_DEFINE_UNQUOTED(LIMIT_T, )` 生成空宏；
- 同理「files to extract signal information from」也返回空，SIGFILES 缺失。

## 解决方案

在 `configure.ac` 的 Checks for programs 段补一行：

```m4
AC_PROG_CC
AC_PROG_CPP      # ← 新增
AC_PROG_INSTALL
```

重新 `autoconf` 生成 configure 后，rlimit 类型正确探测为 `rlim_t`（config.h
`#define LIMIT_T rlim_t`），信号文件列表也恢复，后续 make/test 全通过。

## 验证

```bash
autoconf && ./configure ...   # checking for rlimit type ...... rlim_t
grep 'define LIMIT_T' config.h  # #define LIMIT_T rlim_t
make && make test             # 通过
```

## 适用边界

- 适用于任何 configure.ac 自定义宏引用 `$ac_cpp` 且未 `AC_PROG_CPP` 的 autotools 项目；
- autoconf ≤ 2.71 可能因历史默认行为不触发（ac_cpp 有默认值），autoconf 2.72 必现；
- 症状表现为"检测结果空 + 编译期宏空值报错"，而非 configure 直接报 AC_PROG_CPP 缺失。

## 反例 / 限制

- 若项目已调用 AC_PROG_CPP，则根因不适用，需检查其他探测逻辑；
- 若同时存在 config.guess 不认识平台的问题（es-shell 也遇到），需要另配 OHOS
  补丁版 config.guess/config.sub（见 E114 场景），两者独立。
