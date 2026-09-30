# DRAFT: conan 缓存深路径构建失败的配方级决策树（wrapper 失效 → 浅层 scratch 副本）

> 草稿条目 `DRAFT-edlin-2.24-conan-cache-depth-vs-scratch-build`（.kv 配对见同目录同名 .kv）
> 与 libuio 条目（讲 HMDFS uid 映射根因与 BASH_ENV 修复）**互补**：本条讲当
> wrapper/BASH_ENV 方案失效或不适时，配方层的**升级路径决策树**。

## 症状分层（同一报错 `conf*/subs1.awk: Permission denied`，三种根因）

```text
configure 全过 → config.status: line NNN: ./confXXXXXX/subs1.awk: Permission denied
                → error: could not setup config files machinery
```

| 层 | 根因 | 判别 | 解 |
|---|---|---|---|
| 1 | mktemp -d 建的 `drwx--S---` 目录不可写 | 目录名 6 位随机字符（mktemp 命名） | acct 式 exit-1 失败型 mktemp wrapper（AS_TMPDIR 走 mkdir fallback） |
| 2 | **wrapper 被架空**：PATH 中 `~/usr/local/bin` 的真 GNU mktemp 排在 wrapper 前 | 目录名仍是 mktemp 命名；`which mktemp` 在 conanbuild 环境里不是 wrapper | run configure 时命令内联 `PATH=<wrapper_dir>:$PATH`（Environment prepend 不保证最终顺序） |
| 3 | **深缓存路径连 mkdir fallback 目录都写不进**（conf$$-$RANDOM 命名仍 EACCES） | 目录名带 `$$-数字`（fallback 命名）且换 hnp bash 无效 | 复制源码到 `~/tmp/<pkg>-build-<ver>` 浅层 scratch 构建（dominion/2.8.2、edlin/2.24 双例） |

## 关键教训

1. **目录名即根因指纹**：`confXXXXXX`（6 随机字符）= mktemp 所建；`conf<pid>-<rand>`
   = fallback mkdir 所建。轮次间日志目录名变化说明你修的层生效了、但还没修到根。
2. **Environment().prepend_path/save_script 不保证最终 PATH 顺序**（profile 的
   `PATH=+(path)` 注入和其他 env 脚本的叠加次序不定）——需要 wrapper 绝对优先时，
   在 `self.run()` 的命令串里显式 `PATH=...:$PATH` 前缀最可靠。
3. **升级而非试错**：修了层 2 仍失败就直接上浅层副本，不要在深缓存路径继续换
   shell（/system/bin/sh、hnp bash 都试过一样死——SELinux/hmmac 对该挂载点深路径
   新目录的写限制与 shell 域无关）。
4. scratch 副本配方模板（in-source 构建的小包）：

```python
work = os.path.join(os.path.expanduser("~"), "tmp", f"{name}-build-{version}")
if os.path.exists(work): shutil.rmtree(work)
shutil.copytree(self.source_folder, work, ignore=shutil.ignore_patterns(".git"))
# configure/make/make install 全部 cwd=work；--prefix=self.package_folder
# 好处：源码树小（<1MB）时拷贝开销可忽略；packege() 也从 work 安装
```

## 验证

- edlin 2.24：层 1→2 修复后目录名变为 `conf51120-31381`（fallback 生效）但依旧
  EACCES → 层 3 浅层副本一次通过（configure/make/install/test 全绿）；
- dominion 2.8.2 同法（先例）。

## 适用边界

- 巨型源码树拷贝代价高时改用 out-of-tree 构建目录指向 `~/tmp`（保留源码在缓存）；
- `~/tmp` 同样是 HMDFS，但属主名匹配挂载点，写行为正常（与 libuio 条目观察一致）；
- 先确认不是 E011/E112 的 umask/mktemp 基础问题（层 1），否则浅层副本掩盖问题。
