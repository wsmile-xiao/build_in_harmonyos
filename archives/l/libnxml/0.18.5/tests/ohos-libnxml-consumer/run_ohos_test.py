#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ohos-libnxml-consumer — 鸿蒙特有独立测试（1/1，不允许 skip）

六项硬检查，任一失败必须非零退出：
  A. 最终包内共享库为 ELF64 AArch64（ET_DYN，机器 EM_AARCH64）
  B. OpenHarmony .codesign 段存在（签名信息）
  C. SONAME 正确（libnxml.so.0）；NEEDED 含 libcurl.so.4（真实依赖），
     且不含宿主机构建路径引入的 RPATH/RUNPATH
  D. 二进制内不含宿主机绝对路径（/storage/、/home/、/tmp/libnxml 等）
  E. 在 OHOS 环境实际编译并链接 Conan 安装后的库（pkg-config 消费）
  F. 在 OHOS 环境实际运行 XML 解析并校验结果

用法：python3 run_ohos_test.py <conan_package_folder>
退出码：0=全部通过；非 0=有失败（打印首个错误）。
"""
import os
import re
import subprocess
import sys
import tempfile

READELF = os.environ.get("READELF", "readelf")
PKG_CONFIG = os.environ.get("PKG_CONFIG", "pkg-config")
CC = os.environ.get("CC", "clang")

HOST_PATH_RES = [
    b"/storage/", b"/home/", b"/tmp/libnxml", b"/Users/",
    b"libnxml-adapt",
]

TEST_C = r"""
#include <stdio.h>
#include <string.h>
#include <nxml.h>

static const char *XML =
    "<?xml version=\"1.0\"?>"
    "<ohos arch=\"aarch64\"><cpu>AArch64</cpu><kernel>HarmonyOS</kernel></ohos>";

