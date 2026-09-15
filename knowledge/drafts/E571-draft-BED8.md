# E571 — 手写 install-data-local 缺 DESTDIR 且未用 $(srcdir)，staging 下装错位置或找不到源文件

## 错误特征

症状有两种，取决于构建目录与源码树的分离程度，都源于同一条规则：

```
# 形态 A（out-of-tree）：源文件找不到
make[2]: *** No rule to make target 'cpu.conf'
 doc/Makefile.in: install-data-local: $(INSTALL_DATA) cpu.conf $(sysconfdir)/cpu.conf

# 形态 B（最危险）：安装"成功"但包内缺文件
$ conan create .          # 全绿通过
$ ls <package>/etc/       # 空的 —— 文件其实写进了宿主 /etc
```

形态 B 的判定要点：检查**宿主** `/etc` 是否被写入（`ls -l /etc/cpu.conf`），staging 目录（DESTDIR 指向处）却没有该文件。构建机被静默污染，而 CI 干净环境上表现为"包内容缺失"。

## 触发条件

- 构建系统: autotools，**手写**的 `install-data-local` / `install-exec-local`（automake 自动生成的 `install-data` 规则无此问题）
- 阶段: make install（conan 的 `package()` 以 DESTDIR staging 方式安装）
- 观察: 版本化 `Makefile.in` 的 install 规则里目标路径**不带 `$(DESTDIR)`**，或源文件名**不带 `$(srcdir)/`**

## 根因分析

手写 install 规则通常默认两个前提：

1. **安装目标是宿主根**：直接写 `$(sysconfdir)/cpu.conf`，缺 `$(DESTDIR)` 前缀。conan 打包依赖 DESTDIR 把文件收进包目录，缺前缀时文件被装到宿主真实 `/etc`——既污染构建机（并可能被后续 CI 判定为"改动系统"），又导致 package 内空目录。
2. **源文件在构建目录中**：直接写 `cpu.conf` 而非 `$(srcdir)/cpu.conf`。in-tree 构建时构建目录 == 源码目录，恰好能命中；conan 是 out-of-tree，源文件在源码树，规则在 build 目录执行，于是找不到（形态 A）。

两者的共同点是**用了"构建环境等于安装环境、构建目录等于源码目录"的隐含假设**，而这正是交叉编译/打包工具链必然打破的假设。

## 解决方案

### 推荐方案

以最小补丁修正规则（cpu 1.4.3 的 `0004-doc-Makefile.in.patch` 即此形态），同时补齐两处前缀：

```diff
--- a/doc/Makefile.in
+++ b/doc/Makefile.in
 install-data-local:
-	$(INSTALL_DATA) cpu.conf $(sysconfdir)/cpu.conf
+	$(INSTALL_DATA) $(srcdir)/cpu.conf $(DESTDIR)$(sysconfdir)/cpu.conf
```

该补丁符合可上游化要求（P005）：修的是上游规则对 DESTDIR/out-of-tree 支持不全，不引入任何平台宏或平台专有逻辑。

### 禁止做法

- ❌ 在 conanfile.py 的 `package()` 里手工 `copy("cpu.conf", ...)` 补上文件——绕过 install 规则，掩盖真实缺陷，且与上游行为永久分叉
- ❌ 用 `--srcdir=<path>` 之类参数把构建拉回 in-tree 来"让相对路径刚好能命中"
- ❌ 忽略形态 B：看到 `conan create` 全绿就认为 install 正常（文件可能装到了宿主，包内实际缺文件）

## 验证

```bash
# 1. 包内应有文件
ls <package_folder>/etc/cpu.conf
# 2. 宿主不应被写入（前后对比）
ls -l /etc/cpu.conf            # 期望：不存在
# 3. 端到端
python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify cpu 1.4.3
```

## 关联条目

- 相关: E569（同属 out-of-tree 假设，发生在编译期；本条目在安装期）
- 相关: E046（HMDFS 权限语义，install 阶段易混淆的相邻现象）
