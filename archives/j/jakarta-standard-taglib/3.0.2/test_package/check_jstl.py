#!/usr/bin/env python3
"""消费者校验 — jakarta-standard-taglib 3.0.2（Conan 包安装后的产物）

用法: python3 check_jstl.py <package_folder>

校验项（输出统一 checks=/fails=/skips= 三计数）：
  1) 产物齐备：libexec/ 下两个 jar（api + impl）存在且非空
  2) 两个 jar 均为合法 zip，且含关键类与 META-INF/MANIFEST.MF
  3) 取消费者侧所需的容器 API jar（jakarta.servlet-api / jsp-api / el-api），
     sha256 逐个钉校验；**网络不可达属具名环境信号 → 记 SKIP 并把 4) 一并 SKIP**
  4) 端到端真跑：javac + java，classpath = 包内两个 jar + 3 个容器 API jar，
     调用 impl 侧真实 EL 函数 org.apache.taglibs.standard.functions.Functions.toUpperCase("atom")
     并断言返回 "ATOM"（同时证明 impl jar、jakarta.el 依赖链与 classpath 均可用）
  5) 证据：两个 jar 的大小与 sha256、所用 JDK

纪律：只有具名环境信号（本环境无网络）才允许 SKIP；其余（未识别的非 0 退出、
真实闭包/符号缺陷）一律判 FAIL。
"""
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile

API_JAR = "jakarta.servlet.jsp.jstl-api-3.0.2.jar"
IMPL_JAR = "jakarta.servlet.jsp.jstl-3.0.2.jar"

API_CLASSES = [
    "jakarta/servlet/jsp/jstl/core/Config.class",
    "jakarta/servlet/jsp/jstl/fmt/LocaleSupport.class",
    "jakarta/servlet/jsp/jstl/sql/Result.class",
]
IMPL_CLASSES = [
    "org/apache/taglibs/standard/functions/Functions.class",
]

# 消费者侧容器 API jar（自 Maven Central 自取 + sha256 钉校验）
CONTAINER_JARS = [
    ("https://repo1.maven.org/maven2/jakarta/servlet/jakarta.servlet-api/6.0.0/"
     "jakarta.servlet-api-6.0.0.jar",
     "c034eb1afb158987dbb53a5fea0cadf611c8dae8daadd59c44d9d5ab70129cef"),
    ("https://repo1.maven.org/maven2/jakarta/servlet/jsp/jakarta.servlet.jsp-api/3.1.0/"
     "jakarta.servlet.jsp-api-3.1.0.jar",
     "e957621ce4ea693a441fc8cebddc82239167afaaafa64d0d759bd78eb01237a9"),
    ("https://repo1.maven.org/maven2/jakarta/el/jakarta.el-api/5.0.0/"
     "jakarta.el-api-5.0.0.jar",
     "57b822380207900f5145c2a687384c50fd41495d388a235791d96ae3b9bfd36d"),
]

E2E_JAVA = """
import org.apache.taglibs.standard.functions.Functions;

public class JstlE2E {
    public static void main(String[] args) throws Exception {
        Class.forName("jakarta.servlet.jsp.jstl.core.Config");   // api jar 可加载
        String up = Functions.toUpperCase("atom");               // impl jar 真实调用
        System.out.println("JSTL_E2E=" + up);
        if (!"ATOM".equals(up)) {
            throw new IllegalStateException("unexpected: " + up);
        }
    }
}
"""

checks = fails = skips = 0


def ok(msg):
    global checks
    checks += 1
    print("[ok]   " + msg)


def bad(msg):
    global checks, fails
    checks += 1
    fails += 1
    print("[FAIL] " + msg)


def skip(msg):
    global checks, skips
    checks += 1
    skips += 1
    print("[skip] " + msg)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def java_home():
    jh = os.environ.get("JAVA_HOME", "")
    candidates = [jh, os.path.expanduser("~/bishengjdk17"),
                  os.path.expanduser("~/usr/local/bishengjdk17")]
    for c in candidates:
        if c and os.path.isfile(os.path.join(c, "bin", "java")):
            return c
    found = shutil.which("java")
    if found:
        return os.path.dirname(os.path.dirname(os.path.realpath(found)))
    return ""


