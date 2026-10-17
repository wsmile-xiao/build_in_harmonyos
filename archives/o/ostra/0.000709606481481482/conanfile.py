#!/usr/bin/env python3
"""Conan recipe - ostra 0.000709606481481482.

This package targets the `components/ostra-sysctl` CMake project from the
Ostra repository snapshot.
"""
import os
from textwrap import dedent

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, get, replace_in_file


class OstraConan(ConanFile):
    name = "ostra"
    version = "0.000709606481481482"
    description = "Read-only Ostra system-monitoring utility"
    license = "unknown"
    homepage = "https://github.com/tej-1916/ostra"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True
    exports_sources = "patches/*"

    def configure(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "ostra only supports Linux/OHOS because the upstream code reads /proc and /sys"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)
        metrics_path = os.path.join(
            self.source_folder,
            "components",
            "ostra-sysctl",
            "src",
            "metrics.c",
        )

        replace_in_file(
            self,
            metrics_path,
            dedent(
                """
                static int collect_cpu_usage(double *usage_percent) {
                    cpu_times_t first;
                    cpu_times_t second;

                    if (read_cpu_times(&first) != 0) {
                        return -1;
                    }

                    struct timespec delay = {
                        .tv_sec = 0,
                        .tv_nsec = 200000000
                    };

                    while (nanosleep(&delay, &delay) != 0 && errno == EINTR) {
                    }

                    if (read_cpu_times(&second) != 0) {
                        return -1;
                    }

                    unsigned long long total_delta = second.total - first.total;
                    unsigned long long idle_delta = second.idle - first.idle;

                    if (total_delta == 0) {
                        *usage_percent = 0.0;
                        return 0;
                    }

                    *usage_percent =
                        100.0 *
                        (double)(total_delta - idle_delta) /
                        (double)total_delta;

                    return 0;
                }
                """
            ).strip("\n"),
            dedent(
                """
                static void collect_cpu_usage(double *usage_percent) {
                    cpu_times_t first;
                    cpu_times_t second;

                    *usage_percent = 0.0;

                    if (read_cpu_times(&first) != 0) {
                        return;
                    }

                    struct timespec delay = {
                        .tv_sec = 0,
                        .tv_nsec = 200000000
                    };

                    while (nanosleep(&delay, &delay) != 0 && errno == EINTR) {
                    }

                    if (read_cpu_times(&second) != 0) {
                        return;
                    }

                    unsigned long long total_delta = second.total - first.total;
                    unsigned long long idle_delta = second.idle - first.idle;

                    if (total_delta == 0) {
                        return;
                    }

                    *usage_percent =
                        100.0 *
                        (double)(total_delta - idle_delta) /
                        (double)total_delta;
                }
                """
            ).strip("\n"),
        )

        replace_in_file(
            self,
            metrics_path,
            dedent(
                """
                static int collect_memory(ostra_metrics_t *metrics) {
                    FILE *file = fopen("/proc/meminfo", "r");

                    if (file == NULL) {
                        return -1;
                    }

                    unsigned long long memory_total_kb = 0;
                    unsigned long long memory_available_kb = 0;
                    unsigned long long swap_total_kb = 0;
                    unsigned long long swap_free_kb = 0;

                    char line[256];

                    while (fgets(line, sizeof(line), file) != NULL) {
                        unsigned long long value = 0;

                        if (sscanf(line, "MemTotal: %llu kB", &value) == 1) {
                            memory_total_kb = value;
                        } else if (
                            sscanf(line, "MemAvailable: %llu kB", &value) == 1
                        ) {
                            memory_available_kb = value;
                        } else if (
                            sscanf(line, "SwapTotal: %llu kB", &value) == 1
                        ) {
                            swap_total_kb = value;
                        } else if (
                            sscanf(line, "SwapFree: %llu kB", &value) == 1
                        ) {
                            swap_free_kb = value;
                        }
                    }

                    fclose(file);

                    if (
                        memory_total_kb == 0 ||
                        memory_available_kb > memory_total_kb ||
                        swap_free_kb > swap_total_kb
                    ) {
                        return -1;
                    }

                    metrics->memory_total_bytes = memory_total_kb * 1024ULL;
                    metrics->memory_used_bytes =
                        (memory_total_kb - memory_available_kb) * 1024ULL;

                    metrics->swap_total_bytes = swap_total_kb * 1024ULL;
                    metrics->swap_used_bytes =
                        (swap_total_kb - swap_free_kb) * 1024ULL;

                    return 0;
                }
                """
            ).strip("\n"),
            dedent(
                """
                static void collect_memory(ostra_metrics_t *metrics) {
                    FILE *file = fopen("/proc/meminfo", "r");

                    if (file == NULL) {
                        return;
                    }

                    unsigned long long memory_total_kb = 0;
                    unsigned long long memory_available_kb = 0;
                    unsigned long long swap_total_kb = 0;
                    unsigned long long swap_free_kb = 0;

                    char line[256];

                    while (fgets(line, sizeof(line), file) != NULL) {
                        unsigned long long value = 0;

                        if (sscanf(line, "MemTotal: %llu kB", &value) == 1) {
                            memory_total_kb = value;
                        } else if (
                            sscanf(line, "MemAvailable: %llu kB", &value) == 1
                        ) {
                            memory_available_kb = value;
                        } else if (
                            sscanf(line, "SwapTotal: %llu kB", &value) == 1
                        ) {
                            swap_total_kb = value;
                        } else if (
                            sscanf(line, "SwapFree: %llu kB", &value) == 1
                        ) {
                            swap_free_kb = value;
                        }
                    }

                    fclose(file);

                    if (
                        memory_total_kb == 0 ||
                        memory_available_kb > memory_total_kb ||
                        swap_free_kb > swap_total_kb
                    ) {
                        return;
                    }

                    metrics->memory_total_bytes = memory_total_kb * 1024ULL;
                    metrics->memory_used_bytes =
                        (memory_total_kb - memory_available_kb) * 1024ULL;

                    metrics->swap_total_bytes = swap_total_kb * 1024ULL;
                    metrics->swap_used_bytes =
                        (swap_total_kb - swap_free_kb) * 1024ULL;
                }
                """
            ).strip("\n"),
        )

        replace_in_file(
            self,
            metrics_path,
            dedent(
                """
                int ostra_collect_metrics(
                    ostra_metrics_t *metrics,
                    char *error,
                    size_t error_size
                ) {
                    if (metrics == NULL) {
                        return set_error(error, error_size, "metrics pointer is null");
                    }

                    memset(metrics, 0, sizeof(*metrics));

                    if (gethostname(metrics->hostname, sizeof(metrics->hostname)) != 0) {
                        return set_error(
                            error,
                            error_size,
                            "failed to read hostname: %s",
                            strerror(errno)
                        );
                    }

                    metrics->hostname[sizeof(metrics->hostname) - 1] = '\\0';

                    struct utsname system_information;

                    if (uname(&system_information) != 0) {
                        return set_error(
                            error,
                            error_size,
                            "failed to read kernel information: %s",
                            strerror(errno)
                        );
                    }

                    snprintf(
                        metrics->kernel,
                        sizeof(metrics->kernel),
                        "%s %s",
                        system_information.sysname,
                        system_information.release
                    );

                    struct sysinfo system_status;

                    if (sysinfo(&system_status) != 0) {
                        return set_error(
                            error,
                            error_size,
                            "failed to read system uptime: %s",
                            strerror(errno)
                        );
                    }

                    metrics->uptime_seconds =
                        system_status.uptime > 0
                            ? (uint64_t)system_status.uptime
                            : 0;

                    double loads[3] = {0.0, 0.0, 0.0};

                    if (getloadavg(loads, 3) != 3) {
                        return set_error(error, error_size, "failed to read system load");
                    }

                    metrics->load_1m = loads[0];
                    metrics->load_5m = loads[1];
                    metrics->load_15m = loads[2];

                    if (collect_cpu_usage(&metrics->cpu_usage_percent) != 0) {
                        return set_error(error, error_size, "failed to read CPU usage");
                    }

                    if (collect_memory(metrics) != 0) {
                        return set_error(error, error_size, "failed to read memory usage");
                    }

                    if (
                        collect_disk(
                            "/",
                            &metrics->root_total_bytes,
                            &metrics->root_used_bytes
                        ) != 0
                    ) {
                        return set_error(
                            error,
                            error_size,
                            "failed to read root disk usage"
                        );
                    }

                    metrics->data_disk_available =
                        collect_disk(
                            "/srv/ostra",
                            &metrics->data_total_bytes,
                            &metrics->data_used_bytes
                        ) == 0;

                    collect_temperature(metrics);

                    return 0;
                }
                """
            ).strip("\n"),
            dedent(
                """
                int ostra_collect_metrics(
                    ostra_metrics_t *metrics,
                    char *error,
                    size_t error_size
                ) {
                    if (metrics == NULL) {
                        return set_error(error, error_size, "metrics pointer is null");
                    }

                    memset(metrics, 0, sizeof(*metrics));

                    if (gethostname(metrics->hostname, sizeof(metrics->hostname)) != 0) {
                        snprintf(metrics->hostname, sizeof(metrics->hostname), "unknown");
                    }

                    metrics->hostname[sizeof(metrics->hostname) - 1] = '\\0';

                    struct utsname system_information;

                    if (uname(&system_information) != 0) {
                        snprintf(metrics->kernel, sizeof(metrics->kernel), "unknown");
                    } else {
                        snprintf(
                            metrics->kernel,
                            sizeof(metrics->kernel),
                            "%s %s",
                            system_information.sysname,
                            system_information.release
                        );
                    }

                    struct sysinfo system_status;

                    if (sysinfo(&system_status) == 0 && system_status.uptime > 0) {
                        metrics->uptime_seconds =
                            (uint64_t)system_status.uptime;
                    }

                    double loads[3] = {0.0, 0.0, 0.0};

                    if (getloadavg(loads, 3) == 3) {
                        metrics->load_1m = loads[0];
                        metrics->load_5m = loads[1];
                        metrics->load_15m = loads[2];
                    }

                    collect_cpu_usage(&metrics->cpu_usage_percent);
                    collect_memory(metrics);
                    collect_disk(
                        "/",
                        &metrics->root_total_bytes,
                        &metrics->root_used_bytes
                    );

                    metrics->data_disk_available =
                        collect_disk(
                            "/srv/ostra",
                            &metrics->data_total_bytes,
                            &metrics->data_used_bytes
                        ) == 0;

                    collect_temperature(metrics);

                    return 0;
                }
                """
            ).strip("\n"),
        )

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure(build_script_folder="components/ostra-sysctl")
        cmake.build()
        if self.settings.os != "OHOS" and can_run(self):
            cmake.test()
        else:
            self.output.info("Skipping upstream ctest on OHOS; runtime probes are covered in test_package")

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
