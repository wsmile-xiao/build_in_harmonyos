"""kconfiglib 消费者侧验证。

站在「库的使用者」角度，只通过公开 API 调用，验证：
  1. 包能 import、版本正确
  2. 核心 API 可用（Kconfig 解析、sym 取值、配置写入）
  3. 命令行工具的入口模块可导入（menuconfig/olddefconfig 等）
  4. guiconfig 已按预期剔除（OHOS 无 Tkinter）

R34：所有断言都实质调用被测包，不是空壳打印。
"""
import os
import subprocess
import sys
import tempfile

import kconfiglib

n_ok = 0


def check(cond, msg):
    global n_ok
    if not cond:
        raise AssertionError("FAIL: " + msg)
    n_ok += 1
    print("  PASS  " + msg)


# ── 1. 版本与基本导入 ────────────────────────────────────────
# 注意：kconfiglib 暴露的是 VERSION 元组，不是 __version__ 字符串
check(kconfiglib.VERSION == (14, 1, 0),
      "版本号 VERSION == (14, 1, 0)（实际 %r）" % (kconfiglib.VERSION,))
check(hasattr(kconfiglib, "Kconfig"), "公开 API Kconfig 类存在")
check(hasattr(kconfiglib, "KconfigSyntaxError"), "异常类型 KconfigSyntaxError 存在")
check(hasattr(kconfiglib, "MenuNode"), "公开 API MenuNode 类存在")

# ── 2. 实际解析一份 Kconfig ──────────────────────────────────
# 构造一个最小 Kconfig：一个 bool 选项 + 一个 string 选项 + 一个依赖关系
src = """\
mainmenu "consumer test"

config FOO
	bool "Enable FOO"
	default y

config BAR
	string "BAR value"
	default "hello"
	depends on FOO
"""
tmp = tempfile.mkdtemp(prefix="kconfiglib-test-")
kfile = os.path.join(tmp, "Kconfig")
with open(kfile, "w") as f:
    f.write(src)

c = kconfiglib.Kconfig(kfile, warn=False)
check("FOO" in c.syms, "解析后 syms 含 FOO")
check("BAR" in c.syms, "解析后 syms 含 BAR")
check(c.syms["FOO"].str_value == "y", "FOO 默认值按 Kconfig 解析为 'y'")
check(c.syms["BAR"].str_value == "hello", "BAR 字符串默认值解析为 'hello'")

# ── 3. 写配置并回读（验证配置读写闭环）────────────────────────
out = os.path.join(tmp, "out.config")
c.write_config(out)
check(os.path.exists(out), "write_config 产出 .config 文件")
with open(out) as f:
    body = f.read()
check("CONFIG_FOO=y" in body, "写出的 .config 含 CONFIG_FOO=y")
check('CONFIG_BAR="hello"' in body, "写出的 .config 含 CONFIG_BAR=\"hello\"")

# 回读：用 Kconfig.load_config 读刚写的配置
c2 = kconfiglib.Kconfig(kfile, warn=False)
c2.load_config(out)
check(c2.syms["FOO"].str_value == "y", "回读后 FOO 仍为 'y'")

# ── 4. 改值并验证「依赖关系」真实生效 ───────────────────────
# BAR 声明了 depends on FOO，关掉 FOO 后 BAR 应随之失效（值变空）。
# 这是 Kconfig 依赖语义的核心，也是本库区别于普通配置解析器之处。
c.syms["FOO"].set_value(0)          # 关掉 FOO
check(c.syms["FOO"].str_value == "n", "set_value(0) 后 FOO 变为 'n'")
check(c.syms["BAR"].str_value == "",
      "关掉 FOO 后，依赖它的 BAR 值变为空（依赖生效）")

c.syms["FOO"].set_value(2)          # 重新打开 FOO（2 = 'y'）
check(c.syms["FOO"].str_value == "y", "重新打开后 FOO 恢复为 'y'")
check(c.syms["BAR"].str_value == "hello",
      "依赖恢复后 BAR 回到默认值 'hello'")

c.syms["BAR"].set_value("world")
check(c.syms["BAR"].str_value == "world", "依赖满足时 set_value 生效，BAR 为 'world'")
check(c.syms["BAR"].visibility == 2, "BAR 可见性为 2（可见）")

# ── 5. 命令行工具的入口模块可导入 ────────────────────────────
for mod in ("menuconfig", "olddefconfig", "savedefconfig", "genconfig",
            "defconfig", "listnewconfig", "setconfig"):
    __import__(mod)
    n_ok += 1
print("  PASS  7 个 CLI 工具模块可导入（menuconfig/olddefconfig/saveddefconfig/"
      "genconfig/defconfig/listnewconfig/setconfig）")

# ── 6. 实际调用 CLI 工具（olddefconfig 无需交互，可直接跑）────
# 注意入口名：setup.py 里 menuconfig/guiconfig 是 `_main`，
# 而 olddefconfig 等是 `main`。这里跑 olddefconfig。
env = dict(os.environ)
cli_out = os.path.join(tmp, "cli.config")
env["KCONFIG_CONFIG"] = cli_out
r = subprocess.run(
    [sys.executable, "-c",
     "import sys; sys.argv=['olddefconfig', {!r}]; "
     "import olddefconfig; olddefconfig.main()".format(kfile)],
    capture_output=True, text=True, env=env, cwd=tmp,
)
check(r.returncode == 0,
      "olddefconfig CLI 实际执行成功（退出码 0）" +
      ("" if r.returncode == 0 else "；stderr=" + r.stderr[:200]))
check(os.path.exists(cli_out), "CLI 产出配置文件")
with open(cli_out) as f:
    cli_body = f.read()
check("CONFIG_FOO=y" in cli_body, "CLI 产出的配置含 CONFIG_FOO=y")

# ── 7. guiconfig 应已被剔除（OHOS 无 Tkinter）─────────────────
try:
    import guiconfig  # noqa: F401
    raise AssertionError("FAIL: guiconfig 不该存在（OHOS 无 _tkinter）")
except ImportError:
    n_ok += 1
    print("  PASS  guiconfig 已按预期剔除（OHOS 无 Tkinter）")

print()
print("kconfiglib 消费者测试：%d/%d 项通过" % (n_ok, n_ok))
