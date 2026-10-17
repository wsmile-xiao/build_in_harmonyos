#include <curl/curl.h>

#include <stdio.h>
#include <string.h>

static int require_true(int condition, const char *message) {
  if (!condition) {
    fprintf(stderr, "%s\n", message);
    return 0;
  }
  return 1;
}

int main(void) {
  CURLcode code = curl_global_init(CURL_GLOBAL_DEFAULT);
  if (!require_true(code == CURLE_OK, "curl_global_init failed")) return 1;

  CURL *handle = curl_easy_init();
  if (!require_true(handle != NULL, "curl_easy_init returned NULL")) return 1;

  code = curl_easy_setopt(handle, CURLOPT_URL, "https://example.com/");
  if (!require_true(code == CURLE_OK, "CURLOPT_URL failed")) return 1;
  code = curl_easy_setopt(handle, CURLOPT_NOBODY, 1L);
  if (!require_true(code == CURLE_OK, "CURLOPT_NOBODY failed")) return 1;

  curl_version_info_data *info = curl_version_info(CURLVERSION_NOW);
  if (!require_true(info != NULL, "curl_version_info returned NULL")) return 1;
  if (!require_true(info->version_num == LIBCURL_VERSION_NUM,
                    "libcurl version does not match headers"))
    return 1;
  if (!require_true((info->features & CURL_VERSION_SSL) != 0,
                    "SSL feature is missing"))
    return 1;
  if (!require_true(info->ssl_version != NULL &&
                        strstr(info->ssl_version, "OpenSSL") != NULL,
                    "OpenSSL backend is missing"))
    return 1;
  if (!require_true(info->libz_version != NULL, "zlib support is missing"))
    return 1;

  printf("%s; %s; zlib/%s\n", info->version, info->ssl_version,
         info->libz_version);
  curl_easy_cleanup(handle);
  curl_global_cleanup();
  return 0;
}
