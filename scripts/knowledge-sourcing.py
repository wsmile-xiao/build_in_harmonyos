#!/usr/bin/env python3
"""knowledge-sourcing.py — 知识库贡献者溯源工具（主编维护用）

作者口径：PR 原始 commit 的 author。
  平台合并 PR 时，main 上的 commit 是重签副本（合并机器 git 身份），贡献者真实署名
  仅存于 PR 分支的原始 commit（AtomGit API 可查）；本地非重签 commit 直接用其 author。

溯源口径：source_pr 仅用于溯源知识来源（软件适配任务），不作作者归属。
  解析路径：commit→merge 链路（merge-ancestry）或收割 commit 软件名反查（software-infer）。

用法（在仓库根目录执行）：
  python3 scripts/knowledge-sourcing.py map [E编号范围]   # 重建 草稿→条目 映射 + 双口径作者
  python3 scripts/knowledge-sourcing.py apply              # 将 authors/source_pr 写入条目

输出：$TMPDIR/knowledge-sourcing/mapping.json + pr-author-cache.json + pr-commits-cache.json
依赖：git（本仓库）、python3 urllib（AtomGit API，匿名只读够用）
"""
import json
import re
import os
import subprocess
import sys
import urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # scripts/ 的上级 = 仓库根
API = "https://atomgit.com/api/v5/repos/OpenHarmonyPCDeveloper/build_in_harmonyos"
PR_URL = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/{n}"
OUT = os.path.join(os.environ.get("TMPDIR") or os.path.expanduser("~/tmp"), "knowledge-sourcing")
os.makedirs(OUT, exist_ok=True)


def sh(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True,
                          cwd=REPO, timeout=600).stdout


def tokens(text):
    return set(w for w in re.split(r"[^a-z0-9_.-]+", text.lower()) if len(w) > 3)


def kv_field_text(blob, key):
    m = re.search(rf"^{key}:\s*(.+?)(?=\n[a-z_]+:|\n#|\Z)", blob, re.M | re.S)
    return m.group(1).strip().strip('"') if m else ""


def git_blob_before_delete(path, refs=None):
    """草稿删除前的最后版本（从 HEAD 逐级回退尝试）"""
    for ref in (refs or ["HEAD~6", "HEAD~5", "HEAD~4", "HEAD~3", "HEAD~2", "HEAD~1", "HEAD"]):
        blob = sh(f"git show '{ref}:{path}'")
        if "error_signature" in blob:
            return blob
    return ""


def _pr_commits(pr):
    """PR 分支的原始 commits（含真实作者署名）"""
    path = os.path.join(OUT, "pr-commits-cache.json")
    cache = json.load(open(path)) if os.path.exists(path) else {}
    if pr not in cache:
        try:
            req = urllib.request.Request(f"{API}/pulls/{pr}/commits?per_page=100",
                                         headers={"User-Agent": "curl/8"})
            d = json.loads(urllib.request.urlopen(req, timeout=20).read().decode())
            cache[pr] = [{"sha": c.get("sha", ""),
                          "author": (c.get("commit", {}).get("author", {}) or {}).get("name", ""),
                          "email": (c.get("commit", {}).get("author", {}) or {}).get("email", ""),
                          "msg": c.get("commit", {}).get("message", "").split("\n")[0]}
                         for c in (d if isinstance(d, list) else [])]
        except Exception:
            cache[pr] = []
        json.dump(cache, open(path, "w"), ensure_ascii=False)
    return cache[pr]


def _original_author(pr, local_msg, local_author):
    """真实作者：本地 goblinrs 重签副本 → 从 PR 原始 commits 按 message 匹配取作者；
    本地非 goblinrs（未被重签）→ 直接用本地 author。返回 (author, via, email)"""
    if local_author != "goblinrs" or not pr:
        return local_author, "", ""
    commits = _pr_commits(pr)
    if not commits:
        return local_author, "", ""
    for c in commits:
        if c["msg"] == local_msg and c["author"]:
            return c["author"], f"PR原始commit {c['sha'][:8]}", c.get("email", "")
    authors = {c["author"] for c in commits if c["author"]}
    if len(authors) == 1:
        a = authors.pop()
        return a, "PR单一作者", next((c.get("email", "") for c in commits if c["author"] == a), "")
    return local_author, "", ""


