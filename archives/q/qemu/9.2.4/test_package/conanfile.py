"""test_package for the qemu package — validates the packaged emulator by
actually executing ARM code with it.

The decisive assertion is the ARM execution one: a small ARM Linux program is
assembled and linked with the already-published ``arm-none-eabi-binutils``
package and then run under the packaged ``qemu-arm``.  That is the whole point
of this package on HarmonyOS PC -- a cross toolchain such as
``gcc-11-cross`` (target ``arm-none-eabi``) can produce ARM output but cannot
execute it, because the host has no AArch32 compatibility layer.

Implementation notes:
* ``ConanFile.run()`` only returns an exit code (it streams to the log), so
  ``subprocess`` is used wherever the *output text* is the assertion subject.
  Same approach as the gcc-11-cross test_package.
* ``arm-none-eabi-binutils`` is a *tool* requirement, so it is looked up via
  ``self.dependencies.build[...]``.
"""
import os
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException


class QemuTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build_requirements(self):
        # Only the assembler, linker and readelf are needed: the probe program
        # issues Linux system calls directly, so no C library and no C
        # compiler take part in this test.
        self.tool_requires("arm-none-eabi-binutils/2.46.1")

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def _package_dir(self, name, build=False):
        deps = self.dependencies.build if build else self.dependencies
        return deps[name].package_folder

    def _runtime_env(self):
        """Environment the packaged binaries need in order to start.

        The system emulators link against pixman and libslirp, so without those
        directories on LD_LIBRARY_PATH they abort before main() with

            Error loading shared library libpixman-1.so.0: No such file or directory

        which would otherwise show up as unrelated assertion failures (the
        machine and CPU lists stay empty because the binary never ran).
        """
        env = dict(os.environ)
        libdirs = []
        for dep in self.dependencies.values():
            for libdir in dep.cpp_info.libdirs:
                if os.path.isdir(libdir) and libdir not in libdirs:
                    libdirs.append(libdir)
        if libdirs:
            existing = env.get("LD_LIBRARY_PATH", "")
            joined = ":".join(libdirs)
            env["LD_LIBRARY_PATH"] = joined + (":" + existing if existing else "")
        return env

    def _capture(self, command, timeout=180):
        """Run ``command`` and return ``(returncode, combined output)``.

        ``ConanFile.run()`` streams to the Conan log and only yields an exit
        code, which is not enough when the output itself is what gets
        asserted, so subprocess is used here.
        """
        try:
            done = subprocess.run(
                command,
                shell=True,
                executable="/data/service/hnp/bin/bash",
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=timeout,
                env=self._runtime_env(),
            )
        except (subprocess.TimeoutExpired, OSError) as exc:
            return 1, "command could not run: {} ({})".format(command, exc)
        return done.returncode, done.stdout.decode("utf-8", "replace")

    # ------------------------------------------------------------------
    # the test
    # ------------------------------------------------------------------
    def test(self):
        qemu_dir = self._package_dir(self.tested_reference_str)
        binutils_dir = self._package_dir("arm-none-eabi-binutils", build=True)

        checks = []

        def check(label, ok, detail=""):
            checks.append((label, bool(ok), detail))
            self.output.info("  [{}] {}{}".format(
                "PASS" if ok else "FAIL", label,
                (" -- " + str(detail).replace("\n", " ")[:90]) if detail else "",
            ))

        def tool(name, build=False):
            base = binutils_dir if build else qemu_dir
            path = os.path.join(base, "bin", name)
            if not os.path.isfile(path):
                raise ConanException("missing packaged binary: {}".format(path))
            return path

        # ---- 1. every packaged tool is present and reports its version -----
        for name in ("qemu-system-arm", "qemu-system-aarch64", "qemu-arm",
                     "qemu-aarch64", "qemu-img"):
            path = tool(name)
            rc, out = self._capture("{} --version".format(path))
            first = out.strip().splitlines()[0] if out.strip() else "no output"
            check("{} --version reports 9.2.4".format(name),
                  rc == 0 and "9.2.4" in out, first)

        # ---- 2. the ARM system emulator exposes machines and CPUs ---------
        arm_system = tool("qemu-system-arm")
        rc, machines = self._capture("{} -M help".format(arm_system))
        check("qemu-system-arm -M help exits cleanly", rc == 0, "rc={}".format(rc))
        check("machine list contains the 'virt' board", "virt" in machines,
              "{} machines listed".format(len(machines.splitlines())))
        check("machine list contains 'versatilepb'", "versatilepb" in machines)
        rc, cpus = self._capture("{} -cpu help".format(arm_system))
        check("CPU list contains cortex-a15", "cortex-a15" in cpus)
        check("CPU list contains cortex-m3", "cortex-m3" in cpus)

        # ---- 3. qemu-img really manipulates a disk image -------------------
        qemu_img = tool("qemu-img")
        img = os.path.join(self.build_folder, "probe.qcow2")
        # `create` runs through ConanFile.run() with scope="run", which sources
        # the generated conanrun environment: that is what puts every
        # dependency's libdir on LD_LIBRARY_PATH.  The default scope is "build",
        # whose environment does not carry the link-time dependency libdirs, so
        # the binaries abort before main() once they link libzstd/libgcrypt (the
        # compression and crypto backends enabled for this package):
        #
        #   Error loading shared library libzstd.so.1: (needed by .../qemu-img)
        #   Error relocating .../qemu-img: ZSTD_createCCtx: symbol not found
        #
        # run() is also what puts the command in the CI log, and the L0 gate
        # requires the test to really invoke something rather than stub itself
        # out, so this stays a run() call rather than a bare subprocess.
        rc = self.run('"{}" create -f qcow2 "{}" 16M'.format(qemu_img, img),
                      scope="run", ignore_errors=True)
        check("qemu-img create writes a qcow2 image",
              rc == 0 and os.path.isfile(img), "rc={}".format(rc))
        rc, info = self._capture("{} info {}".format(qemu_img, img))
        check("qemu-img info reports the qcow2 format",
              rc == 0 and "qcow2" in info, info.strip()[:80])
        check("qemu-img info reports the 16 MiB virtual size",
              "16 MiB" in info or "16777216" in info)

        # ---- 4. firmware/data files shipped inside the package ------------
        # QEMU's install rule puts the pc-bios payload (firmware, device trees,
        # option ROMs) directly under share/qemu, not in a pc-bios/ subdirectory
        # -- the binaries find it there through the relocatable prefix they were
        # built with.  Both facts were checked against the installed tree.
        share_qemu = os.path.join(qemu_dir, "share", "qemu")
        check("packaged share/qemu contains the ARM UEFI firmware",
              os.path.isfile(os.path.join(share_qemu, "edk2-arm-code.fd")),
              share_qemu)
        check("packaged share/qemu contains the AArch64 UEFI firmware",
              os.path.isfile(os.path.join(share_qemu, "edk2-aarch64-code.fd")))
        check("packaged share/qemu contains device-tree blobs",
              os.path.isfile(os.path.join(share_qemu, "bamboo.dtb")))
        check("packaged share/qemu contains the i386 option ROMs",
              os.path.isfile(os.path.join(share_qemu, "pxe-e1000.rom")))

        # ---- 5. THE goal: execute ARM code on this host -------------------
        source = os.path.join(self.recipe_folder, "hello_arm.s")
        obj = os.path.join(self.build_folder, "hello_arm.o")
        elf = os.path.join(self.build_folder, "hello_arm.elf")
        assembler = tool("arm-none-eabi-as", build=True)
        linker = tool("arm-none-eabi-ld", build=True)
        readelf = tool("arm-none-eabi-readelf", build=True)

        rc, out = self._capture("{} -o {} {}".format(assembler, obj, source))
        check("arm-none-eabi-as assembles the ARM probe",
              rc == 0 and os.path.isfile(obj), out.strip()[-70:])

        rc, out = self._capture(
            "{} -static -e _start -o {} {}".format(linker, elf, obj))
        check("arm-none-eabi-ld links a static ARM ELF",
              rc == 0 and os.path.isfile(elf), out.strip()[-70:])

        rc, header = self._capture("{} -h {}".format(readelf, elf))
        elf_summary = " ".join(
            line.strip() for line in header.splitlines()
            if "Machine" in line or "Type" in line or "Class" in line)
        check("the linked file is a 32-bit ARM executable",
              "ARM" in header and "ELF32" in header and "EXEC" in header,
              elf_summary)

        rc, output = self._capture("{} {}".format(tool("qemu-arm"), elf))
        check("qemu-arm EXECUTES the ARM binary and prints its message",
              rc == 0 and "qemu-arm-ok" in output, repr(output.strip()[:60]))

        # The same ELF is also executed through the AArch64 user-mode
        # emulator's companion check: qemu-aarch64 must reject a 32-bit ARM
        # binary rather than silently mis-handle it (negative control).
        rc, output = self._capture(
            "{} {} 2>&1".format(tool("qemu-aarch64"), elf))
        check("qemu-aarch64 rejects a 32-bit ARM binary (negative control)",
              "qemu-arm-ok" not in output, output.strip()[:70])

        # ---- 6. OHOS hardening: shipped binaries carry .codesign ----------
        if self.settings.os == "OHOS":
            reader = (shutil.which("llvm-readelf")
                      or "/data/service/hnp/bin/llvm-readelf")
            _, sections = self._capture(
                "{} -S {}".format(reader, tool("qemu-system-arm")))
            check("qemu-system-arm carries an OHOS .codesign section",
                  ".codesign" in sections,
                  "sections: {}".format(len(sections.splitlines())))
            _, sections = self._capture(
                "{} -S {}".format(reader, tool("qemu-arm")))
            check("qemu-arm carries an OHOS .codesign section",
                  ".codesign" in sections)

        # ---- 7. end-to-end consumer case ---------------------------------
        # One complete workflow rather than another batch of assertions: the
        # packaged engine builds a disk image, writes fixed patterns, verifies
        # it, converts it to raw / compressed qcow2 / vmdk and the resulting
        # payloads are compared byte for byte against a reference built
        # independently of QEMU (python bytes, not QEMU output -- using the
        # tool's own output as the golden file would certify nothing).  A
        # second conversion is compared with the first to show determinism,
        # and a mismatching pattern proves the negative control fires.
        consumer = os.path.join(self.recipe_folder, "consumer_roundtrip.py")
        consumer_work = os.path.join(self.build_folder, "consumer")
        rc, out = self._capture('"{}" "{}" "{}" "{}"'.format(
            sys.executable, consumer, os.path.join(qemu_dir, "bin"), consumer_work))
        check("the end-to-end consumer round trip passes all of its checks",
              rc == 0 and "12/12 checks passed" in out, out.strip()[-90:])

        # ---- summary -----------------------------------------------------
        total = len(checks)
        passed = sum(1 for _, ok, _ in checks if ok)
        self.output.info("=" * 74)
        self.output.info(
            "qemu functional test: {}/{} assertions passed".format(passed, total))
        self.output.info("=" * 74)
        failed = [label for label, ok, _ in checks if not ok]
        if failed:
            raise ConanException("{} assertion(s) failed: {}".format(
                len(failed), "; ".join(failed)))
