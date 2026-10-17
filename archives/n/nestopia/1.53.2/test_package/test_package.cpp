// Headless smoke test for the installed Nestopia 1.53.2 emulation core.
//
// Two groups of assertions:
//   [A] Core API smoke (logical flow 1):
//       Drives the Nestopia core API (Nes::Core::Api::Emulator / Nes::Api::Machine)
//       with a programmatically generated minimal iNES ROM (16-byte header +
//       16 KiB PRG + 8 KiB CHR). No FLTK/SDL/GL initialisation is performed, so
//       the test runs on headless HarmonyOS PC environments.
//   [B] HarmonyOS-specific tests (OHOS-1 .. OHOS-6): platform-attribute and
//       toolchain assertions that only make sense on HarmonyOS PC (aarch64,
//       musl libc, static core library link integrity).
//
// All assertions are pure computation / pure IO; no display initialisation.

#include "core/api/NstApi.hpp"
#include "core/api/NstApiMachine.hpp"
#include "core/api/NstApiEmulator.hpp"

#include <cstdio>
#include <cstring>
#include <cerrno>
#include <cstdint>
#include <sstream>
#include <string>
#include <vector>
#include <unistd.h>

// Compile-time assertion: this consumer must be built with the HarmonyOS
// toolchain (the OHOS clang driver defines __OHOS__ for ohos targets).
#if !defined(__OHOS__)
#error "OHOS-1: test_package must be compiled with the HarmonyOS toolchain (__OHOS__ undefined)"
#endif

namespace
{
    const unsigned long kFrames = 3u;

    int g_core_passed = 0;
    int g_ohos_passed = 0;
    int g_failed = 0;

    void report_ohos(bool ok, const char* name)
    {
        if (ok)
        {
            std::printf("  [PASS] %s\n", name);
            ++g_ohos_passed;
        }
        else
        {
            std::printf("  [FAIL] %s\n", name);
            ++g_failed;
        }
    }

    std::string make_minimal_ines_rom()
    {
        std::vector<unsigned char> rom(16 + 16 * 1024 + 8 * 1024, 0x00);

        // iNES 1.0 header.
        rom[0] = 'N';
        rom[1] = 'E';
        rom[2] = 'S';
        rom[3] = 0x1A;
        rom[4] = 1;   // 1 x 16 KiB PRG bank
        rom[5] = 1;   // 1 x 8 KiB CHR bank
        rom[6] = 0x00; // mapper 0, horizontal mirroring

        // Standard reset-vector semantics: the last PRG bank is mapped to
        // 0xC000..0xFFFF, so the reset vector at 0xFFFC points back into
        // the PRG area.  Fill it with a branch-to-self loop.
        const std::size_t prg_start = 16;
        const std::size_t prg_end = prg_start + 16 * 1024;
        for (std::size_t i = prg_start; i < prg_end; ++i)
        {
            rom[i] = 0xEA; // NOP
        }
        // Reset vector -> 0x8000 (start of PRG).
        rom[prg_end - 4] = 0x00;
        rom[prg_end - 3] = 0x80;

        return std::string(rom.begin(), rom.end());
    }

    // ------------------------------------------------------------------
    // [B] HarmonyOS-specific tests
    // ------------------------------------------------------------------

    // OHOS-1: aarch64 runtime confirmation.
    // The compile-time __OHOS__ check is enforced by #error above; this
    // function additionally verifies we execute on an aarch64 target.
    bool test_ohos_compile_env()
    {
#if defined(__aarch64__)
        return true;
#else
        return false;
#endif
    }

    // OHOS-2: arm64 LP64 data model.
    // HarmonyOS PC aarch64 uses LP64: long == 8, pointer == 8, int == 4.
    bool test_ohos_lp64_datamodel()
    {
        return sizeof(long) == 8 && sizeof(void*) == 8 &&
               sizeof(long long) == 8 && sizeof(int) == 4;
    }

    // OHOS-3: little-endian byte order (aarch64 is little-endian).
    bool test_ohos_little_endian()
    {
        std::uint32_t v = 0x01020304U;
        unsigned char b[4];
        std::memcpy(b, &v, sizeof(v));
        return b[0] == 0x04 && b[1] == 0x03 && b[2] == 0x02 && b[3] == 0x01;
    }

    // OHOS-4: musl libc detection (glibc-distinguishable behaviour).
    // glibc defines __GLIBC__ and confstr(_CS_GNU_LIBC_VERSION) returns
    // the "glibc x.y" string; musl defines no __GLIBC__ and does not
    // support that confstr name.  POSIX guarantees confstr() returns 0 for
    // an unsupported name; we avoid depending on the exact errno value
    // (implementation detail) and additionally check the buffer was left
    // untouched.  Both signals were measured on the HarmonyOS PC toolchain.
    bool test_ohos_musl_libc()
    {
#if defined(__GLIBC__)
        return false;
#else
        char buf[128];
        buf[0] = '\x7f'; // poison marker: must remain untouched on musl
        std::size_t r = confstr(_CS_GNU_LIBC_VERSION, buf, sizeof(buf));
        return r == 0 && buf[0] == '\x7f';
#endif
    }

