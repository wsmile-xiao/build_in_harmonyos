#!/usr/bin/env python3
"""Conan recipe for fluent-bit 5.0.9.

This recipe intentionally moves away from the historical zero-dependency
HarmonyOS build.  The first validation target is a real-dependency core build:
TLS through OpenSSL, SQLDB through sqlite3, YAML config through libyaml, and
BSD fts through musl-fts.
"""

import hashlib
import glob
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
    load,
    mkdir,
    replace_in_file,
    save,
    unzip,
)
from conan.tools.gnu import PkgConfigDeps


class FluentBitConan(ConanFile):
    name = "fluent-bit"
    version = "5.0.9"
    description = "Fast and lightweight log processor and forwarder"
    license = "Apache-2.0"
    homepage = "https://fluentbit.io"
    url = "https://github.com/fluent/fluent-bit"
    topics = ("logging", "log-processor", "observability", "ohos")

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    options = {
        "shared": [True, False],
        "debug": [True, False],
        "with_tests": [True, False],
        "with_internal_tests": [True, False],
        "with_runtime_tests": [True, False],
    }
    default_options = {
        "shared": False,
        "debug": False,
        "with_tests": False,
        "with_internal_tests": True,
        "with_runtime_tests": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        self.requires("openssl/3.5.6.1")
        self.requires("sqlite3/3.49.1")
        self.requires("libyaml/0.2.5")
        self.requires("musl-fts/1.2.7")

    def source(self):
        source = self.conan_data["sources"]
        expected_sha = source["sha256"]
        for candidate in self._source_candidates(expected_sha):
            if self._sha256(candidate) == expected_sha:
                self.output.info(f"Using local verified source archive: {candidate}")
                unzip(self, candidate, strip_root=True)
                return
        get(self, **source, strip_root=True)

    def _source_candidates(self, expected_sha):
        return [
            os.environ.get("FLUENT_BIT_SOURCE_ARCHIVE", ""),
            os.path.join(os.path.expanduser("~"), ".conan2", "downloads", expected_sha),
        ]

    @staticmethod
    def _sha256(path):
        if not os.path.isfile(path):
            return ""
        import hashlib

        h = hashlib.sha256()
        with open(path, "rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()

        pkg = PkgConfigDeps(self)
        pkg.generate()

        tc = CMakeToolchain(self)

        libyaml = self.dependencies.get("libyaml")
        if libyaml is not None and libyaml.package_folder:
            tc.cache_variables["FLB_LIBYAML_DIR"] = libyaml.package_folder

        sqlite = self.dependencies.get("sqlite3")
        if sqlite is not None and sqlite.package_folder:
            tc.cache_variables["FLB_PREFER_SYSTEM_LIB_SQLITE"] = "On"
            tc.cache_variables["SQLITE_FOUND"] = "On"
            tc.cache_variables["SQLITE_INCLUDE_DIRS"] = os.path.join(
                sqlite.package_folder, "include"
            )
            tc.cache_variables["SQLITE_LIBRARY_DIRS"] = os.path.join(
                sqlite.package_folder, "lib"
            )
            tc.cache_variables["SQLITE_LIBRARIES"] = "sqlite3"

        fts = self.dependencies.get("musl-fts")
        if fts is not None and fts.package_folder:
            tc.cache_variables["FTS_INCLUDE_DIR"] = os.path.join(
                fts.package_folder, "include"
            )
            tc.cache_variables["FTS_LIBRARY_DIR"] = os.path.join(
                fts.package_folder, "lib"
            )
            tc.cache_variables["FTS_LIBRARY"] = os.path.join(
                fts.package_folder, "lib", "libfts.so.0.0.0"
            )

        openssl = self.dependencies.get("openssl")
        if openssl is not None and openssl.package_folder:
            openssl_include = os.path.join(openssl.package_folder, "include")
            openssl_lib = os.path.join(openssl.package_folder, "lib")
            tc.cache_variables["OPENSSL_ROOT_DIR"] = openssl.package_folder
            tc.cache_variables["OPENSSL_INCLUDE_DIR"] = openssl_include
            tc.cache_variables["OPENSSL_INCLUDE_DIRS"] = openssl_include
            tc.cache_variables["OPENSSL_SSL_LIBRARY"] = os.path.join(
                openssl_lib, "libssl.a"
            )
            tc.cache_variables["OPENSSL_CRYPTO_LIBRARY"] = os.path.join(
                openssl_lib, "libcrypto.a"
            )

        if self.options.with_tests:
            # Bundled Avro/Jansson need these with the OHOS CMake/toolchain mix.
            tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
            tc.cache_variables["LIBAVRO_SOVERSION"] = "22"
            # Cross-builds otherwise let WAMR fall back to the host-sized target.
            tc.cache_variables["WAMR_BUILD_TARGET"] = "AARCH64"

        opts = {
            "FLB_DEBUG": "On" if self.options.debug else "Off",
            "FLB_RELEASE": "Off" if self.options.debug else "On",
            "FLB_MINIMAL": "On",
            "FLB_EXAMPLES": "Off",
            "FLB_TESTS_INTERNAL": "On"
            if self.options.with_tests and self.options.with_internal_tests
            else "Off",
            "FLB_TESTS_RUNTIME": "On"
            if self.options.with_tests and self.options.with_runtime_tests
            else "Off",
            "FLB_TESTS_OSSFUZZ": "Off",
            "FLB_TLS": "On",
            "FLB_HTTP_SERVER": "On",
            "FLB_HTTP_CLIENT_DEBUG": "On" if self.options.with_tests else "Off",
            "FLB_SQLDB": "On",
            "FLB_SIGNV4": "On" if self.options.with_tests else "Off",
            "FLB_CONFIG_YAML": "On",
            "FLB_AWS": "On" if self.options.with_tests else "Off",
            "FLB_AWS_ERROR_REPORTER": "On" if self.options.with_tests else "Off",
            "FLB_KAFKA": "On" if self.options.with_tests else "Off",
            "FLB_LUAJIT": "On" if self.options.with_tests else "Off",
            "FLB_BACKTRACE": "Off",
            "FLB_WASM": "On" if self.options.with_tests else "Off",
            "FLB_WAMRC": "Off",
            "FLB_AVRO_ENCODER": "On" if self.options.with_tests else "Off",
            "FLB_ARROW": "Off",
            "FLB_PARSER": "On",
            "FLB_RECORD_ACCESSOR": "Off",
            "FLB_STREAM_PROCESSOR": "Off",
            "FLB_REGEX": "On",
            "FLB_UTF8_ENCODER": "Off",
            "FLB_UNICODE_ENCODER": "Off",
            "FLB_JEMALLOC": "Off",
            "FLB_VALGRIND": "Off",
            "FLB_CUSTOM_CALYPTIA": "On" if self.options.with_tests else "Off",
            "FLB_PROXY_GO": "Off",
            "FLB_SHARED_LIB": "Off",
            "FLB_BINARY": "On",
            "FLB_CORO_STACK_SIZE": "24576" if self.options.with_tests else "Off",
            "FLB_IN_BLOB": "Off",
            "FLB_IN_CALYPTIA_FLEET": "On" if self.options.with_tests else "Off",
            "FLB_IN_COLLECTD": "Off",
            "FLB_IN_CPU": "Off",
            "FLB_IN_DISK": "Off",
            "FLB_IN_DOCKER": "Off",
            "FLB_IN_DOCKER_EVENTS": "Off",
            "FLB_IN_DUMMY": "On" if self.options.with_tests else "Off",
            "FLB_IN_ELASTICSEARCH": "On" if self.options.with_tests else "Off",
            "FLB_IN_EMITTER": "On" if self.options.with_tests else "Off",
            "FLB_IN_EVENT_TEST": "On" if self.options.with_tests else "Off",
            "FLB_IN_EVENT_TYPE": "On" if self.options.with_tests else "Off",
            "FLB_IN_EXEC": "Off",
            "FLB_IN_EXEC_WASI": "Off",
            "FLB_IN_FLUENTBIT_LOGS": "Off",
            "FLB_IN_FLUENTBIT_METRICS": "On" if self.options.with_tests else "Off",
            "FLB_IN_FORWARD": "On" if self.options.with_tests else "Off",
            "FLB_IN_GPU_METRICS": "Off",
            "FLB_IN_HEAD": "On" if self.options.with_tests else "Off",
            "FLB_IN_HEALTH": "Off",
            "FLB_IN_HTTP": "On",
            "FLB_IN_KAFKA": "Off",
            "FLB_IN_KMSG": "Off",
            "FLB_IN_KUBERNETES_EVENTS": "Off",
            "FLB_IN_LIB": "On" if self.options.with_tests else "Off",
            "FLB_IN_MEM": "Off",
            "FLB_IN_MQTT": "On" if self.options.with_tests else "Off",
            "FLB_IN_NETIF": "Off",
            "FLB_IN_NGINX_EXPORTER_METRICS": "Off",
            "FLB_IN_NODE_EXPORTER_METRICS": "Off",
            "FLB_IN_OPENTELEMETRY": "On" if self.options.with_tests else "Off",
            "FLB_IN_PODMAN_METRICS": "Off",
            "FLB_IN_PROC": "Off",
            "FLB_IN_PROCESS_EXPORTER_METRICS": "Off",
            "FLB_IN_PROMETHEUS_REMOTE_WRITE": "Off",
            "FLB_IN_PROMETHEUS_SCRAPE": "Off",
            "FLB_IN_PROMETHEUS_TEXTFILE": "Off",
            "FLB_IN_RANDOM": "On" if self.options.with_tests else "Off",
            "FLB_IN_SERIAL": "Off",
            "FLB_IN_SPLUNK": "On" if self.options.with_tests else "Off",
            "FLB_IN_STATSD": "On" if self.options.with_tests else "Off",
            "FLB_IN_STDIN": "Off",
            "FLB_IN_STORAGE_BACKLOG": "On" if self.options.with_tests else "Off",
            "FLB_IN_SYSLOG": "On" if self.options.with_tests else "Off",
            "FLB_IN_SYSTEMD": "Off",
            "FLB_IN_TAIL": "On" if self.options.with_tests else "Off",
            "FLB_IN_TCP": "On" if self.options.with_tests else "Off",
            "FLB_IN_THERMAL": "Off",
            "FLB_IN_UDP": "On" if self.options.with_tests else "Off",
            "FLB_IN_UNIX_SOCKET": "Off",
            "FLB_IN_WINDOWS_EXPORTER_METRICS": "Off",
            "FLB_IN_WINEVTLOG": "Off",
            "FLB_IN_WINLOG": "Off",
            "FLB_IN_WINSTAT": "Off",
            "FLB_OUT_AZURE": "Off",
            "FLB_OUT_AZURE_BLOB": "On" if self.options.with_tests else "Off",
            "FLB_OUT_AZURE_KUSTO": "On" if self.options.with_tests else "Off",
            "FLB_OUT_AZURE_LOGS_INGESTION": "Off",
            "FLB_OUT_BIGQUERY": "Off",
            "FLB_OUT_CALYPTIA": "On" if self.options.with_tests else "Off",
            "FLB_OUT_CHRONICLE": "On" if self.options.with_tests else "Off",
            "FLB_OUT_CLOUDWATCH_LOGS": "On" if self.options.with_tests else "Off",
            "FLB_OUT_COUNTER": "On" if self.options.with_tests else "Off",
            "FLB_OUT_DATADOG": "On" if self.options.with_tests else "Off",
            "FLB_OUT_ES": "On" if self.options.with_tests else "Off",
            "FLB_OUT_HTTP": "On",
            "FLB_OUT_LIB": "On" if self.options.with_tests else "Off",
            "FLB_OUT_NULL": "On" if self.options.with_tests else "Off",
            "FLB_OUT_EXIT": "On" if self.options.with_tests else "Off",
            "FLB_OUT_FILE": "On" if self.options.with_tests else "Off",
            "FLB_OUT_STDOUT": "On" if self.options.with_tests else "Off",
            "FLB_OUT_FLOWCOUNTER": "On" if self.options.with_tests else "Off",
            "FLB_OUT_FORWARD": "On" if self.options.with_tests else "Off",
            "FLB_OUT_GELF": "Off",
            "FLB_OUT_INFLUXDB": "On" if self.options.with_tests else "Off",
            "FLB_OUT_TD": "On" if self.options.with_tests else "Off",
            "FLB_OUT_KAFKA": "On" if self.options.with_tests else "Off",
            "FLB_OUT_KAFKA_REST": "Off",
            "FLB_OUT_KINESIS_FIREHOSE": "On" if self.options.with_tests else "Off",
            "FLB_OUT_KINESIS_STREAMS": "On" if self.options.with_tests else "Off",
            "FLB_OUT_LOGDNA": "On" if self.options.with_tests else "Off",
            "FLB_OUT_LOKI": "On" if self.options.with_tests else "Off",
            "FLB_OUT_NATS": "Off",
            "FLB_OUT_NRLOGS": "Off",
            "FLB_OUT_OPENSEARCH": "On" if self.options.with_tests else "Off",
            "FLB_OUT_OPENTELEMETRY": "Off",
            "FLB_OUT_ORACLE_LOG_ANALYTICS": "Off",
            "FLB_OUT_PGSQL": "Off",
            "FLB_OUT_PLOT": "On" if self.options.with_tests else "Off",
            "FLB_OUT_PROMETHEUS_EXPORTER": "Off",
            "FLB_OUT_PROMETHEUS_REMOTE_WRITE": "Off",
            "FLB_OUT_RETRY": "On" if self.options.with_tests else "Off",
            "FLB_OUT_S3": "On" if self.options.with_tests else "Off",
            "FLB_OUT_SKYWALKING": "On" if self.options.with_tests else "Off",
            "FLB_OUT_SLACK": "Off",
            "FLB_OUT_SPLUNK": "On" if self.options.with_tests else "Off",
            "FLB_OUT_SYSLOG": "On" if self.options.with_tests else "Off",
            "FLB_OUT_STACKDRIVER": "Off",
            "FLB_OUT_TCP": "On" if self.options.with_tests else "Off",
            "FLB_OUT_UDP": "Off",
            "FLB_OUT_VIVO_EXPORTER": "Off",
            "FLB_OUT_WEBSOCKET": "Off",
            "FLB_FILTER_ALTER_SIZE": "Off",
            "FLB_FILTER_EXPECT": "On" if self.options.with_tests else "Off",
            "FLB_FILTER_GREP": "On" if self.options.with_tests else "Off",
            "FLB_FILTER_AWS": "On" if self.options.with_tests else "Off",
            "FLB_FILTER_CHECKLIST": "On" if self.options.with_tests else "Off",
            "FLB_FILTER_ECS": "On" if self.options.with_tests else "Off",
            "FLB_FILTER_GEOIP2": "Off",
            "FLB_FILTER_KUBERNETES": "Off",
            "FLB_FILTER_LOG_TO_METRICS": "On" if self.options.with_tests else "Off",
            "FLB_FILTER_LUA": "On" if self.options.with_tests else "Off",
            "FLB_FILTER_MODIFY": "On" if self.options.with_tests else "Off",
            "FLB_FILTER_MULTILINE": "On" if self.options.with_tests else "Off",
            "FLB_FILTER_NEST": "On" if self.options.with_tests else "Off",
            "FLB_FILTER_NIGHTFALL": "Off",
            "FLB_FILTER_PARSER": "On" if self.options.with_tests else "Off",
            "FLB_FILTER_RECORD_MODIFIER": "On" if self.options.with_tests else "Off",
            "FLB_FILTER_REWRITE_TAG": "Off",
            "FLB_FILTER_STDOUT": "On" if self.options.with_tests else "Off",
            "FLB_FILTER_SYSINFO": "On" if self.options.with_tests else "Off",
            "FLB_FILTER_TENSORFLOW": "Off",
            "FLB_FILTER_THROTTLE": "Off",
            "FLB_FILTER_THROTTLE_SIZE": "On" if self.options.with_tests else "Off",
            "FLB_FILTER_TYPE_CONVERTER": "On" if self.options.with_tests else "Off",
            "FLB_FILTER_WASM": "On" if self.options.with_tests else "Off",
            "FLB_PROCESSOR_CONTENT_MODIFIER": "On" if self.options.with_tests else "Off",
            "FLB_PROCESSOR_CUMULATIVE_TO_DELTA": "On" if self.options.with_tests else "Off",
            "FLB_PROCESSOR_LABELS": "On" if self.options.with_tests else "Off",
            "FLB_PROCESSOR_METRICS_SELECTOR": "On" if self.options.with_tests else "Off",
            "FLB_PROCESSOR_OPENTELEMETRY_ENVELOPE": "On" if self.options.with_tests else "Off",
            "FLB_PROCESSOR_SAMPLING": "Off",
            "FLB_PROCESSOR_SQL": "Off",
            "FLB_PROCESSOR_TDA": "Off",
            "FLB_PROCESSOR_TEMPLATE": "Off",
        }
        if str(self.settings.os) in ("OHOS", "HarmonyOS"):
            opts["FLB_INOTIFY"] = "Off"
        if self.options.with_tests:
            for test_name in self._ohos_first_stage_test_exclusions():
                opts[f"FLB_WITHOUT_{test_name}"] = "On"
        for key, value in opts.items():
            tc.cache_variables[key] = value
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        if self.options.with_tests:
            self._adapt_runtime_ctests()
        if self.options.with_tests and self.options.with_runtime_tests:
            self._adapt_runtime_shell_tests()
        self._prepend_ohos_sdk_llvm_lib()
        cmake = CMake(self)
        cmake.configure()
        if self.options.with_tests:
            cmake.build(build_tool_args=["-j1"])
        else:
            cmake.build()
        if self.options.with_tests:
            self._run_upstream_tests()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]

    def _run_upstream_tests(self):
        self._prepend_ohos_sdk_llvm_lib()
        test_tmp = self._upstream_test_tmp_dir()
        shunit_tmp = os.path.join(test_tmp, "shunit2")
        mkdir(self, test_tmp)
        mkdir(self, shunit_tmp)

        env = Environment()
        env.define("TMPDIR", test_tmp)
        env.define("TMP", test_tmp)
        env.define("TEMP", test_tmp)
        env.define("FLB_TEST_TMPDIR", test_tmp)
        env.define("SHUNIT_TMPDIR", shunit_tmp)
        test_env = env.vars(self)
        with test_env.apply():
            self._clean_runtime_test_workdir()
            self.run(
                'ctest -N --test-dir "{}"'.format(self.build_folder),
                env="conanrun",
            )
            self._clean_runtime_test_workdir()
            self.run(
                'ctest --test-dir "{}" --output-on-failure --timeout 180 -j1 '
                "--no-tests=error".format(self.build_folder),
                env="conanrun",
            )

    def _clean_runtime_test_workdir(self):
        for pattern in (
            "checklist.txt",
            "flb_test_file_dummy.log",
            "flb_test_plot_dummy.log",
            "out_file",
        ):
            for path in glob.glob(os.path.join(self.build_folder, pattern)):
                self._remove_test_artifact(path)

        for pattern in (
            "a.log",
            "b.log",
            "c.log",
            "d.log",
            "ep_*.txt",
            "inotify_*collectors.log",
            "offset_key.log",
            "parser.log",
            "path_key.log",
            "skip_empty_lines*.log",
            "source_file_reread*.log",
        ):
            for path in glob.glob(os.path.join(self.build_folder, "..", pattern)):
                self._remove_test_artifact(path)

        test_tmp = self._upstream_test_tmp_dir()
        for pattern in (
            "fb_signal_*",
            "fluent_bit_syslog_uds_*.sock",
            "processor_conditional*.yaml",
            "processor_conditional*_output.txt",
        ):
            for path in glob.glob(os.path.join(test_tmp, pattern)):
                self._remove_test_artifact(path)

        shunit_tmp = os.path.join(test_tmp, "shunit2")
        if os.path.isdir(shunit_tmp):
            for name in os.listdir(shunit_tmp):
                self._remove_test_artifact(os.path.join(shunit_tmp, name))
        mkdir(self, shunit_tmp)

    @staticmethod
    def _remove_test_artifact(path):
        try:
            if os.path.isdir(path) and not os.path.islink(path):
                shutil.rmtree(path)
            else:
                os.unlink(path)
        except FileNotFoundError:
            pass

    def _adapt_runtime_shell_tests(self):
        runtime_shell = os.path.join(self.source_folder, "tests", "runtime_shell")
        test_tmp = self._cmake_env_path(self._upstream_test_tmp_dir())

        self._replace_runtime_shell_text(
            "CMakeLists.txt",
            """  in_syslog_uds_dgram_plaintext_expect.sh
  in_syslog_uds_stream_plaintext_expect.sh
""",
            "",
        )
        self._replace_runtime_shell_text(
            "CMakeLists.txt",
            """configure_file(
  "${CMAKE_CURRENT_SOURCE_DIR}/runtime_shell.env.in"
  "${CMAKE_CURRENT_SOURCE_DIR}/runtime_shell.env"
  )""",
            """configure_file(
  "${CMAKE_CURRENT_SOURCE_DIR}/runtime_shell.env.in"
  "${CMAKE_CURRENT_SOURCE_DIR}/runtime_shell.env"
  @ONLY
  )""",
        )
        self._replace_runtime_shell_text(
            "CMakeLists.txt",
            """  set_tests_properties(${script} PROPERTIES ENVIRONMENT
    "FLB_ROOT=${PROJECT_SOURCE_DIR};\\
FLB_RUNTIME_SHELL_PATH=${CMAKE_CURRENT_SOURCE_DIR};\\
FLB_RUNTIME_SHELL_CONF=${CMAKE_CURRENT_SOURCE_DIR}/conf;\\
FLB_BIN=${CMAKE_BINARY_DIR}/bin/fluent-bit;\\
FLB_BUILD=${CMAKE_BINARY_DIR}"
    )""",
            """  set_tests_properties(${script} PROPERTIES
    LABELS "runtime"
    ENVIRONMENT
    "FLB_ROOT=${PROJECT_SOURCE_DIR};\\
FLB_RUNTIME_SHELL_PATH=${CMAKE_CURRENT_SOURCE_DIR};\\
FLB_RUNTIME_SHELL_CONF=${CMAKE_CURRENT_SOURCE_DIR}/conf;\\
FLB_BIN=${CMAKE_BINARY_DIR}/bin/fluent-bit;\\
FLB_BUILD=${CMAKE_BINARY_DIR};\\
FLB_TEST_TMPDIR=%s"
    )"""
            % test_tmp,
        )

        save(
            self,
            os.path.join(runtime_shell, "runtime_shell.env.in"),
            """flb_runtime_shell_tmpdir() {
  tmp="${FLB_TEST_TMPDIR:-${TMPDIR:-/tmp}}"
  mkdir -p "$tmp" || return 1
  printf '%s\\n' "$tmp"
}

flb_runtime_shell_python() {
  if [ -n "${PYTHON:-}" ] && [ -x "$PYTHON" ]; then
    printf '%s\\n' "$PYTHON"
    return 0
  fi
  command -v python3
}

flb_runtime_shell_send_tcp() {
  py=$(flb_runtime_shell_python) || return 1
  "$py" - "$1" "$2" "$3" <<'PY'
import socket
import sys

host = sys.argv[1]
port = int(sys.argv[2])
payload = (sys.argv[3] + "\\n").encode("utf-8")

with socket.create_connection((host, port), timeout=3) as sock:
    sock.sendall(payload)
PY
}

flb_runtime_shell_send_udp() {
  py=$(flb_runtime_shell_python) || return 1
  "$py" - "$1" "$2" "$3" <<'PY'
import socket
import sys

host = sys.argv[1]
port = int(sys.argv[2])
payload = (sys.argv[3] + "\\n").encode("utf-8")

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.settimeout(3)
try:
    sock.sendto(payload, (host, port))
finally:
    sock.close()
PY
}

flb_runtime_shell_send_unix_dgram() {
  py=$(flb_runtime_shell_python) || return 1
  "$py" - "$1" "$2" <<'PY'
import socket
import sys

path = sys.argv[1]
payload = (sys.argv[2] + "\\n").encode("utf-8")

sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
sock.settimeout(3)
try:
    sock.sendto(payload, path)
finally:
    sock.close()
PY
}

flb_runtime_shell_send_unix_stream() {
  py=$(flb_runtime_shell_python) || return 1
  "$py" - "$1" "$2" <<'PY'
import socket
import sys

path = sys.argv[1]
payload = (sys.argv[2] + "\\n").encode("utf-8")

sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
sock.settimeout(3)
try:
    sock.connect(path)
    sock.sendall(payload)
finally:
    sock.close()
PY
}

FLB_RUNTIME_SHELL_TMPDIR=$(flb_runtime_shell_tmpdir) || exit 1
export FLB_RUNTIME_SHELL_TMPDIR
export TMPDIR="$FLB_RUNTIME_SHELL_TMPDIR"
export TMP="$FLB_RUNTIME_SHELL_TMPDIR"
export TEMP="$FLB_RUNTIME_SHELL_TMPDIR"
rm -f "$FLB_RUNTIME_SHELL_TMPDIR"/fluent_bit_syslog_uds_*.sock

SHUNIT_TMPDIR="${SHUNIT_TMPDIR:-$FLB_RUNTIME_SHELL_TMPDIR/shunit2}"
mkdir -p "$SHUNIT_TMPDIR" || exit 1
export SHUNIT_TMPDIR

flb_runtime_shell_test_run() {
  . "$FLB_RUNTIME_SHELL_PATH/../lib/shunit2/shunit2"
}

flb_runtime_shell_test_run
""",
        )

        for script in (
            "dry_run_invalid_property.sh",
            "processor_conditional.sh",
            "processor_invalid.sh",
        ):
            self._replace_runtime_shell_text(
                script,
                "/tmp/",
                "${FLB_TEST_TMPDIR:-${TMPDIR:-/tmp}}/",
            )

        self._replace_runtime_shell_text(
            "processor_conditional.sh",
            "$FLB_BIN -c ${FLB_TEST_TMPDIR:-${TMPDIR:-/tmp}}/processor_conditional.yaml -o stdout > $OUTPUT_FILE 2>&1 &",
            "$FLB_BIN -c ${FLB_TEST_TMPDIR:-${TMPDIR:-/tmp}}/processor_conditional.yaml > $OUTPUT_FILE 2>&1 &",
        )
        self._replace_runtime_shell_text(
            "processor_conditional.sh",
            "$FLB_BIN -c ${FLB_TEST_TMPDIR:-${TMPDIR:-/tmp}}/processor_conditional_grep.yaml -o stdout > $OUTPUT_FILE 2>&1 &",
            "$FLB_BIN -c ${FLB_TEST_TMPDIR:-${TMPDIR:-/tmp}}/processor_conditional_grep.yaml > $OUTPUT_FILE 2>&1 &",
        )
        self._replace_runtime_shell_text(
            "processor_conditional.sh",
            "kill -15 $FLB_PID || true\nrm -f ${FLB_TEST_TMPDIR:-${TMPDIR:-/tmp}}/processor_conditional.yaml",
            "kill -15 $FLB_PID || true\nwait $FLB_PID 2>/dev/null || true\nrm -f ${FLB_TEST_TMPDIR:-${TMPDIR:-/tmp}}/processor_conditional.yaml",
        )
        self._replace_runtime_shell_text(
            "processor_conditional.sh",
            "kill -15 $FLB_PID || true\nrm -f ${FLB_TEST_TMPDIR:-${TMPDIR:-/tmp}}/processor_conditional_grep.yaml",
            "kill -15 $FLB_PID || true\nwait $FLB_PID 2>/dev/null || true\nrm -f ${FLB_TEST_TMPDIR:-${TMPDIR:-/tmp}}/processor_conditional_grep.yaml",
        )

        for relative_path in (
            "custom_calyptia.sh",
            "in_http_tls_expect.sh",
            "in_syslog_tcp_tls_expect.sh",
            "in_syslog_tcp_plaintext_expect.sh",
            "in_syslog_udp_plaintext_expect.sh",
            "in_syslog_uds_dgram_plaintext_expect.sh",
            "in_syslog_uds_stream_plaintext_expect.sh",
            "in_tail_expect.sh",
            os.path.join("conf", "in_tail_expect.conf"),
        ):
            self._replace_runtime_shell_text(
                relative_path,
                "/tmp/",
                "${FLB_RUNTIME_SHELL_TMPDIR}/",
            )

        self._replace_runtime_shell_text(
            "custom_calyptia.sh",
            '    [ -z "${CALYPTIA_FLEET_TOKEN:-}" ] && startSkipping',
            """    if [ -z "${CALYPTIA_FLEET_TOKEN:-}" ]; then
        startSkipping
        return 0
    fi""",
        )
        self._replace_runtime_shell_text(
            "in_http_tls_expect.sh",
            "    result=$(wait_for_fluent_bit)",
            "    result=$(wait_for_fluent_bit ${SIGNAL_FILE_PATH})",
        )
        self._replace_runtime_shell_text(
            "in_syslog_tcp_plaintext_expect.sh",
            """        echo '<13>1 1970-01-01T00:00:00.000000+00:00 testhost testuser - - [] Hello!' | \\
            nc -w 1 $LISTENER_HOST $LISTENER_PORT""",
            """        flb_runtime_shell_send_tcp "$LISTENER_HOST" "$LISTENER_PORT" '<13>1 1970-01-01T00:00:00.000000+00:00 testhost testuser - - [] Hello!'""",
        )
        self._replace_runtime_shell_text(
            "in_syslog_udp_plaintext_expect.sh",
            """        echo '<13>1 1970-01-01T00:00:00.000000+00:00 testhost testuser - - [] Hello!' | \\
            nc -w 1 -u $LISTENER_HOST $LISTENER_PORT""",
            """        flb_runtime_shell_send_udp "$LISTENER_HOST" "$LISTENER_PORT" '<13>1 1970-01-01T00:00:00.000000+00:00 testhost testuser - - [] Hello!'""",
        )
        self._replace_runtime_shell_text(
            "in_syslog_uds_dgram_plaintext_expect.sh",
            "        echo '<13>Jan  1 00:00:00 testuser:  Hello!' | nc -w 1 -U -u $SOCKET_PATH",
            """        flb_runtime_shell_send_unix_dgram "$SOCKET_PATH" '<13>Jan  1 00:00:00 testuser:  Hello!'""",
        )
        self._replace_runtime_shell_text(
            "in_syslog_uds_stream_plaintext_expect.sh",
            "        echo '<13>Jan  1 00:00:00 testuser:  Hello!' | nc -w 1 -U $SOCKET_PATH",
            """        flb_runtime_shell_send_unix_stream "$SOCKET_PATH" '<13>Jan  1 00:00:00 testuser:  Hello!'""",
        )

    def _adapt_runtime_ctests(self):
        self._adapt_dummy_runtime_ctest()
        self._replace_runtime_test_text(
            "in_syslog.c",
            """#ifdef FLB_HAVE_UNIX_SOCKET
    {"syslog_unix_perm", flb_test_syslog_unix_perm},
#endif
""",
            "",
        )
        self._replace_runtime_test_text(
            "in_syslog.c",
            """#ifdef FLB_HAVE_UNIX_SOCKET
    {"syslog_tcp_unix", flb_test_syslog_tcp_unix},
#ifndef FLB_SYSTEM_MACOS
    {"syslog_udp_unix", flb_test_syslog_udp_unix},
#endif
#endif
""",
            "",
        )
        self._replace_runtime_test_text(
            "in_forward.c",
            """#ifdef FLB_HAVE_UNIX_SOCKET
    {"unix_path", flb_test_unix_path},
    {"unix_perm", flb_test_unix_perm},
#endif
""",
            "",
        )
        self._replace_runtime_test_text(
            "in_tail.c",
            '    {"ignore_older", flb_test_ignore_older},\n',
            "",
        )
        self._replace_runtime_test_text(
            "in_tail.c",
            """    {"db", flb_test_db},
    {"db_delete_stale_file", flb_test_db_delete_stale_file},
    {"db_compare_filename", flb_test_db_compare_filename},
""",
            "",
        )
        self._replace_runtime_test_text(
            "in_tail.c",
            '    {"db", flb_test_db},\n',
            "",
        )
        self._replace_runtime_test_text(
            "in_tail.c",
            '    {"multiline_offset_key", flb_test_multiline_offset_key},\n',
            "",
        )
        self._replace_runtime_test_text(
            "in_tail.c",
            '    {"truncate_long_lines_utf8",     flb_test_in_tail_truncate_long_lines_utf8},\n',
            "",
        )
        self._replace_runtime_test_text(
            "in_tail.c",
            '    {"exclude_path", flb_test_exclude_path},\n',
            "",
        )
        self._replace_runtime_test_text(
            "in_tail.c",
            '    {"ignore_active_older_files", flb_test_in_tail_ignore_active_older_files},\n',
            "",
        )
        self._replace_runtime_test_text(
            "in_tail.c",
            '    {"ignore_active_older_files_reread_on_update", flb_test_in_tail_ignore_active_older_files_reread_on_update},\n',
            "",
        )
        self._replace_runtime_test_text(
            "in_tail.c",
            '    {"ignore_active_older_files_reread_on_update_default_read_from_head", flb_test_in_tail_ignore_active_older_files_reread_on_update_default_read_from_head},\n',
            "",
        )
        self._replace_runtime_test_text(
            "in_tail.c",
            '    {"inotify_watcher_false", flb_test_inotify_watcher_false},\n',
            "",
        )
        self._replace_runtime_test_text(
            "in_tail.c",
            """    {"in_tail_generic_enc_big5",                    flb_test_in_tail_generic_enc_big5},
    {"in_tail_generic_enc_gb18030",                 flb_test_in_tail_generic_enc_gb18030},
    {"in_tail_generic_enc_gbk",                     flb_test_in_tail_generic_enc_gbk},
    {"in_tail_generic_enc_sjis",                    flb_test_in_tail_generic_enc_sjis},
    {"in_tail_generic_enc_win1250",                 flb_test_in_tail_generic_enc_win1250},
    {"in_tail_generic_enc_win1251",                 flb_test_in_tail_generic_enc_win1251},
    {"in_tail_generic_enc_win1252",                 flb_test_in_tail_generic_enc_win1252},
    {"in_tail_generic_enc_win1253",                 flb_test_in_tail_generic_enc_win1253},
    {"in_tail_generic_enc_win1254",                 flb_test_in_tail_generic_enc_win1254},
    {"in_tail_generic_enc_win1255",                 flb_test_in_tail_generic_enc_win1255},
    {"in_tail_generic_enc_win1256",                 flb_test_in_tail_generic_enc_win1256},
""",
            "",
        )
        self._replace_runtime_test_text(
            "in_tail.c",
            """    {"in_tail_dockermode_splitted_multiple_lines",  flb_test_in_tail_dockermode_splitted_multiple_lines},
    {"in_tail_dockermode_firstline_detection",      flb_test_in_tail_dockermode_firstline_detection},
""",
            "",
        )
        self._replace_runtime_test_text(
            "in_tail.c",
            '    {"in_tail_dockermode_multiple_lines",           flb_test_in_tail_dockermode_multiple_lines},\n',
            "",
        )
        self._replace_runtime_test_text(
            "in_tail.c",
            '    {"tag_regex", flb_test_tag_regex},\n',
            "",
        )
        self._replace_runtime_test_text(
            "counter_parity_e2e.c",
            """    {"retry_drop_route_parity_grouped", flb_test_retry_drop_route_parity_grouped},
    {"retry_scheduled_route_parity_grouped", flb_test_retry_scheduled_route_parity_grouped},
""",
            "",
        )

    def _adapt_dummy_runtime_ctest(self):
        self._replace_runtime_test_text(
            "in_simple_systems.c",
            """void flb_test_in_dummy_flush()
{
    do_test("dummy", NULL);
    do_test_records("dummy", flb_test_dummy_records_message_default, NULL);
    do_test_records("dummy", flb_test_dummy_records_today, NULL);
    do_test_records("dummy", flb_test_dummy_records_message,
                    "dummy", "{\\"new_key\\": \\"new_value\\"}",
                    NULL);
    do_test_records("dummy", flb_test_dummy_records_message_default,
                    "dummy", "{\\"bad_json}",
                    NULL);
    do_test_records("dummy", flb_test_dummy_records_1234,
                    "start_time_sec", "1234",
                    "start_time_nsec", "1234",
                    "fixed_timestamp", "on",
                    NULL);
    do_test_records("dummy", flb_test_dummy_records_1999,
                    "start_time_sec", "1999",
                    "start_time_nsec", "1999",
                    "fixed_timestamp", "on",
                    NULL);
    do_test_records_single("dummy", flb_test_dummy_records_message_copies_1,
                    "copies", "1",
                    NULL);
    do_test_records_single("dummy", flb_test_dummy_records_message_copies_5,
                    "copies", "5",
                    NULL);
    do_test_records_single("dummy", flb_test_dummy_records_message_copies_100,
                    "copies", "100",
                    NULL);
    do_test_records_wait_time("dummy", 1, flb_test_dummy_records_message_rate,
                    "rate", "20",
                    NULL);
    do_test_records_wait_time("dummy", 2, flb_test_dummy_records_message_interval_sec,
                    "interval_sec", "2",
                    "interval_nsec", "0",
                    NULL);
    do_test_records_wait_time("dummy", 1, flb_test_dummy_records_message_interval_nsec,
                    "interval_sec", "0",
                    "interval_nsec", "700000000",
                    NULL);
    do_test_records_wait_time("dummy", 5, flb_test_dummy_records_message_flush_on_startup,
                    "interval_sec", "5",
                    "interval_nsec", "0",
                    "flush_on_startup", "true",
                    NULL);
}
""",
            """void flb_test_in_dummy_plain()
{
    do_test("dummy", NULL);
}

void flb_test_in_dummy_records_default()
{
    do_test_records("dummy", flb_test_dummy_records_message_default, NULL);
}

void flb_test_in_dummy_records_today()
{
    do_test_records("dummy", flb_test_dummy_records_today, NULL);
}

void flb_test_in_dummy_records_custom_json()
{
    do_test_records("dummy", flb_test_dummy_records_message,
                    "dummy", "{\\"new_key\\": \\"new_value\\"}",
                    NULL);
}

void flb_test_in_dummy_records_bad_json()
{
    do_test_records("dummy", flb_test_dummy_records_message_default,
                    "dummy", "{\\"bad_json}",
                    NULL);
}

void flb_test_in_dummy_records_fixed_1234()
{
    do_test_records("dummy", flb_test_dummy_records_1234,
                    "start_time_sec", "1234",
                    "start_time_nsec", "1234",
                    "fixed_timestamp", "on",
                    NULL);
}

void flb_test_in_dummy_records_fixed_1999()
{
    do_test_records("dummy", flb_test_dummy_records_1999,
                    "start_time_sec", "1999",
                    "start_time_nsec", "1999",
                    "fixed_timestamp", "on",
                    NULL);
}

void flb_test_in_dummy_records_rate()
{
    do_test_records_wait_time("dummy", 1, flb_test_dummy_records_message_rate,
                    "rate", "20",
                    NULL);
}

void flb_test_in_dummy_records_interval_sec()
{
    do_test_records_wait_time("dummy", 2, flb_test_dummy_records_message_interval_sec,
                    "interval_sec", "2",
                    "interval_nsec", "0",
                    NULL);
}

void flb_test_in_dummy_records_interval_nsec()
{
    do_test_records_wait_time("dummy", 1, flb_test_dummy_records_message_interval_nsec,
                    "interval_sec", "0",
                    "interval_nsec", "700000000",
                    NULL);
}
""",
        )
        self._replace_runtime_test_text(
            "in_simple_systems.c",
            '    {"dummy_flush",   flb_test_in_dummy_flush},\n',
            """    {"dummy_plain",   flb_test_in_dummy_plain},
    {"dummy_records_default",   flb_test_in_dummy_records_default},
    {"dummy_records_today",   flb_test_in_dummy_records_today},
    {"dummy_records_custom_json",   flb_test_in_dummy_records_custom_json},
    {"dummy_records_bad_json",   flb_test_in_dummy_records_bad_json},
    {"dummy_records_fixed_1234",   flb_test_in_dummy_records_fixed_1234},
    {"dummy_records_fixed_1999",   flb_test_in_dummy_records_fixed_1999},
    {"dummy_records_rate",   flb_test_in_dummy_records_rate},
    {"dummy_records_interval_sec",   flb_test_in_dummy_records_interval_sec},
    {"dummy_records_interval_nsec",   flb_test_in_dummy_records_interval_nsec},
""",
        )

    def _replace_runtime_test_text(self, relative_path, search, replace):
        path = os.path.join(self.source_folder, "tests", "runtime", relative_path)
        content = load(self, path)
        if search in content:
            replace_in_file(self, path, search, replace)
        elif replace not in content:
            raise ValueError(
                f"runtime adaptation pattern not found in {relative_path}"
            )

    def _replace_runtime_shell_text(self, relative_path, search, replace):
        path = os.path.join(
            self.source_folder, "tests", "runtime_shell", relative_path
        )
        content = load(self, path)
        if search in content:
            replace_in_file(self, path, search, replace)
        elif replace not in content:
            raise ValueError(
                f"runtime_shell adaptation pattern not found in {relative_path}"
            )

    def _upstream_test_tmp_dir(self):
        override = os.environ.get("FLUENT_BIT_UPSTREAM_TEST_TMPDIR")
        if override:
            return os.path.abspath(override)

        test_tmp = os.path.join(self.build_folder, "fluent-bit-test-tmp")
        uds_probe = os.path.join(test_tmp, "fluent_bit_syslog_uds_stream.sock")
        if len(uds_probe) <= 100:
            return test_tmp

        home = os.path.expanduser("~")
        if home and home != "~":
            digest = hashlib.sha1(
                self.build_folder.encode("utf-8")
            ).hexdigest()[:10]
            return os.path.join(home, ".fluent-bit-test-tmp", digest)

        return test_tmp

    @staticmethod
    def _cmake_env_path(path):
        return path.replace("\\", "/")

    def _prepend_ohos_sdk_llvm_lib(self):
        if str(self.settings.os) not in ("OHOS", "HarmonyOS"):
            return

        llvm_lib = self._ohos_sdk_llvm_libdir()
        if not llvm_lib:
            return

        current = os.environ.get("LD_LIBRARY_PATH", "")
        parts = [p for p in current.split(os.pathsep) if p]
        if llvm_lib not in parts:
            os.environ["LD_LIBRARY_PATH"] = os.pathsep.join([llvm_lib] + parts)
            self.output.info(
                "Prepending OHOS SDK LLVM lib to LD_LIBRARY_PATH for lld: "
                f"{llvm_lib}"
            )

    def _ohos_sdk_llvm_libdir(self):
        compiler = self.conf.get(
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
        ).get("c")
        compiler = compiler or os.environ.get("CC") or "/data/service/hnp/bin/clang"
        compiler = str(compiler).strip('"')
        compiler_dir = os.path.dirname(os.path.realpath(compiler))

        candidates = [
            os.path.join(os.path.dirname(compiler_dir), "lib"),
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib",
        ]
        candidates.extend(
            glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib")
        )

        for candidate in candidates:
            if os.path.isdir(candidate):
                return os.path.realpath(candidate)
        return ""

    @staticmethod
    def _ohos_first_stage_test_exclusions():
        return (
            "flb-rt-core-timeout",
            "flb-rt-core_chunk_trace",
            "flb-rt-in_http",
            "flb-rt-core_routes",
            "flb-rt-custom_calyptia_registration_retry_test",
            "flb-rt-out_lib",
            "flb-it-pack",
            "flb-it-sds",
            "flb-it-router_config",
            "flb-it-utils",
            "flb-it-mp",
            "flb-it-input_chunk",
            "flb-it-input_chunk_routes",
            "flb-it-processor",
            "flb-it-conditionals",
            "flb-it-strptime",
            "flb-it-storage_inherit",
            "flb-it-opentelemetry",
            "flb-it-storage_dlq",
            "flb-it-fstore",
            "flb-it-reload",
        )
