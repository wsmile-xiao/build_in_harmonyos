#!/usr/bin/env python3
"""zsxd 1.12.2 数据包消费者验证。

用法: python3 test_zsxd.py <package_folder>

验证的是**打包产物本体**，而非"文件存在"占位：

  A. data.solarus（上游 `zip data/` 的成品）
     - 是合法 zip 且条目数 == 上游 CMake glob 文件数（674，本版本 tarball 实测）；
     - 关键文件齐全：quest.dat / project_db.dat / main.lua /
       languages/{en,es,fr}/text/dialogs.dat；
     - 无多余条目：上游 glob 只收 *.spc/*.ogg/*.it/*.png/*.dat/*.lua/*.ttf/*.ttc/*.fon，
       icon.ico / icon.icns / sounds/wav2ogg 这三类必须**不在**归档里；
     - quest.dat 内容自述 quest_version = "1.12.2"。
  B. bin/zsxd launcher
     - 存在、可执行、shebang 为 #!/bin/sh、全文无 CR（CRLF 会写坏 shebang）；
     - `zsxd --version` 自处理分支输出 "zsxd 1.12.2"（引擎缺失时 launcher 可自检）。
  C. 端到端消费者行为（rule12）
     - 用 stub `solarus-run`（记录 argv 后退出 0）驱动 bin/zsxd，
       断言 stub 被真实调用、首个参数 == <package>/share/solarus/zsxd、
       追加参数原样透传 —— 即 launcher 与真实引擎的调用契约成立。
  D. 随包发布物：licenses/license.txt、share/applications/zsxd.desktop、
     share/pixmaps/zsxd.png。

任一断言失败 → 退出码 1（Conan test_package 随之失败）。
"""

import os
import shutil
import subprocess
import sys
import tempfile
import zipfile

EXPECTED_ENTRIES = 674          # 上游 CMake glob 对 data/ 匹配的文件数（v1.12.2 tarball 实测）
ARCHIVE_NAME = "data.solarus"
QUEST_DIR = os.path.join("share", "solarus", "zsxd")
# 上游 glob 不收集、不得出现在归档里的文件（相对 data/）
FORBIDDEN_IN_ARCHIVE = (
    os.path.join("logos", "icon.ico"),
    os.path.join("logos", "icon.icns"),
    os.path.join("sounds", "wav2ogg"),
)
KEY_ENTRIES = (
    "quest.dat",
    "project_db.dat",
    "main.lua",
    os.path.join("languages", "en", "text", "dialogs.dat"),
    os.path.join("languages", "fr", "text", "dialogs.dat"),
    os.path.join("languages", "es", "text", "dialogs.dat"),
)

_results = []


def check(ok, label) -> bool:
    _results.append((bool(ok), label))
    print(f"        [{'ok' if ok else 'FAIL'}] {label}")
    return bool(ok)