    // OHOS-5: static link integrity of libnestopia_core.a.
    // The consumer links libnestopia_core.a statically; all of the calls
    // below resolve to symbols of the static core library that the main
    // smoke flow does not touch.  Each call returning its measured,
    // documented value proves the corresponding core symbol was resolved
    // at link time and behaves correctly on HarmonyOS PC:
    //   SetRamPowerState(0)  -> RESULT_OK (0)
    //   Is(0)                -> 0 (no flag set)
    //   IsLocked()           -> false
    //   Reset(no cart)       -> RESULT_ERR_NOT_READY (-3)
    bool test_ohos_static_link_integrity()
    {
        Nes::Api::Emulator emulator;
        Nes::Api::Machine machine(emulator);

        if (machine.SetRamPowerState(0u) != Nes::RESULT_OK)
        {
            return false;
        }
        if (machine.Is(0u) != 0u)
        {
            return false;
        }
        if (machine.IsLocked())
        {
            return false;
        }
        if (machine.Reset(false) != Nes::RESULT_ERR_NOT_READY)
        {
            return false;
        }
        return true;
    }

    // OHOS-6: core API lifecycle loop (resource integrity).
    // Repeated create/load/power/execute/power-off/unload cycles exercise
    // the static core library on aarch64 without a display; any misalignment
    // or resource bug would surface as a crash or a non-OK result code.
    bool test_ohos_core_lifecycle_loop()
    {
        for (int i = 0; i < 5; ++i)
        {
            std::istringstream rom(make_minimal_ines_rom());
            Nes::Api::Emulator emulator;
            Nes::Api::Machine machine(emulator);
            if (machine.Load(rom, Nes::Api::Machine::FAVORED_NES_NTSC,
                             Nes::Api::Machine::DONT_ASK_PROFILE) != Nes::RESULT_OK)
            {
                return false;
            }
            if (machine.Power(true) != Nes::RESULT_OK)
            {
                return false;
            }
            emulator.Execute(0, 0, 0);
            if (machine.Power(false) != Nes::RESULT_OK)
            {
                return false;
            }
            if (machine.Unload() != Nes::RESULT_OK)
            {
                return false;
            }
        }
        return true;
    }
} // namespace

int main()
{
    bool passed = true;

    // ------------------------------------------------------------------
    // [A] Core API smoke (existing logical flow, unchanged assertions)
    // ------------------------------------------------------------------
    std::istringstream ines_stream(make_minimal_ines_rom());

    Nes::Api::Emulator emulator;
    Nes::Api::Machine machine(emulator);

    Nes::Result load_result = machine.Load(
        ines_stream, Nes::Api::Machine::FAVORED_NES_NTSC,
        Nes::Api::Machine::DONT_ASK_PROFILE);
    if (load_result != Nes::RESULT_OK)
    {
        std::fprintf(stderr, "FAIL: Load returned result %d, expected RESULT_OK\n",
                     static_cast<int>(load_result));
        passed = false;
    }

    if (machine.Power(true) != Nes::RESULT_OK)
    {
        std::fprintf(stderr, "FAIL: Power(true) did not return RESULT_OK\n");
        passed = false;
    }

    for (unsigned long i = 0; i < kFrames; ++i)
    {
        emulator.Execute(0, 0, 0);
    }

    const unsigned long frames = emulator.Frame();
    if (frames != kFrames)
    {
        std::fprintf(stderr, "FAIL: frame counter is %lu, expected %lu\n",
                     frames, kFrames);
        passed = false;
    }

    if (machine.Reset(true) != Nes::RESULT_OK)
    {
        std::fprintf(stderr, "FAIL: Reset(true) did not return RESULT_OK\n");
        passed = false;
    }

    emulator.Execute(0, 0, 0);
    const unsigned long frames_after_reset = emulator.Frame();
    if (frames_after_reset != 1)
    {
        std::fprintf(stderr,
                     "FAIL: frame counter after reset is %lu, expected 1\n",
                     frames_after_reset);
        passed = false;
    }

    if (machine.Power(false) != Nes::RESULT_OK)
    {
        std::fprintf(stderr, "FAIL: Power(false) did not return RESULT_OK\n");
        passed = false;
    }

    if (machine.Unload() != Nes::RESULT_OK)
    {
        std::fprintf(stderr, "FAIL: Unload did not return RESULT_OK\n");
        passed = false;
    }

    if (passed)
    {
        ++g_core_passed;
        std::printf("PASS [A] nestopia core smoke: load=%d power=ok frames=%lu "
                    "reset_frame=%lu unload=ok\n",
                    static_cast<int>(load_result), frames, frames_after_reset);
    }
    else
    {
        ++g_failed;
    }

    // ------------------------------------------------------------------
    // [B] HarmonyOS-specific tests (6 cases)
    // ------------------------------------------------------------------
    std::printf("[B] HarmonyOS-specific tests (6)\n");
    report_ohos(test_ohos_compile_env(),
                "OHOS-1: __OHOS__ compile env + aarch64 runtime");
    report_ohos(test_ohos_lp64_datamodel(),
                "OHOS-2: arm64 LP64 data model (long/ptr=8, int=4)");
    report_ohos(test_ohos_little_endian(),
                "OHOS-3: little-endian byte order");
    report_ohos(test_ohos_musl_libc(),
                "OHOS-4: musl libc (no __GLIBC__, confstr unsupported)");
    report_ohos(test_ohos_static_link_integrity(),
                "OHOS-5: static link integrity (core symbols resolvable)");
    report_ohos(test_ohos_core_lifecycle_loop(),
                "OHOS-6: core API lifecycle loop (5x, no display)");

    const int total = g_core_passed + g_ohos_passed + g_failed;
    std::printf("=== 测试结果 ===\n");
    std::printf("通过: %d\n", g_core_passed + g_ohos_passed);
    std::printf("失败: %d\n", g_failed);
    std::printf("合计: %d\n", total);

    if (g_failed > 0)
    {
        std::fprintf(stderr, "\nFAIL: %d test(s) failed\n", g_failed);
        return 1;
    }

    std::printf("\nAll tests passed.\n");
    return 0;
}