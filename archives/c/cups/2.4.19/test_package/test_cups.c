#include <cups/cups.h>
#include <cups/ipp.h>

#include <stdio.h>
#include <string.h>

#define CHECK(condition, label) \
  do \
  { \
    if (!(condition)) \
    { \
      fprintf(stderr, "%s=FAIL\n", label); \
      goto fail; \
    } \
    passed ++; \
  } \
  while (0)

int
main(void)
{
  ipp_t *request = NULL;
  ipp_attribute_t *attribute;
  cups_option_t *options = NULL;
  const char *value;
  int num_options = 0;
  int passed = 0;

  CHECK(CUPS_VERSION_MAJOR == 2 && CUPS_VERSION_MINOR == 4 &&
        CUPS_VERSION_PATCH == 19, "VERSION");

  request = ippNewRequest(IPP_OP_GET_PRINTER_ATTRIBUTES);
  CHECK(request != NULL, "IPP_NEW_REQUEST");
  CHECK(ippGetOperation(request) == IPP_OP_GET_PRINTER_ATTRIBUTES,
        "IPP_OPERATION");

  attribute = ippAddString(request, IPP_TAG_OPERATION, IPP_TAG_CHARSET,
                           "attributes-charset", NULL, "utf-8");
  CHECK(attribute != NULL, "IPP_ADD_CHARSET");
  attribute = ippFindAttribute(request, "attributes-charset", IPP_TAG_CHARSET);
  value = attribute ? ippGetString(attribute, 0, NULL) : NULL;
  CHECK(value != NULL && !strcmp(value, "utf-8"), "IPP_FIND_CHARSET");

  attribute = ippAddBoolean(request, IPP_TAG_OPERATION, "my-boolean", 1);
  CHECK(attribute != NULL && ippGetBoolean(attribute, 0) == 1,
        "IPP_BOOLEAN");

  num_options = cupsAddOption("media", "iso_a4_210x297mm", num_options,
                              &options);
  CHECK(num_options == 1, "CUPS_ADD_OPTION");
  value = cupsGetOption("media", num_options, options);
  CHECK(value != NULL && !strcmp(value, "iso_a4_210x297mm"),
        "CUPS_GET_OPTION");

  CHECK(ippLength(request) >= 16, "IPP_LENGTH");

  cupsFreeOptions(num_options, options);
  ippDelete(request);
  printf("CUPS_TEST_ASSERTIONS=%d/9\n", passed);
  return 0;

fail:
  cupsFreeOptions(num_options, options);
  if (request)
    ippDelete(request);
  return 1;
}
