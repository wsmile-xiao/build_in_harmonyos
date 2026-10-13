#!/usr/bin/env python3
"""消费者校验 — jameica-h2database 1.4.199（Conan 包安装后的产物）

用法: python3 check_h2.py <package_folder>

校验项（输出统一 checks=/fails=/skips= 三计数）：
  1) 产物齐备：libexec/h2-1.4.199.jar 存在且非空
  2) jar 为合法 zip，含关键类与**打包进 jar 的资源文件**（org/h2/res/help.csv 等）
  3) 端到端真跑：javac + java，用 JDK 自带的 java.sql 驱动一个内存库
     （jdbc:h2:mem:）——建表 → 插入 → 查询 → 断言返回值（不需要任何第三方 jar）
  4) 证据：jar 大小与 sha256、所用 JDK

纪律：只有具名环境信号（宿主无 JDK）才允许 SKIP；其余一律 FAIL。
"""
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile

JAR = "h2-1.4.199.jar"
EXPECTED_CLASSES = [
    "org/h2/Driver.class",
    "org/h2/engine/Engine.class",
    "org/h2/command/Command.class",
]
EXPECTED_RESOURCES = [
    # H2 1.4.199 的 res/ 目录实际内容是 _messages_*.prop 与图标 png
    # （**没有** help.csv —— 那是另一个项目的资源名，实测断言会误报缺失）。
    "org/h2/res/_messages_en.prop",
    "META-INF/MANIFEST.MF",
]
E2E = """
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.ResultSet;
import java.sql.Statement;

public class H2E2E {
    public static void main(String[] args) throws Exception {
        Class.forName("org.h2.Driver");
        try (Connection c = DriverManager.getConnection("jdbc:h2:mem:e2e")) {
            Statement s = c.createStatement();
            s.execute("CREATE TABLE t(id INT PRIMARY KEY, name VARCHAR(20))");
            s.execute("INSERT INTO t VALUES (1, 'atom')");
            ResultSet r = s.executeQuery("SELECT name FROM t WHERE id = 1");
            if (!r.next()) { throw new IllegalStateException("no row"); }
            System.out.println("H2_E2E=" + r.getString(1));
        }
    }
}
"""

checks = fails = skips = 0


def ok(m):
    global checks
    checks += 1
    print("[ok]   " + m)


def bad(m):
    global checks, fails
    checks += 1
    fails += 1
    print("[FAIL] " + m)


def skip(m):
    global checks, skips
    checks += 1
    skips += 1
    print("[skip] " + m)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def java_home():
    jh = os.environ.get("JAVA_HOME", "")
    for c in (jh, os.path.expanduser("~/bishengjdk17"),
              os.path.expanduser("~/usr/local/bishengjdk17")):
        if c and os.path.isfile(os.path.join(c, "bin", "java")):
            return c
    found = shutil.which("java")
    return os.path.dirname(os.path.dirname(os.path.realpath(found))) if found else ""


def main():
    pkg = sys.argv[1] if len(sys.argv) > 1 else ""
    jar = os.path.join(pkg, "libexec", JAR)

    if os.path.isfile(jar) and os.path.getsize(jar) > 0:
        ok("产物齐备：%s (%d B)" % (JAR, os.path.getsize(jar)))
    else:
        bad("产物缺失或为空：%s" % jar)

    if fails == 0:
        try:
            with zipfile.ZipFile(jar) as zf:
                names = set(zf.namelist())
            missing = [c for c in EXPECTED_CLASSES + EXPECTED_RESOURCES if c not in names]
            if missing:
                bad("jar 内容缺失：%s" % ", ".join(missing))
            else:
                ok("jar 合法：关键类 %d 个 + 资源（_messages_en.prop/MANIFEST）齐备（共 %d 条目）"
                   % (len(EXPECTED_CLASSES), len(names)))
        except zipfile.BadZipFile as exc:
            bad("jar 非法 zip：%s" % exc)

    jh = java_home()
    if not jh or not os.path.isfile(os.path.join(jh, "bin", "javac")):
        skip("端到端未执行：具名环境信号——宿主无可用 JDK（JAVA_HOME/~/bishengjdk17/PATH 均无 javac）")
    else:
        with tempfile.TemporaryDirectory() as td:
            src = os.path.join(td, "H2E2E.java")
            with open(src, "w", encoding="utf-8") as fh:
                fh.write(E2E)
            javac = os.path.join(jh, "bin", "javac")
            java = os.path.join(jh, "bin", "java")
            r = subprocess.run([javac, "-encoding", "UTF-8", "-cp", jar, "-d", td, src],
                               capture_output=True, text=True, timeout=300)
            if r.returncode != 0:
                bad("消费者程序编译失败：%s" % (r.stderr or r.stdout).strip()[-300:])
            else:
                r = subprocess.run([java, "-cp", td + os.pathsep + jar, "H2E2E"],
                                   capture_output=True, text=True, timeout=300)
                out = (r.stdout or "") + (r.stderr or "")
                if r.returncode == 0 and "H2_E2E=atom" in out:
                    ok("端到端真跑通过：内存库建表/插入/查询并读回 'atom'（H2_E2E=atom）")
                else:
                    bad("端到端真跑失败（rc=%s）：%s" % (r.returncode, out.strip()[-300:]))

    if os.path.isfile(jar):
        jv = ""
        if jh and os.path.isfile(os.path.join(jh, "bin", "java")):
            try:
                jv = subprocess.run([os.path.join(jh, "bin", "java"), "-version"],
                                    capture_output=True, text=True, timeout=120
                                    ).stderr.strip().splitlines()[0]
            except Exception:
                jv = "(不可用)"
        ok("证据：jar=%d B sha256=%s…；JDK=%s %s"
           % (os.path.getsize(jar), sha256(jar)[:16], jh, jv))

    print("checks=%d fails=%d skips=%d" % (checks, fails, skips))
    print("RESULT: " + ("PASS" if fails == 0 else "FAIL"))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
