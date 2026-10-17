from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
import os


class AvidaConan(ConanFile):
    name = "avida"
    version = "2.12.4"
    description = "Avida - Digital Evolution Platform for ALife research"
    license = "GPL-3.0-only"
    homepage = "https://avida.devosoft.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        cmake_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def validate(self):
        if self.settings.os != "OHOS":
            raise ConanInvalidConfiguration("avida is only adapted for OHOS")
        if self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("avida/2.12.4 only supports OHOS armv8")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["AVD_ENABLE_TCMALLOC"] = False
        tc.cache_variables["AVD_GUI_NCURSES"] = False
        tc.cache_variables["AVD_UNIT_TESTS"] = False
        tc.cache_variables["AVD_TASK_EVENT_GEN"] = False
        tc.cache_variables["AVD_GUI_PROTOTYPE_TEXT"] = False
        tc.cache_variables["APTO_UNIT_TESTS"] = False
        # Belt and braces for CMake 4.x: patches/0001 raises every CMakeLists.txt
        # in the tree to 3.5, and this keeps the policy floor at the same value so
        # that no nested cmake_minimum_required() below 3.5 can abort configure.
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()

    def _read(self, path):
        with open(path, "r") as f:
            return f.read()

    def _write(self, path, content):
        with open(path, "w") as f:
            f.write(content)

    def _fix_file(self, path, replacements):
        if not os.path.exists(path):
            return
        c = self._read(path)
        for old, new in replacements:
            c = c.replace(old, new)
        self._write(path, c)

    def build(self):
        # Two build-system changes are carried by patches (see conandata.yml):
        #   patches/0001-bump-cmake-minimum-version.patch
        #       CMAKE_MINIMUM_REQUIRED 2.6 -> 3.5 in the four CMakeLists.txt
        #       (CMake 4.x refuses a minimum below 3.5 outright).
        #   patches/0002-disable-tcmalloc-on-ohos.patch
        #       Drops the bundled tcmalloc-1.4 subdirectory; its
        #       atomicops-internals-x86.h uses x86-only inline assembly.
        # The remaining phases below are kept in the recipe because they are
        # per-file source edits that need conditional string surgery.
        apply_conandata_patches(self)
        src = self.source_folder

        # --- Phase 1: cRandom.h — comprehensive fix ---
        crandom = os.path.join(src, "avida-core", "source", "tools", "cRandom.h")
        if os.path.exists(crandom):
            c = self._read(crandom)

            # Remove custom std::iota that clashes with C++11
            iota_start = c.find('#if !APTO_PLATFORM(WINDOWS)')
            if iota_start != -1:
                iota_end = c.find('#endif', iota_start)
                if iota_end != -1:
                    c = c[:iota_start] + c[iota_end + len('#endif'):]

            # Add missing includes
            if "#include <random>" not in c:
                c = c.replace("#include <vector>",
                              "#include <vector>\n#include <random>\n#include <algorithm>")
            if "#include <cstdlib>" not in c:
                c = c.replace("#include <algorithm>",
                              "#include <algorithm>\n#include <cstdlib>")

            # C++17 removed std::random_shuffle, but std::shuffle is NOT a drop-in
            # replacement: std::shuffle draws through uniform_int_distribution with
            # rejection sampling, which consumes a different number of values from
            # the underlying generator.  avida seeds its RNG from RANDOM_SEED and
            # every later draw shifts, so the whole simulation desynchronises and
            # upstream's consistency-test expected files stop matching
            # (reproduced: multi_level_selection fails).  Reproduce the pre-C++17
            # draw pattern against the generator that is already in scope instead.
            c = c.replace("std::random_shuffle(rmap.begin(), rmap.end());",
                          "for (std::size_t i = 1; i < rmap.size(); ++i)\n"
                          "\t\tstd::iter_swap(rmap.begin() + i,\n"
                          "\t\t               rmap.begin() + rng(static_cast<unsigned int>(i + 1)));")

            # Same idea for the three-argument call sites in the .cc files: a
            # helper that reproduces std::random_shuffle(first, last, rng).
            shuffle_helper = (
                "/*! C++17 removed std::random_shuffle.  Do not substitute\n"
                " * std::shuffle: it draws from the generator with a different pattern\n"
                " * (uniform_int_distribution plus rejection sampling), which consumes a\n"
                " * different number of values and desynchronises avida's RNG stream, so\n"
                " * upstream's consistency-test expected files stop matching.  This helper\n"
                " * reproduces the pre-C++17 draw pattern exactly.\n"
                " */\n"
                "template<class RandomIt, class RandomFunc>\n"
                "void avida_random_shuffle(RandomIt first, RandomIt last, RandomFunc rand) {\n"
                "\tfor (RandomIt i = first + 1; i != last; ++i)\n"
                "\t\tstd::iter_swap(i, first + rand(static_cast<unsigned int>(i - first) + 1));\n"
                "}\n\n"
            )
            shuffle_anchor = ("template <typename ForwardIterator, typename OutputIterator, typename RNG>\n"
                              "void sample_without_replacement(")
            c = c.replace(shuffle_anchor, shuffle_helper + shuffle_anchor)

            # Fix cRandomStdAdaptor — expose the URNG interface the helper needs
            old_adaptor = (
                "struct cRandomStdAdaptor {\n"
                "\ttypedef int argument_type;\n"
                "\ttypedef int result_type;\n"
                "\t\n"
                "\tcRandomStdAdaptor(cRandom& rng) : _rng(rng) { }\n"
                "\tint operator()(int n) { return _rng.GetInt(n); }\n"
                "\t\n"
                "\tcRandom& _rng;\n"
                "};"
            )
            new_adaptor = (
                "struct cRandomStdAdaptor {\n"
                "\ttypedef unsigned int argument_type;\n"
                "\ttypedef unsigned int result_type;\n"
                "\t\n"
                "\tcRandomStdAdaptor(cRandom& rng) : _rng(rng) { }\n"
                "\tunsigned int operator()() { return static_cast<unsigned int>(_rng.GetDouble() * 4294967295.0); }\n"
                "\tunsigned int operator()(unsigned int n) { return _rng.GetUInt(n); }\n"
                "\tstatic constexpr result_type min() { return 0; }\n"
                "\tstatic constexpr result_type max() { return 0xFFFFFFFF; }\n"
                "\t\n"
                "\tcRandom& _rng;\n"
                "};"
            )
            c = c.replace(old_adaptor, new_adaptor)

            self._write(crandom, c)

        # --- Phase 1b: Add missing #include <cstdlib> in tArray.h (for qsort) ---
        tarray = os.path.join(src, "avida-core", "source", "tools", "tArray.h")
        if os.path.exists(tarray):
            c = self._read(tarray)
            if "qsort(" in c and "#include <cstdlib>" not in c:
                c = c.replace("#include <cassert>",
                              "#include <cassert>\n#include <cstdlib>")
                self._write(tarray, c)

        # --- Phase 2: 3-arg random_shuffle call sites in the .cc files ---
        # Routed through avida_random_shuffle (defined in cRandom.h) rather than
        # std::shuffle, so the RNG draw pattern — and therefore avida's whole
        # random stream — matches the pre-C++17 build that upstream's expected
        # consistency-test output was generated with.
        for f in ["avida-core/source/actions/PrintActions.cc",
                  "avida-core/source/main/cGenomeUtil.cc",
                  "avida-core/source/main/cPopulation.cc"]:
            p = os.path.join(src, f)
            if os.path.exists(p):
                c = self._read(p)
                if "std::random_shuffle(" in c:
                    if "#include <random>" not in c:
                        c = c.replace("#include <vector>", "#include <vector>\n#include <random>")
                    c = c.replace("std::random_shuffle(", "avida_random_shuffle(")
                    self._write(p, c)

        # --- Phase 3: llabs ---
        self._fix_file(os.path.join(src, "avida-core", "source", "main", "cPopulationInterface.cc"),
                       [("std::abs(static_cast<long long int>", "llabs(static_cast<long long int>")])

        # --- Phase 4: apto Atomic x86 asm → __sync ---
        # The #else branch assumes x86 (uses mfence, lock xaddl). Replace the
        # entire #else block with a portable version using __sync builtins.
        atomic_h = os.path.join(src, "libs", "apto", "include", "apto", "core", "Atomic.h")
        if os.path.exists(atomic_h):
            c = self._read(atomic_h)
            if "APTO_PLATFORM(WINDOWS)" in c and "#else\n\n// Assuming x86" in c:
                else_start = c.find("#else\n\n// Assuming x86")
                endif_pos = c.find("#endif", else_start)
                if else_start != -1 and endif_pos != -1:
                    old_else = c[else_start:endif_pos]
                    new_else = (
                        "#elif defined(__aarch64__) || defined(__arm__)\n\n"
                        "// AArch64 / ARM — use __sync builtins\n"
                        "inline int Apto::Atomic::Add(volatile int* atomic, int value)\n"
                        "{\n"
                        "  return __sync_add_and_fetch(atomic, value);\n"
                        "}\n\n"
                        "inline int Apto::Atomic::Get(volatile int* atomic)\n"
                        "{\n"
                        "  __sync_synchronize();\n"
                        "  return *atomic;\n"
                        "}\n\n"
                        "inline void Apto::Atomic::Set(volatile int* atomic, int value)\n"
                        "{\n"
                        "  __sync_synchronize();\n"
                        "  *atomic = value;\n"
                        "}\n\n"
                        "#else\n\n"
                        "// Fallback — assume x86 or compatible\n"
                        "inline int Apto::Atomic::Add(volatile int* atomic, int value)\n"
                        "{\n"
                        "  return __sync_add_and_fetch(atomic, value);\n"
                        "}\n\n"
                        "inline int Apto::Atomic::Get(volatile int* atomic)\n"
                        "{\n"
                        "  __asm__ __volatile__(\"\" : : : \"memory\");\n"
                        "  return *atomic;\n"
                        "}\n\n"
                        "inline void Apto::Atomic::Set(volatile int* atomic, int value)\n"
                        "{\n"
                        "  __asm__ __volatile__(\"mfence\" : : : \"memory\");\n"
                        "  *atomic = value;\n"
                        "}\n"
                    )
                    c = c[:else_start] + new_else + c[endif_pos:]
                    self._write(atomic_h, c)

        # --- Phase 5: pthread_cancel not available on OHOS musl ---
        self._fix_file(os.path.join(src, "libs", "apto", "src", "core", "Thread.cc"),
                       [("pthread_cancel(m_thread);\n", "// pthread_cancel not available on OHOS\n")])

        # --- Phase 6: Fix cPopulation.cc push_back type mismatch ---
        # cString has no implicit conversion to std::string, but has operator const char*().
        # Use const char* as intermediate: cString → const char* → std::string
        cpop = os.path.join(src, "avida-core", "source", "main", "cPopulation.cc")
        if os.path.exists(cpop):
            c = self._read(cpop)
            if "new_genome.AsString())" in c and "track_founders.push_back" in c:
                c = c.replace(
                    "track_founders.push_back(make_pair(organism->GetBioGroup(\"genotype\")->GetID(), new_genome.AsString()));",
                    "const char* tmp_genome_cstr = new_genome.AsString();\n    track_founders.push_back(std::make_pair(organism->GetBioGroup(\"genotype\")->GetID(), std::string(tmp_genome_cstr)));"
                )
                self._write(cpop, c)

        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        # Add package bin dir to PATH so that avida binary is found
        self.cpp_info.bindirs = ["bin", "work"]
