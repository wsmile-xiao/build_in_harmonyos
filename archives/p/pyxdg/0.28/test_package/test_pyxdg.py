#!/usr/bin/env python3
"""pyxdg consumer test（R34：真实调用被测库 API）。

不依赖系统 MIME 数据库，故选取纯用户空间的 API：
  * xdg.BaseDirectory.xdg_data_home / xdg_cache_home（XDG 基目录解析）
  * xdg.IniFile / xdg.DesktopEntry（解析一个自造的 .desktop 文件）
导入失败或任一断言失败即返回非零。
"""
import os
import sys
import tempfile


def main() -> int:
    try:
        import xdg
    except ImportError as e:
        print(f"FAIL: cannot import xdg: {e}", file=sys.stderr)
        return 1

    # 1) XDG Base Directory：0.28 里 xdg_data_home/xdg_cache_home 是**模块级字符串**
    #    （import 时算好），不是函数；函数是 save_*_path / load_*_paths。
    try:
        from xdg import BaseDirectory as B
        if not os.path.isabs(B.xdg_data_home) or not os.path.isabs(B.xdg_cache_home):
            print(f"FAIL: non-absolute XDG dirs: "
                  f"data={B.xdg_data_home!r} cache={B.xdg_cache_home!r}",
                  file=sys.stderr)
            return 1
        # 真实函数 API：save_cache_path 返回并创建该目录
        probe_dir = B.save_cache_path("pyxdg-probe")
        if not os.path.isdir(probe_dir):
            print(f"FAIL: save_cache_path did not create {probe_dir!r}",
                  file=sys.stderr)
            return 1
        # load_config_paths 返回**生成器**；资源不存在时产出为空是正确行为，
        # 故只校验「产出项都是字符串」，不要求非空。
        cfg = list(B.load_config_paths("probe"))
        if not all(isinstance(x, str) for x in cfg):
            print(f"FAIL: load_config_paths('probe') -> {cfg!r}", file=sys.stderr)
            return 1
        # save_config_path 返回并创建该目录（确定性断言）
        cfg_dir = B.save_config_path("pyxdg-probe")
        if not os.path.isdir(cfg_dir):
            print(f"FAIL: save_config_path did not create {cfg_dir!r}",
                  file=sys.stderr)
            return 1
    except Exception as e:
        print(f"FAIL: BaseDirectory API raised: {e}", file=sys.stderr)
        return 1

    # 2) DesktopEntry：解析自造 .desktop 文件（纯用户空间，无需系统数据库）
    try:
        from xdg.DesktopEntry import DesktopEntry
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "probe.desktop")
            with open(p, "w") as fh:
                fh.write("[Desktop Entry]\nType=Application\n"
                         "Name=PyXDG Probe\nExec=probe\n")
            de = DesktopEntry(p)
            if de.getName() != "PyXDG Probe" or de.getType() != "Application":
                print(f"FAIL: DesktopEntry parse wrong: "
                      f"name={de.getName()!r} type={de.getType()!r}",
                      file=sys.stderr)
                return 1
            if not de.getExec():
                print("FAIL: DesktopEntry Exec missing", file=sys.stderr)
                return 1
    except Exception as e:
        print(f"FAIL: DesktopEntry API raised: {e}", file=sys.stderr)
        return 1

    # 3) IniFile：解析同款 INI
    try:
        from xdg.IniFile import IniFile
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "probe.ini")
            with open(p, "w") as fh:
                fh.write("[Group]\nKey=Value\n")
            ini = IniFile(p)
            if ini.get("Key", "Group") != "Value":
                print(f"FAIL: IniFile get wrong: {ini.get('Key', 'Group')!r}",
                      file=sys.stderr)
                return 1
    except Exception as e:
        print(f"FAIL: IniFile API raised: {e}", file=sys.stderr)
        return 1

    print("OK: pyxdg real API ok (BaseDirectory / DesktopEntry / IniFile)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