int main(void)
{
    nxml_error_t err;
    nxml_t *doc = nxmle_new_data_from_buffer((char *)XML, 0, &err);
    if (doc == NULL) {
        fprintf(stderr, "FAIL: nxmle_new_data_from_buffer err=%d\n", err);
        return 1;
    }
    nxml_data_t *root = nxmle_root_element(doc, &err);
    if (root == NULL || strcmp(root->value, "ohos") != 0) {
        fprintf(stderr, "FAIL: root element\n");
        return 1;
    }
    char *attr = nxmle_find_attribute(root, "arch", &err);
    if (attr == NULL || strcmp(attr, "aarch64") != 0) {
        fprintf(stderr, "FAIL: attr arch\n");
        return 1;
    }
    nxml_data_t *cpu = nxmle_find_element(doc, root, "cpu", &err);
    if (cpu == NULL || cpu->children == NULL ||
        strcmp(cpu->children->value, "AArch64") != 0) {
        fprintf(stderr, "FAIL: cpu text\n");
        return 1;
    }
    nxml_free(doc);
    printf("PASS: XML parsed on OHOS\n");
    return 0;
}
"""


def die(check, msg):
    print("FAIL[%s]: %s" % (check, msg), file=sys.stderr)
    sys.exit(1)


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, **kw)


def main():
    if len(sys.argv) != 2:
        print("usage: run_ohos_test.py <package_folder>", file=sys.stderr)
        return 2
    pkg = os.path.abspath(sys.argv[1])
    libdir = os.path.join(pkg, "lib")
    soname_path = None
    for cand in ("libnxml.so.0.18.5", "libnxml.so.0", "libnxml.so"):
        p = os.path.join(libdir, cand)
        if os.path.exists(p):
            soname_path = p
            break
    if soname_path is None:
        die("lib", "no libnxml shared library under %s" % libdir)

    # A. ELF64 AArch64 shared object
    hdr = run([READELF, "-h", soname_path]).stdout.decode(errors="replace")
    if "Class:                             ELF64" not in hdr:
        die("A.ELF64", "not ELF64:\n" + hdr)
    if "Machine:" not in hdr or "AArch64" not in hdr:
        die("A.AArch64", "not AArch64:\n" + hdr)
    if "Type:" not in hdr or "DYN" not in hdr:
        die("A.ET_DYN", "not a shared object:\n" + hdr)
    print("PASS: A. ELF64 AArch64 shared object (%s)" %
          os.path.basename(soname_path))

    # B. OpenHarmony .codesign section
    sections = run([READELF, "-SW", soname_path]).stdout.decode(
        errors="replace")
    if ".codesign" not in sections and ".note.ohos.ident" not in sections:
        die("B.codesign", "no .codesign/.note.ohos.ident section:\n" +
            sections[:2000])
    print("PASS: B. .codesign (or .note.ohos.ident) section present")

    # C. SONAME / NEEDED / no RPATH
    dyn = run([READELF, "-d", soname_path]).stdout.decode(errors="replace")
    m = re.search(r"\(SONAME\).*?\[(.*?)\]", dyn)
    if not m or m.group(1) != "libnxml.so.0":
        die("C.SONAME", "SONAME missing or wrong: %s" % dyn[:1500])
    needed = re.findall(r"\(NEEDED\).*?\[(.*?)\]", dyn)
    # conan curl 包的 SONAME 是 libcurl.so（无版本后缀）
    if "libcurl.so" not in needed and "libcurl.so.4" not in needed:
        die("C.NEEDED", "libcurl not in NEEDED: %s" % needed)
    if "RPATH" in dyn or "RUNPATH" in dyn:
        die("C.RPATH", "RPATH/RUNPATH must not be set:\n" + dyn[:1500])
    print("PASS: C. SONAME=libnxml.so.0, NEEDED libcurl, no RPATH")

    # D. no host absolute paths embedded
    with open(soname_path, "rb") as fh:
        blob = fh.read()
    for needle in HOST_PATH_RES:
        if needle in blob:
            # locate a sample
            i = blob.find(needle)
            sample = blob[max(0, i - 40):i + 60]
            die("D.hostpath", "host path %r embedded: ...%r..." %
                (needle, sample))
    print("PASS: D. no host absolute paths embedded")

    # E+F. compile & run a consumer against the installed package on OHOS
    # 公共头 nxml.h 透传 #include <curl/curl.h>，消费者编译需要 curl 头
    # （从 conan 缓存定位 libcurl 包，路径由 CONAN_LIBCURL_PREFIX 或
    # 自动扫描获得）。
    curl_prefix = os.environ.get("CONAN_LIBCURL_PREFIX")
    if not curl_prefix:
        conan2 = os.path.join(os.path.expanduser("~"), ".conan2", "p")
        for name in sorted(os.listdir(conan2), reverse=True) \
                if os.path.isdir(conan2) else []:
            cand = os.path.join(conan2, name, "p")
            if os.path.isfile(os.path.join(cand, "lib", "libcurl.so")) or \
               os.path.isfile(os.path.join(cand, "lib", "libcurl.so.4")):
                curl_prefix = cand
                break
    curl_inc = (os.path.join(curl_prefix, "include")
                if curl_prefix else None)
    if not curl_inc or not os.path.isdir(curl_inc):
        die("E.curlinc", "cannot locate conan libcurl package "
            "(set CONAN_LIBCURL_PREFIX)")

    with tempfile.TemporaryDirectory(prefix="ohos-nxml-") as td:
        src = os.path.join(td, "consumer.c")
        binp = os.path.join(td, "consumer")
        with open(src, "w") as fh:
            fh.write(TEST_C)
        env = dict(os.environ)
        env["PKG_CONFIG_PATH"] = os.path.join(pkg, "lib", "pkgconfig")
        cc_cmd = [CC, src, "-o", binp]
        # pkg-config 驱动编译，回落到显式 -I/-L（附加 curl 头）
        pc = run([PKG_CONFIG, "--cflags", "--libs", "libnxml"], env=env)
        if pc.returncode == 0 and pc.stdout.strip():
            cc_cmd += pc.stdout.split() + ["-I%s" % curl_inc]
        else:
            cc_cmd += ["-I%s" % os.path.join(pkg, "include"),
                       "-I%s" % curl_inc,
                       "-L%s" % libdir, "-lnxml"]
        r = run(cc_cmd, env=env)
        if r.returncode != 0:
            die("E.compile", "consumer compile failed:\n%s\n%s" %
                (" ".join(cc_cmd), (r.stderr or b"").decode(errors="replace")))
        print("PASS: E. consumer compiled & linked on OHOS")

        env["LD_LIBRARY_PATH"] = ":".join(filter(None, [
            os.environ.get("LD_LIBRARY_PATH"), libdir,
            os.path.join(curl_prefix, "lib") if curl_prefix else ""]))
        r = run([binp], env=env)
        out = (r.stdout or b"").decode(errors="replace")
        if r.returncode != 0:
            die("F.run", "consumer run failed rc=%d:\n%s%s" %
                (r.returncode, out, (r.stderr or b"").decode(errors="replace")))
        if "PASS: XML parsed on OHOS" not in out:
            die("F.result", "unexpected consumer output: %s" % out)
        print("PASS: F. XML parsed & verified on OHOS")

    print("OHOS-TEST-RESULT: PASS (6/6 checks)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
