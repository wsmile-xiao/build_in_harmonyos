#!/usr/bin/env python3
"""Verify the packaged zxing core JAR and run a real consumer against it."""

import argparse
import os
import re
import struct
import subprocess
import zipfile


EXPECTED_CLASSES = 291
EXPECTED_CONSUMER_CHECKS = 16


def class_major(data, entry, jar):
    if len(data) < 8 or data[:4] != b"\xca\xfe\xba\xbe":
        raise RuntimeError("{} is not a valid Java class".format(entry))
    return struct.unpack(">H", data[6:8])[0]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--lib", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--work", required=True)
    parser.add_argument("--java", required=True)
    parser.add_argument("--javac", required=True)
    parser.add_argument("--source", required=True)
    args = parser.parse_args()

    jar = os.path.join(args.lib, "zxing-core-{}.jar".format(args.version))
    jar_checks = 0

    if not os.path.isfile(jar) or os.path.getsize(jar) <= 0:
        raise RuntimeError("Packaged JAR is missing or empty: {}".format(jar))
    jar_checks += 1

    with zipfile.ZipFile(jar) as archive:
        corrupt = archive.testzip()
        if corrupt:
            raise RuntimeError("{} has a corrupt ZIP entry: {}".format(jar, corrupt))
        jar_checks += 1

        entries = set(archive.namelist())
        classes = sorted(e for e in entries if e.endswith(".class"))
        if len(classes) != EXPECTED_CLASSES:
            raise RuntimeError(
                "Unexpected class count: {} (expected {})".format(
                    len(classes), EXPECTED_CLASSES
                )
            )
        jar_checks += 1

        majors = {class_major(archive.read(e), e, jar) for e in classes}
        if majors != {52}:
            raise RuntimeError(
                "Unexpected bytecode majors: {} (expected [52])".format(sorted(majors))
            )
        jar_checks += 1

        manifest = archive.read("META-INF/MANIFEST.MF").decode("utf-8", "replace")
        if "Automatic-Module-Name: com.google.zxing" not in manifest:
            raise RuntimeError("Missing Automatic-Module-Name in manifest")
        jar_checks += 1
        if "Bundle-Version: {}".format(args.version) not in manifest:
            raise RuntimeError("Missing Bundle-Version {} in manifest".format(args.version))
        jar_checks += 1

    required = (
        "com/google/zxing/MultiFormatReader.class",
        "com/google/zxing/MultiFormatWriter.class",
        "com/google/zxing/RGBLuminanceSource.class",
        "com/google/zxing/common/HybridBinarizer.class",
        "com/google/zxing/qrcode/QRCodeWriter.class",
        "com/google/zxing/qrcode/decoder/Version.class",
    )
    with zipfile.ZipFile(jar) as archive:
        entries = set(archive.namelist())
    missing = [e for e in required if e not in entries]
    if missing:
        raise RuntimeError("JAR is missing entries: " + ", ".join(missing))
    jar_checks += len(required)

    classes_dir = os.path.join(args.work, "consumer-classes")
    os.makedirs(classes_dir, exist_ok=True)
    subprocess.run(
        [
            args.javac,
            "-encoding",
            "UTF-8",
            "-cp",
            jar,
            "-d",
            classes_dir,
            args.source,
        ],
        check=True,
    )

    environment = os.environ.copy()
    existing = environment.get("JAVA_TOOL_OPTIONS", "").strip()
    environment["JAVA_TOOL_OPTIONS"] = (existing + " -Dos.name=Linux").strip()
    classpath = os.pathsep.join([classes_dir, jar])
    result = subprocess.run(
        [args.java, "-cp", classpath, "TestZxingCore"],
        check=True,
        text=True,
        capture_output=True,
        env=environment,
    )
    output = result.stdout.strip().splitlines()[-1]

    expected = "zxing {} consumer tests passed: {}".format(
        args.version, EXPECTED_CONSUMER_CHECKS
    )
    if output != expected:
        raise RuntimeError(
            "Unexpected consumer output: {!r}; expected {!r}".format(output, expected)
        )

    print(
        "JAR verification passed: {} packaging checks, {} Java 8 classes, "
        "clean ZIP, Automatic-Module-Name present".format(jar_checks, EXPECTED_CLASSES)
    )
    print(
        "Consumer verification passed: javac + java against the packaged JAR, "
        "{} assertions".format(EXPECTED_CONSUMER_CHECKS)
    )
    print(output)
    print(
        "test_package total assertions: {}".format(
            jar_checks + EXPECTED_CONSUMER_CHECKS + 1
        )
    )


if __name__ == "__main__":
    main()
