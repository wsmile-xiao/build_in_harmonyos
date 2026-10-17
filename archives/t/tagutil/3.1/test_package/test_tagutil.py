import json
import os
import shutil
import subprocess
import sys


def run(binary, args, cwd):
    result = subprocess.run(
        [binary, *args], cwd=cwd, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise AssertionError("command %r exited %d: %s" %
                             (args, result.returncode, result.stdout))
    return result.stdout


def main():
    if len(sys.argv) not in (4, 5):
        raise SystemExit("usage: test_tagutil.py BINARY PACKAGE_FOLDER BUILD_FOLDER [OHOS]")
    binary, package_folder, build_folder = sys.argv[1:4]
    ohos = len(sys.argv) == 5 and sys.argv[4] == "OHOS"

    result_path = os.path.join(
        package_folder, "share", "tagutil", "upstream-test-result.json")
    with open(result_path, "r", encoding="utf-8") as result_file:
        upstream_result = json.load(result_file)
    if upstream_result.get("status") != "passed":
        raise AssertionError("packaged upstream Cucumber result is not passed")
    print("HMBS_UPSTREAM_TEST_RESULT=" +
          json.dumps(upstream_result, ensure_ascii=False))

    cases = []

    def check(name, args, expected):
        output = run(binary, args, build_folder)
        if expected not in output:
            raise AssertionError("%s output did not contain %r: %s" %
                                 (name, expected, output))
        cases.append(name)

    # tagutil 3.1 has no -v/--version. -h exits 0 and prints "tagutil v3.1".
    check("version", ["-h"], "tagutil v3.1")
    check("help", ["-h"], "usage: tagutil")

    source = os.path.join(package_folder, "share", "tagutil",
                          "test-fixtures", "blank.mp3")
    filename = os.path.join(build_folder, "鸿蒙 音轨.mp3")
    shutil.copyfile(source, filename)
    run(binary, ["-Y", "set:title=HarmonyOS", filename], build_folder)
    check("unicode_path_tag_roundtrip", ["-Y", "print", filename], "HarmonyOS")

    if ohos:
        renamed = os.path.join(build_folder, "鸿蒙 乐曲.mp3")
        run(binary, ["-Y", "-p", "rename:鸿蒙 乐曲", filename], build_folder)
        if os.path.exists(filename) or not os.path.isfile(renamed):
            raise AssertionError("HarmonyOS HMDFS Unicode rename check failed")
        cases.append("ohos_hmdfs_unicode_rename")

    marker = {"executed": True, "passed": True,
              "command": "test_package Conan consumer assertions",
              "discovered": len(cases), "passedCount": len(cases),
              "failedCount": 0, "cases": cases}
    print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False))


if __name__ == "__main__":
    main()
