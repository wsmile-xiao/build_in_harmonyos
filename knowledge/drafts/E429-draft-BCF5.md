# E429 — 补丁改动 configure 触发 autotools 文档重生成（makeinfo 缺失 + version.texi 写入环境变量）

> 状态：草稿（draft，待主编审核）
> 来源：diffutils 3.12 适配（2026-09-14）
> 关联条目：E011（HMDFS umask/临时目录）、E007（config.guess 不识别 HarmonyOS）

## 错误特征

典型日志（make 阶段）：

```
makeinfo: command not found
Makefile:xxx: recipe for target 'doc/diffutils.info' failed
make[3]: *** [doc/diffutils.info] Error 127
```

或（本条目真正危险的形态）——`doc/version.texi` / `doc/stamp-vti` 被重写为**进程环境变量清单**：

```
$ head -3 doc/version.texi
-@set UPDATED 12 January 2025
-@set UPDATED-MONTH January 2025
+AGENT_NAME=runner32
+ALACRITTY_WINDOW_ID=window112_terminal0
+CC=clang
+CFLAGS='-fPIC -O2'
```

此时若再执行 `refresh-patch --auto`，生成的是 +121 行的「补丁」，内容即构建机环境变量 dump。

## 触发条件

- 构建系统：autotools（随包发布预生成的 `doc/*.info`）
- 阶段：make（文档子目录）
- 前置动作：适配补丁修改了 `configure`（或 `Makefile.in` 等由 automake 生成的输入文件）

## 根因分析

1. `doc/stamp-vti` 的依赖包含 `$(top_srcdir)/configure`。补丁改动 `configure` 后其 mtime 比 tarball 内随包发布的 `stamp-vti` 更新，make 于是判定过期并重生成 `stamp-vti → version.texi → <pkg>.info`。
2. 构建环境通常无 texinfo（`makeinfo`），重生成在 `.info` 处失败（Error 127）。
3. 更隐蔽的后果：上游 `build-aux/mdate-sh`（被 `version.texi` 规则调用）在 HarmonyOS 上会把**整个进程环境**当作命令输出写入 `version.texi`，而不是写入日期；这些被污染的源文件随后被 `refresh-patch` 识别为「源码修改」，产出一个把构建机环境变量（含路径、以及可能的凭据类变量）带进仓库的垃圾补丁。
4. 与普通「文档重生成失败」的区别：**编译不一定会失败**（只是 mtime 被刷新），但会静默污染补丁集——因此必须单独检查补丁产物。

## 解决方案

### 推荐方案

在配方 `build()` 中、执行 `make` **之前**，把随包发布的文档产物 mtime 统一刷新，使其不再满足「比 configure 旧」的重生成条件：

```python
def _preserve_prebuilt_docs(self):
    """doc/*.info 随包发布，不应重生成。"""
    doc_dir = os.path.join(self.source_folder, "doc")
    now = time.time()
    for name in ("stamp-vti", "version.texi", "<pkg>.info"):
        path = os.path.join(doc_dir, name)
        if os.path.isfile(path):
            try:
                os.utime(path, (now, now))
            except OSError as exc:
                self.output.warning(f"cannot touch doc/{name}: {exc}")
```

若只需构建工具、不需要文档，也可在 configure 阶段使用上游提供的 `--disable-doc` 类开关（上游支持时优先）。

补丁收尾时核对产物：`patches/` 中不应出现 `doc/stamp-vti`、`doc/version.texi` 之类“文档”补丁；一旦出现，先确认是否被环境变量 dump 污染，再决定是否保留。

### 禁止做法

- ❌ 把被污染的 `doc/version.texi` / `doc/stamp-vti` 当作源码修改打成补丁提交（等于泄漏构建机环境）
- ❌ 通过额外打补丁去“修”被污染的文件（应把 `.work` 中该文件回滚至 `.orig`，并清理 `.edit-tracker.json` 的 `edited` 列表后重新生成）
- ❌ 依赖 `MAKEINFO=true` 之类 stub 绕过而不处理 mtime 语义（换包/换版本即复发）

## 验证

```bash
# 1) 重生成是否被阻止（构建后 doc 未被改写）
head -3 doc/version.texi          # 应为 @set UPDATED ...，不得出现 VAR=value
# 2) 补丁集是否干净
ls patches/                       # 不应出现 doc/stamp-vti / doc/version.texi 补丁
git diff --stat patches/
# 3) 干净源码验证
python3 scripts/ohc-run.py clean-verify <软件> <版本>
```

## 实证

- diffutils 3.12：补丁 `0002-configure.patch` 改动 configure → 触发 `stamp-vti`/`version.texi` 重生成 → `makeinfo` 缺失 Error 127；同一次会话中 `refresh-patch --auto` 因 `.work` 内两文件被环境 dump 污染，误生成 `0003-doc-stamp-vti.patch`、`0004-doc-version.texi.patch`（各 +121 行）。回滚后补丁集恢复为 2 个。
- 配方实现见：`archives/d/diffutils/3.12/conanfile.py::_preserve_prebuilt_docs`

## 关联条目

- 相关：E011（umask/HMDFS 临时目录）、E007（config.guess 三元组）、E232（configure 需 native shell）
