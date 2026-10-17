#!/usr/bin/env python3
"""Build a signed HAP host and run the OHAudio progress test on a device."""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time


def run(command, cwd=None, env=None, check=True):
    result = subprocess.run(command, cwd=cwd, env=env, check=False, text=True,
                            encoding="utf-8", errors="replace",
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if result.stdout:
        sys.stdout.write(result.stdout)
    if check and result.returncode:
        raise RuntimeError("command failed ({}): {}".format(result.returncode, command))
    return result


def hdc_command(hdc, serial, *args):
    return [hdc, "-t", serial] + list(args)


def ensure_workspace_is_build_output(path, build_root):
    path = os.path.realpath(path)
    build_root = os.path.realpath(build_root)
    if os.path.commonpath([path, build_root]) != build_root or os.path.basename(path) != "ohos_device_app":
        raise RuntimeError("refusing to replace an HAP workspace outside the Conan test build folder")
    return path


def find_repository_root(start):
    current = os.path.realpath(start)
    while True:
        marker = os.path.join(current, ".git")
        if os.path.isdir(marker) or os.path.isfile(marker):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            raise RuntimeError("could not find the repository root for a short HAP build workspace")
        current = parent


def configure_signing(profile_path, signing_config_path):
    signing_config_path = os.path.abspath(signing_config_path)
    if not os.path.isfile(signing_config_path):
        raise RuntimeError("local signing config file does not exist")
    with open(signing_config_path, "r", encoding="utf-8") as source:
        config = json.load(source)
    entries = config.get("signingConfigs")
    if not isinstance(entries, list) and isinstance(config.get("app"), dict):
        entries = config["app"].get("signingConfigs")
    if not isinstance(entries, list) or len(entries) != 1:
        raise RuntimeError("signing config must contain exactly one signingConfigs entry")
    signing = entries[0]
    name = signing.get("name")
    material = signing.get("material")
    required = ("certpath", "storePassword", "keyAlias", "keyPassword", "profile", "signAlg", "storeFile")
    if not name or not isinstance(material, dict) or any(not material.get(key) for key in required):
        raise RuntimeError("signing config is missing its name or required material fields")
    for key in ("certpath", "profile", "storeFile"):
        value = material[key]
        if not os.path.isabs(value):
            material[key] = os.path.abspath(os.path.join(os.path.dirname(signing_config_path), value))
        if not os.path.isfile(material[key]):
            raise RuntimeError("a file referenced by the local signing config does not exist")
    with open(profile_path, "r", encoding="utf-8") as source:
        profile = json.load(source)
    profile["app"]["signingConfigs"] = entries
    profile["app"]["products"][0]["signingConfig"] = name
    with open(profile_path, "w", encoding="utf-8", newline="\n") as target:
        json.dump(profile, target, ensure_ascii=False, indent=2)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--app-template", required=True)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--build-root", required=True)
    parser.add_argument("--generators-dir", required=True)
    parser.add_argument("--serial", required=True, help="HDC device serial")
    parser.add_argument("--hdc", help="Path to hdc.exe; defaults to PATH lookup")
    parser.add_argument("--hvigor", required=True, help="Path to hvigorw.js")
    parser.add_argument("--node", required=True, help="Path to Node.js")
    parser.add_argument("--sdk-root", required=True, help="OpenHarmony base SDK root used by the native build")
    parser.add_argument("--harmonyos-sdk-root", help="HarmonyOS SDK root used by the HarmonyOS HAP builder")
    parser.add_argument("--build-only", action="store_true",
                        help="Build the HAP and stop before installing it on the device")
    parser.add_argument("--hap-output", help="Copy the generated HAP to this path")
    signing = parser.add_mutually_exclusive_group()
    signing.add_argument("--signing-config", help="Local JSON file with a DevEco signingConfigs entry")
    signing.add_argument("--signed-hap", help="Path to a locally signed HAP built from the test app")
    args = parser.parse_args()
    if args.build_only and args.signed_hap:
        parser.error("--build-only cannot be combined with --signed-hap")
    if args.build_only and not args.hap_output:
        parser.error("--build-only requires --hap-output")
    hdc = args.hdc or shutil.which("hdc")
    if not hdc:
        parser.error("hdc.exe was not found; pass --hdc with its full path")

    build_root = os.path.realpath(args.build_root)
    ensure_workspace_is_build_output(args.workspace, build_root)
    generators_source = os.path.realpath(args.generators_dir)
    if os.path.commonpath([generators_source, build_root]) != build_root:
        raise RuntimeError("refusing to use Conan generators outside the test build folder")

    scratch = None
    installed = False
    bundle = "org.buildinharmonyos.rtaudio_ohaudio_test"
    try:
        if args.signed_hap:
            hap = os.path.realpath(args.signed_hap)
            if not os.path.isfile(hap):
                raise RuntimeError("the signed HAP path does not point to a file")
        else:
            if not args.harmonyos_sdk_root or not os.path.isdir(args.harmonyos_sdk_root):
                raise RuntimeError("building a HarmonyOS HAP requires user.rtaudio:harmonyos_sdk")
            repository_root = find_repository_root(os.path.dirname(__file__))
            scratch_parent = os.path.join(repository_root, ".superpowers")
            os.makedirs(scratch_parent, exist_ok=True)
            scratch = tempfile.mkdtemp(prefix="rtaudio-hap-", dir=scratch_parent)
            workspace = os.path.join(scratch, "ohos_device_app")
            generators_dir = os.path.join(scratch, "generators")
            shutil.copytree(args.app_template, workspace, dirs_exist_ok=True)
            shutil.copytree(generators_source, generators_dir)

            profile = os.path.join(workspace, "entry", "build-profile.json5")
            with open(profile, "r", encoding="utf-8") as source:
                profile_text = source.read()
            if "@RTAUDIO_GENERATORS_DIR@" not in profile_text:
                raise RuntimeError("HAP build profile is missing the Conan generators path placeholder")
            with open(profile, "w", encoding="utf-8", newline="\n") as target:
                target.write(profile_text.replace("@RTAUDIO_GENERATORS_DIR@",
                                                  os.path.abspath(generators_dir).replace("\\", "/")))
            if args.signing_config:
                configure_signing(os.path.join(workspace, "build-profile.json5"),
                                  os.path.abspath(args.signing_config))

            with open(os.path.join(workspace, "local.properties"), "w", encoding="utf-8", newline="\n") as target:
                target.write("sdk.dir={}\n".format(os.path.abspath(args.sdk_root).replace("\\", "/")))
            shutil.copy2(os.path.join(os.path.dirname(__file__), "ohos_device_test.cpp"),
                         os.path.join(workspace, "entry", "src", "main", "cpp", "ohos_device_test.cpp"))

            env = os.environ.copy()
            tool_paths = [os.path.dirname(args.node), os.path.dirname(args.hvigor)]
            ohpm_bin = os.path.join(os.path.dirname(args.node), "..", "ohpm", "bin")
            tool_paths.append(os.path.abspath(ohpm_bin))
            env["PATH"] = os.pathsep.join(tool_paths + [env.get("PATH", "")])
            env["OHOS_BASE_SDK_HOME"] = os.path.abspath(args.sdk_root)
            env["DEVECO_SDK_HOME"] = os.path.abspath(args.harmonyos_sdk_root)
            tmp_dir = os.path.join(workspace, "tmp")
            os.makedirs(tmp_dir, exist_ok=True)
            env["TMP"] = env["TEMP"] = env["TMPDIR"] = tmp_dir

            run([args.node, args.hvigor, "--stop-daemon"], cwd=workspace, env=env, check=False)
            run([args.node, args.hvigor, "assembleHap", "-p", "product=default"],
                cwd=workspace, env=env)
            hap_files = []
            for root, _, files in os.walk(workspace):
                for filename in files:
                    if filename.endswith(".hap"):
                        hap_files.append(os.path.join(root, filename))
            if not hap_files:
                raise RuntimeError("Hvigor produced no HAP package")
            signed = [path for path in hap_files if "unsigned" not in os.path.basename(path).lower()]
            hap = max(signed or hap_files, key=os.path.getmtime)
            if not signed:
                sys.stdout.write("Hvigor produced an unsigned HAP; trying device developer-mode installation.\n")

        if args.hap_output:
            output_path = os.path.abspath(args.hap_output)
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            shutil.copy2(hap, output_path)
            sys.stdout.write("HAP_BUILD_OUTPUT={}\n".format(output_path))
            sys.stdout.flush()
        if args.build_only:
            return

        existing = run(hdc_command(hdc, args.serial, "shell", "bm", "dump", "-n", bundle), check=False)
        if bundle in existing.stdout and "bundleName" in existing.stdout:
            raise RuntimeError("test bundle is already installed; refusing to replace an existing app")
        install_result = run(hdc_command(hdc, args.serial, "install", hap))
        if "failed to install bundle" in install_result.stdout.lower() or "no signature file" in install_result.stdout.lower():
            raise RuntimeError("HarmonyOS rejected the test HAP during installation")
        installed = True
        log_tags = "RTAudioOHAudioTest"
        before_logs = run(hdc_command(hdc, args.serial, "shell", "hilog", "-x", "-T",
                                      log_tags), check=False).stdout
        before_run_ids = set(re.findall(r"RTAUDIO_DEVICE_TEST_ID=([^\s]+)", before_logs))
        run(hdc_command(hdc, args.serial, "shell", "aa", "start", "-b", bundle,
                         "-a", "EntryAbility"))
        deadline = time.time() + 240
        run_log = []
        run_id = None
        suite_complete = False
        while time.time() < deadline:
            logs = run(hdc_command(hdc, args.serial, "shell", "hilog", "-x", "-T",
                                   log_tags), check=False).stdout
            log_lines = logs.splitlines()
            run_ids = set(re.findall(r"RTAUDIO_DEVICE_TEST_ID=([^\s]+)", logs))
            fresh_run_ids = run_ids - before_run_ids
            if fresh_run_ids:
                run_id = sorted(fresh_run_ids)[-1]
                run_log = [line for line in log_lines
                           if "RTAUDIO_DEVICE_TEST_ID=" + run_id in line]
            suite_complete = any("RTAUDIO_SUITE_COMPLETE" in line for line in run_log)
            if (suite_complete or
                    any("MICROPHONE_PERMISSION_DENIED" in line or "OHOS_SUITE_FAIL" in line or
                        "OHOS_SUITE_FATAL" in line for line in run_log)):
                break
            if (any("OHOS_AUDIO_PASS" in line for line in run_log) and
                    not any("RTAUDIO_UPSTREAM_TEST" in line for line in run_log)):
                break
            time.sleep(2)

        for line in run_log:
            if ("RTAUDIO_UPSTREAM_TEST" in line or "RTAUDIO_DEVICE_TEST" in line or
                    "RTAUDIO_SUITE_COMPLETE" in line or "OHOS_DIRECT_OHAUDIO_" in line or
                    "MICROPHONE_PERMISSION_" in line or "OHOS_SUITE_" in line):
                sys.stdout.write(line + "\n")
        sys.stdout.flush()

        results = {}
        for line in run_log:
            match = re.search(r"\b([UH][0-9]{2})_(PASS|FAIL)\b", line)
            if match:
                results[match.group(1)] = match.group(2)
        expected = ["U{:02d}".format(index) for index in range(1, 28)] + ["H01", "H02"]
        missing = [case_id for case_id in expected if case_id not in results]
        failed = [case_id for case_id in expected if results.get(case_id) != "PASS"]
        if not run_log or not suite_complete or missing or failed:
            raise RuntimeError(
                "HarmonyOS device suite incomplete: missing={}, failed={}".format(
                    ",".join(missing) or "none", ",".join(failed) or "none"))
    finally:
        if installed:
            run(hdc_command(hdc, args.serial, "uninstall", bundle), check=False)
        if scratch:
            shutil.rmtree(scratch, ignore_errors=True)


if __name__ == "__main__":
    main()
