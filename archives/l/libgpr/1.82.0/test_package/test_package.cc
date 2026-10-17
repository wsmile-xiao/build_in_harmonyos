// Consumer test for libgpr (gRPC Portable Runtime, grpc 1.82.0).
// Exercises real gpr APIs: monotonic clock arithmetic, allocation, string
// duplication, CPU count, mutex round-trip and logging.
#include <cstdio>
#include <cstring>

#include <grpc/support/alloc.h>
#include <grpc/support/cpu.h>
#include <grpc/support/log.h>
#include <grpc/support/string_util.h>
#include <grpc/support/sync.h>
#include <grpc/support/time.h>

static int failures = 0;

#define CHECK(cond, msg)                                          \
  do {                                                            \
    if (!(cond)) {                                                \
      std::printf("FAIL: %s\n", msg);                             \
      ++failures;                                                 \
    } else {                                                      \
      std::printf("ok  : %s\n", msg);                             \
    }                                                             \
  } while (0)

int main() {
  // 1. monotonic clock arithmetic
  gpr_timespec now = gpr_now(GPR_CLOCK_MONOTONIC);
  gpr_timespec future = gpr_time_add(now, gpr_time_from_seconds(1, GPR_TIMESPAN));
  gpr_timespec delta = gpr_time_sub(future, now);
  CHECK(gpr_time_to_millis(delta) == 1000, "gpr_time_to_millis(1s) == 1000");
  CHECK(gpr_time_cmp(future, now) > 0, "gpr_time_cmp(future, now) > 0");

  // 2. allocation
  void* buf = gpr_malloc(64);
  CHECK(buf != nullptr, "gpr_malloc(64) != NULL");
  gpr_free(buf);

  // 3. string duplication
  char* dup = gpr_strdup("libgpr");
  CHECK(dup != nullptr && std::strcmp(dup, "libgpr") == 0, "gpr_strdup round-trip");
  gpr_free(dup);

  // 4. cpu count
  unsigned cores = gpr_cpu_num_cores();
  CHECK(cores >= 1, "gpr_cpu_num_cores() >= 1");

  // 5. mutex round-trip
  gpr_mu mu;
  gpr_mu_init(&mu);
  gpr_mu_lock(&mu);
  gpr_mu_unlock(&mu);
  gpr_mu_destroy(&mu);
  CHECK(true, "gpr_mu init/lock/unlock/destroy");

  // Public logging entry point (gpr_log itself is not in the public header).
  char msg[128];
  std::snprintf(msg, sizeof(msg),
                "libgpr consumer test: %u cpu(s), %d failure(s)", cores, failures);
  grpc_absl_log(GPR_INFO, msg);
  if (failures == 0) {
    std::printf("libgpr consumer test PASSED\n");
    return 0;
  }
  std::printf("libgpr consumer test FAILED (%d)\n", failures);
  return 1;
}