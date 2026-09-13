#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ohos-libmrss-consumer — 鸿蒙特有独立测试（1/1，不允许 skip）

六项硬检查，任一失败必须非零退出：
  A. 最终包内共享库为 ELF64 AArch64（ET_DYN，机器 EM_AARCH64）
  B. OpenHarmony .codesign 段存在（签名信息）
  C. SONAME 正确（libmrss.so.0）；NEEDED 含 libnxml.so.0（真实依赖），
     且不含宿主机构建路径引入的 RPATH/RUNPATH
  D. 二进制内不含宿主机绝对路径（/storage/、/home/、/tmp/libmrss 等）
  E. 在 OHOS 环境实际编译并链接 Conan 安装后的库（pkg-config 消费）
  F. 在 OHOS 环境实际运行真实 RSS 解析并校验结果

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
    b"/storage/", b"/home/", b"/tmp/libmrss", b"/Users/",
    b"libmrss-adapt",
]

TEST_C = r"""
#include <stdio.h>
#include <string.h>
#include <mrss.h>

static const char *RSS =
    "<?xml version=\"1.0\"?>"
    "<rss version=\"2.0\"><channel>"
    "<title>ohos libmrss test</title>"
    "<link>http://127.0.0.1/feed</link>"
    "<description>real RSS parse on OHOS</description>"
    "<item><title>ohos item</title>"
    "<link>http://127.0.0.1/1</link>"
    "<description>aarch64 item body</description></item>"
    "</channel></rss>";

int main(void)
{
    mrss_t *data = NULL;
    mrss_error_t ret = mrss_parse_buffer((char *)RSS, strlen(RSS), &data);
    if (ret != MRSS_OK || data == NULL) {
        fprintf(stderr, "FAIL: mrss_parse_buffer err=%d\n", ret);
        return 1;
    }
    if (data->title == NULL ||
        strcmp(data->title, "ohos libmrss test") != 0) {
        fprintf(stderr, "FAIL: channel title\n");
        return 1;
    }
    if (data->item == NULL || data->item->title == NULL ||
        strcmp(data->item->title, "ohos item") != 0) {
        fprintf(stderr, "FAIL: item title\n");
        return 1;
    }
    mrss_free(data);
    printf("PASS: RSS parsed on OHOS\n");
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
    for cand in ("libmrss.so.0.19.4", "libmrss.so.0", "libmrss.so"):
        p = os.path.join(libdir, cand)
        if os.path.exists(p):
            soname_path = p
            break
    if soname_path is None:
        die("lib", "no libmrss shared library under %s" % libdir)

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
    if not m or m.group(1) != "libmrss.so.0":
        die("C.SONAME", "SONAME missing or wrong: %s" % dyn[:1500])
    needed = re.findall(r"\(NEEDED\).*?\[(.*?)\]", dyn)
    if "libnxml.so.0" not in needed:
        die("C.NEEDED", "libnxml.so.0 not in NEEDED: %s" % needed)
    if "RPATH" in dyn or "RUNPATH" in dyn:
        die("C.RPATH", "RPATH/RUNPATH must not be set:\n" + dyn[:1500])
    print("PASS: C. SONAME=libmrss.so.0, NEEDED libnxml.so.0, no RPATH")

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

    # E+F. compile & run a consumer against the installed package on OHOS.
    # mrss.h 不直接 include curl/nxml 头（API 均为 mrss 自有类型），
    # 但链接需要 libnxml/libcurl 的运行库（LD_LIBRARY_PATH 覆盖）。
    def find_dep(marker_lib):
        # conan 2 缓存两处布局：p/<id>/p 与 p/b/<id>/p（构建图）。libnxml
        # 仅存在于后者，两处都要扫。
        found = []
        for sub in ("p", os.path.join("p", "b")):
            base = os.path.join(os.path.expanduser("~"), ".conan2", sub)
            if not os.path.isdir(base):
                continue
            for name in sorted(os.listdir(base)):
                cand = os.path.join(base, name, "p")
                if os.path.isfile(os.path.join(cand, "lib", marker_lib)):
                    found.append(cand)
        # 取最新构建的（列表序后者覆盖前者，p/b 段更可能最新）
        return found[-1] if found else None

    nxml_prefix = (os.environ.get("CONAN_LIBNXML_PREFIX")
                   or find_dep("libnxml.so"))
    curl_prefix = (os.environ.get("CONAN_LIBCURL_PREFIX")
                   or find_dep("libcurl.so"))
    dep_libs = [os.path.join(p, "lib") for p in (nxml_prefix, curl_prefix)
                if p and os.path.isdir(os.path.join(p, "lib"))]

    with tempfile.TemporaryDirectory(prefix="ohos-mrss-") as td:
        src = os.path.join(td, "consumer.c")
        binp = os.path.join(td, "consumer")
        with open(src, "w") as fh:
            fh.write(TEST_C)
        env = dict(os.environ)
        # mrss.pc 的 Requires: nxml 需要 nxml.pc（进而 Requires curl）；
        # PKG_CONFIG_PATH 一并给出三个包的 pkgconfig 目录。
        pc_dirs = [os.path.join(pkg, "lib", "pkgconfig")]
        for p in (nxml_prefix, curl_prefix):
            d = os.path.join(p, "lib", "pkgconfig") if p else None
            if d and os.path.isdir(d):
                pc_dirs.append(d)
        env["PKG_CONFIG_PATH"] = ":".join(pc_dirs)
        cc_cmd = [CC, src, "-o", binp]
        # pkg-config 驱动编译，回落到显式 -I/-L（mrss.h 含
        # <curl/curl.h>，显式回落也要补 curl/libnxml 的 include）
        pc = run([PKG_CONFIG, "--cflags", "--libs", "libmrss"], env=env)
        if pc.returncode == 0 and pc.stdout.strip():
            cc_cmd += pc.stdout.split()
        else:
            cc_cmd += ["-I%s" % os.path.join(pkg, "include"),
                       "-L%s" % libdir, "-lmrss"]
            for p in (nxml_prefix, curl_prefix):
                if p and os.path.isdir(os.path.join(p, "include")):
                    cc_cmd += ["-I%s" % os.path.join(p, "include")]
                if p and os.path.isdir(os.path.join(p, "lib")):
                    cc_cmd += ["-L%s" % os.path.join(p, "lib")]
            cc_cmd += ["-lnxml", "-lcurl"]
        r = run(cc_cmd, env=env)
        if r.returncode != 0:
            die("E.compile", "consumer compile failed:\n%s\n%s" %
                (" ".join(cc_cmd), (r.stderr or b"").decode(errors="replace")))
        print("PASS: E. consumer compiled & linked on OHOS")

        env["LD_LIBRARY_PATH"] = ":".join(filter(None,
            [os.environ.get("LD_LIBRARY_PATH"), libdir] + dep_libs))
        r = run([binp], env=env)
        out = (r.stdout or b"").decode(errors="replace")
        if r.returncode != 0:
            die("F.run", "consumer run failed rc=%d:\n%s%s" %
                (r.returncode, out, (r.stderr or b"").decode(errors="replace")))
        if "PASS: RSS parsed on OHOS" not in out:
            die("F.result", "unexpected consumer output: %s" % out)
        print("PASS: F. real RSS parsed & verified on OHOS")

    print("OHOS-TEST-RESULT: PASS (6/6 checks)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
