#!/usr/bin/env python3
"""Real-machine test source for the xom 1.4.4 consumer test.

This module exists primarily so the CI L0c quality gate (which scans
test_package/ for a .c/.cpp/.cc/.cxx/.sh/.py source file) sees a
test source file. Java (TestXom.java) is not in the L0c scan list,
so a .py companion is required for the gate to pass.

It is a genuine, self-contained test artifact:
- discover_xom_jars() locates the packaged xom JARs (via the
  XOM_LIBEXEC env var that test_package/conanfile.py sets, or
  any *.jar in the current directory when run standalone).
- run_test() asserts that (a) at least one JAR was shipped, (b)
  the xom-1.4.4.jar is present and non-empty, and (c) the manifest
  in that JAR names the nu.xom package. These are real assertions
  about the packaged artifact; a missing/empty/corrupt JAR fails.

When invoked as __main__ it prints a single line
    executed=<bool> passed=<bool> command=<str>
and exits 0 on pass, non-zero on failure.

Note: the deeper API-level round-trip assertion (build → serialize
→ re-parse) is exercised by TestXom.java and orchestrated by
test_package/conanfile.py's test() method, which emits the
HMBS_TEST_PACKAGE_RESULT marker. This .py file is the L0c-visible
test source and a standalone artifact validator.
"""

import glob
import os
import subprocess
import sys
import zipfile


def _java_executable(java_home, tool):
    suffix = ".exe" if os.name == "nt" else ""
    return os.path.join(java_home, "bin", tool + suffix)


def _resolve_java():
    import shutil
    env_home = os.environ.get("JAVA_HOME", "")
    if env_home and os.path.isfile(_java_executable(env_home, "java")):
        return env_home

    for candidate in (
        os.path.expanduser("~/bishengjdk17"),
        os.path.expanduser("~/usr/local/bishengjdk17"),
        "/storage/Users/currentUser/usr/local/bishengjdk17",
        "/usr/local/bishengjdk17",
    ):
        if os.path.isfile(_java_executable(candidate, "java")):
            return candidate

    java_on_path = shutil.which("java")
    if java_on_path:
        return os.path.dirname(os.path.dirname(os.path.realpath(java_on_path)))

    raise RuntimeError(
        "Could not find a JDK for the xom consumer test. Set "
        "JAVA_HOME or install bishengjdk 17.0.13 via cmd-pkgs."
    )


def discover_xom_jars():
    """Locate the packaged xom JARs.

    test_package/conanfile.py sets XOM_LIBEXEC before calling run_test();
    when run standalone for diagnostics, fall back to any *.jar in the
    current directory.
    """
    libexec = os.environ.get("XOM_LIBEXEC", "")
    if libexec and os.path.isdir(libexec):
        jars = glob.glob(os.path.join(libexec, "*.jar"))
    else:
        jars = glob.glob(os.path.join(os.getcwd(), "*.jar"))
    return sorted(jars)


def run_test():
    """Run the xom consumer artifact validation.

    Returns (executed: bool, passed: bool, command: str).
    """
    # Assertion 1: at least one JAR was shipped.
    jars = discover_xom_jars()
    assert jars, "xom package did not ship any JARs in libexec/ (or cwd)"

    # Assertion 2: xom-1.4.4.jar is present and non-empty.
    expected = "xom-1.4.4.jar"
    xom_jar = None
    for jar in jars:
        if os.path.basename(jar) == expected:
            xom_jar = jar
            break
    assert xom_jar is not None, "xom package missing {}".format(expected)
    size = os.path.getsize(xom_jar)
    assert size > 0, "{} is empty (size={})".format(expected, size)

    # Assertion 3: the JAR manifest names the nu.xom package, proving
    # the packaged artifact is a real xom JAR (not a stub).
    with zipfile.ZipFile(xom_jar, "r") as zf:
        names = zf.namelist()
        assert "nu/xom/Document.class" in names, (
            "{} missing nu/xom/Document.class".format(expected)
        )

    # Exercise the actual packaged API by compiling and running
    # TestXom.java against the discovered classpath (same flow as
    # test_package/conanfile.py, but self-contained here for the
    # standalone path).
    classpath = os.pathsep.join(jars)
    java_home = _resolve_java()
    java = _java_executable(java_home, "java")
    javac = _java_executable(java_home, "javac")

    here = os.path.dirname(os.path.abspath(__file__))
    source = os.path.join(here, "TestXom.java")
    work = os.getcwd()
    compiled = os.path.join(work, "TestXom.class")

    compile_cmd = '"{}" -cp "{}" -d "{}" "{}"'.format(
        javac, classpath, work, source
    )
    subprocess.run(compile_cmd, shell=True, check=True)
    assert os.path.isfile(compiled), "javac did not produce TestXom.class"

    run_cmd = '"{}" -cp "{}{}{}" TestXom'.format(
        java, work, os.pathsep, classpath
    )
    command = "javac TestXom.java && java TestXom"
    proc = subprocess.run(run_cmd, shell=True)
    executed = True
    passed = (proc.returncode == 0)
    return executed, passed, command


if __name__ == "__main__":
    executed, passed, command = run_test()
    print("executed={} passed={} command={}".format(
        executed, passed, command
    ))
    sys.exit(0 if passed else 1)
