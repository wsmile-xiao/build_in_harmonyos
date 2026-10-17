# E544（草稿，建议 merge-into E011）— 本地绿 / CI 红：全局 mktemp 垫片掩盖 HMDFS 临时目录权限问题

## 错误特征

CI 完整错误链：

```
./config.status: line 620: ./confLKEcNb/subs1.awk: Permission denied
config.status: error: could not create ./confLKEcNb/subs1.awk
config.status: error: could not setup config files machinery
...
ERROR: syrep/0.9: Error in build() method, line 70
	autotools.configure()
```

而**同一份源码、同一个 commit 在本地 W3（CI 同款 profile）全绿** ——
"本地绿 / CI 红"是本模式的判别特征。

## 触发条件

- 构建系统: autotools（configure 以 `mktemp -d ./confXXXXXX` 生成 config.status 的临时脚本）
- 阶段: configuration（configure 尾部 / config.status 运行期）
- 文件系统: HMDFS 工作区（`mktemp -d` 恒 0700，umask 对目录无效）
- 保真度前提: 运行环境 PATH 中存在全局 mktemp 垫片（本地有、CI 无）

## 根因分析

1. **根因同 E011**：HMDFS 上 `mktemp -d` 创建的目录恒为 `drwx--S---`（0700 + setgid），
   configure/config.status 内联的 `umask 077` 对其无效，写 `subs1.awk` / `subs1.sed` 被拒。
2. **本条补充的保真度陷阱**：若此前某个任务把 mktemp 垫片（`umask 002` + `chmod 2770`）
   装进了共享/用户前缀（如 `~/usr/local/bin/mktemp`、`$TMPDIR/shimbin/mktemp`），
   本地 configure 会静默命中垫片而成功；CI worker 的 PATH 中没有垫片 → 直接红。
   实测：syrep 0.9（PR #12742）CI 构建 #61679 在 6.38s 失败于上述权限错误，
   同 sha 的本地 W3 全绿——唯一差异来自 PATH。
3. **同轮踩到、但属独立模式的两个坑**（避免误判为同一问题）：
   - 系统 autoconf 与 conan perl 混搭 → `Perl_my_cxt_init: symbol not found`
     （重生成路线在 CI 上不可行，见 E041/E071 口径）；
   - 用 `os.utime` 阻止 make 重跑 autotools 时，时间戳若取未来值（`time.time() + 10`），
     autoconf 时钟自检报 `configure: error: newly created file is older than distributed files!`
     → 必须取当前时刻（`time.time()`）：不早于依赖文件、也不超前于当前时间。

## 解决方案

### 推荐方案：配方内化垫片 + 私有 PATH（不依赖宿主机环境）

```python
# conanfile.py build()
shim_bin = os.path.join(self.build_folder, "_shimbin")
os.makedirs(shim_bin, exist_ok=True)
# 写入 mktemp 垫片：umask 002; 调用真实 mktemp; 对 -d 结果 chmod 2770
env = {"PATH": f"{shim_bin}:{os.environ['PATH']}"}
# configure / make / make install 全部在该 PATH 下执行
```

参考实现：`archives/s/syrep/0.9/conanfile.py`（本地 W3 与 CI 行为一致）。

### 回退方案

E011 推荐方案：在 configure/config.status 侧把 `umask 077` 改为 `umask 022`
（固化为 `patches/*.patch` 随配方携带，R3），不改运行环境 PATH；适合单包一次性适配。

### 禁止做法

- ❌ 把垫片装进共享/系统前缀（`/usr/local/bin`、`~/usr/local/bin` 供多任务共享）——
  本地绿会变成环境假象，CI 恒红（R49/E524 同类污染教训）。
- ❌ 因"本地 W3 绿"就判定配方无问题——本地与 CI 的 PATH 不同时，必须按 CI 的 PATH 复现。

## 验证

```bash
# 1) 暴露环境中的垫片
which -a mktemp; ls -l ~/usr/local/bin/mktemp /usr/local/bin/mktemp 2>/dev/null

# 2) 直连 HMDFS 观察临时目录权限
umask 077; d=$(mktemp -d ./confXXXXXX) && ls -ld "$d"      # 期望 drwx--S--- / 0700

# 3) 配方化复现（CI 同款 profile）
conan create archives/s/syrep/0.9 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

## 关联条目

- **相似（同根因，建议合并）**: **E011** — HMDFS 文件系统 umask 077 权限问题；
  本条即其"本地垫片掩盖 + 配方内化实现"变体，合并时请保留本条的 forbid_1（共享前缀垫片）
  与 verification_cmd（`which -a mktemp` 暴露环境）。
- 相关: E041 / E071（CI 不应依赖 autotools 重生成）、E524（共享前缀注入污染）。
- 出处: PR #12742 / `archives/s/syrep/0.9`（W3 绿 → CI #61716 重跑验证中）。
