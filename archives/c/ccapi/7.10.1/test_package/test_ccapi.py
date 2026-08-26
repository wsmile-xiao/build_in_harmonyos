#!/usr/bin/env python3
"""消费测试：验证 ccapi 7.10.1 header-only 头文件布局 + 编译冒烟。

ccapi 是 header-only C++ 库（include/ccapi_cpp/*.h），上游 test_unit
（358 用例）需 googletest 网络下载（configure 时）——沙箱网络受限时
如实记录未运行；本测试验证：
1. include/ccapi_cpp/ 目录存在
2. 关键头文件存在（ccapi_session.h 主入口 + ccapi_hmac.h 等）
3. 编译冒烟：小 C++ 程序 include <ccapi_cpp/ccapi_session.h> 编译
   链接（clang++ + openssl 依赖搜索路径）——验证 header 可被消费方
   使用。编译失败 = 头文件/链接依赖不可消费（真实适配缺陷）——
   必须 FAIL exit 1（airview P1：不再无条件 ALL PASS）。
"""
import os
import shutil
import subprocess
import sys
import tempfile

PASS = "PASS:"
NOTE = "NOTE:"
FAIL = "FAIL:"

KEY_HEADERS = ("ccapi_session.h", "ccapi_element.h", "ccapi_event.h",
               "ccapi_hmac.h", "ccapi_logger.h")


def main():
    pkg_folder = sys.argv[1]
    # 依赖 include 目录（openssl/boost/rapidjson）+ openssl lib 目录
    # （conanfile.py 传入，--lib 分隔）
    dep_incs = []
    openssl_lib = ""
    args = sys.argv[2:]
    if "--lib" in args:
        i = args.index("--lib")
        dep_incs = [a for a in args[:i] if a]
        if i + 1 < len(args):
            openssl_lib = args[i + 1]
    else:
        dep_incs = [a for a in args if a]
    inc = os.path.join(pkg_folder, "include", "ccapi_cpp")
    failures = 0

    # 1. include/ccapi_cpp/ 目录存在
    if not os.path.isdir(inc):
        print(f"{FAIL} include/ccapi_cpp/ 目录缺失")
        sys.exit(1)
    print(f"{PASS} include/ccapi_cpp/ 目录存在")

    # 2. 关键头文件存在
    for h in KEY_HEADERS:
        p = os.path.join(inc, h)
        if not os.path.isfile(p):
            print(f"{FAIL} {h} 缺失")
            failures += 1
        else:
            print(f"{PASS} {h} 存在")

    # 3. 编译冒烟：include ccapi_session.h 的小程序（header-only 可消费性）
    #    airview P3：smoke.cc 写临时目录（不污染归档 test_package 目录）
    tmpdir = tempfile.mkdtemp(prefix="ccapi_smoke_")
    smoke = os.path.join(tmpdir, "smoke.cc")
    out = os.path.join(tmpdir, "smoke.out")
    with open(smoke, "w", encoding="utf-8") as f:
        f.write('#include <ccapi_cpp/ccapi_session.h>\n'
                'int main() { ccapi::Session session; return 0; }\n')

    # CI 的 conanrun 环境可能设 CXX=clang++（相对名）——不能直接取用，
    # 候选列表逐个 isfile 校验（绝对路径优先，本地/CI 均可用）
    cc = ""
    for cand in ("/data/service/hnp/bin/clang++",
                 "/storage/Users/currentUser/usr/local/bin/clang++",
                 os.environ.get("CXX") or "",
                 shutil.which("clang++") or ""):
        if cand and os.path.isfile(cand):
            cc = cand
            break
    if not cc:
        # airview P1：clang++ 缺失不能 ALL PASS——FAIL（编译冒烟是
        # header-only 包唯一可消费性验证，无法执行即视为失败）
        print(f"{FAIL} clang++ 不在 PATH——编译冒烟无法执行（可消费性验证缺失）")
        sys.exit(1)

    # airview P3：编译命令携带全部依赖搜索路径（与真实消费者一致）
    cmd = [cc, "-std=c++17", "-I" + os.path.join(pkg_folder, "include")]
    for d in dep_incs:
        if d:
            cmd.append("-I" + d)
    if openssl_lib:
        cmd.append("-L" + openssl_lib)
    cmd += [smoke, "-o", out, "-lssl", "-lcrypto"]

    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        # airview P1：编译失败 = 头文件/链接依赖不可消费（真实适配
        # 缺陷）——必须 FAIL exit 1，不得 ALL PASS
        print(f"{FAIL} 编译冒烟失败（rc={r.returncode}——头文件不可被消费方编译链接）")
        print((r.stderr or "")[:400])
        failures += 1
    else:
        print(f"{PASS} 编译冒烟通过（header-only 可被消费方编译链接）")

    shutil.rmtree(tmpdir, ignore_errors=True)

    if failures > 0:
        print(f"{FAIL} {failures} 项检查失败")
        sys.exit(1)
    print("ALL PASS")
    sys.exit(0)


if __name__ == "__main__":
    main()
