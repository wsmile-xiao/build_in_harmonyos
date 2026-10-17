// Consumer test for vixl 5.1.0.
//
// Exercises the real VIXL public API (not a stub): generate an AArch64
// function with the MacroAssembler, decode it with the Decoder and execute it
// in the Simulator, then verify the computed register result.
//
// API follows the upstream examples/aarch64/getting-started.cc.
#define VIXL_INCLUDE_SIMULATOR_AARCH64
#include <cinttypes>
#include <cstdio>

#include "aarch64/macro-assembler-aarch64.h"
#include "aarch64/simulator-aarch64.h"

using namespace vixl;
using namespace vixl::aarch64;

// demo_function(uint64_t x0) -> uint64_t:
//   x1 = 0x1122334455667788
//   x0 = x0 & x1
//   ret
static void GenerateDemoFunction(MacroAssembler* masm) {
  masm->Ldr(x1, 0x1122334455667788);
  masm->And(x0, x0, x1);
  masm->Ret();
}

int main() {
  MacroAssembler masm;
  Decoder decoder;
  Simulator simulator(&decoder);

  Label demo_function;
  masm.Bind(&demo_function);
  GenerateDemoFunction(&masm);
  masm.FinalizeCode();

  // The generated buffer must contain at least three instructions
  // (ldr + and + ret == 12 bytes minimum).
  size_t code_size = masm.GetSizeOfCodeGenerated();
  if (code_size < 12) {
    fprintf(stderr, "unexpected code size: %zu\n", code_size);
    return 1;
  }

  const uint64_t input = 0x8899aabbccddeeffULL;
  const uint64_t expected = input & 0x1122334455667788ULL;

  simulator.WriteXRegister(0, input);
  simulator.RunFrom(masm.GetLabelAddress<Instruction*>(&demo_function));
  uint64_t result = simulator.ReadXRegister(0);

  printf("code_size = %zu bytes\n", code_size);
  printf("x0 = 0x%016" PRIx64 "\n", result);
  printf("expected = 0x%016" PRIx64 "\n", expected);

  if (result != expected) {
    fprintf(stderr, "simulator result mismatch\n");
    return 1;
  }

  printf("vixl consumer test PASS\n");
  return 0;
}