def _software_from_msg(msg):
    """从收割 commit message 提取软件名+版本：feat(libxcvt): 0.1.3 / 适配 dpkg 1.23.7"""
    m = re.search(r"feat\(([\w.+-]+)\)[:：]\s*([\d.]+)", msg)
    if m:
        return m.group(1).lower(), m.group(2)
    m = re.search(r"适配\s+([\w.+-]+)\s+([\d.]+)", msg)
    if m:
        return m.group(1).lower(), m.group(2)
    return "", ""


def _find_pr_by_software(soft, ver, merges, before_date=None):
    """在 merge 历史中匹配 feat/<软件>-<版本> 分支的 PR；取日期最近（且早于收割前）的一个"""
    cands = []
    for h, ad, s in merges:
        m = re.search(r"!(\d+) merge (?:feat|fix)/([\w.+-]+?)(?:-v?{}(?:\.\d+)*)?(?:-ohos.*)? into main".format(re.escape(ver)), s)
        if m and m.group(2).lower().startswith(soft[:max(4, len(soft) - 2)]):
            cands.append((h, ad, m.group(1), s))
    if not cands:
        return "", ""
    if before_date:
        cands = [c for c in cands if c[1] <= before_date] or cands
    cands.sort(key=lambda c: c[1])
    return cands[-1][2], cands[-1][3]


def build_mapping():
    # 全量 merge 历史（软件名→PR 反查用）
    mlog = sh("git log --merges --format='%H|%ad|%s' --date=short")
    merges = []
    for l in mlog.split("\n"):
        p = l.split("|", 2)
        if len(p) == 3 and "merge" in p[2] and "!" in p[2]:
            merges.append((p[0], p[1], p[2]))
    merges.sort(key=lambda x: x[1])

    # 1) 全部草稿 token
    log = sh("git log --no-renames --diff-filter=A --name-only --format= -- knowledge/drafts/")
    draft_files = sorted(set(l.strip() for l in log.split("\n") if l.strip().endswith(".kv")))
    drafts = {}
    for f in draft_files:
        blob = git_blob_before_delete(f)
        if blob:
            txt = " ".join(kv_field_text(blob, k) for k in ("title", "error_signature", "root_cause", "match_keywords"))
            drafts[f] = tokens(txt)

    # 2) 磁盘现存条目 token
    entry_files = sorted(f for f in os.listdir(os.path.join(REPO, "knowledge/graph")) if re.match(r"E\d+\.kv$", f))
    entries = {}
    for f in entry_files:
        c = open(os.path.join(REPO, "knowledge/graph", f)).read()
        txt = " ".join(kv_field_text(c, k) for k in ("title", "error_signature", "root_cause", "match_keywords"))
        entries[f] = tokens(txt)

    # 3) 草稿首次引入 commit
    log = sh("git log --no-renames --format='%H|%an|%ae|%ad|%s' --date=short --diff-filter=A --name-only -- knowledge/drafts/")
    intro = {}
    cur = None
    for line in log.split("\n"):
        if re.match(r"^[0-9a-f]{40}\|", line):
            cur = line.split("|", 4)
        elif line.strip().startswith("knowledge/drafts/") and cur and line.strip().endswith(".kv"):
            intro[line.strip()] = cur

    # 4) PR 解析 + 作者解析
    cache_path = os.path.join(OUT, "pr-author-cache.json")
    cache = json.load(open(cache_path)) if os.path.exists(cache_path) else {}

    mapping = []
    used = set()
    for dpath, dtok in sorted(drafts.items()):
        best, best_j = None, 0.0
        for ef, etok in entries.items():
            if ef in used:
                continue
            u = len(dtok | etok)
            j = len(dtok & etok) / u if u else 0
            if j > best_j:
                best, best_j = ef, j
        if not best or best_j < 0.4:
            continue
        used.add(best)
        eid = best[:-3]
        h = intro.get(dpath)
        if not h:
            continue
        chash, c_author, c_email, c_date, c_msg = h
        pr, pr_via = "", ""
        if c_author == "goblinrs" and not c_msg.startswith("knowledge:"):
            soft, ver = _software_from_msg(c_msg)
            if soft:
                pr, _via = _find_pr_by_software(soft, ver, merges, before_date=c_date)
                pr_via = "software-infer" if pr else ""
        if not pr:
            alog = sh(f"git log --merges --ancestry-path --format='%H|%ad|%s' --date=short {chash}..main")
            lines = [l for l in alog.split("\n") if "!" in l]
            if lines:
                pr = lines[-1].split("!")[1].split(" ")[0]
                pr_via = "merge-ancestry"
        if pr and pr not in cache:
            try:
                req = urllib.request.Request(f"{API}/pulls/{pr}", headers={"User-Agent": "curl/8"})
                d = json.loads(urllib.request.urlopen(req, timeout=15).read().decode())
                cache[pr] = {"author": d.get("user", {}).get("login", ""), "title": d.get("title", "")}
            except Exception:
                cache[pr] = {"author": "", "title": ""}
        info = cache.get(pr, {"author": "", "title": ""}) if isinstance(cache.get(pr, None), dict) else \
            ({"author": cache.get(pr, ""), "title": ""} if pr else {"author": "", "title": ""})
        real_author, author_via, author_email = _original_author(pr, c_msg, c_author)
        mapping.append({
            "draft": os.path.basename(dpath)[:-3],
            "eid": eid, "match": round(best_j, 3),
            "commit_author": c_author, "commit_email": c_email, "commit_date": c_date,
            "author": real_author, "author_via": author_via, "author_email": author_email,
            "pr": pr, "pr_author": info["author"], "pr_title": info["title"], "pr_via": pr_via,
        })
    json.dump(cache, open(cache_path, "w"))
    mapping.sort(key=lambda x: int(x["eid"][1:]))
    json.dump(mapping, open(os.path.join(OUT, "mapping.json"), "w"), ensure_ascii=False, indent=1)
    ok = sum(1 for m in mapping if m["match"] >= 0.7)
    infer = sum(1 for m in mapping if m["pr_via"] == "software-infer")
    fixed = sum(1 for m in mapping if m["author"] != m["commit_author"])
    print(f"映射总数: {len(mapping)}（高置信 {ok}）；软件反查 PR: {infer}；重签副本作者修正: {fixed}")
    for m in mapping:
        if m["match"] < 0.7:
            print(f"  低置信: {m['eid']}:{m['match']} <- {m['draft'][:40]}")


