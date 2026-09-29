# E429 — HMDFS 上执行的 ELF 降级到 SELinux adhoc_bin 域后无法 execve/加载 HMDFS 文件

## 错误特征
```
./configure: Permission denied            # autotools，exit 126
make: rm: Execution permission denied
Error loading shared library libX11.so.6: needed by .../bin/wmnd (test_package)
```
迷惑点：同一文件在 shell 侧执行**成功**，仅 conan 子进程失败；`stat` 显示 `0o770/0o755`、
`os.access(p, X_OK)=True`、文件可读。

## 触发条件
- 构建系统: 任意（autotools/cmake/meson 均可）
- 阶段: build / test_package（凡由 conan 派生子进程）
- 进程来源: **从 HMDFS（/storage/Users/...）执行的 ELF**，典型为
  `pip install --user` 装到 `~/usr/local/bin/` 的 `conan` 与 `python3`（ad-hoc ELF）

## 根因分析
HarmonyOS PC SELinux 策略按**可执行文件所在文件系统**做域转换：

| 启动的二进制 | 进程域 | execve HMDFS 文件 | 加载 HMDFS .so |
|---|---|---|---|
| 受信任 bundle python（/data/storage/el1/bundle/libs/arm64/python/bin/python3） | u:r:develop_tools_hap:s0 | ✅ | ✅ |
| ~/usr/local/bin/python3 / conan（HMDFS 上的 ELF） | u:r:adhoc_bin:s0 | ❌ EACCES | ❌ EACCES |

`adhoc_bin` 域被禁止 execve HMDFS 上的**任何**文件——包括本进程刚创建并 chmod 755
的脚本——也无法从 HMDFS 加载共享库。三个干扰因素叠加导致极易误判：
1. HMDFS 忽略 `chmod()`（E046），`os.chmod(0o755)` 后 stat 值看似变化但策略不变；
2. HMDFS 属主映射到其他 UID，本进程 uid 不同；
3. shell 侧（develop_tools_hap 域）执行同一文件成功，让人怀疑"时序/缓存"。

实测排除项：`sh -c` 包装、source conanbuild.sh、以 0o755 新建脚本、
`CONAN_HOME` 迁到 /data/storage/el2/base/cache（appdat）——**全部无效**。

## 解决方案

### 推荐方案（trusted-python-shim）
用受信任 bundle python 统一入口，进程保持 develop_tools_hap 域：
```sh
mkdir -p ~/.shimfix
cat > ~/.shimfix/conan <<'EOF'
#!/bin/sh
exec /data/storage/el1/bundle/libs/arm64/python/bin/python3 -c 'import sys; from conans.conan import run; sys.exit(run())' "$@"
EOF
chmod 755 ~/.shimfix/conan
export PATH="$HOME/.shimfix:$PATH"
export CONAN_HOME=/data/storage/el2/base/cache/conan-home   # .so 加载需非 HMDFS 缓存
```
`ohc-run.py` 等 python 脚本同理：`~/.shimfix/python3` → bundle python。

### 禁止做法
- ❌ 用 `os.chmod(x, 0o755)`/重建文件"修复" configure Permission denied（根因是 SELinux 域；HMDFS 忽略 chmod）
- ❌ 只迁移 `CONAN_HOME` 到 appdat 而不修复进程域
- ❌ 把 `~/usr/local/bin` 前置进 PATH 却不建 python3 shim

## 验证
```bash
export PATH="$HOME/.shimfix:$PATH"; export CONAN_HOME=/data/storage/el2/base/cache/conan-home
conan create archives/w/wmnd/0.4.18 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable
# wmnd/0.4.18 实测：configure/make/package 全部 rc=0，test_package 17 passed / 0 failed
```

## 关联条目
- 相关: E046（HMDFS chmod=0）、E114（HMDFS tmp 权限）、E540（runner PATH 前置）
