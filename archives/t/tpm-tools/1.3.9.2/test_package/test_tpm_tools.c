/*
 * Consumer smoke test for the packaged tpm-tools library.
 *
 * libtpm_unseal's tpmUnsealStrerror() is the one entry point that can be
 * driven without a TPM device (the other two operate on sealed files or heap
 * buffers), so the C part of the consumer test exercises the library's public
 * error-message API; the CLI tools are smoke tested by the test_package
 * conanfile (tpm_version --version / tpm_nvinfo --help).
 */
#include <stdio.h>
#include <string.h>

#include <tpm_tools/tpm_unseal.h>

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
  char *msg_success = tpmUnsealStrerror(0);

  check(msg_success != NULL && msg_success[0] != '\0',
        "tpmUnsealStrerror(0) returns a non-empty message");
  check(msg_success != NULL && strcmp(msg_success, "Success") == 0,
        "tpmUnsealStrerror(0) reports Success");

  printf("%d checks, %d failures\n", checks, failed);
  return failed == 0 ? 0 : 1;
}
