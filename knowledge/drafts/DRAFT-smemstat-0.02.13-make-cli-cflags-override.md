# 草稿 smemstat-0.02.13-make-cli-cflags-override — GNU make 命令行 CFLAGS 使 Makefile 的 `CFLAGS +=` 追加失效（上游 -DVERSION 宏丢失）

## 错误特征

```
smemstat.c:1511:13: error: use of undeclared identifier 'VERSION'
```

或（重供了宏但引号被 shell 层剥掉、裸值直达编译器时）：

```
smemstat.c:1511:13: error: invalid suffix '.13' on floating constant
```

典型场景：配方 build() 用 `make CFLAGS="..."` 直驱纯 Makefile 项目，编译期在
使用 `VERSION` 宏的位置（usage banner、`-DVERSION` 依赖的输出）报未声明标识符，
或报浮点常量后缀非法——而不是链接或头文件错误。

## 触发条件

- 构建系统：纯 Makefile（无 configure），配方以**命令行变量**形式传 `CFLAGS=...`
- 上游 Makefile 存在追加式赋值：`CFLAGS += -Wall ... -DVERSION='"$(VERSION)"' ...`
- 平台：任何（OHOS aarch64 实证）
- make 类型语料占本仓库归档 ~21%，凡 Makefile 用 `+=` 注入版本宏/警告标志的包均适用

## 根因分析

GNU make 的变量优先级为 命令行 > makefile > 环境。对**命令行**变量，makefile
内的 `+=` 追加**整体失效**（这与环境变量不同：环境来源的变量被 `+=` 追加时仍然生效）。
因此一旦在命令行传入 `CFLAGS=`，上游 Makefile 中 `CFLAGS += ...` 携带的所有
追加（本例 `-DVERSION`、`-Wall -Wextra`、`-O2 -g`）全部静默丢失，编译仅使用
配方传入的子集。

第二个独立坑在同一处叠加：即使记得重供 `-DVERSION`，引号要穿过**两层 shell**
（调用 make 的 shell → make 展开配方的 shell）才能到达编译器。任何一层处理不当
（如写成裸的 `-DVERSION=0.02.13`），编译器收到的就是裸 token `0.02.13`，
被解析成浮点字面量而报 `invalid suffix`。

注意区分：E063 是 `-Werror` 把警告升级为错误的 CFLAGS 主题；本条是
**命令行变量覆盖语义**导致的宏/标志整体丢失，二者根因不同。

## 解决方案

### 推荐方案：命令行完整重供 CFLAGS，版本宏用上游引号形态

```python
# conanfile.py build()
cflags = f"-O2 -fPIC -DVERSION='\"{self.version}\"' -I{dep_inc}"   # 注意 '\"' 引号形态
ldflags = f"-L{dep_lib}"
self.run(
    f'make -C "{self.source_folder}" -j{jobs} CC="{cc}" '
    f"CFLAGS={shlex.quote(cflags)} LDFLAGS={shlex.quote(ldflags)} smemstat",
)
```

要点：
1. 在配方注释中显式记录"命令行变量使 `+=` 失效，故完整重供"——这是审查关注点；
2. `-DVERSION='"X.Y.Z"'`：单引号被调用层 shell 吃掉、双引号被配方层 shell 吃掉，
   编译器收到 `-DVERSION="X.Y.Z"`（C 字符串字面量），与上游
   `-DVERSION='"$(VERSION)"'` 形态一致；
3. 用 `shlex.quote()` 包整个 CFLAGS 值，防 include/lib 路径中的 shell 元字符；
4. 备选：把 CFLAGS 放进**环境变量**（makefile 的 `+=` 对环境变量仍追加），
   但命令行形态确定性更强、且不依赖环境注入（R33）。

## 验证

- 负例 A（缺宏）：`error: use of undeclared identifier 'VERSION'`（本任务实测复现）
- 负例 B（裸值）：`error: invalid suffix '.13' on floating constant`（本任务实测复现）
- 正例（本方案）：smemstat/0.02.13 conan-verify G1–G4、L2 smoke、L4/L5 全绿，
  消费者 test_package 3/3 PASS（ohos-aarch64 / clang 15）

## 关联

- `archives/s/smemstat/0.02.13/conanfile.py`（工作配方）
- `archives/d/dhcpoptinj/0.5.3/conanfile.py`（direct clang 同款引号形态先例）
- `knowledge/graph/E063.kv`（-Werror 主题，区分条目）
