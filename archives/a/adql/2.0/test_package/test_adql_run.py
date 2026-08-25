#!/usr/bin/env python3
"""Conan test_package for adql 2.0 — 真实消费测试。

用法: python3 test_adql_run.py <package_folder> <boost_include_dir>
验证:
1. 编译 test_adql.cpp（clang++ -I pkg/include -I boost/include
   -L pkg/lib -ladql_query）——验证库可被消费方编译链接
2. 运行 test_adql——解析 ADQL SELECT 查询 + round-trip 验证
3. 运行包内 bin/parse_adql（上游 test/parse_adql.cxx 真实测试程序
   ——420 pass + 62 fail 用例，rc=0 即全部通过）
"""
import os
import shutil
import subprocess
import sys

PASS = "PASS:"
NOTE = "NOTE:"
FAIL = "FAIL:"


def main():
    pkg_folder = sys.argv[1]
    boost_inc = sys.argv[2] if len(sys.argv) > 2 else ""
    bindir = os.path.join(pkg_folder, "bin")
    libdir = os.path.join(pkg_folder, "lib")
    incdir = os.path.join(pkg_folder, "include")
    failures = 0

    # 1. 库与头文件存在
    lib = os.path.join(libdir, "libadql_query.so")
    hdr = os.path.join(incdir, "ADQL", "Query.hxx")
    if not os.path.isfile(lib):
        print(f"{FAIL} libadql_query.so 缺失")
        failures += 1
    else:
        print(f"{PASS} libadql_query.so 存在")
    if not os.path.isfile(hdr):
        print(f"{FAIL} ADQL/Query.hxx 缺失")
        failures += 1
    else:
        print(f"{PASS} ADQL/Query.hxx 存在")

    # 2. 编译 + 运行 test_adql.cpp（真实消费）
    # CI 的 conanrun 环境可能设 CXX=clang++（相对名）——不能直接取用，
    # 候选列表逐个 isfile 校验（绝对路径优先，本地/CI 均可用——
    # ccapi #6498 同款修复）
    cc = ""
    for cand in ("/data/service/hnp/bin/clang++",
                 "/storage/Users/currentUser/usr/local/bin/clang++",
                 os.environ.get("CXX") or "",
                 shutil.which("clang++") or ""):
        if cand and os.path.isfile(cand):
            cc = cand
            break
    if not cc:
        print(f"{FAIL} clang++ 不在 PATH——编译冒烟无法执行（可消费性验证缺失）")
        sys.exit(1)
    test_dir = os.path.dirname(os.path.abspath(__file__))
    src = os.path.join(test_dir, "test_adql.cpp")
    out = os.path.join(test_dir, "test_adql.out")
    cmd = [cc, "-std=c++17", "-I" + incdir]
    if boost_inc:
        cmd.append("-I" + boost_inc)
    cmd += [src, "-o", out, "-L" + libdir, "-ladql_query"]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    if r.returncode != 0:
        print(f"{FAIL} test_adql.cpp 编译失败（rc={r.returncode}）")
        print((r.stderr or "")[:400])
        failures += 1
    else:
        print(f"{PASS} test_adql.cpp 编译链接通过")
        # 运行（LD_LIBRARY_PATH 指向 lib 目录——OHOS 动态链接器
        # namespace 隔离可能需 rpath，先尝试环境变量）
        env = dict(os.environ)
        env["LD_LIBRARY_PATH"] = libdir + os.pathsep + env.get("LD_LIBRARY_PATH", "")
        r2 = subprocess.run([out], capture_output=True, text=True, timeout=60,
                            env=env)
        print((r2.stdout or "") + (r2.stderr or ""))
        if r2.returncode != 0:
            print(f"{FAIL} test_adql 运行失败（rc={r2.returncode}）")
            failures += 1
        else:
            print(f"{PASS} test_adql 真实解析 ADQL SELECT 通过")

    # 3. 上游真实测试程序 parse_adql（420 pass + 62 fail 用例）
    pa = os.path.join(bindir, "parse_adql")
    if os.path.isfile(pa):
        r3 = subprocess.run([pa, "-q"], capture_output=True, text=True,
                            timeout=120)
        out3 = (r3.stdout or "") + (r3.stderr or "")
        pass_cnt = out3.count("PASS:")
        fail_cnt = out3.count("FAIL:")
        if r3.returncode != 0 or fail_cnt > 0:
            print(f"{FAIL} parse_adql 上游测试失败（rc={r3.returncode}，"
                  f"PASS={pass_cnt} FAIL={fail_cnt}）")
            print(out3[:400])
            failures += 1
        else:
            print(f"{PASS} parse_adql 上游测试全部通过（PASS={pass_cnt}，"
                  f"FAIL={fail_cnt}）")
    else:
        print(f"{NOTE} bin/parse_adql 缺失——跳过上游测试")

    if failures > 0:
        print(f"{FAIL} {failures} 项检查失败")
        sys.exit(1)
    print("ALL PASS")
    sys.exit(0)


if __name__ == "__main__":
    main()
