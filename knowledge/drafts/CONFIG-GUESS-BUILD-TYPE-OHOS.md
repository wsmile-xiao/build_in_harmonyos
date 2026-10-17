# 老版 config.guess 不识别 OHOS/aarch64 — 处理策略与配方模板

> 知识库条目：`CONFIG-GUESS-BUILD-TYPE-OHOS`
> 样例库：swish-e/2.4.7（`archives/s/swish-e/2.4.7`）
> 检测脚本：`detect_config_guess.py`（同目录）

## 适用场景（一类问题，非单库补丁）

老 autotools 包（ bundled config.guess 早于 2016 年，不含
`aarch64`/`arm64` 分支）在 OHOS PC 上执行 `./configure` 即失败：

```
configure: error: cannot guess build type; you must specify one
```

swish-e 2.4.7（config.guess timestamp=2009-04-27）实测命中；同型包在
积分赛批量任务中反复出现（凡 2016 年前发布且未刷新 config.guess 的
autotools 包均属此家族）。

## 根因

`configure` 运行 `config.guess` 探测构建三元组；老版脚本只认识
历史上登记过的 `*-linux-*`/`*-gnu*` 机器形态，OHOS 交叉环境
（`aarch64-unknown-linux-ohos` / 无法探测的宿主）落入 "无法识别" 分支，
configure 直接退出。`config.sub` 侧同理可能拒绝 `*-linux-ohos`。

## 处理策略（二选一或组合）

### 策略 A：显式 build 三元组（免补丁，首选）

```python
# conanfile.py build()
self.run(
    './configure --disable-shared --disable-nls '
    '--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu '
    'CC="clang"',
    cwd=self.source_folder)
```

* autotools 对**格式合法但未知**的三元组照单全收（仅用于路径推导），
  configure 顺利生成 Makefile（swish-e 实测 19 项 config.status 通过）；
* 若包不感知交叉（`--host` 未用），只给 `--build` 即可；
* 优点：零补丁、向上游无侵入；缺点：canonical triple 显示为
  linux-gnu（纯展示，不影响产物，因为 CC 已是 OHOS clang、sysroot 由
  工具链自带）。

### 策略 B：刷新 config.guess/config.sub（补丁，E007 路线）

从 modern automake 拷入新的 `config.guess`/`config.sub`（或打含
`__OHOS__` libc 探针的补丁，同 babeltrace 先例）。适用于策略 A 被
configure 逻辑拒绝（如包内对 `$build_os` 做 case 分支强校验）时。

### 组合策略

策略 A 过 configure + 策略 B 换 config.sub，当包内 `Makefile` 用
`config.sub` 二次校验三元组时需要。

## 复现脚本（双向验证，样例库 swish-e）

```sh
# ① 不启用 SKILL：原始 configure 直接失败
cd <swish-e-2.4.7-src>
./configure --disable-shared > repro.log 2>&1; echo "rc=$?"
grep "cannot guess build type" repro.log   # 命中 => 问题复现

# ② 启用 SKILL：显式三元组后 configure 通过
./configure --disable-shared --disable-nls \
  --build=aarch64-unknown-linux-gnu CC=<ohos clang> > fix.log 2>&1
echo "rc=$?"   # 0 => 缓解生效
```

> SIGPIPE 注意：复现脚本日志一律 `> file 2>&1` 重定向，不得
> `... | head`（管道读者退出会 SIGPIPE 掩盖真实退出码）。

## 检测逻辑（自动，无需人工）

* **源码信号**：bundled `config.guess` 的 `timestamp=` 早于 2016 或
  全文无 `aarch64`/`arm64` 分支（脚本递归扫描）；
* **日志信号**：configure 日志命中
  `cannot guess build type|unable to guess system type`。

## 边界 / 不适用场景

* 包若已在构建期显式传 `--build/--host`，本问题不会出现（无需处理）；
* `config.sub` 拒绝 triplet 是另一症状（`Invalid configuration`），
  属 E007 覆盖面，本条目只管 "cannot guess build type"；
* 策略 A 改变的 canonical triple 对 `libtool` 版本后缀无影响
  （swish-e 实测产物为标准 musl ELF）。

## 样例验证结果（swish-e/2.4.7，OHOS aarch64）

| 阶段 | 命令 | 结果 |
|---|---|---|
| 不启用 | `./configure --disable-shared` | rc=1，`cannot guess build type` |
| 启用 | `./configure … --build=aarch64-unknown-linux-gnu` | rc=0，19 项 config.status |
| 编译 | `make -j8`（patch 0001 后） | rc=0，`swish-e` 620992B ELF arm64 |
| 运行 | `./swish-e -V` | `SWISH-E 2.4.7`，rc=0 |
