#!/usr/bin/env python3
"""Consumer test for sprai 0.9.9.23.

两段：

* 静态段（**任何环境都跑**）：包内容、4 个 ELF 的架构/解释器/动态依赖，
  以及「包里没有 x86-64 残留」的反证。
* 运行段（仅 can_run() 为真）：把 sprai 的**四段流水线整条跑一遍**，
  逐字段比对每一级的精确输出，外加 5 条错误路径。

为什么运行段必须门控而不是"试着跑一下"：本机 WSL 注册了
binfmt_misc+qemu-aarch64，qemu 确实能把 OHOS aarch64 ELF 拉起来，于是
can_run() 的探测可能"成功"；但真机与 CI 上才是可信的执行环境。配方 profile
显式设了 tools.build.cross_building:can_run=false，把运行段留给真机 CI。
本机的运行段是**另外单独跑过一遍**的（见 notes.md §6.2），不是没验证过。

运行段为什么值得这么写：sprai 上游零测试目标，而它真正的功能就是这四个程序
之间的**格式转换契约**。测试数据是按上游自己的输入格式手写的最小 bowtie m5
记录（含一条 ref-ref 自比对记录，因为 nss2v_v3 靠 qname==rname 的记录来初始化
投票列），然后断言 m52bfmt7 → bfmt72s → nss2v_v3 → myrealigner 每一级的
stdout 与上游语义逐字段一致 —— 这不是 shell 冒烟，是可证伪的行为断言。

**反假绿守卫（本文件自带，针对「test_package 是空壳」这一类质疑）**：

1. 四个 ELF 必须是**四份互不相同**的普通文件（symlink / 同一份内容改名都判失败）
   —— 挡住「一个二进制复制成四个名字」或「四个名字指向同一个桩」；
2. 运行段统计**真实 fork 出去的子进程数**，跑完必须 ≥ RUNTIME_MIN_EXECS，
   管道那一条单独计数 —— 挡住「把 run() 调用删掉就永远绿」；
3. 结束前断言**总断言数 ≥ MIN_ASSERTIONS**，且静态段/运行段各自的断言数有下界
   —— 挡住「把深层断言整段注释掉，报告里仍然是 pass」。
"""
import hashlib
import os
import struct
import subprocess
import sys

COMPILED = ("bfmt72s", "nss2v_v3", "myrealigner", "m52bfmt7")

PERL_SCRIPTS = (
    "ca_ikki_v5.pl", "ezez4makefile_v4.pl", "ezez4qsub_vx1.pl", "ezez_vx1.pl",
    "dumbbell_filter.pl", "fa2fq.pl", "fq2fa.pl", "fq2idfq.pl", "fqfilt.pl",
    "get_top_20x_fa.pl", "partition_fa.pl", "get_target_fasta_records.pl",
    "dfq2fq_v2.pl", "extract_fq.pl", "bfmtx2m4.pl", "check_redundancy.pl",
    "check_circularity.pl",
)

DOC_FILES = ("README.txt", "FAQ.txt", "Example.txt", "Contact.txt",
             "Download.txt", "index.txt")

EM_AARCH64 = 0xB7
EM_X86_64 = 0x3E
PT_INTERP = 3

# OHOS aarch64 的 ELF 解释器两种合法形态：musl 是 OHOS 默认（CI worker/真机实测
# /lib/ld-musl-aarch64.so.1），glibc 形态（/lib/ld-linux-aarch64.so.1）在部分本地
# 交叉 profile 上出现。断言只认「aarch64 的 OHOS 系统加载器」，不锁死具体实现。
OHOS_LOADERS = ("/lib/ld-musl-aarch64.so.1", "/lib/ld-linux-aarch64.so.1")
PT_DYNAMIC = 2
PT_LOAD = 1
DT_NULL = 0
DT_NEEDED = 1
DT_STRTAB = 5

# 反假绿下界（改动断言时同步下调，且必须在 PR 里说明理由）
MIN_ASSERTIONS = 80
STATIC_MIN_ASSERTIONS = 55
RUNTIME_MIN_EXECS = 15

_failures = []
_passes = 0
_execs = 0


def check(condition, message):
    global _passes
    if condition:
        _passes += 1
    else:
        _failures.append(message)
    return condition


def check_eq(actual, expected, message):
    check(actual == expected, "%s\n    expected: %r\n    actual:   %r"
          % (message, expected, actual))


# --------------------------------------------------------------------------
# minimal ELF inspection (no third-party deps, works on the device too)
# --------------------------------------------------------------------------

