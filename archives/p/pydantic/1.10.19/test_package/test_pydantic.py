#!/usr/bin/env python3
"""pydantic consumer test (R34): module importable from package site-packages
+ real pydantic API usage (BaseModel validation round-trip)."""
import os
import subprocess
import sys

SMOKE_PY = r'''
import sys
sys.path[0:0] = __import__("os").environ["PYTHONPATH"].split(":")
import pydantic
print("pydantic", pydantic.__version__)

from pydantic import BaseModel, ValidationError

class User(BaseModel):
    name: str
    age: int = 0

# 真实 API：构造 + 校验 + 字段访问
u = User(name="alice", age=30)
assert u.name == "alice"
assert u.age == 30
assert u.dict() == {"name": "alice", "age": 30}

# 校验失败路径（pydantic v1 对 str 字段的 int/float 宽松转换——
# 123→'123' 实测不抛错；None 才抛 ValidationError）
try:
    User(name=None)
    print("FAIL: expected ValidationError")
    sys.exit(1)
except ValidationError:
    pass

print("OK: pydantic BaseModel validate/dict works")
'''


def main() -> int:
    if len(sys.argv) < 2:
        print("FAIL: missing package path argument", file=sys.stderr)
        return 1
    pkg = sys.argv[1]
    site = os.path.join(pkg, "lib", "python3.12", "site-packages")
    mod = os.path.join(site, "pydantic", "__init__.py")
    if not os.path.isfile(mod):
        print(f"FAIL: pydantic module missing: {mod}", file=sys.stderr)
        return 1
    env = dict(os.environ)
    env["PYTHONPATH"] = site
    # 用调用本脚本的 python（必然存在且可执行——沙箱 PATH 无 python3 实测）
    py = sys.executable
    r = subprocess.run([py, "-c", SMOKE_PY], capture_output=True,
                       text=True, env=env)
    if r.returncode != 0:
        print(f"FAIL: pydantic API: {r.stderr}", file=sys.stderr)
        return 1
    print(r.stdout.strip())
    print("OK: pydantic module + BaseModel real API works")
    return 0


if __name__ == "__main__":
    sys.exit(main())
