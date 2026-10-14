// EVMC consumer end-to-end case (OHPC / OpenHarmony).
//
// Exercises the packaged EVMC artifacts the way a real Ethereum client host
// does, end to end -- not a set of isolated assertions:
//
//   1. build an evmc::MockedHost (evmc::mocked_host, packaged header),
//   2. load a VM shared library from disk through the packaged loader
//      (libevmc-loader.a, evmc_load_and_configure), wrapping the resulting
//      evmc_vm* in the RAII evmc::VM that the packaged evmc.hpp provides,
//   3. execute real EVM bytecode through evmc::VM::execute(),
//   4. validate the returned status/gas/output and the instruction metrics
//      table (libevmc-instructions.a),
//   5. run a second execution through the same VM to show the loaded instance
//      is reusable and that SSTORE reaches host storage through the callbacks.
//
// Every stage consumes the previous stage's output, so the case exits non-zero
// as soon as any check fails. The last lines are a machine-readable summary that
// the recipe records verbatim as evidence.

#include <evmc/evmc.h>
#include <evmc/evmc.hpp>
#include <evmc/instructions.h>
#include <evmc/loader.h>
#include <evmc/mocked_host.hpp>

#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <string>

using namespace evmc::literals;

namespace {

int g_checks = 0;
int g_failures = 0;

void check(bool ok, const char* what)
{
    ++g_checks;
    if (ok)
        std::printf("  [ok]   %s\n", what);
    else
    {
        ++g_failures;
        std::printf("  [FAIL] %s\n", what);
    }
}

}  // namespace

