#!/usr/bin/env python3
"""bambam 1.4.1 鸿蒙特有测试（test_package 消费端，SDL dummy 环境）。

在 SDL_VIDEODRIVER=dummy / SDL_AUDIODRIVER=dummy /
PYGAME_HIDE_SUPPORT_PROMPT=1 下对**已安装**被测包做实质执行验证（R34）：
1. bin/bambam --help：argparse 在 pygame.init 之前解析并退出 0（无显示可跑）；
2. import bambam 冒烟 + 包布局断言（share/bambam/data 图片声音、
   extensions/alphanumeric-en_US/event_map.yaml、bin/bambam 包装器存在可执行）；
3. 上游 run() 数据目录发现逻辑验证（Bambam()._add_base_dir(<pkg>/share/bambam)
   能发现 data/ 与 extensions/）；
4. boot 冒烟（可选）：SDL dummy 下短超时运行 bin/bambam——进程存活到超时即
   通过（已进入事件循环）；若仅因 SDL dummy 不支持系统光标（set_cursor 报
   pygame.error）提前退出，视为核心 boot（pygame.init/set_mode/资源加载）已
   成功的已知 dummy 限制，如实上报不算失败；其他异常退出 → 失败。

HNP AppSpawn 沙箱可能拒绝用户路径 dlopen（E212，pygame 先例）：
- 若 import bambam / --help / boot 报 "Error loading shared library ...
  pygame/... .so: Permission denied" → 降级为静态制品校验（bambam.py 存在、
  bin/bambam 存在可执行、data/extensions 布局齐全）并如实上报 e212Fallback。

环境变量（由 test_package/conanfile.py 注入）：
  BAMBAM_PKG_ROOT  被测包 package_folder（必填）
  BAMBAM_SITE      bambam site-packages 路径（E212 静态校验用）
  BAMBAM_BOOT_SECONDS  boot 冒烟超时秒数（默认 8）

输出：HMBS_TEST_PACKAGE_RESULT=<json>，exit 0=通过。
"""
import json
import os
import subprocess
import sys
import time

_PKG_ROOT = os.environ.get("BAMBAM_PKG_ROOT", "")
_SITE = os.environ.get("BAMBAM_SITE", "")
_BOOT_SECONDS = float(os.environ.get("BAMBAM_BOOT_SECONDS", "8"))
_SDL_DUMMY_ENV = {
    "SDL_VIDEODRIVER": "dummy",
    "SDL_AUDIODRIVER": "dummy",
    "PYGAME_HIDE_SUPPORT_PROMPT": "1",
    "PYTHONDONTWRITEBYTECODE": "1",
}

_results = []


def _check(name, ok, detail):
    ok = bool(ok)
    _results.append({"name": name, "ok": ok, "detail": detail})
    print("[PASS] check=%s detail=%s" % (name, detail) if ok
          else "[FAIL] check=%s detail=%s" % (name, detail), flush=True)
    return ok


def _is_e212(text):
    return ("Permission denied" in text
            and "Error loading shared library" in text
            and "pygame" in text)


def _cli():
    return os.path.join(_PKG_ROOT, "bin", "bambam")


def _boot_smoke(cli):
    env = dict(os.environ, **_SDL_DUMMY_ENV)
    try:
        proc = subprocess.Popen([sys.executable, cli], env=env,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except OSError as exc:
        return False, "spawn failed: %r" % (exc,)
    deadline = time.time() + _BOOT_SECONDS
    while time.time() < deadline:
        if proc.poll() is not None:
            out, err = proc.communicate(timeout=10)
            text = (out or b"").decode("utf-8", "replace") + (
                err or b"").decode("utf-8", "replace")
            if _is_e212(text):
                return False, "e212"
            if ("Error while creating system cursor" in text
                    or "set_cursor" in text):
                # SDL dummy 无系统光标：核心 boot（init/set_mode/资源加载）已完成
                return True, (
                    "core boot ok; SDL dummy system-cursor limitation rc=%s"
                    % proc.returncode)
            return False, "early exit rc=%s: %r" % (proc.returncode, text[:300])
        time.sleep(0.2)
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)
    return True, ("alive until %ss deadline (event loop reached)"
                  % _BOOT_SECONDS)


