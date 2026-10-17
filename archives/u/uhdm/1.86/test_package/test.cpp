// L1 consumer test: link libuhdm and exercise the VPI API surface.
// Pattern borrowed from upstream tests/vpi_get_test.cpp (write/read roundtrip).
#include <cassert>
#include <cstdio>
#include <string>

#include "uhdm/constant.h"
#include "uhdm/uhdm.h"
#include "uhdm/uhdm_types.h"
#include "uhdm/vhpi_user.h"
#include "uhdm/vpi_uhdm.h"

int main() {
  UHDM::Serializer serializer;

  // A type multiple levels deep: base-class <- expr <- constant
  UHDM::constant *value = serializer.MakeConstant();

  // Base class values
  assert(value->VpiFile("hello.v"));
  assert(value->VpiLineNo(42));

  // Expr values
  assert(value->VpiSize(12345));
  assert(value->VpiDecompile("decompile"));

  // Read the properties back through the VPI interface
  uhdm_handle uhdm_handle(UHDM::uhdmconstant, value);
  vpiHandle vpi_handle = (vpiHandle)&uhdm_handle;

  assert(std::string(vpi_get_str(vpiFile, vpi_handle)) == "hello.v");
  assert(vpi_get(vpiLineNo, vpi_handle) == 42);
  assert(vpi_get(vpiSize, vpi_handle) == 12345);
  assert(std::string(vpi_get_str(vpiDecompile, vpi_handle)) == "decompile");

  std::printf("uhdm L1 consumer test: OK\n");
  return 0;
}
