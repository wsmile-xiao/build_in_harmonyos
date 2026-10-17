/*
 * Consumer smoke test for the packaged trousers (TSS 1.2) library.
 *
 * It exercises the context/policy part of the public TSPI API, which is the
 * part a downstream application can drive without a running TPM or the tcsd
 * daemon: create a context, fetch the default usage policy, build a new policy
 * object, set a secret on it and close everything again.
 */
#include <stdio.h>
#include <string.h>

#include <tss/tspi.h>

static int checks;
static int failed;

static void check(int condition, const char *what)
{
  checks++;
  if (condition) {
    printf("ok %d - %s\n", checks, what);
  } else {
    failed++;
    printf("FAIL %d - %s\n", checks, what);
  }
}

int main(void)
{
  TSS_HCONTEXT hContext = 0;
  TSS_HPOLICY hPolicy = 0;
  TSS_HPOLICY hNewPolicy = 0;
  TSS_RESULT result;
  BYTE secret[] = "trousers-consumer-test";

  result = Tspi_Context_Create(&hContext);
  check(result == TSS_SUCCESS && hContext != 0,
        "Tspi_Context_Create() returns a context handle");

  result = Tspi_Context_GetDefaultPolicy(hContext, &hPolicy);
  check(result == TSS_SUCCESS && hPolicy != 0,
        "Tspi_Context_GetDefaultPolicy() returns the default policy");

  result = Tspi_Context_CreateObject(hContext, TSS_OBJECT_TYPE_POLICY,
                                     TSS_POLICY_USAGE, &hNewPolicy);
  check(result == TSS_SUCCESS && hNewPolicy != 0,
        "Tspi_Context_CreateObject() creates a usage policy object");

  result = Tspi_Policy_SetSecret(hNewPolicy, TSS_SECRET_MODE_PLAIN,
                                 sizeof(secret) - 1, secret);
  check(result == TSS_SUCCESS,
        "Tspi_Policy_SetSecret() accepts a plain secret");

  result = Tspi_Context_CloseObject(hContext, hNewPolicy);
  check(result == TSS_SUCCESS, "Tspi_Context_CloseObject() releases the policy");

  result = Tspi_Context_Close(hContext);
  check(result == TSS_SUCCESS, "Tspi_Context_Close() tears the context down");

  printf("%d checks, %d failures\n", checks, failed);
  return failed == 0 ? 0 : 1;
}