def apply_authors(min_match=0.7):
    """作者 = PR 原始 commit 的 author（goblinrs 重签副本反查）；无 PR 匹配时 = 本地首次引入 commit author"""
    mapping = json.load(open(os.path.join(OUT, "mapping.json")))
    by_eid = {}
    for m in mapping:
        if m["match"] >= min_match:
            by_eid.setdefault(m["eid"], m)
    updated = 0
    for eid, m in sorted(by_eid.items(), key=lambda x: int(x[0][1:])):
        path = os.path.join(REPO, "knowledge/graph", f"{eid}.kv")
        if not os.path.exists(path):
            continue
        c = open(path).read()
        real, email = m["author"], m["commit_email"]
        if real != m["commit_author"]:
            email = m.get("author_email") or f"{real}@noreply.atomgit.com"
        c = re.sub(r"^authors:.*$", f"authors: {real} <{email}>", c, flags=re.M, count=1)
        if m["pr"]:
            if re.search(r"^source_pr:.*$", c, re.M):
                c = re.sub(r"^source_pr:.*$", f"source_pr: !{m['pr']}", c, flags=re.M, count=1)
            else:
                c = re.sub(r"(\nlast_updated:)", rf"\nsource_pr: !{m['pr']}\1", c, count=1)
        open(path, "w").write(c)
        updated += 1
    print(f"已更新 authors/source_pr: {updated} 条")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "map"
    if cmd == "map":
        build_mapping()
    elif cmd == "apply":
        apply_authors(float(sys.argv[2]) if len(sys.argv) > 2 else 0.7)