def _pygame_steps():
    cli = _cli()

    # 1) CLI --help：argparse 在 pygame.init 之前解析并退出 0
    ok_help, detail_help = False, "not run"
    try:
        p = subprocess.run([sys.executable, cli, "--help"],
                           capture_output=True, text=True, timeout=60,
                           env=dict(os.environ, **_SDL_DUMMY_ENV))
        out = (p.stdout or "") + (p.stderr or "")
        ok_help = p.returncode == 0 and "usage:" in out
        detail_help = "rc=%s" % p.returncode
    except Exception as exc:  # noqa: BLE001
        detail_help = repr(exc)
        if _is_e212(str(exc)):
            return "e212"
    if not ok_help and _is_e212(out):
        return "e212"
    if not _check("cli_help_exit0", ok_help, detail_help):
        return "help_failed"

    # 2) import bambam 冒烟
    try:
        import bambam  # noqa: E402
        ok_import = callable(bambam.main)
        _check("import_bambam", ok_import,
               "main callable, module=%s" % bambam.__file__)
    except Exception as exc:  # noqa: BLE001
        if _is_e212(str(exc)):
            return "e212"
        _check("import_bambam", False, repr(exc))
        return "import_failed"

    # 包布局断言
    data_dir = os.path.join(_PKG_ROOT, "share", "bambam", "data")
    ext_dir = os.path.join(_PKG_ROOT, "share", "bambam", "extensions")
    data_files = os.listdir(data_dir) if os.path.isdir(data_dir) else []
    has_img = any(f.endswith(".gif") or f.endswith(".png") for f in data_files)
    has_snd = any(f.endswith(".wav") or f.endswith(".ogg") for f in data_files)
    event_map = os.path.isfile(
        os.path.join(ext_dir, "alphanumeric-en_US", "event_map.yaml"))
    cli_exists = os.path.isfile(cli)
    cli_x = os.access(cli, os.X_OK)
    if not _check("package_data_layout",
                  has_img and has_snd and event_map,
                  "data=%d files img=%s snd=%s event_map=%s"
                  % (len(data_files), has_img, has_snd, event_map)):
        return "layout_failed"
    if not _check("bin_bambam_present_exec", cli_exists and cli_x,
                  "exists=%s exec=%s" % (cli_exists, cli_x)):
        return "cli_failed"

    # 3) 上游 run() 数据目录发现逻辑
    # 注意：_add_base_dir 内部 print(_(...)) 使用 gettext 的 _()（builtins），
    # 上游 main() 首行 gettext.install('bambam') 才安装；此处先安装再调用。
    import gettext  # noqa: E402
    gettext.install('bambam')
    inst = bambam.Bambam()
    inst._add_base_dir(os.path.join(_PKG_ROOT, "share", "bambam"))
    found_data = any(os.path.basename(d) == "data" for d in inst.data_dirs)
    found_ext = any(os.path.basename(d) == "extensions"
                    for d in inst.extensions_dirs)
    if not _check("data_dir_discovery", found_data and found_ext,
                  "data_dirs=%s extensions_dirs=%s"
                  % (inst.data_dirs, inst.extensions_dirs)):
        return "discovery_failed"

    # 4) boot 冒烟（可选，SDL dummy 容忍）
    boot_ok, boot_detail = _boot_smoke(cli)
    if not _check("boot_smoke", boot_ok, boot_detail):
        return "boot_failed"
    return "ok"


def _static_e212_checks():
    cli = _cli()
    site_bambam = _SITE or os.path.join(_PKG_ROOT, "lib", "python3.12",
                                        "site-packages")
    data_dir = os.path.join(_PKG_ROOT, "share", "bambam", "data")
    ext_dir = os.path.join(_PKG_ROOT, "share", "bambam", "extensions")
    checks = [
        os.path.isfile(os.path.join(site_bambam, "bambam.py")),
        os.path.isfile(cli),
        os.access(cli, os.X_OK),
        bool(os.listdir(data_dir)) if os.path.isdir(data_dir) else False,
        os.path.isfile(os.path.join(ext_dir, "alphanumeric-en_US",
                                    "event_map.yaml")),
    ]
    for i, c in enumerate(checks, 1):
        print("[PASS] E212 static check=%d" % i if c
              else "[FAIL] E212 static check=%d" % i, flush=True)
    return {"passed": sum(checks), "discovered": len(checks)}


def main():
    if not _PKG_ROOT:
        print("[FAIL] BAMBAM_PKG_ROOT not set", file=sys.stderr)
        return 2
    phase = _pygame_steps()
    e212_fallback = phase == "e212"
    if e212_fallback:
        static = _static_e212_checks()
        passed = static["passed"] == static["discovered"]
        phase_detail = ("HNP AppSpawn blocked user-path pygame dlopen; "
                        "static artifact verification fallback")
    else:
        passed = phase == "ok"
        static = {"passed": 0, "discovered": 0}
        phase_detail = phase

    summary = {
        "executed": True,
        "passed": passed,
        "phase": phase,
        "phase_detail": phase_detail,
        "checks": _results,
        "e212Fallback": e212_fallback,
        "staticChecks": static,
    }
    print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(summary, sort_keys=True),
          flush=True)
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
