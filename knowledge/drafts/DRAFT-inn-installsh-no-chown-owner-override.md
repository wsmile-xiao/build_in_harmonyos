# DRAFT-inn-installsh-no-chown-owner-override — 无 chown/chgrp 时 install-sh 中止

## 可复现症状与稳定错误签名

```
support/install-sh[546]: chown: inaccessible or not found      （连续 30+ 行）
make: *** [Makefile:99: directories] Error 1
```
签名正则：`install-sh\[\d+\]: chown: inaccessible or not found`

## 根因与最小复现

- 环境能力缺失：`ls -l /bin/chown` → `Permission denied`；`chown --version` →
  `inaccessible or not found`。**chgrp 同样缺失**。此外本机也没有 `news` 账号。
- INN `Makefile.global`：`OWNER = -o $(RUNASUSER) -g $(RUNASGROUP)`（默认 `-o news -g news`）；
  顶层 `directories:` 目标对 `$(INSTDIRS)` 每个目录执行
  `support/install-sh $(OWNER) -m 0755 -d $(DESTDIR)$D`。
- install-sh 头部：`chownprog=${CHOWNPROG-chown}`、`chgrpprog=${CHGRPPROG-chgrp}`；
  处理 `-o`/`-g` 后执行 `$doit $chowncmd "$dst"` → 命令不存在 → `exit 1`。

最小复现：
```bash
command -v chown && chown --version      # 失败
make install DESTDIR=$PWD/dest           # exit 2，满屏 chown: inaccessible
```

## 已尝试方案（含失败方案及结果）

| 方案 | 结果 |
|---|---|
| `make install DESTDIR=... OWNER=` | 仍失败：libtool 把 `-o news -g news` 写死在 install 调用里，绕过 OWNER |
| `OWNER= CHOWNPROG=true CHGRPPROG=true` | 通过（`true` 需要可执行位，在本环境可用但不如 `:` 稳） |
| `OWNER= CHOWNPROG=: CHGRPPROG=:` | **通过，采用**（`:` 是 shell 内建，无需可执行位） |
| root 运行 | 不可行：沙箱无 root |

## 最终方案、输入输出与真实验证

`conanfile.py` 的 `package()`：

```python
os.environ["CHOWNPROG"] = ":"
os.environ["CHGRPPROG"] = ":"
Autotools(self).install(args=["OWNER="])
```

- 输入：install-sh 以 `-o news -g news` 被调用、且 PATH 中无 chown/chgrp。
- 输出：`make install DESTDIR=... OWNER= CHOWNPROG=: CHGRPPROG=:` **exit 0**，
  安装树完整（80 个 bin、3 个 .a、44 个 include 头、etc/db/spool 骨架）。
- 真实验证：inn2/2.7.4 的 `conan-verify` G2 通过、`conan create` exit 0，
  `.staging-verified` 判 verified=1；`make install` 目标 exit 0。
- 先例：`archives/l/libecap/1.0.1` 用同一组覆盖（其注释写明
  "cfgaux/install-sh honors CHGRPPROG/CHOWNPROG/STRIPPROG env; `:` is an ash builtin no-op"）。

## 注意事项

1. **两个开关要一起给**：只给 `OWNER=` 不够——libtool 的 `install` 调用会把
   `-o news -g news` 直接作为参数传给 install-sh，绕开 Makefile 变量。
2. 用 `:` 而非 `true`：`:` 是 shell 内建，不依赖可执行位，在 chmod 受限的
   HMDFS 上更稳（与 E490「可执行位缺失」是同一类环境约束）。
3. 该方案不改上游源码，属**环境覆盖**；若后续环境补齐 chown 与 news 账号，
   这些覆盖可移除。
4. 同族现象见 `DRAFT-E574-libosip-installsh-single-file-batch-loss`
   （老版 install-sh 的单文件限制），二者同属 install 通道，但根因不同：
   那条是 install-sh 版本能力不足，本条是宿主缺 chown/chgrp。
