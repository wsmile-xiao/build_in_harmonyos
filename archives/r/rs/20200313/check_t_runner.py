#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_t_runner.py —— 上游回归语料 check.t 的等价执行器（rs 20200313）。

为什么要有这个文件
------------------
上游 rs 的回归目标是

    regress: ${PROG} check.t
        perl ${MKSHDIR:Q}/check.pl -s ${SRCDIR:Q}/check.t -v -p ./${PROG:Q}

其中 `${MKSHDIR}` = `${BSDSRCDIR}/bin/mksh`，即 **mksh 源码树里的 check.pl**，
该脚本不在 rs 的 upstream tarball 内（Debian 也是从 `/usr/share/doc/mksh/` 里取
现成的 check.pl 来跑这套语料）。⇒ 语料在、执行器不在。本文件按 check.t 的语料
约定实现一个**等效执行器**，使这 13 条上游用例能在 conan create / CI 里真实跑起来。

check.t 语料约定（本执行器的解析与断言口径）
--------------------------------------------
* 用例之间用单独一行 `---` 分隔；顶层 `key:` 出现在第 0 列；
* 同行有值 ⇒ 单行值；同行无值 ⇒ 值随后以制表符缩进的块给出，块值**逐行剥掉
  恰好一个前导 TAB**（所以 `stdin` 里形如 `\t\t0` 的行仍保留一个真实制表符）；
* 单行值里的 `!` 是**分词符**：`arguments: !-e!0!5!` ⇒ argv `["-e","0","5"]`，
  `env-setup: !LC_ALL=C.UTF-8!` ⇒ 一个环境变量赋值；
* 唯一的例外是 `category:`，它借用开头的 `!` 表达**取反**：
  `category: os:mirbsd` = 仅在 MirBSD 成立；`category: !os:mirbsd` = 仅在
  非 MirBSD 成立。⇒ 这里读原文（`*_raw`）而不是读分词结果；
* 断言 = 子进程退出码 0 **且** stdout 与 expected-stdout **逐字节**相等。
  语料里含非法 UTF-8 字节（0xFF），故全程按 bytes 处理，不做任何编码转换。

用法：check_t_runner.py <rs 可执行文件> <check.t> [--allow-skip] [--verbose]
退出码：0 = 无失败；1 = 有失败。
`--allow-skip` 只影响**上游自己用 category 声明"仅 MirBSD 成立"**的那条用例：
它照样会被真实执行并把实测差异打进日志，只是不判负（本平台不是 MirBSD，
该期望在 musl 上本就不成立；其镜像用例 unicode-3-utf8 才是本平台的期望行为）。
"""
import os
import subprocess
import sys

MIRBSD_CATEGORY = "os:mirbsd"
# 本平台既不是 MirOS 也不是 OpenBSD；category 里出现这些串才算"命中本平台"。
LOCAL_CATEGORIES = ()


def split_bang(value):
    """`!-e!0!5!` → ['-e','0','5']；不以 `!` 开头时按空白分词。"""
    if value.startswith("!"):
        return [tok for tok in value.split("!")[1:] if tok != ""]
    return [tok for tok in value.split() if tok]


def parse_corpus(path):
    """把 check.t 解析成用例列表；块值是 bytes 行列表，单行值是字符串列表。"""
    with open(path, "rb") as handle:
        lines = handle.read().split(b"\n")
    cases, cur, block = [], None, None
    for line in lines:
        if line == b"---":
            if cur:
                cases.append(cur)
            cur, block = {}, None
            continue
        if cur is None:
            cur = {}
        if line and not line.startswith(b"\t"):
            key, sep, rest = line.partition(b":")
            key = key.decode("ascii", "replace").strip()
            if not sep or key.startswith("#") or " " in key:
                continue
            text = rest.decode("latin-1").strip()
            block = None
            if text:
                cur[key] = split_bang(text)
                cur[key + "_raw"] = text
            else:
                cur[key] = []
                block = key
            continue
        if block is not None:
            cur.setdefault(block, []).append(
                line[1:] if line.startswith(b"\t") else line)
    if cur:
        cases.append(cur)
    return [case for case in cases if case.get("name")]


def block_bytes(lines):
    """块值 → 字节串：每行补一个换行（与 check.t 的行尾语义一致）。"""
    return b"".join(line + b"\n" for line in lines)


def declared_categories(case):
    """返回 (要求"是本平台"的 category, 要求"不是本平台"的 category)。"""
    raw = case.get("category_raw", "")
    positive, negated = [], []
    for token in raw.split():
        if token.startswith("!"):
            negated.append(token[1:])
        elif token:
            positive.append(token)
    return positive, negated


def main(argv):
    if len(argv) < 3:
        sys.stderr.write("usage: %s <rs-binary> <check.t> [--allow-skip] [--verbose]\n"
                         % os.path.basename(argv[0]))
        return 2
    exe, corpus = argv[1], argv[2]
    allow_skip = "--allow-skip" in argv
    verbose = "--verbose" in argv

    cases = parse_corpus(corpus)
    passed, failed, skipped = [], [], []
    for case in cases:
        name = case["name"][0]
        args = [tok for tok in case.get("arguments", []) if isinstance(tok, str)]
        stdin = block_bytes(case.get("stdin", []))
        want = block_bytes(case.get("expected-stdout", []))
        env = dict(os.environ)
        for pair in case.get("env-setup", []):
            if isinstance(pair, str):
                key, _, value = pair.partition("=")
                env[key] = value
        positive, negated = declared_categories(case)
        tag = ""
        if positive or negated:
            tag = "category=%s" % case.get("category_raw", "")
        # 上游用 category 自声明的"别家平台专属"：本平台不属 MirOS/OpenBSD，
        # 该期望在 musl 上不成立，与适配质量无关（照样执行、如实打日志）。
        foreign = [c for c in positive if c not in LOCAL_CATEGORIES]

        proc = subprocess.run([exe] + args, input=stdin, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, env=env, timeout=120,
                              cwd=os.path.dirname(os.path.abspath(exe)) or ".")
        if proc.returncode == 0 and proc.stdout == want:
            passed.append(name)
            print("PASS    %-22s rc=0 expected-stdout=%db %s" % (name, len(want), tag))
            continue
        if foreign and allow_skip:
            skipped.append(name)
            print("SKIP    %-22s 上游自声明 %s（本平台非该 category；已真实执行并记录差异，"
                  "不判负）rc=%d got=%r want=%r"
                  % (name, " ".join(positive), proc.returncode,
                     proc.stdout[:24], want[:24]))
            continue
        failed.append(name)
        detail = []
        if proc.returncode != 0:
            detail.append("rc=%d stderr=%s"
                          % (proc.returncode,
                             proc.stderr.decode("latin-1").strip()[:90]))
        if proc.stdout != want:
            detail.append("stdout got=%r want=%r" % (proc.stdout[:40], want[:40]))
        print("FAIL    %-22s %s %s" % (name, " | ".join(detail), tag))
        if verbose and proc.stderr.strip():
            print("        stderr: %s" % proc.stderr.decode("latin-1").strip()[:200])

    print("UPSTREAM_CHECK_SUMMARY N_static=%d N_executed=%d pass=%d skip=%d fail=%d"
          % (len(cases), len(cases), len(passed), len(skipped), len(failed)))
    if skipped:
        print("UPSTREAM_CHECK_SKIPPED %s" % ",".join(skipped))
    if failed:
        print("UPSTREAM_CHECK_FAILED %s" % ",".join(failed))
    print("UPSTREAM_CHECK_VERDICT %s" % ("PASS" if not failed else "FAIL"))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
