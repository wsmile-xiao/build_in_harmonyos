# DRAFT（路径 B 知识条目）: 上游 install 钩子把 `$(DESTDIR)$(bindir)` 烙进符号链接别名 ⇒ conan 交付包不可重定位，package() 内改写为相对链接

## 基本信息
- **严重度**: 2
- **类别**: packaging, symlink, relocatability, autotools
- **阶段**: package（编译、链接、上游测试都已通过）
- **作者**: QC-10
- **来源 PR**: (本 PR) ／ **来源 commit**: (待提交后回填)
- **关联 Issue**: 见 PR 正文与本条目 `.kv` 的 `related_issue`

## 错误特征
交付包目录里（**未修时**，probabel 0.5.0 实测）：

```
$ ls -l <package_folder>/bin/
-rwxrwx--- probabel
lrwxrwxrwx probabel.pl -> /storage/Users/currentUser/tmp/ch/home-qc10-probabel/p/b/proba71b739ce08285/p/bin/probabel
```

关键指纹：**别名链接的目标是一个含构建期 `package_folder` 的绝对路径**，而不是同目录相对名。
`conan create`、`G4 产物完整性`、原地 `test_package` **全部通过**——因为原地那个绝对路径还存在。
只有把包目录复制到别的 `CONAN_HOME`（或换机后从远端拉包）时，别名才成为悬空链接。

## 根因分析
上游安装规则（`src/Makefile.am:436`）：

```make
install-exec-hook:
        ln -s $(DESTDIR)$(bindir)/probabel $(DESTDIR)$(bindir)/probabel.pl
```

`$(DESTDIR)` 在 conan 的 `package()` 里为空（配方用 `make install`、`prefix=<package_folder>`，
不用 DESTDIR 暂存），于是 `$(bindir)` 被展开成**构建机上** package 目录下的绝对路径，
并被**固化进符号链接目标**。autotools 的 `$(DESTDIR)$(bindir)` 写法本是为暂存打包设计的，
在没有 DESTDIR 暂存、又要求产物可重定位的 conan 模型下正好留下这个洞。

**判据（一句话）**：交付包里任何符号链接的目标若以 `/` 开头且含构建路径，即不可重定位。

## 推荐方案
**方法**: `rewrite-alias-symlink-relative`（优先级 1，配方侧后处理，不改上游、不改安装规则）

```python
def package(self):
    self.run("make install", cwd=self.source_folder, env="conanbuild")
    bindir = os.path.join(self.package_folder, "bin")
    alias = os.path.join(bindir, "probabel.pl")
    if os.path.islink(alias):
        os.unlink(alias)
    try:
        os.symlink("probabel", alias)          # 相对目标：随目录整体搬迁仍有效
    except OSError:
        shutil.copyfile(os.path.join(bindir, "probabel"), alias)   # HMDFS 拒绝建链时退化
    os.chmod(alias, 0o755)
```

**验证/命令**（设备实测）：
```
# 1) 目标应为相对名
ls -l <package_folder>/bin/probabel.pl            # → probabel.pl -> probabel

# 2) 重定位模拟（忠实复现换 CONAN_HOME / 换机）
X=~/tmp/relo; mkdir -p $X/A/bin $X/B/bin
cp probabel $X/A/bin/; cp probabel $X/B/bin/
ln -s $X/A/bin/probabel $X/B/bin/probabel.pl      # 复现"烙进绝对路径"
rm -rf $X/A
[ -e $X/B/bin/probabel.pl ] && echo 可解析 || echo "绝对链接：悬空"   # → 悬空
( cd $X/B/bin && ln -s probabel probabel.rel ); [ -e $X/B/bin/probabel.rel ] && echo "相对链接：可解析"
```
本包两条探针脚本：`~/tmp/uc2/qc10-r2/pbsym.sh`（上游裸 `make install DESTDIR=` 复现规则本身）、
`~/tmp/uc2/qc10-r2/pbsym2.sh`（重定位 A/B 对照）。

**并且**：`test_package` 里必须有"别名可解析且可执行"的断言，否则该缺陷会随版本升级回归
（probabel 的消费者测试第 9 号断言即为此设）。

## 适用边界 / 反例 / 解除条件
- **适用**：上游在 install 阶段自建符号链接别名的包（`install-data-local` / `install-exec-hook` /
  裸 Makefile 里的 `ln -s $(DESTDIR)…`）；常见于 `*.pl`、`*.py` 兼容别名、无扩展名包装器、man 别名。
- **反例 1（不是本条）**：链接目标属**另一个 conan 依赖包**（跨包资源叠加）⇒ 走 E362/E382，
  必须按 `self.dependencies` 解析真实节点并实体化，盲目复制同名文件会打包过期内容。
- **反例 2（判定陷阱）**：如果要删除别名，清理逻辑别用 `Path.is_file()`——它跟随目标，
  目标已删时返回 False 而漏掉残留链接（E395），须用 `lexists`/`is_link` 语义。
- **注意**：改相对目标前要确认链接与目标**同目录**，跨目录要按真实相对路径计算；
  HMDFS 拒绝建软链时退化为复制，但要在 notes 写明"别名已由链接改为副本"
  （丢掉上游"一处更新两处生效"的语义）。
- **解除条件**：上游改为 `ln -s $(bindir-relative)` 或安装脚本自带相对链接时，配方侧修正可移除。

## 关键词
install-exec-hook, install-data-local, ln -s $(DESTDIR), 符号链接别名, 绝对路径固化, 不可重定位包, dangling symlink,
package_folder, 相对链接改写, HMDFS 软链退化复制, 可重定位性校验

---
*实测来源：probabel 0.5.0（任务 9728）。修后 `conan-verify` G1/G2/G3/G4 通过，
`build()` 内 `make -j1 check` 上游 11 项 **TOTAL 11 / PASS 11 / SKIP 0 / FAIL 0**，
消费者测试 9 组断言全通过（含本条目对应的别名断言）。*
