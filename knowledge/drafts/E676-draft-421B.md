# E676 — configure 补丁触发 doc 时间戳链重算，缺 makeinfo 报 Error 127

## 错误特征
```
MAKEINFO  …/doc/shishi.info
build-aux/missing[81]: makeinfo: inaccessible or not found
WARNING: 'makeinfo' is missing on your system.
make[3]: *** [Makefile:…: …/doc/shishi.info] Error 127
make: *** [Makefile:…: check] Error 2        # 同样出现在 install
```
设备侧连锁（可选观察）：
```
build-aux/mdate-sh: failed parsing 'ls -L -l -d -n /' output
doc/version.texi / doc/stamp-vti 内容被 shell 环境变量导出覆盖（含凭证）
```

## 触发条件
- 构建系统: autotools + info_TEXINFOS（info 手册随 tarball 发布）
- 阶段: make check / make install（doc 子目录）
- 前提: 打过 configure（或上游文件）补丁 → mtime 新于 `stamp-vti` → 时间戳链重算

## 根因分析
上游 `doc/Makefile` 的链条：

```
$(srcdir)/stamp-vti: shishi.texi $(top_srcdir)/configure
$(srcdir)/version.texi: $(srcdir)/stamp-vti
$(srcdir)/shishi.info: shishi.texi $(srcdir)/version.texi
```

我们对 `configure` 打补丁（HMDFS mktemp → mkdir）后 configure 变新 → `stamp-vti` 规则触发 →
`version.texi` 重建且新于 `shishi.info` → make 要求用 **makeinfo** 重建 info 手册。
设备与 CI worker 都没有 makeinfo（ohpcd 未发布 texinfo），`missing` 包装打出 Error 127，
`make check` 与 `make install`（= conan `package()`）同时失败。

**设备连锁（凭证泄漏近失）**：stamp 规则先跑 `build-aux/mdate-sh`，它解析不了 toybox
`ls -L -l -d -n /` 输出而返回空；规则里的 `set \`\``（零参数）在 mksh 系 shell 下**打印全部
shell 变量**，被重定向进 `vti.tmp` → `version.texi`/`stamp-vti` 被整个环境（含
`GITCODE_TOKEN`）覆盖。本次恰逢 `refresh-patch --auto` 快照，几乎被打成 `0002/0003`
补丁入库——人工审查发现后已还原并删除。

## 解决方案

### 推荐方案
`build()` 在 `apply_conandata_patches()` 之后、configure 之前，对以下文件**只对齐 mtime**
（内容零改动 ⇒ 零 diff 零补丁）：

```python
doc/stamp-vti, doc/version.texi,
doc/shishi.info, doc/shishi.info-1, doc/shishi.info-2, doc/shishi.info-3
# os.utime(path, None)，按此顺序（stamp → version → info）
```

stamp 新于补丁后的 configure、info 新于 version.texi ⇒ 规则不再触发、makeinfo 不再被调用、
`mdate-sh` 不再执行（环境泄漏路径同时被封）。

### 禁止做法
- ❌ `MAKEINFO=true`：规则先把已发布 `shishi.info*` 挪进备份目录，`true` 不生成新文件却退出 0，
  备份随后 `rm -rf` ⇒ info 文档被删、install 丢文档。
- ❌ 删 `stamp-vti` 强制重算：会重新触发 mdate-sh 环境泄漏路径。
- ❌ 手改 `version.texi`/`stamp-vti` 内容进补丁（内容里可能已含运行环境与凭证）。

## 验证
```bash
command -v makeinfo || echo "makeinfo absent (expected on device & CI)"
grep -n "stamp-vti: " <builddir>/doc/Makefile          # 看到 prereq 含 $(top_srcdir)/configure
ls -l <srcdir>/doc/stamp-vti <srcdir>/doc/version.texi <srcdir>/doc/shishi.info
make check && make install DESTDIR=<scratch>            # 对齐后两者均 rc=0
# 补丁卫生：补丁里出现 +KEY=value 成片新增即环境泄漏，立即停下还原
```

## 关联条目
- 同族: E011 / E600（HMDFS mktemp → config.status）、E007（config.guess）
- 同包: E670（gengetopt 生成物只在 release tarball）