int main(int argc, char** argv)
{
    if (argc != 2)
    {
        std::fprintf(stderr, "usage: %s <path-to-vm-shared-library>\n", argv[0]);
        return 2;
    }
    const std::string vm_path = argv[1];

    std::printf("EVMC consumer end-to-end case\n");
    std::printf("  vm               : %s\n", vm_path.c_str());
    std::printf("  evmc ABI version : %d\n", EVMC_ABI_VERSION);

    // ---------------------------------------------------------------- stage 1
    // The host services the VM's state-access callbacks.
    evmc::MockedHost host;
    // Upstream's user-defined literal takes a plain hex integer literal and
    // parses its digits into the 20-byte address, exactly as upstream's own
    // cpp_test.cpp/mocked_host_test.cpp use it (e.g. 0xaa00...4400_address).
    const auto sender = 0x00000000000000000000000000000000c0ffee00_address;
    const auto recipient = 0x00000000000000000000000000000000000000aa_address;
    host.accounts[recipient].balance = evmc::uint256be{0x10000000000};
    check(host.get_balance(recipient) == evmc::uint256be{0x10000000000},
          "MockedHost constructed from the packaged header and accounts seeded");

    // ---------------------------------------------------------------- stage 2
    // Load the VM through the packaged loader (libevmc-loader.a), then hand the
    // raw evmc_vm* to evmc::VM so the C++ wrapper owns it (RAII destroy).
    evmc_loader_error_code load_error = EVMC_LOADER_UNSPECIFIED_ERROR;
    evmc_vm* raw_vm = evmc_load_and_configure(vm_path.c_str(), &load_error);
    if (raw_vm == nullptr || load_error != EVMC_LOADER_SUCCESS)
    {
        std::fprintf(stderr, "FAIL: evmc_load_and_configure(%s) error=%d\n", vm_path.c_str(),
                     static_cast<int>(load_error));
        // evmc_load_and_configure returns NULL on error, but if a VM was handed
        // back anyway it owns a dlopen() handle and must be released: evmc::VM
        // (created below) is the only owner and is never constructed here.
        if (raw_vm != nullptr)
            raw_vm->destroy(raw_vm);
        return 1;
    }
    evmc::VM vm{raw_vm};
    check(static_cast<bool>(vm), "VM loaded through evmc_load_and_configure is non-null");
    check(vm.is_abi_compatible(), "loaded VM reports an ABI version matching EVMC_ABI_VERSION");
    check(vm.name() != nullptr && std::strlen(vm.name()) > 0, "loaded VM exposes a non-empty name");
    std::printf("  vm name          : %s\n", vm.name() ? vm.name() : "(null)");
    std::printf("  vm version       : %s\n", vm.version() ? vm.version() : "(null)");

    // ---------------------------------------------------------------- stage 3
    // Execute real EVM bytecode. PUSH1 0x2a PUSH1 0x00 MSTORE PUSH1 0x20
    // PUSH1 0x00 RETURN returns the 32-byte word 0x00..2a.
    const uint8_t code[] = {0x60, 0x2a, 0x60, 0x00, 0x52, 0x60, 0x20, 0x60, 0x00, 0xf3};

    evmc_message msg{};
    msg.kind = EVMC_CALL;
    msg.flags = 0;
    msg.depth = 0;
    msg.gas = 100000;
    msg.recipient = recipient;
    msg.sender = sender;
    msg.input_data = nullptr;
    msg.input_size = 0;
    msg.value = evmc::uint256be{};
    msg.create2_salt = evmc::bytes32{};
    msg.code_address = recipient;

    const evmc_revision revision = EVMC_SHANGHAI;
    evmc::Result result = vm.execute(host, revision, msg, code, sizeof(code));

    check(result.status_code == EVMC_SUCCESS, "bytecode execution returned EVMC_SUCCESS");
    // VM::execute() takes the message by const reference, so the local msg is
    // not updated with the gas left; the gas consumed has to be derived from the
    // returned result, otherwise the assertion below is trivially true.
    const int64_t gas_used = static_cast<int64_t>(msg.gas) - static_cast<int64_t>(result.gas_left);
    check(gas_used > 0 && gas_used < static_cast<int64_t>(msg.gas),
          "execution consumed part of the gas");
    check(result.output_size == 32, "execution produced a 32-byte output word");
    if (result.status_code == EVMC_SUCCESS && result.output_size == 32)
    {
        std::printf("  output           : ");
        for (size_t i = 0; i < result.output_size; ++i)
            std::printf("%02x", result.output_data[i]);
        std::printf("\n  gas used         : %lld\n", static_cast<long long>(gas_used));
        check(result.output_data[31] == 0x2a && result.output_data[0] == 0x00,
              "returned word equals the value the bytecode stored");
    }
    else
    {
        check(false, "execution produced the expected output word");
    }
    // The executed bytecode contains no refund-generating opcode, so a correct
    // VM must report exactly zero. Asserting `>= 0` would be tautologically
    // true for a signed field and would only inflate the check count.
    check(result.gas_refund == 0, "gas refund is zero for bytecode with no refund opcode");

    // ---------------------------------------------------------------- stage 4
    // The instruction metrics/names tables come from libevmc-instructions.a.
    const auto* metrics = evmc_get_instruction_metrics_table(revision);
    const auto* names = evmc_get_instruction_names_table(revision);
    check(metrics != nullptr, "evmc_get_instruction_metrics_table(SHANGHAI) is available");
    check(names != nullptr, "evmc_get_instruction_names_table(SHANGHAI) is available");
    if (metrics != nullptr && names != nullptr)
    {
        check(names[0x60] != nullptr && std::strcmp(names[0x60], "PUSH1") == 0,
              "instruction table names opcode 0x60 as PUSH1");
        check(metrics[0x60].gas_cost == 3, "instruction table gives PUSH1 a gas cost of 3");
        check(names[0x00] != nullptr && std::strcmp(names[0x00], "STOP") == 0,
              "instruction table names opcode 0x00 as STOP");
    }

    // ---------------------------------------------------------------- stage 5
    // A host keeps one VM instance per client, so drive a second, independent
    // execution through the same loaded VM: SSTORE(0, 1) then STOP.
    const uint8_t code2[] = {0x60, 0x01, 0x60, 0x00, 0x55, 0x00};
    evmc::Result result2 = vm.execute(host, revision, msg, code2, sizeof(code2));
    check(result2.status_code == EVMC_SUCCESS, "second execution through the same VM succeeded");
    // Only meaningful if the execution actually succeeded; otherwise a failure
    // here would be misreported as "SSTORE did not reach the host".
    if (result2.status_code == EVMC_SUCCESS)
    {
        const auto written = host.get_storage(recipient, evmc::bytes32{});
        check(written.bytes[31] == 0x01, "SSTORE reached host storage through the VM callbacks");
    }
    else
    {
        check(false, "second execution succeeded, so SSTORE could reach host storage");
    }

    // ---------------------------------------------------------------- report
    const int passed = g_checks - g_failures;
    std::printf("CONSUMER_RESULT checks=%d passed=%d failed=%d\n", g_checks, passed, g_failures);
    std::printf("%s\n", g_failures == 0 ? "CONSUMER_VERDICT PASS" : "CONSUMER_VERDICT FAIL");
    return g_failures == 0 ? 0 : 1;
}
