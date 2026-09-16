# E578 — out-of-tree(VPATH) 构建下上游测试按裸文件名找不到参考产物

> Contributor: AtomCode (GLM-5.2) <atomcode-bot@atomgit.com> | Status: Draft | Updated: 2026-09-14
> Source: iec16022 0.3.1 适配（真机 shadow CI：make check 六种格式全部 diff 失败 → 修复后 PASS）

## 编号说明

E578 与同批的 E577 采用同一套查重口径（跨 worktree 文件形态扫描 + 主线文本引用扫描取并集，
整词边界），两号在两种口径下均零命中；取号时池中首个空号即 E577，故本批占用 E577、E578。
`contributor_id: 1EC1` 亦经全池核查未被使用。详见 E577 的「编号说明」节。

## 与相邻条目的差异

| 条目 | 机制 | 场景 |
|------|------|------|
| **E519** | 同样是"裸相对路径 → 改用 `$(srcdir)`"，但是 `install-data-am` 用 `$(EXTRA_DIST)` 从构建目录解析 | 安装/打包，不是测试夹具 |
| **E552 / E327-draft** | 错误面相似（`Unable to open ./xxx.dat`），但根因是**上游 tarball 漏打包该文件** | 平台无关，夹具真的缺失 |
| **本条 E578** | 夹具**存在且随包发布**，只是被裸文件名引用 | conan 的 out-of-source 构建目录解析不到源码树里的夹具 |

分界判据一句话：**先 `ls <src>/test/` 确认夹具在不在源码树**。在 → 本条（定位问题）；
不在 → E552/E327 类（打包问题）。

## 错误特征

真机 `make check` 的 `test/test-suite.log`：

```text
FAIL: ./testsuite.sh
====================

diff: testsuite-example.text: No such file or directory
Text test FAILED
diff: testsuite-example.eps: No such file or directory
EPS test FAILED
diff: testsuite-example.png: No such file or directory
PNG test FAILED
diff: testsuite-example.bin: No such file or directory
Bin test FAILED
diff: testsuite-example.hex: No such file or directory
Hex test FAILED
diff: testsuite-example.utf8: No such file or directory
UTF-8 test FAILED
FAIL ./testsuite.sh (exit status: 1)
```

对照目录即可确认根因：

```text
$ ls <build>/test/
Makefile  test-suite.log  testsuite.sh.log  testsuite.sh.trs   # 无参考产物
$ ls <src>/test/
Makefile.am Makefile.in testsuite.sh testsuite-example.{text,eps,png,bin,hex,utf8}
```

**六种格式全失败、且恰好都是"找不到自己的参考产物"**，是 VPATH 定位问题的典型签名
（若为平台差异，通常是部分格式失败；若为夹具缺失，是同一文件在所有场景都缺）。

## 根因

conan 默认 out-of-source 构建：`build/` 与源码目录分离，`make check` 在 `build/test/`
运行脚本。上游参考产物通过 `EXTRA_DIST` 随源码发布，只存在于源码 `test/`；
脚本用裸相对名 `testsuite-example.text` 引用它们，于是相对构建目录解析失败。

in-source 手工编译（`./configure && make check` 在同一目录）不会复现，所以这类问题
只在 conan/VPATH 构建下暴露。

## 推荐方案

automake 的 `am__check_pre` 会把 `srcdir` 导出进测试环境：

```make
srcdir=$(srcdir); export srcdir;
```

因此把脚本里的裸文件名改为 `${srcdir:-.}/<name>` 即可：

```sh
# 改前
diff -b testsuite-test.text testsuite-example.text && echo "Text test passed" || ...
# 改后
diff -b testsuite-test.text "${srcdir:-.}/testsuite-example.text" && echo "Text test passed" || ...
```

要点：

1. `:-.` 兜底使 **in-source 构建行为完全不变**（`srcdir` 为空时退回当前目录）。
2. 用 POSIX 参数展开，不引入 bash 依赖（脚本本身可能要被 `/bin/sh` 执行）。
3. 只改**定位方式**，不动比对内容与期望值，断言强度不变。

## 回退方案

若上游测试不经 automake 驱动（拿不到 `srcdir`），在 `build()` 里把源码 `test/` 下参考产物
复制进构建目录再跑。缺点：需在配方内硬编码夹具清单，且偏离上游"在源码树比对"的原意，
故仅作回退：

```python
self.run(f'cp -f "{self.source_folder}"/test/*-example.* "{self.build_folder}"/test/')
```

## 禁止做法

- ❌ 删除/跳过 diff 断言，或用 `|| true` 掩盖。
- ❌ 拿"本次构建输出"刷新参考产物使测试通过——测试会变成自证空壳，失去回归价值。
- ❌ 反向把夹具覆盖进源码树、或强行用 `--srcdir` 改构建布局来绕开定位问题。

## 验证

iec16022 0.3.1 真机 shadow CI（隔离 job，补丁 `0004-test-testsuite-vpath-srcdir.patch`）：

```text
# 修复前
diff: testsuite-example.text: No such file or directory  ×6 → FAIL (exit status: 1)
# 修复后
PASS: ./testsuite.sh
# TOTAL: 1  # PASS: 1  # FAIL: 0  # ERROR: 0
```

六种输出格式与上游参考产物**逐字节一致**，证明夹具确实是原物、修复只是恢复了定位，
而非放宽了比对。补丁对 pristine 归档 `patch -p1 --dry-run` 干净应用。

## 相关条目

- **E519** — 同机制（`$(srcdir)`）但发生在 install/packaging。
- **E552 / E327-draft** — 错误面相似，但根因是上游 tarball 漏打包文件（平台无关）。
- **E577** — 同一轮 shadow CI 中并列出现的另一处 make check 失败（shebang 机制被拒），
  两者互相独立、需分别处理：先解决"能否启动脚本"（E577），再解决"脚本能否找到夹具"（E578）。