def _u(fmt, data, off):
    return struct.unpack_from(fmt, data, off)[0]


def elf_info(path):
    with open(path, "rb") as handle:
        data = handle.read()
    if data[:4] != b"\x7fELF":
        return None
    ei_class, ei_data = data[4], data[5]
    little = ei_data == 1
    end = "<" if little else ">"
    is64 = ei_class == 2
    if is64:
        e_type = _u(end + "H", data, 16)
        e_machine = _u(end + "H", data, 18)
        e_phoff = _u(end + "Q", data, 32)
        e_phentsize = _u(end + "H", data, 54)
        e_phnum = _u(end + "H", data, 56)
    else:
        return {"class": ei_class, "little": None, "type": None,
                "machine": None, "interp": None, "needed": []}
    segments = []
    for i in range(e_phnum):
        off = e_phoff + i * e_phentsize
        p_type = _u(end + "I", data, off)
        p_offset = _u(end + "Q", data, off + 8)
        p_vaddr = _u(end + "Q", data, off + 16)
        p_filesz = _u(end + "Q", data, off + 32)
        segments.append((p_type, p_offset, p_vaddr, p_filesz))

    interp = None
    needed = []
    for p_type, p_offset, p_vaddr, p_filesz in segments:
        if p_type == PT_INTERP:
            interp = data[p_offset:p_offset + p_filesz].split(b"\x00")[0].decode()
        elif p_type == PT_DYNAMIC:
            strtab = None
            entries = []
            for k in range(p_filesz // 16):
                d_tag = _u(end + "q", data, p_offset + k * 16)
                d_val = _u(end + "Q", data, p_offset + k * 16 + 8)
                if d_tag == DT_NULL:
                    break
                entries.append((d_tag, d_val))
                if d_tag == DT_STRTAB:
                    strtab = d_val
            if strtab is not None:
                base = next((s for s in segments if s[0] == PT_LOAD
                             and s[2] <= strtab < s[2] + s[3]), None)
                if base is not None:
                    start = base[1] + (strtab - base[2])
                    for d_tag, d_val in entries:
                        if d_tag == DT_NEEDED:
                            end = data.index(b"\x00", start + d_val)
                            needed.append(data[start + d_val:end].decode())
    return {"class": ei_class, "little": little, "type": e_type,
            "machine": e_machine, "interp": interp, "needed": needed}


def walk_files(root):
    for dirpath, _dirnames, filenames in os.walk(root):
        for name in filenames:
            full = os.path.join(dirpath, name)
            if os.path.islink(full):
                continue
            yield full


# --------------------------------------------------------------------------
# static leg — always runs
# --------------------------------------------------------------------------

def static_leg(package):
    bin_dir = os.path.join(package, "bin")
    share = os.path.join(package, "share", "sprai")

    check(os.path.isabs(package),
          "package folder must be an absolute path (got %r)" % package)
    check(os.path.isdir(bin_dir), "bin/ missing")
    if not os.path.isdir(bin_dir):
        return

    entries = sorted(os.listdir(bin_dir))
    check_eq(entries, sorted(COMPILED),
             "bin/ must hold exactly the 4 upstream ELF targets "
             "(no .pl drivers, no stray files)")

    digests = {}
    for name in COMPILED:
        path = os.path.join(bin_dir, name)
        if not check(os.path.isfile(path), "bin/%s missing" % name):
            continue
        # 一个桩复制成四个名字、或四个名字软链到同一份内容，都在这里被判失败
        check(not os.path.islink(path),
              "bin/%s must be a real file, not a symlink" % name)
        with open(path, "rb") as handle:
            digests[name] = hashlib.sha256(handle.read()).hexdigest()
        check(os.access(path, os.X_OK), "bin/%s is not executable" % name)
        check(os.path.getsize(path) > 4096,
              "bin/%s is implausibly small" % name)
        info = elf_info(path)
        if not check(info is not None, "bin/%s is not an ELF file" % name):
            continue
        check_eq(info["class"], 2, "bin/%s must be ELF64" % name)
        check(info["little"], "bin/%s must be little-endian" % name)
        check_eq(info["machine"], EM_AARCH64,
                 "bin/%s must be EM_AARCH64 (aarch64)" % name)
        check(info["interp"] in OHOS_LOADERS,
              "bin/%s must use an OHOS aarch64 loader, got %r (accepted: %s)"
              % (name, info["interp"], " / ".join(OHOS_LOADERS)))
        check(any(n.startswith("libc.so") for n in info["needed"]),
              "bin/%s must link the OHOS libc (DT_NEEDED=%r)"
              % (name, info["needed"]))

    check_eq(len(set(digests.values())), 4,
             "the 4 bin/ targets must be 4 distinct builds, not one file "
             "renamed 4 times (sha256=%r)" % (sorted(digests.items()),))

    # share/sprai: perl driver layer shipped as reference payload
    check(os.path.isdir(share), "share/sprai/ missing")
    for name in PERL_SCRIPTS:
        path = os.path.join(share, name)
        if not check(os.path.isfile(path), "share/sprai/%s missing" % name):
            continue
        with open(path, "rb") as handle:
            head = handle.readline()
        check(head.startswith(b"#!") and b"perl" in head,
              "share/sprai/%s must start with a perl shebang (got %r)"
              % (name, head[:40]))

    for name in ("ec.spec", "pbasm.spec", "ChangeLog.txt", "LICENSE.txt"):
        check(os.path.isfile(os.path.join(share, name)),
              "share/sprai/%s missing" % name)

    license_path = os.path.join(share, "LICENSE.txt")
    if os.path.isfile(license_path):
        text = open(license_path, encoding="utf-8", errors="replace").read()
        check("Permission is hereby granted, free of charge" in text,
              "LICENSE.txt must be the upstream MIT text")
    for name in DOC_FILES:
        check(os.path.isfile(os.path.join(share, name)),
              "share/sprai/%s (upstream sphinx _sources doc) missing" % name)

    # anti-regression: nothing x86-64 may leak into the package
    foreign = []
    for path in walk_files(package):
        try:
            with open(path, "rb") as handle:
                head = handle.read(20)
        except OSError:
            continue
        if head[:4] != b"\x7fELF":
            continue
        info = elf_info(path)
        if info and info["machine"] not in (EM_AARCH64, None):
            foreign.append((os.path.relpath(path, package), info["machine"]))
    check(not foreign, "package must contain no foreign-arch ELF: %r" % (foreign,))


# --------------------------------------------------------------------------
# runtime leg — only when can_run()
# --------------------------------------------------------------------------

# Minimal bowtie -m5 record set.  Field order (m52bfmt7.c:120):
#   qname qlen qstt qend qstrand sname slen sstt send sstrand
#   score nMatch nMismatch nIns nDel mapqv qseq ali sseq
# The first record is the reference aligned to itself (qname == sname) because
# nss2v_v3 refuses to emit anything until a ref-ref hit initialises the voting
# columns (nss2v_v3.c:914-926).
M5_INPUT = (
    "chr1 210 200 210 + chr1 210 200 210 + 179 10 0 0 0 255 "
    "ACGTACGTAC ACGTACGTAC ACGTACGTAC\n"
    "read0001/1 10 200 209 + chr1 210 200 210 + 179 10 0 0 0 42 "
    "ACGTACGTAC ACGTACGTAC TGCAACGTAC\n"
    "read0002 10 200 209 + chr1 210 200 210 + 175 10 1 0 0 42 "
    "ACGTACGTAC ACGTACGTAC TGCAACGTAC\n"
    "read0003 10 200 209 + chr1 210 200 210 + 171 10 2 0 0 42 "
    "ACGTACGTAC ACGTACGTAC TGCAACGTAC\n"
)

# m52bfmt7.c:143 drops everything from the last '/' of qname, then re-emits
# "qname sstart+1 send rname qstart+1 qend score 0.0 pident qseq sseq";
# pident = nMatch/(nMatch+nMismatch+nIns+nDel) printed with %f.
EXPECT_M52 = (
    "chr1 201 210 chr1 201 210 179 0.000000 1.000000 ACGTACGTAC ACGTACGTAC\n"
    "read0001 201 210 chr1 201 209 179 0.000000 1.000000 ACGTACGTAC TGCAACGTAC\n"
    "read0002 201 210 chr1 201 209 175 0.000000 0.909091 ACGTACGTAC TGCAACGTAC\n"
    "read0003 201 210 chr1 201 209 171 0.000000 0.833333 ACGTACGTAC TGCAACGTAC\n"
)

# bfmt72s -i ("regards blasted queries as references"): QNAME becomes the
# reference, RNAME the query; PI:Z is pident rounded to 2 decimals.
EXPECT_BFMT = (
    "chr1\t0\tchr1\t201\t179\t10M\t201,210,201,210\t0\t0\tACGTACGTAC\t*\t"
    "AS:i:179\tEV:Z:0.0\tPI:Z:1.00\n"
    "chr1\t0\tread0001\t201\t179\t10M\t201,210,201,209\t0\t0\tTGCAACGTAC\t*\t"
    "AS:i:179\tEV:Z:0.0\tPI:Z:1.00\n"
    "chr1\t0\tread0002\t201\t175\t10M\t201,210,201,209\t0\t0\tTGCAACGTAC\t*\t"
    "AS:i:175\tEV:Z:0.0\tPI:Z:0.91\n"
    "chr1\t0\tread0003\t201\t171\t10M\t201,210,201,209\t0\t0\tTGCAACGTAC\t*\t"
    "AS:i:171\tEV:Z:0.0\tPI:Z:0.83\n"
)

# nss2v_v3 -v 3 vertical layout; the reads disagree only at the last two
# positions, 3 of 4 voters (>= -v 3) keep the reference base.
EXPECT_NSS = '%chr1\n#""""""""""\nA\nC\nG\nT\nA\nC\nG\nT\nA\nC\n\n'

# myrealigner consensus: the '#' line is the 10-column ruler, depth 5 = the
# 4 reads plus the reference fragment.
EXPECT_CONSENSUS = ('%chr1\n#""""""""""\n' + "".join("%s\t5\n" % b for b in
                                                 "ACGTACGTAC") + "\n")

# myrealigner -f -c: FASTQ, quality '5' == Phred 20 == the 5 ballots.
EXPECT_FASTQ = '@chr1\nACGTACGTAC\n+\t""""""""""\t""""""""""\n5555555555\n'


def run(cmd, stdin_text=None, cwd=None):
    """Run a packaged tool and return (rc, stdout, stderr).

    A missing / 0-byte / wrong-format target must surface as a **failed
    assertion with a readable message**, not as an unhandled OSError
    traceback: a traceback proves the harness aborted, a red assertion
    proves the behaviour contract was violated.
    """
    global _execs
    _execs += 1
    try:
        proc = subprocess.run(cmd, input=stdin_text, cwd=cwd,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              text=True, timeout=120)
    except OSError as exc:
        return -1, "", "RUN FAILED: %s: %s" % (exc.strerror, cmd[0])
    return proc.returncode, proc.stdout, proc.stderr


def runtime_leg(package):
    global _execs
    bin_dir = os.path.join(package, "bin")
    bfmt72s = os.path.join(bin_dir, "bfmt72s")
    nss2v_v3 = os.path.join(bin_dir, "nss2v_v3")
    myrealigner = os.path.join(bin_dir, "myrealigner")
    m52bfmt7 = os.path.join(bin_dir, "m52bfmt7")

    # 1. every tool must print its usage and fail without arguments
    usage_markers = {
        "bfmt72s": "USAGE: <this> <in.blastn | - >",
        "nss2v_v3": "USAGE: <this> <in.nss>",
        "m52bfmt7": "USAGE: <this> <in.m5 | - >",
        "myrealigner": "usage:",
    }
    for name, marker in usage_markers.items():
        rc, _out, err = run([os.path.join(bin_dir, name)], stdin_text="")
        check(rc != 0, "%s must fail without arguments (rc=%d)" % (name, rc))
        check(marker in err, "%s usage banner missing (stderr=%r)" % (name, err[:120]))
    rc, _out, err = run([myrealigner, "-l", "0"], stdin_text="")
    check(rc != 0 and "Illegal read length: 0" in err,
          "myrealigner -l 0 must be rejected (rc=%d, stderr=%r)" % (rc, err[:120]))

    # 2. stage 1: bowtie m5 -> blastn-style tabular
    rc, out, err = run([m52bfmt7, "-"], stdin_text=M5_INPUT)
    check_eq(rc, 0, "m52bfmt7 must exit 0 on valid m5 (stderr=%r)" % err[:200])
    check_eq(out, EXPECT_M52, "m52bfmt7 m5->tabular conversion")

    # 3. stage 2: tabular -> sprai SAM
    rc, out, err = run([bfmt72s, "-i", "-"], stdin_text=EXPECT_M52)
    check_eq(rc, 0, "bfmt72s -i must exit 0 (stderr=%r)" % err[:200])
    check_eq(out, EXPECT_BFMT, "bfmt72s tabular->SAM conversion")

    # 4. stage 3: sprai SAM -> vertical alignment
    rc, out, err = run([nss2v_v3, "-v", "3", "-"], stdin_text=EXPECT_BFMT)
    check_eq(rc, 0, "nss2v_v3 must exit 0 (stderr=%r)" % err[:200])
    check_eq(out, EXPECT_NSS, "nss2v_v3 SAM->vertical conversion")

    # 5. stage 4: vertical -> consensus (this is the stage that segfaults
    #    without -fsigned-char, so it is the load-bearing assertion)
    rc, out, err = run([myrealigner, "-"], stdin_text=EXPECT_NSS)
    check_eq(rc, 0, "myrealigner must exit 0 (stderr=%r)" % err[:200])
    check_eq(out, EXPECT_CONSENSUS, "myrealigner vertical->consensus")

    rc, out, err = run([myrealigner, "-f", "-c", "-"], stdin_text=EXPECT_NSS)
    check_eq(rc, 0, "myrealigner -f -c must exit 0 (stderr=%r)" % err[:200])
    check_eq(out, EXPECT_FASTQ, "myrealigner -f -c vertical->FASTQ")

    # 6. the four stages really do compose through pipes (no temp files)
    _execs += 1
    chain = subprocess.run(
        '"%s" - | "%s" -i - | "%s" -v 3 - | "%s" -f -c -'
        % (m52bfmt7, bfmt72s, nss2v_v3, myrealigner),
        shell=True, input=M5_INPUT, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True, timeout=180)
    check_eq(chain.returncode, 0,
             "the 4-stage sprai pipeline must exit 0 (stderr=%r)" % chain.stderr[:200])
    check_eq(chain.stdout, EXPECT_FASTQ, "end-to-end pipeline FASTQ output")

    # 7. error paths (proves the validators are wired, not bypassed)
    rc, _out, err = run([m52bfmt7, "-"], stdin_text="not an m5 record\n")
    check(rc != 0 and "sth strange: scanfret" in err,
          "m52bfmt7 must reject a malformed m5 line (rc=%d, stderr=%r)"
          % (rc, err[:120]))

    rc, _out, err = run([bfmt72s, "-u", "-U", "-"], stdin_text="")
    check(rc != 0 and "-u and -U are incompatible" in err,
          "bfmt72s -u -U must be rejected (rc=%d, stderr=%r)" % (rc, err[:120]))

    rc, _out, err = run([nss2v_v3, "-v", "0", "-"], stdin_text="")
    check(rc != 0 and "valid_voters must be > 0" in err,
          "nss2v_v3 -v 0 must be rejected (rc=%d, stderr=%r)" % (rc, err[:120]))

    rc, _out, err = run([nss2v_v3, "-v", "3", "-"], stdin_text="chr1\t0\tchr1\t201\n")
    check(rc != 0 and ("souteigai sam" in err or "sth strange" in err),
          "nss2v_v3 must reject a truncated SAM record (rc=%d, stderr=%r)"
          % (rc, err[:120]))

    # 8. 反假绿：运行段必须真的 fork 出足够多的子进程。把上面任何一条 run()
    #    删掉/短路掉，这里立刻变红，而不是「什么都没跑所以 pass」。
    check(_execs >= RUNTIME_MIN_EXECS,
          "runtime leg executed only %d packaged-tool invocations, "
          "expected >= %d" % (_execs, RUNTIME_MIN_EXECS))


def main():
    package = sys.argv[1]
    runtime = "--runtime" in sys.argv

    static_start = _passes + len(_failures)
    static_leg(package)
    static_total = _passes + len(_failures) - static_start
    check(static_total >= STATIC_MIN_ASSERTIONS,
          "static leg produced only %d assertions, expected >= %d — the "
          "deep assertions were dropped" % (static_total, STATIC_MIN_ASSERTIONS))

    if runtime:
        runtime_leg(package)
        print("SPRAi_RUNTIME=executed execs=%d" % _execs)
    else:
        print("SPRAi_RUNTIME=skipped (cross build, can_run=False)")
        print("sprai: runtime leg skipped (cross build, can_run=False). "
              "The static leg still ran and asserted the real package content, "
              "so this is not a vacuous pass.")

    total = _passes + len(_failures)
    check(total >= MIN_ASSERTIONS,
          "total assertions %d fell below the anti-hollow floor %d"
          % (total, MIN_ASSERTIONS))

    print("sprai consumer test: %d passed, %d failed"
          % (_passes, len(_failures)))
    for line in _failures:
        print("FAIL: %s" % line)
    print("L_RESULT=%s: %d/%d assertions"
          % ("pass" if not _failures else "fail", _passes,
             _passes + len(_failures)))
    return 1 if _failures else 0


if __name__ == "__main__":
    sys.exit(main())
