# E999 — 手搓递归 Makefile install 并行竞态（prover9 实证）

## 错误特征
```
make[1]: Entering directory '.../apps.src'
mkdir ../bin
mkdir: cannot create directory '../bin': File exists
make[1]: *** [Makefile:47: install] Error 1
make[1]: *** Waiting for unfinished jobs....
make: *** [Makefile:20: install] Error 2
```
仅 `make -j2`（及以上）触发；`make -j1` 全绿。

## 触发条件
- 构建系统: 手搓递归 Makefile（无 automake/libtool 生成的顺序保障）
- 阶段: make install（多个子目录的 install 目标向同一个共享 ../bin/ 复制）
- 实证软件: prover9 2017-11A（顶层 Makefile 递归 ladr/ → mace4.src/ → provers.src/ → apps.src/）

## 根因分析
1990s 风格的手搓递归 Makefile 没有依赖排序：顶层 `install:` 目标用 `$(MAKE) -C` 平行进入各子目录，
provers.src 与 apps.src 的 install 都执行 `mkdir ../bin && cp … ../bin/`。并行时两个子 make 同时
mkdir/cp 同一路径，先到的成功、后到的因 mkdir 非幂等（无 -p）而失败。automake 生成的 install
通常带 `mkinstalldirs`/`mkdir -p` 与串行依赖，所以 autotools 软件很少见到该竞态。

## 解决方案

### 推荐方案
构建+安装一律 `-j1` 串行，并固化进 Conan 配方 build()：
```python
# conanfile.py build()
self.run(f"make all -j1 CC={cc} XFLAGS='-fPIC -O2'")
```
prover9 全量构建 ~11s，并行无收益；package() 不用上游 install 目标，直接把 `bin/` 下 43 个产物
复制到 `${package_folder}/bin/`（策略 B 手动布局），绕开 install 目标本身。

### 禁止做法
- ❌ 为"提速"保留 -j2 再打补丁顺序化——43 个小工具串行 11s，补丁成本远超收益
- ❌ 依赖 `mkdir -p` 化的上游补丁——上游已死（McCune 2023 去世），补丁无法回馈

## 验证
```bash
cd ~/tmp/builds/prover9-2017-11A.work/Prover9-*/
make -j2 install 2>&1 | grep -c "Error 1"   # >0 复现
make -j1 install 2>&1 | tail -1             # install of binaries finished
```

## 关联条目
- 相关: E074（HMDFS jobserver fifo 亦要求 -j1，同属并行约束族）
