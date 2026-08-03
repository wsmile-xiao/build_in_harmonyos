#!/usr/bin/env python3
"""Compile and run a real consumer against the packaged Jackson jr JAR."""

import argparse
import os
import struct
import subprocess
import zipfile


def class_major(data, entry, jar):
    if len(data) < 8 or data[:4] != b"\xca\xfe\xba\xbe":
        raise RuntimeError(
            "{} in {} is not a valid Java class".format(entry, jar)
        )
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

    modules = (
        "jr-all",
        "jr-objects",
        "jr-stree",
        "jr-annotation-support",
        "jr-retrofit2",
    )
    jars = {}
    for module in modules:
        jar = os.path.join(
            args.lib,
            "jackson-{}-{}.jar".format(module, args.version),
        )
        if not os.path.isfile(jar) or os.path.getsize(jar) <= 0:
            raise RuntimeError(
                "Packaged {} JAR is missing or empty: {}".format(module, jar)
            )
        with zipfile.ZipFile(jar) as archive:
            corrupt = archive.testzip()
            if corrupt:
                raise RuntimeError(
                    "{} has a corrupt ZIP entry: {}".format(jar, corrupt)
                )
            entries = set(archive.namelist())
            module_info = "META-INF/versions/9/module-info.class"
            if module_info not in entries:
                raise RuntimeError(
                    "{} is missing its Java 9 JPMS descriptor".format(jar)
                )
            regular_classes = sorted(
                entry
                for entry in entries
                if entry.endswith(".class")
                and not entry.startswith("META-INF/versions/")
            )
            regular_majors = {
                class_major(archive.read(entry), entry, jar)
                for entry in regular_classes
            }
            module_major = class_major(
                archive.read(module_info), module_info, jar
            )
            if regular_majors != {52} or module_major != 53:
                raise RuntimeError(
                    "{} bytecode mismatch: runtime majors={}, JPMS major={}"
                    .format(
                        jar, sorted(regular_majors), module_major
                    )
                )
        jars[module] = jar

    jar = jars["jr-all"]
    required = {
        "com/fasterxml/jackson/jr/ob/JSON.class",
        "com/fasterxml/jackson/jr/stree/JrsObject.class",
        "com/fasterxml/jackson/jr/private_/JsonFactory.class",
    }
    with zipfile.ZipFile(jar) as archive:
        entries = set(archive.namelist())
        missing = sorted(required - entries)
        class_count = sum(name.endswith(".class") for name in entries)
    if missing:
        raise RuntimeError("jr-all is missing entries: " + ", ".join(missing))
    if class_count != 238:
        raise RuntimeError(
            "Unexpected jr-all class count: {} (expected 238)".format(
                class_count
            )
        )

    classes = os.path.join(args.work, "consumer-classes")
    os.makedirs(classes, exist_ok=True)
    subprocess.run(
        [
            args.javac,
            "--release",
            "8",
            "-encoding",
            "UTF-8",
            "-cp",
            jar,
            "-d",
            classes,
            args.source,
        ],
        check=True,
    )
    classpath = os.pathsep.join([classes, jar])
    result = subprocess.run(
        [args.java, "-cp", classpath, "TestJacksonJr"],
        check=True,
        text=True,
        capture_output=True,
    )
    output = result.stdout.strip()
    expected = "jackson-jr 2.14.0 consumer tests passed: 25"
    if output != expected:
        raise RuntimeError(
            "Unexpected consumer output: {!r}; expected {!r}".format(
                output, expected
            )
        )
    print(
        "JAR verification passed: all 5 artifacts, clean ZIPs, Java 8 "
        "runtime classes, Java 9 JPMS descriptors"
    )
    print(output)


if __name__ == "__main__":
    main()
