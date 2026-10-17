#!/usr/bin/env python3
"""test_ohos — meojson 5.1.2 HarmonyOS PC 专项验证.

在真实鸿蒙 PC（aarch64, musl）上对最终 Conan 包做独立专项检查。
本目录完全自包含（不依赖兄弟 test_package 目录，可被单独复制/执行）：

  T1  aarch64 ELF 验证（消费者可执行文件为 ELF64 AArch64）
  T2  musl libc（无 glibc / 无 ld-linux）
  T3  .codesign 段存在（OHOS 签名管线产出）
  T4  无宿主绝对路径泄漏（含 RPATH/RUNPATH 检查）
  T5  真实 JSON 解析/序列化验证（仅公开头文件与公开 API，非伪造输出）

用法：python3 run_ohos_test.py <conan_package_folder>
退出码：0=全部通过；非 0=有失败（打印首个错误）。
"""
import os
import subprocess
import sys
import tempfile

READELF = os.environ.get("READELF", "readelf")
CC = os.environ.get("CC", "clang")
STRINGS = os.environ.get("STRINGS", "strings")

HOST_PATH_RES = [b"/storage/", b"/home/", b"/Users/", b"meojson-5.1.2"]

TEST_CPP = r"""
// meojson 5.1.2 OHOS 专项验证：仅使用已安装公开头文件 <meojson/json.hpp>
// 与公开 API（json::parse / json::value / as_* / dumps），对真实业务形态的
// JSON 数据做解析→访问→再序列化 roundtrip，任一断言失败返回非零。
#include <iostream>
#include <string>

#include <meojson/json.hpp>

namespace
{
int checks = 0;
int failures = 0;

void check(bool cond, const char* what)
{
    ++checks;
    if (!cond) {
        std::cerr << "FAIL: " << what << std::endl;
        ++failures;
    }
}
} // namespace

int main()
{
    // 模拟业务组件读取一份带嵌套、数组、布尔、浮点、转义字符串的 JSON 配置。
    const std::string config = R"({
        "app": "meojson-ohos",
        "enabled": true,
        "max_retries": 5,
        "timeout_ms": 1250.5,
        "backends": ["local", "remote"],
        "nested": { "path": "C:\\temp\\file.json", "unicode": "\u4f60\u597d" },
        "empty_arr": [],
        "null_val": null
    })";

    auto parsed = json::parse(config);
    check(parsed.has_value(), "parse top-level object");
    if (!parsed) {
        std::cerr << "FATAL: cannot parse config" << std::endl;
        return 2;
    }
    json::value v = *parsed;

    check(v["app"].as_string() == "meojson-ohos", "app string");
    check(v["enabled"].as_boolean() == true, "enabled bool");
    check(v["max_retries"].as_integer() == 5, "max_retries int");
    check(v["timeout_ms"].as_double() == 1250.5, "timeout_ms double");
    check(v["backends"].as_array().size() == 2, "backends size");
    check(v["backends"][1].as_string() == "remote", "backends[1]");
    check(v["nested"]["path"].as_string() == "C:\\temp\\file.json", "nested path escapes");
    check(v["nested"]["unicode"].as_string() == "\xe4\xbd\xa0\xe5\xa5\xbd", "nested unicode utf-8");
    check(v["empty_arr"].as_array().empty(), "empty array");
    check(v["null_val"].is_null(), "null value");

    // 修改并 roundtrip 序列化，再解析核对。
    v["app"] = "meojson-ohos-v2";
    v["added"] = json::array { 1, 2, 3 };
    std::string dumped = v.dumps(2);
    auto again = json::parse(dumped);
    check(again.has_value(), "reparse roundtrip");
    if (again) {
        check((*again)["app"].as_string() == "meojson-ohos-v2", "roundtrip app");
        check((*again)["added"].as_array().size() == 3, "roundtrip added array");
        check((*again)["added"][2].as_integer() == 3, "roundtrip added[2]");
    }

    if (failures == 0) {
        std::cout << "OHOS_MEOJSON_TESTS_PASS checks=" << checks << std::endl;
        return 0;
    }
    std::cerr << "OHOS_MEOJSON_TESTS_FAIL failures=" << failures << "/" << checks << std::endl;
    return 1;
}
"""


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: run_ohos_test.py <conan_package_folder>", file=sys.stderr)
        return 2
    pkg = sys.argv[1]
    include = os.path.join(pkg, "include")

    # R10: 临时目录必须显式用 $TMPDIR（鸿蒙 /tmp 只读，gettempdir 回退不可靠）。
    work_base = os.environ.get("TMPDIR") or os.path.expanduser("~/tmp")
    os.makedirs(work_base, exist_ok=True)
    work = tempfile.mkdtemp(prefix="meojson-test-ohos-", dir=work_base)
    src = os.path.join(work, "test_ohos.cpp")
    with open(src, "w") as f:
        f.write(TEST_CPP)
    exe = os.path.join(work, "test_ohos")

    # 编译 + 链接（仅公开头文件；header-only 库无需 -L/-l）
    comp = subprocess.run(
        [CC, "-O2", "-std=c++17", "-I", include, src, "-o", exe],
        capture_output=True, text=True)
    if comp.returncode != 0:
        print("FAIL: compile/link failed:\n" + comp.stderr, file=sys.stderr)
        return 1

    # T1: ELF64 AArch64
    r = subprocess.run([READELF, "-h", exe], capture_output=True)
    if b"ELF64" not in r.stdout or b"AArch64" not in r.stdout:
        print("FAIL: not ELF64 AArch64", file=sys.stderr)
        return 1

    # T2: musl libc（NEEDED 中无 glibc / ld-linux）
    r = subprocess.run([READELF, "-d", exe], capture_output=True)
    if b"GLIBC" in r.stdout or b"ld-linux" in r.stdout:
        print("FAIL: glibc/ld-linux detected", file=sys.stderr)
        return 1

    # T3: .codesign 段存在（OHOS 签名管线产出）
    r = subprocess.run([READELF, "-S", exe], capture_output=True)
    if b".codesign" not in r.stdout:
        print("FAIL: .codesign section missing", file=sys.stderr)
        return 1

    # T4: 无宿主机绝对路径
    st = subprocess.run([STRINGS, exe], capture_output=True)
    for pat in HOST_PATH_RES:
        if pat in st.stdout:
            print("FAIL: host path leak: %s" % pat.decode(), file=sys.stderr)
            return 1

    # T5: 真实运行（真实 JSON 解析/序列化断言）
    run = subprocess.run([exe], capture_output=True, text=True)
    if run.returncode != 0:
        print("FAIL: test run failed rc=%d:\n%s%s" % (run.returncode, run.stdout, run.stderr), file=sys.stderr)
        return 1
    print(run.stdout, end="")
    if "OHOS_MEOJSON_TESTS_PASS" not in run.stdout:
        print("FAIL: test did not report PASS", file=sys.stderr)
        return 1

    print("TEST_OHOS_ALL_PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
