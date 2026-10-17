#!/usr/bin/env python3
"""Consumer test for evmc 12.1.0.

Builds a real EVMC host against the packaged `evmc::evmc` / `evmc::loader` /
`evmc::instructions` / `evmc::mocked_host` targets, then runs it under the
configured cross-compiling emulator (qemu + OHOS musl run root) -- or natively
on an OHOS aarch64 build machine such as the CI workers -- so the end-to-end
case in evmc_consumer_case.cpp is genuinely executed rather than only compiled.
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import get


# Pinned to the same upstream tag the recipe under test builds, so the consumer
# exercises a VM built from exactly the sources the package was produced from.
#
# The URLs are tried in order. The FIRST entry reproduces the rewrite the CI
# performs on the recipe's conandata.yml (its "Mirror fallback" step maps
# github.com -> https://gh-proxy.com/<original>), because the CI worker's direct
# route to github.com times out on connect. A test_package that hard-codes only
# the canonical github.com URL therefore cannot fetch its sources on the worker
# -- which is exactly how CI build #89169 failed, inside generate(), *after* the
# recipe itself had already downloaded this same tarball through the injected
# mirror.
#
# The canonical github.com URL stays last so a direct route (a normal
# workstation, or any environment without the proxy) still works, and so the
# official upstream URL remains the source of truth rather than a mirror.
#
# Every entry is content-addressed by the same sha256, so whichever one answers
# yields a tree byte-identical to the one the package was built from: the
# fallback cannot silently substitute different sources.
_EVMC_SOURCE_URLS = (
    "https://gh-proxy.com/https://github.com/ipsilon/evmc/archive/refs/tags/v12.1.0.tar.gz",
    "https://github.com/ipsilon/evmc/archive/refs/tags/v12.1.0.tar.gz",
)
_EVMC_SOURCE_SHA256 = "0d5458015bf38a5358fad04cc290d21ec40122d1eb6420e0b33ae25546984bcd"


class EvmcTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        # The consumer dlopen()s a real VM at run time through the packaged
        # loader. Upstream builds examples/example_vm/ into a SHARED library but
        # never installs it (the install() rules cover only include/evmc and the
        # lib/ archives), so the consumer cannot obtain it from the evmc package.
        # The test_package fetches the same upstream tag and builds that example
        # VM itself, keeping the run-time dlopen() leg genuinely end-to-end
        # instead of stubbing the VM out.
        tc.cache_variables["EVMC_UPSTREAM_SOURCE_DIR"] = self._upstream_sources()
        tc.generate()

    def _upstream_sources(self):
        """Directory of the upstream evmc tree used to build the example VM.

        The tarball is extracted into a dedicated sub-directory of the *build*
        folder rather than into the test_package source folder: a test_package
        has source_folder == recipe_folder, so extracting with strip_root=True
        alongside it would drop upstream's top-level CMakeLists.txt next to the
        consumer's own and CMake would configure that one instead. Keeping it
        under the build folder also keeps the checked-in recipe directory clean.
        """
        dest = os.path.join(self.build_folder, "upstream_evmc")

        # Conan keeps its own verified download cache, so a repeated build does
        # not hit the network; passing the sha256 keeps that guarantee here too,
        # on every URL in the list.
        errors = []
        for index, url in enumerate(_EVMC_SOURCE_URLS):
            try:
                get(
                    self,
                    url=url,
                    sha256=_EVMC_SOURCE_SHA256,
                    destination=dest,
                    strip_root=True,
                )
            except ConanException as error:
                errors.append("%s: %s" % (url, error))
                if index + 1 < len(_EVMC_SOURCE_URLS):
                    self.output.warning(
                        "could not fetch the upstream evmc sources from %s (%s); "
                        "trying the next URL" % (url, error)
                    )
            else:
                if index:
                    self.output.info(
                        "upstream evmc sources fetched from fallback URL %s" % url
                    )
                return dest.replace("\\", "/")

        # Never fall through to a build that would silently skip the dlopen()
        # leg: without the upstream tree the example VM cannot be built and the
        # consumer would have nothing to load, which would turn a fetch failure
        # into a fake green run.
        raise ConanException(
            "could not fetch the upstream evmc sources from any known URL, so "
            "the consumer cannot build the example VM and the dlopen() leg "
            "would be silently skipped. Attempts:\n  " + "\n  ".join(errors)
        )

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _emulator(self):
        """The configured CMAKE_CROSSCOMPILING_EMULATOR, or None.

        The ohos-aarch64-run profile wires up qemu together with the OHOS musl
        run root; the CI profile (ohos-aarch64) does not, because the CI worker
        *is* an OHOS aarch64 machine and executes the target binaries natively.
        """
        extra = self.conf.get("tools.cmake.cmaketoolchain:extra_variables", default={})
        emulator = extra.get("CMAKE_CROSSCOMPILING_EMULATOR")
        if not emulator:
            return None
        return emulator if isinstance(emulator, str) else ";".join(emulator)

    def _native_target_execution(self):
        """Whether the target binaries are meant to run on this build machine.

        can_run() is not usable as the gate: it is False whenever settings.os is
        OHOS, because OHOS is never the os of the machine running Conan --
        including the CI workers, which *are* OHOS aarch64 boxes and do execute
        the freshly built target binaries natively.

        An earlier revision tried to *prove* executability with a synthetic
        probe, running `evmc_consumer_case --help` and treating a non-zero exit
        as "cannot run here". That was wrong: the consumer has no --help, it
        takes exactly one argument (a VM shared library path) and returns 2
        otherwise, so the probe could never succeed and the gate rejected
        workers that had just run the upstream 146/146 suite natively in
        build(). A synthetic probe that has to be kept in sync with the real
        binary's CLI is a liability; the run that matters is the one in test(),
        which fails loudly by itself if the consumer cannot be launched.

        What remains here is the part that is genuinely decidable from the
        configuration: when host and build profiles agree (the CI passes the
        same profile to -pr:h and -pr:b), the target binaries are meant to run
        on this machine. A genuine cross-build with no emulator stays
        fail-closed, so no pass rate is ever claimed without being measured.
        """
        return not cross_building(self)

    @staticmethod
    def _allow_untested():
        """Whether the caller explicitly accepted a run without executing the case.

        An environment variable is used rather than a custom Conan conf because
        Conan 2 rejects confs that are not registered globally, and registering
        one would impose a machine-wide setting for a per-invocation decision.
        """
        return os.environ.get("EVMC_ALLOW_UNTESTED", "").strip().lower() in (
            "1",
            "true",
            "yes",
        )

    def test(self):
        # An emulator (when present) and native execution are both real
        # execution paths; only a genuine cross-build with no emulator is
        # refused, and even then only unless the caller explicitly opts out.
        if not self._emulator() and not self._native_target_execution():
            # Without a way to run the target the consumer can only be linked,
            # never run. Returning quietly here would make `conan create` report
            # success while the end-to-end case (rule 12) executed zero checks,
            # so the skip has to be an explicit opt-in instead of the default.
            if self._allow_untested():
                self.output.warning(
                    "EVMC_ALLOW_UNTESTED is set: consumer case linked but NOT "
                    "executed -- no end-to-end evidence was produced"
                )
                return
            raise ConanException(
                "the consumer end-to-end case cannot be executed here: this is "
                "a cross-build with no CMAKE_CROSSCOMPILING_EMULATOR configured. "
                "Build with the ohos-aarch64-run profile, or set "
                "EVMC_ALLOW_UNTESTED=1 to explicitly accept a build with no "
                "end-to-end evidence."
            )

        bindirs = self.cpp.build.bindirs
        exe = os.path.join(bindirs[0], "evmc_consumer_case")
        # add_subdirectory() places the example VM in its own sub-directory of
        # the consumer's build tree, not next to the consumer binary. The file
        # name follows the platform convention (libexample-vm.so / .dylib /
        # example-vm.dll), so it is searched for rather than assumed.
        vm_dir = os.path.join(bindirs[0], "upstream_example_vm")
        vm_candidates = []
        for pattern in ("libexample-vm.so", "libexample-vm.dylib", "example-vm.dll"):
            vm_candidates.append(os.path.join(vm_dir, pattern))
        vm_lib = next((p for p in vm_candidates if os.path.isfile(p)), None)
        if vm_lib is None:
            raise ConanException(
                "example VM shared library not found under %s (looked for %s); "
                "the consumer cannot exercise the loader/dlopen leg without it"
                % (vm_dir, ", ".join(os.path.basename(p) for p in vm_candidates))
            )
        self.output.info("running consumer against %s" % vm_lib)
        self.run('"{}" "{}"'.format(exe, vm_lib))
