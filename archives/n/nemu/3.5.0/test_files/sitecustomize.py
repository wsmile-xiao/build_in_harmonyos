# sitecustomize.py — nemu 上游测试在 OHOS 设备真跑的 python 层 /tmp 重定向。
#
# 背景：HarmonyOS 根文件系统 /tmp 为只读 erofs；python.org 构建的
# libpython 为 BIND_NOW 且其 os.mkdir 等调用不经过可被 LD_PRELOAD 拦截的
# PLT 解析路径（实测 libc.mkdir 解析到 /system/lib/ld-musl-aarch64.so，
# preload 库虽已 map 但符号未被选中）。而 nemu 二进制（普通懒绑定）的
# 拦截全部有效。
#
# 因此分两层：
#   - python 层（本文件，经 PYTHONPATH 自动 import）：
#     包装 os.mkdir/os.makedirs/os.stat/os.path.exists/os.access/
#     builtins.open/os.rename/os.rmdir/os.listdir/os.scandir/shutil.rmtree，
#     把 "/tmp/..." 重定向到 $NEMU_TMP_BASE/...
#   - 进程层（libnemu_test_env.so，LD_PRELOAD）：给 nemu/tmux 等原生
#     子进程用（getpwuid、/tmp、/usr/bin/qemu-* 重定向）。
#
# 上游测试文件（utils.py/vm_test.py/ova_test.py）零修改。
import os
import sys

_BASE = os.environ.get("NEMU_TMP_BASE", "")
_QSTUB = os.environ.get("NEMU_QEMU_STUB_DIR", "")
DEBUG = bool(os.environ.get("NEMU_TEST_ENV_DEBUG"))


def _dbg(old, new):
    if DEBUG:
        print("[nemu-py] %s -> %s" % (old, new), file=sys.stderr)


def _r(path):
    """返回重定向后的路径（str/bytes/os.PathLike 均支持），未命中返回原值。"""
    if not _BASE:
        return path
    # os.PathLike（PosixPath 等）：先转 str 判断再保持原类型语义
    if isinstance(path, os.PathLike):
        s = os.fspath(path)
        if isinstance(s, str) and s.startswith("/tmp/"):
            new = os.path.join(_BASE, s[5:])
            _dbg(s, new)
            return new
        return path
    if isinstance(path, bytes):
        if path.startswith(b"/tmp/"):
            new = os.path.join(_BASE.encode(), path[5:])
            _dbg(path, new)
            return new
        return path
    if isinstance(path, str) and path.startswith("/tmp/"):
        new = os.path.join(_BASE, path[5:])
        _dbg(path, new)
        return new
    return path


def _rq(path):
    """qemu 桩重定向：/usr/bin/qemu-* -> $NEMU_QEMU_STUB_DIR/qemu-*"""
    if not _QSTUB:
        return path
    if isinstance(path, str) and path.startswith("/usr/bin/qemu-"):
        new = os.path.join(_QSTUB, path[9:])
        _dbg(path, new)
        return new
    return path


def _wrap(module, name, path_arg_idx=0, redirect=_r):
    orig = getattr(module, name)

    def wrapper(*args, **kwargs):
        if args and isinstance(args[path_arg_idx], (str, bytes)):
            args = list(args)
            args[path_arg_idx] = redirect(args[path_arg_idx])
            args = tuple(args)
        return orig(*args, **kwargs)

    setattr(module, name, wrapper)


# ─── os 层 ───────────────────────────────────────────────
_wrap(os, "mkdir")
_wrap(os, "makedirs")
_wrap(os, "stat")
_wrap(os, "lstat")
_wrap(os, "access")
_wrap(os, "remove")
_wrap(os, "unlink")
_wrap(os, "rmdir")
_wrap(os, "listdir")
_wrap(os, "scandir")
# os.open (pathlib.Path.touch uses it)
_orig_os_open = os.open


def _os_open(path, flags, mode=0o777, *a, **kw):
    return _orig_os_open(_r(path), flags, mode, *a, **kw)


os.open = _os_open
# rename needs both arguments rewritten (explicit implementation below)
_orig_rename = os.rename


def _rename(src, dst, *a, **kw):
    return _orig_rename(_r(src), _r(dst), *a, **kw)


os.rename = _rename

_orig_stat = os.stat
_orig_exists = os.path.exists


def _exists(path, *a, **kw):
    return _orig_exists(_r(path), *a, **kw)


os.path.exists = _exists

_orig_open = open


def _open(file, mode="r", *a, **kw):
    return _orig_open(_r(file), mode, *a, **kw)


builtins_open = _open
import builtins  # noqa: E402
builtins.open = _open

# subprocess 的 argv[0] 重定向（qemu 桩）+ 相对命令名绝对化
# （python.org 3.12.9 在 OHOS 上：sitecustomize 存在时 subprocess 的
#   posix_spawn PATH 查找路径异常（FileNotFoundError），把 argv[0] 预解析
#   为绝对路径可完全绕开——utils.py 的 tmux 调用即相对名。）
import subprocess  # noqa: E402
_orig_run = subprocess.run
_orig_popen_init = subprocess.Popen.__init__
import shutil  # noqa: E402


def _fix_argv(args):
    if isinstance(args, (list, tuple)) and args:
        exe = args[0]
        if isinstance(exe, str):
            exe = _rq(exe)  # qemu 桩重定向（绝对路径替换）
            if "/" not in exe:
                resolved = shutil.which(exe)
                if resolved:
                    exe = resolved
            if exe != args[0]:
                new = list(args)
                new[0] = exe
                args = new
    return args


def _run(*args, **kwargs):
    if args and isinstance(args[0], (list, tuple)):
        args = (_fix_argv(args[0]),) + args[1:]
    elif isinstance(kwargs.get("args"), (list, tuple)):
        kwargs["args"] = _fix_argv(kwargs["args"])
    return _orig_run(*args, **kwargs)


subprocess.run = _run


def _popen_init(self, args, *a, **kw):
    _orig_popen_init(self, _fix_argv(args), *a, **kw)


subprocess.Popen.__init__ = _popen_init

# shutil.rmtree（utils.cleanup 用）
import shutil  # noqa: E402
_orig_rmtree = shutil.rmtree


def _rmtree(path, *a, **kw):
    return _orig_rmtree(_r(path), *a, **kw)


shutil.rmtree = _rmtree

if DEBUG:
    print("[nemu-py] sitecustomize loaded: NEMU_TMP_BASE=%s QSTUB=%s"
          % (_BASE, _QSTUB), file=sys.stderr)
