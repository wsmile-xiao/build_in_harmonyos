/*
 * Consumer test for langford 0.0.20130228: link against the installed
 * liblangford_spi.a + headers and drive the public SPI helper.
 *
 * LangordSpiWrite() bit-bangs three ioctl pin writes; called on an invalid
 * file descriptor every ioctl() fails, so the helper must return a non-zero
 * error code (and must not crash).  This proves the packaged library and
 * headers are usable by a downstream consumer.
 */
#include <cstdio>

#include "langford_ioctl.h"
#include "langford_spi.h"

int main() {
  int fails = 0;

  /* The ioctl command constants must survive packaging unchanged. */
  if (IOCTL_SET_ADCAnCS != 249 || IOCTL_SET_ADCASClk != 245 ||
      IOCTL_SET_ADCASDIO != 247 || IOCTL_GET_N21at0 != 100 ||
      IOCTL_SET_GPIOout != 625) {
    printf("FAIL: ioctl constants changed by packaging\n");
    fails++;
  } else {
    printf("OK: ioctl constants intact\n");
  }

  int rc = LangordSpiWrite(-1, 3, 0x123456, IOCTL_SET_ADCAnCS,
                           IOCTL_SET_ADCASClk, IOCTL_SET_ADCASDIO);
  if (rc == 0) {
    printf("FAIL: LangordSpiWrite on invalid fd returned 0\n");
    fails++;
  } else {
    printf("OK: LangordSpiWrite on invalid fd returned %d\n", rc);
  }

  printf("SPI_CONSUMER_FAILS=%d\n", fails);
  return fails ? 1 : 0;
}
