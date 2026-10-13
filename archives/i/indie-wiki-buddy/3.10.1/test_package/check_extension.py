#!/usr/bin/env python3
"""Consumer checks for the indie-wiki-buddy package.

usage: check_extension.py <package-folder>

Checks（全部针对打包后的产物；纯静态包 → 校验偏"资源口径 + 配置语义"）：
  1. 两棵浏览器树都存在，且各有 manifest.json / background.js 与 7 个内容目录；
  2. 两份 manifest.json 都是合法 JSON，`version` 均为 3.10.1，且
     chromium 的 `manifest_version` == 3、firefox 的 == 2（**关键语义**：装错模板会被抓到）；
  3. firefox manifest 的 `browser_specific_settings.gecko.id` 等于包路径里使用的 Mozilla 扩展 ID；
  4. 资源口径：favicons/images/data/pages/scripts/css 的文件数不低于下限（防止"只是把空目录装过去"）；
  5. 记录证据：两棵树的总文件数 / 总字节数。
"""
import json
import os
import sys

CHROMIUM_REL = os.path.join("res", "chromium", "extensions", "indie-wiki-buddy")
FIREFOX_REL = os.path.join("res", "mozilla", "extensions",
                           "{ec8030f7-c20a-464f-9b0e-13a3a9e97384}",
                           "{cb31ec5d-c49a-4e5a-b240-16c767444f62}")
GECKO_ID = "{cb31ec5d-c49a-4e5a-b240-16c767444f62}"
CONTENT_DIRS = ("_locales", "css", "data", "favicons", "images", "pages", "scripts")
MIN_COUNTS = {"favicons": 400, "images": 15, "data": 10, "pages": 5, "scripts": 3, "css": 5}
VERSION = "3.10.1"
EXPECTED_MANIFEST_VERSION = {"chromium": 3, "firefox": 2}

fails = []


def fail(msg):
    fails.append(msg)
    print("[FAIL] %s" % msg)


def ok(msg):
    print("[ok]   %s" % msg)


def check_trees(pkg):
    trees = {}
    for name, rel in (("chromium", CHROMIUM_REL), ("firefox", FIREFOX_REL)):
        base = os.path.join(pkg, rel)
        if not os.path.isdir(base):
            fail("缺少 %s 树：%s" % (name, rel))
            continue
        missing = [d for d in CONTENT_DIRS if not os.path.isdir(os.path.join(base, d))]
        if missing:
            fail("%s 树缺少内容目录：%s" % (name, ", ".join(missing)))
            continue
        for f in ("manifest.json", "background.js"):
            if not os.path.isfile(os.path.join(base, f)):
                fail("%s 树缺少 %s" % (name, f))
                break
        else:
            trees[name] = base
    if len(trees) == 2:
        ok("两棵浏览器树齐备（chromium + firefox，各含 manifest.json/background.js 与 %d 个内容目录）"
           % len(CONTENT_DIRS))
    return trees


def check_manifests(trees):
    for name, base in sorted(trees.items()):
        path = os.path.join(base, "manifest.json")
        try:
            with open(path, errors="replace") as fh:
                data = json.load(fh)
        except Exception as exc:  # noqa: BLE001
            fail("%s/manifest.json 不是合法 JSON：%s" % (name, exc))
            continue
        if data.get("version") != VERSION:
            fail("%s/manifest.json version=%s，期望 %s"
                 % (name, data.get("version"), VERSION))
            continue
        want = EXPECTED_MANIFEST_VERSION[name]
        if data.get("manifest_version") != want:
            fail("%s/manifest.json manifest_version=%s，期望 %s（疑似装错模板）"
                 % (name, data.get("manifest_version"), want))
            continue
        ok("%s/manifest.json 合法：version=%s、manifest_version=%s"
           % (name, data["version"], data["manifest_version"]))
    # firefox 特有线：gecko 扩展 ID 必须与包内目录名一致
    base = trees.get("firefox")
    if base:
        # 二次读取同样要异常兜底（循环里那次有 except，这里原本没有）：
        # manifest 损坏时按 FAIL 明确报出，不要抛未捕获异常把结构化结果行冲掉。
        try:
            with open(os.path.join(base, "manifest.json"), errors="replace") as fh:
                data = json.load(fh)
        except Exception as exc:
            fail("firefox manifest 无法解析（%s）：%s" % (base, str(exc)[:120]))
            return
        gecko = ((data.get("browser_specific_settings") or {}).get("gecko") or {}).get("id")
        if gecko != GECKO_ID:
            fail("firefox manifest 的 gecko id=%s，期望 %s（与目录名不一致）" % (gecko, GECKO_ID))
        else:
            ok("firefox manifest 的 gecko id 与包内目录名一致（%s）" % GECKO_ID)


def check_resources(trees):
    if not trees:
        return
    bad = []
    for name, base in sorted(trees.items()):
        for d, minimum in MIN_COUNTS.items():
            count = sum(len(files) for _r, _d, files in os.walk(os.path.join(base, d)))
            if count < minimum:
                bad.append("%s/%s=%d(<%d)" % (name, d, count, minimum))
    if bad:
        fail("资源口径不足：%s" % ", ".join(bad))
        return
    ok("资源口径达标（favicons/images/data/pages/scripts/css 均不低于下限，两棵树各一份）")


def check_evidence(trees):
    if not trees:
        return
    for name, base in sorted(trees.items()):
        count = 0
        size = 0
        for root, _dirs, files in os.walk(base):
            for f in files:
                count += 1
                size += os.path.getsize(os.path.join(root, f))
        ok("证据：%s 树 %d 个文件 / %.1f MB" % (name, count, size / (1024.0 * 1024.0)))


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    trees = check_trees(sys.argv[1])
    check_manifests(trees)
    check_resources(trees)
    check_evidence(trees)
    print("checks=%d fails=%d skips=0" % (5, len(fails)))
    if fails:
        print("RESULT: FAIL")
        return 1
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
