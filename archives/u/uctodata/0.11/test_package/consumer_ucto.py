#!/usr/bin/env python3
"""uctodata 消费者用例：按 ucto 的**真实启动路径**消费安装后的数据。

用法: python3 consumer_ucto.py <package_folder>

端到端链路（不是文件存在性断言）：

  1. **pkg-config 契约**：以 `<package_folder>/lib/pkgconfig` 为 `PKG_CONFIG_PATH`
     执行 `pkg-config --variable=prefix uctodata` —— 这正是 ucto/configure.ac 定位
     这份数据的方式；执行环境没有 `pkg-config` 工具时退化为直接解析
     `lib/pkgconfig/uctodata.pc` 的 `prefix=`（同一契约，不经工具）。
  2. **读分词配置**：`<prefix>/share/ucto/tokconfig-nld`（ucto 的 `version=0.2`
     配置：`[SECTION]` 分节 + `key=value`/正则条目 + `%include` 指令）。
  3. **按 `%include` 约定加载数据文件**（ucto 启动时就是这么把数据读进来的）：
     `ABBREVIATIONS`→`*.abr`、`RULES`→`*.rule`、`QUOTES`→`*.quote`、
     `EOSMARKERS`→`*.eos`、`FILTER`→`*.filter`；逐文件解析出条目数。
  4. 打印解析摘要并给出退出码：配置读不出、任一 `%include` 找不到对应数据文件、
     或数据文件解析为空 → 非 0（CI 据此判定）。
"""

import os
import re
import subprocess
import sys

TOKCONFIG = "tokconfig-nld"
SECTION_EXT = {
    "ABBREVIATIONS": (".abr",),
    "RULES": (".rule",),
    "QUOTES": (".quote",),
    "EOSMARKERS": (".eos",),
    "FILTER": (".filter",),
}
ALL_EXT = (".abr", ".rule", ".quote", ".eos", ".filter", ".tok")


def resolve_prefix(package_folder):
    """按消费者的方式拿到 prefix：pkg-config 工具优先，其次直接读 .pc。"""
    pc_dir = os.path.join(package_folder, "lib", "pkgconfig")
    env = dict(os.environ, PKG_CONFIG_PATH=pc_dir)
    try:
        out = subprocess.run(["pkg-config", "--variable=prefix", "uctodata"],
                             capture_output=True, text=True, env=env, timeout=60)
        if out.returncode == 0 and out.stdout.strip():
            print(f"        [consumer] pkg-config --variable=prefix uctodata -> {out.stdout.strip()}")
            return out.stdout.strip()
    except (FileNotFoundError, subprocess.SubprocessError):
        pass
    pc = os.path.join(pc_dir, "uctodata.pc")
    if not os.path.isfile(pc):
        raise SystemExit(f"consumer: 既无 pkg-config 工具、也没有 {pc}")
    for line in open(pc, encoding="utf-8", errors="replace"):
        if line.startswith("prefix="):
            prefix = line.split("=", 1)[1].strip()
            print(f"        [consumer] 无 pkg-config 工具，直接读 uctodata.pc -> prefix={prefix}")
            return prefix
    raise SystemExit("consumer: uctodata.pc 里没有 prefix=")


def count_entries(path):
    n = 0
    for line in open(path, encoding="utf-8", errors="replace"):
        s = line.strip()
        if s and not s.startswith("#"):
            n += 1
    return n


def resolve_include(datadir, section, name):
    for ext in SECTION_EXT.get(section, ALL_EXT):
        cand = os.path.join(datadir, name + ext)
        if os.path.isfile(cand):
            return cand
    return None


def consume(datadir):
    cfg = os.path.join(datadir, TOKCONFIG)
    if not os.path.isfile(cfg):
        raise SystemExit(f"consumer: 分词配置缺失: {TOKCONFIG}")
    section, sections, includes, meta_version = None, [], [], None
    for line in open(cfg, encoding="utf-8", errors="replace"):
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if s.startswith("[") and s.endswith("]"):
            section = s[1:-1]
            sections.append(section)
            continue
        if s.startswith("version="):
            meta_version = s.split("=", 1)[1].strip()
            continue
        m = re.match(r"^%include\s+(\S+)\s*$", s)
        if m:
            includes.append((section, m.group(1)))
    if not sections:
        raise SystemExit("consumer: 配置里没有任何 [SECTION]")
    if not includes:
        raise SystemExit("consumer: 配置里没有任何 %include（数据没有真正被消费）")

    loaded, total = [], 0
    for sec, name in includes:
        path = resolve_include(datadir, sec, name)
        if path is None:
            raise SystemExit(f"consumer: [{sec}] %include {name} 在数据目录里找不到对应文件")
        n = count_entries(path)
        if n == 0:
            raise SystemExit(f"consumer: 数据文件 {os.path.basename(path)} 解析出 0 条目（空文件/全注释）")
        loaded.append((sec, os.path.basename(path), n))
        total += n

    print(f"        [consumer] {TOKCONFIG}: version={meta_version} "
          f"分节 {len(sections)} 个，%include {len(includes)} 条 -> 全部解析成功")
    for sec, fname, n in loaded:
        print(f"        [consumer]   [{sec}] {fname}: {n} 条目")
    print(f"        [consumer] 消费合计: {len(loaded)} 个数据文件 / {total} 条目")
    return 0


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    package_folder = sys.argv[1]
    prefix = resolve_prefix(package_folder)
    datadir = os.path.join(prefix, "share", "ucto")
    if not os.path.isdir(datadir):
        raise SystemExit(f"consumer: pkg-config 契约指向的 {datadir} 不存在")
    print(f"        [consumer] 数据目录（pkg-config 契约解析）: {datadir}")
    return consume(datadir)


if __name__ == "__main__":
    sys.exit(main())