def _shell():
    cand = os.environ.get("CONFIG_SHELL") or shutil.which("sh") or shutil.which("bash")
    if not cand:
        raise RuntimeError("no POSIX shell found (set CONFIG_SHELL)")
    return cand


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: test_zsxd.py <package_folder>")
        return 2
    package_folder = os.path.realpath(sys.argv[1])

    # ── A. data.solarus ──────────────────────────────────────────────
    archive = os.path.join(package_folder, QUEST_DIR, ARCHIVE_NAME)
    if not check(os.path.isfile(archive), f"share/solarus/zsxd/{ARCHIVE_NAME} 存在"):
        return finish()
    try:
        with zipfile.ZipFile(archive) as zf:
            names = zf.namelist()
            bad = zf.testzip()
            check(bad is None, "data.solarus 是合法 zip（CRC 校验通过）")
            check(len(names) == EXPECTED_ENTRIES,
                  f"归档条目数 == {EXPECTED_ENTRIES}（实际 {len(names)}）")
            missing = [k for k in KEY_ENTRIES if k not in names]
            check(not missing, f"关键文件齐全（缺 {missing[:5]}）")
            leaked = [f for f in FORBIDDEN_IN_ARCHIVE if f in names]
            check(not leaked,
                  f"归档无多余条目（上游 glob 外文件 {leaked[:5]} 不得入包）")
            for lang in ("en", "es", "fr"):
                strings = os.path.join("languages", lang, "text", "strings.dat")
                check(strings in names, f"languages/{lang}/text/strings.dat 在归档中")
            quest_txt = zf.read("quest.dat").decode("utf-8", "replace")
            check('quest_version = "1.12.2"' in quest_txt,
                  "quest.dat 自述 quest_version = 1.12.2")
    except zipfile.BadZipFile as exc:
        check(False, f"data.solarus 不是合法 zip: {exc}")
        return finish()

    # ── B. bin/zsxd launcher 静态检查 ────────────────────────────────
    launcher = os.path.join(package_folder, "bin", "zsxd")
    check(os.path.isfile(launcher), "bin/zsxd 存在")
    if os.path.isfile(launcher):
        check(os.access(launcher, os.X_OK), "bin/zsxd 可执行（X_OK）")
        with open(launcher, "rb") as handle:
            raw = handle.read()
        check(raw.startswith(b"#!/bin/sh"), "bin/zsxd shebang 为 #!/bin/sh")
        check(b"\r" not in raw, "bin/zsxd 全文无 CR（无 CRLF shebang 污染）")

    # ── B2. --version 自处理分支（不依赖 solarus-run）─────────────────
    shell = _shell()
    proc = subprocess.run([shell, launcher, "--version"],
                          capture_output=True, text=True, timeout=30)
    check(proc.returncode == 0 and proc.stdout.strip() == "zsxd 1.12.2",
          f"bin/zsxd --version → 'zsxd 1.12.2'（rc={proc.returncode}，out={proc.stdout.strip()!r}）")

    # ── C. 端到端：stub solarus-run 驱动 launcher ────────────────────
    tmp = tempfile.mkdtemp(prefix="zsxd-test-")
    try:
        stub_dir = os.path.join(tmp, "stub")
        os.makedirs(stub_dir, exist_ok=True)
        stub = os.path.join(stub_dir, "solarus-run")
        out = os.path.join(tmp, "argv.txt")
        with open(stub, "w", encoding="utf-8", newline="\n") as handle:
            handle.write("#!/bin/sh\n")
            handle.write('printf "%s\\n" "$1" > "$SOLARUS_STUB_OUT"\n')
            handle.write('printf "%s\\n" "$@" >> "$SOLARUS_STUB_OUT"\n')
            handle.write("exit 0\n")
        os.chmod(stub, 0o755)
        env = dict(os.environ)
        env["PATH"] = stub_dir + os.pathsep + env.get("PATH", "")
        env["SOLARUS_STUB_OUT"] = out
        proc = subprocess.run([shell, launcher, "--extra", "arg2"],
                              capture_output=True, text=True, timeout=30,
                              env=env)
        check(proc.returncode == 0, "bin/zsxd 端到端执行成功（rc=0）")
        if os.path.isfile(out):
            lines = open(out, encoding="utf-8").read().splitlines()
            check(bool(lines), "stub solarus-run 被真实调用（记录了 argv）")
            if lines:
                got_quest = os.path.realpath(lines[0])
                want_quest = os.path.realpath(os.path.join(package_folder, QUEST_DIR))
                check(got_quest == want_quest,
                      f"launcher 传给 solarus-run 的 quest 目录正确\n"
                      f"          (got {got_quest})")
            check("--extra" in lines and "arg2" in lines,
                  "追加参数 --extra arg2 原样透传给 solarus-run")
        else:
            check(False, "solarus-run stub 输出文件未生成（launcher 未调用 stub）")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # ── D. 随包发布物 ────────────────────────────────────────────────
    check(os.path.isfile(os.path.join(package_folder, "licenses", "license.txt")),
          "licenses/license.txt 随包发布")
    lic = open(os.path.join(package_folder, "licenses", "license.txt"),
               encoding="utf-8", errors="replace").read()
    check("GNU General Public License" in lic,
          "license.txt 声明 GPL（Lua 脚本许可）")
    check(os.path.isfile(os.path.join(package_folder, "share", "applications",
                                      "zsxd.desktop")),
          "share/applications/zsxd.desktop 随包发布")
    check(os.path.isfile(os.path.join(package_folder, "share", "pixmaps",
                                      "zsxd.png")),
          "share/pixmaps/zsxd.png（徽标）随包发布")

    return finish()


def finish() -> int:
    passed = sum(1 for ok, _ in _results if ok)
    total = len(_results)
    print(f"\n        [test] {passed}/{total} assertions passed")
    if passed != total:
        for ok, label in _results:
            if not ok:
                print(f"  - {label}")
        return 1
    print("All tests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
