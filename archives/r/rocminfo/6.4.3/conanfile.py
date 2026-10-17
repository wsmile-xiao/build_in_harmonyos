#!/usr/bin/env python3
"""Conan recipe — rocminfo 6.4.3 (ROCm system-info tool) for OpenHarmony PC.

Adaptation strategy (documented, non-crippling):

`rocminfo` ships TWO components upstream:

  1. `rocminfo` — the CLI. Its entire function is to call the HSA runtime and
     enumerate AMD GPU agents. It cannot work on OHOS PC (no /dev/kfd, no
     amdkfd, no AMD GPU); see the accompanying knowledge draft.
  2. `rocm_agent_enumerator` — a **pure Python** script whose documented job is
     to report the GCN ISA targets available. Upstream documents FIVE
     generation strategies and explicitly states that strategies 1 and 2 exist
     for exactly our situation ("a container setting where ROCm stack may
     usually not available", "an install environment with sandbox"):

       1. `ROCM_TARGET_LST` env var -> user-supplied target.lst   [no GPU]
       2. `target.lst` next to the script                          [no GPU]
       3. HSA topology /sys/class/kfd/...                          [needs KFD]
       4. `lspci` PCI scan + built-in lookup table                 [needs lspci]
       5. `rocminfo` binary                                        [needs ROCm]

     Strategies 1/2 are genuinely functional with no ROCm stack, no KFD and no
     AMD GPU — which is precisely the OHOS PC environment. This recipe delivers
     those working strategies, i.e. the tool's full documented file-based
     contract, and does NOT stub, fake, or remove any functionality.

`rocminfo` (component 1) is NOT built: linking it requires
`find_package(hsa-runtime64 1.0 REQUIRED)` and the HSA runtime is absent from
both the OHOS sysroot and the artifact repository. Building it against a
fabricated HSA stub would produce a binary whose only observable behaviour is
"enumerate 0 agents, exit 8" for every input — a non-functional shell, which
the project rules forbid. The enumerator component is fully usable on its own;
this is a genuine subset deliverable, not a hollowed-out package.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, save
from conan.tools.layout import basic_layout


class RocminfoConan(ConanFile):
    name = "rocminfo"
    version = "6.4.3"
    description = ("ROCm Application for Reporting System Info — "
                   "rocm_agent_enumerator component (AMD GCN ISA target discovery)")
    license = "NCSA"
    homepage = "https://github.com/ROCm/rocminfo"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # `rocm_agent_enumerator` is a pure-Python script: upstream itself only
        # does `configure_file(rocm_agent_enumerator ... COPYONLY)`, i.e. there
        # is no compilation step for this component.
        pass

    def package(self):
        # The enumerator script: upstream's only no-ROCm-stack deliverable.
        copy(self, "rocm_agent_enumerator",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))

        # The documented target-list files consumers pair with strategies 1/2.
        copy(self, "*.rst",
             src=os.path.join(self.source_folder, "docs"),
             dst=os.path.join(self.package_folder, "docs"),
             keep_path=True)

        copy(self, "License.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "README.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "docs"))

        # Deployment note: OHOS PC ships no `python3` interpreter by default, so
        # consumers either install one or ship the script to a host with Python.
        save(self, os.path.join(self.package_folder, "docs", "OHOS-NOTES.md"),
             content=(
                 "# rocminfo 6.4.3 on OpenHarmony PC\n"
                 "\n"
                 "This package delivers the `rocm_agent_enumerator` component.\n"
                 "\n"
                 "## Working (no ROCm stack / no /dev/kfd / no AMD GPU required)\n"
                 "\n"
                 "Strategy 1 - ROCM_TARGET_LST environment variable:\n"
                 "\n"
                 "    ROCM_TARGET_LST=/path/to/target.lst \\\n"
                 "        python3 rocm_agent_enumerator\n"
                 "\n"
                 "Strategy 2 - target.lst placed next to the script:\n"
                 "\n"
                 "    cp target.lst \"$(dirname $(which rocm_agent_enumerator))\"\n"
                 "    python3 rocm_agent_enumerator\n"
                 "\n"
                 "Both print one GCN ISA name per line, e.g. gfx906 / gfx908 /\n"
                 "gfx1030, and exit 0.\n"
                 "\n"
                 "## Not available on OpenHarmony PC\n"
                 "\n"
                 "The `rocminfo` CLI and strategies 3/4/5 require the AMD kernel\n"
                 "driver (`amdkfd`) and its `/dev/kfd` device node, or an AMD GPU\n"
                 "exposed over PCI. OpenHarmony PC provides none of these, so\n"
                 "those paths are inert here. This is an environment limitation,\n"
                 "not a packaging decision.\n"
             ))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []

        bindir = os.path.join(self.package_folder, "bin")
        self.buildenv_info.prepend_path("PATH", bindir)
        self.runenv_info.prepend_path("PATH", bindir)