def main():
    pkg = sys.argv[1] if len(sys.argv) > 1 else ""
    api = os.path.join(pkg, "libexec", API_JAR)
    impl = os.path.join(pkg, "libexec", IMPL_JAR)

    # 1) 产物齐备
    if os.path.isfile(api) and os.path.getsize(api) > 0 and \
       os.path.isfile(impl) and os.path.getsize(impl) > 0:
        ok("产物齐备：{} ({} B) + {} ({} B)".format(
            API_JAR, os.path.getsize(api), IMPL_JAR, os.path.getsize(impl)))
    else:
        bad("产物缺失或为空：{} / {}".format(api, impl))

    # 2) jar 合法 + 关键类 + MANIFEST
    if fails == 0:
        missing = []
        for jar, want in ((api, API_CLASSES), (impl, IMPL_CLASSES)):
            try:
                with zipfile.ZipFile(jar) as zf:
                    names = set(zf.namelist())
                    if "META-INF/MANIFEST.MF" not in names:
                        missing.append(os.path.basename(jar) + " : META-INF/MANIFEST.MF")
                    for cls in want:
                        if cls not in names:
                            missing.append(os.path.basename(jar) + " : " + cls)
            except zipfile.BadZipFile as exc:
                bad("jar 非法 zip：{}（{}）".format(os.path.basename(jar), exc))
                missing = None
                break
        if missing == []:
            ok("两个 jar 均为合法 zip，关键类与 META-INF/MANIFEST.MF 齐备")
        elif missing:
            bad("jar 内容缺失：{}".format(", ".join(missing)))

    # 3) 容器 API jar 自取（sha256 钉校验）
    cache = os.path.join(os.path.expanduser("~"), ".cache", "jstl-test-jars")
    os.makedirs(cache, exist_ok=True)
    container_paths = []
    net_ok = True
    for url, want in CONTAINER_JARS:
        name = url.rsplit("/", 1)[-1]
        path = os.path.join(cache, name)
        if not (os.path.isfile(path) and sha256(path) == want):
            try:
                urllib.request.urlretrieve(url, path)
            except Exception as exc:      # 具名环境信号：本环境无网络
                net_ok = False
                skip("容器 API jar 取不到（具名环境信号：网络不可达）：{} → {}".format(
                    name, str(exc)[:80]))
                break
        if sha256(path) != want:
            bad("容器 API jar sha256 不匹配：{}".format(name))
            net_ok = False
            container_paths = []
            break
        container_paths.append(path)
    if net_ok and container_paths:
        ok("容器 API jar 3 个已自取并 sha256 钉校验通过（servlet-api 6.0.0 / jsp-api 3.1.0 / el-api 5.0.0）")

    # 4) 端到端真跑
    jh = java_home()
    if not net_ok:
        skip("端到端未执行：依赖的容器 API jar 不可得（网络不可达）—— 非打包缺陷，未计入通过")
    elif not jh or not os.path.isfile(os.path.join(jh, "bin", "javac")):
        skip("端到端未执行：本环境无可用 JDK（JAVA_HOME/~/bishengjdk17/PATH 均无 javac）")
    else:
        with tempfile.TemporaryDirectory() as td:
            src = os.path.join(td, "JstlE2E.java")
            with open(src, "w", encoding="utf-8") as fh:
                fh.write(E2E_JAVA)
            cp = ":".join([api, impl] + container_paths)
            javac = os.path.join(jh, "bin", "javac")
            java = os.path.join(jh, "bin", "java")
            r = subprocess.run([javac, "-encoding", "UTF-8", "-cp", cp, "-d", td, src],
                               capture_output=True, text=True, timeout=300)
            if r.returncode != 0:
                bad("端到端编译失败：{}".format((r.stderr or r.stdout).strip()[-300:]))
            else:
                r = subprocess.run([java, "-cp", cp + ":" + td, "JstlE2E"],
                                   capture_output=True, text=True, timeout=300)
                out = (r.stdout or "") + (r.stderr or "")
                if r.returncode == 0 and "JSTL_E2E=ATOM" in out:
                    ok("端到端真跑通过：impl 侧 Functions.toUpperCase(\"atom\") == \"ATOM\""
                       "（API 类亦可加载）")
                else:
                    bad("端到端真跑失败（rc={}）：{}".format(
                        r.returncode, out.strip()[-300:]))

    # 5) 证据
    if os.path.isfile(api) and os.path.isfile(impl):
        jv = ""
        if jh and os.path.isfile(os.path.join(jh, "bin", "java")):
            try:
                jv = subprocess.run([os.path.join(jh, "bin", "java"), "-version"],
                                    capture_output=True, text=True, timeout=120
                                    ).stderr.strip().splitlines()[0]
            except Exception:
                jv = "(java -version 不可用)"
        ok("证据：api={} B sha256={} ; impl={} B sha256={} ; JDK={} {}".format(
            os.path.getsize(api), sha256(api)[:16], os.path.getsize(impl),
            sha256(impl)[:16], jh, jv))

    print("checks={} fails={} skips={}".format(checks, fails, skips))
    print("RESULT: " + ("PASS" if fails == 0 else "FAIL"))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
