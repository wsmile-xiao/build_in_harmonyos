/* test_pdfio.c - pdfio 1.6.5 链接验证
 *
 * 实际调用 pdfio 公共 API,覆盖上游 testpdfio.c do_unit_tests() 的
 * 核心测试项:
 *   1. PDF 创建:pdfioFileCreate(上游 testBegin "pdfioFileCreate(...)")
 *   2. 字典操作:pdfioDictCreate + pdfioDictSetBoolean/Name/Number/String
 *      + pdfioDictIterateKeys (upstream testBegin "pdfioDictCreate/Set/Iterate")
 *   3. PDF 权限设置:pdfioFileSetPermissions RC4-128 加密
 *      (上游 testBegin "pdfioFileSetPermissions(...)")
 *   4. PDF 关闭:pdfioFileClose(上游 testBegin "pdfioFileClose")
 *   5. PDF 文件打开:pdfioFileOpen 打开刚创建的 PDF
 *      (上游 testBegin "pdfioFileOpen(...)")
 *   6. 版本宏校验:PDFIO_VERSION/PDFIO_VERSION_MAJOR/MINOR
 *
 * 无法覆盖的私有 API 测试项(_pdfioCrypto*,_pdfioValueRead):
 *   上游 do_crypto_tests() 用 _pdfioCryptoAESInit/MD5/RC4/SHA256 等私有 API,
 *   test_package 只能访问 pdfio.h 公共 API,无法覆盖.
 *
 * 创建 test_pdfio_output.pdf 在当前工作目录,关闭后删除.
 */
#include <pdfio.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

/* Dict iterate callback: count key/value pairs
 * (corresponds to upstream pdfioDictIterateKeys + iterate_cb) */
static bool count_keys(pdfio_dict_t *dict, const char *key, void *cb_data) {
  int *count = (int *)cb_data;
  (void)dict;
  (void)key;
  (*count)++;
  return true;
}

/* Password callback for pdfioFileOpen (returns the "user" password)
 * (corresponds to upstream password_cb usage in testpdfio.c) */
static const char *password_cb(void *data, const char *filename) {
  (void)data;
  (void)filename;
  return "user";
}

int main(void) {
  /* PDF 页面尺寸:US Letter 612x792 pt */
  pdfio_rect_t media_box = {0.0, 0.0, 612.0, 792.0};
  pdfio_rect_t crop_box  = {0.0, 0.0, 612.0, 792.0};

  /* === 测试 1:PDF 创建(pdfioFileCreate)=== */
  pdfio_file_t *pdf = pdfioFileCreate("test_pdfio_output.pdf", "1.4",
                                      &media_box, &crop_box,
                                      NULL, NULL);
  if (pdf == NULL) {
    fprintf(stderr, "FAIL: pdfioFileCreate returned NULL\n");
    return 1;
  }
  printf("OK: pdfioFileCreate\n");

  /* === 测试 2:字典操作(pdfioDictCreate + Set* + IterateKeys)=== */
  pdfio_dict_t *dict = pdfioDictCreate(pdf);
  if (dict == NULL) {
    fprintf(stderr, "FAIL: pdfioDictCreate returned NULL\n");
    pdfioFileClose(pdf);
    unlink("test_pdfio_output.pdf");
    return 1;
  }
  printf("OK: pdfioDictCreate\n");

  /* pdfioDictSet*:对应上游 pdfioDictSetBoolean/Name/Number/String */
  bool set_ok = true;
  set_ok &= pdfioDictSetBoolean(dict, "Boolean", true);
  set_ok &= pdfioDictSetName(dict, "Name", "TestName");
  set_ok &= pdfioDictSetNumber(dict, "Number", 42.0);
  set_ok &= pdfioDictSetString(dict, "String", "TestString");
  if (!set_ok) {
    fprintf(stderr, "FAIL: pdfioDictSet* returned false\n");
    pdfioFileClose(pdf);
    unlink("test_pdfio_output.pdf");
    return 1;
  }
  printf("OK: pdfioDictSetBoolean/Name/Number/String\n");

  /* pdfioDictIterateKeys:对应上游 iterate_cb + count */
  int key_count = 0;
  pdfioDictIterateKeys(dict, count_keys, &key_count);
  if (key_count != 4) {
    fprintf(stderr, "FAIL: pdfioDictIterateKeys got %d keys, expected 4\n",
            key_count);
    pdfioFileClose(pdf);
    unlink("test_pdfio_output.pdf");
    return 1;
  }
  printf("OK: pdfioDictIterateKeys (%d keys)\n", key_count);

  /* === 测试 3:PDF 权限设置(pdfioFileSetPermissions RC4-128)=== */
  if (!pdfioFileSetPermissions(pdf, PDFIO_PERMISSION_ALL,
                               PDFIO_ENCRYPTION_RC4_128,
                               /*owner*/"owner", /*user*/"user")) {
    fprintf(stderr, "FAIL: pdfioFileSetPermissions returned false\n");
    pdfioFileClose(pdf);
    unlink("test_pdfio_output.pdf");
    return 1;
  }
  printf("OK: pdfioFileSetPermissions (RC4-128)\n");

  /* === 测试 4:PDF 关闭(pdfioFileClose)=== */
  if (!pdfioFileClose(pdf)) {
    fprintf(stderr, "FAIL: pdfioFileClose returned false\n");
    unlink("test_pdfio_output.pdf");
    return 1;
  }
  printf("OK: pdfioFileClose\n");

  /* === 测试 5:PDF 文件打开(pdfioFileOpen 打开刚创建的加密 PDF)=== */
  pdfio_file_t *reopen = pdfioFileOpen("test_pdfio_output.pdf",
                                       password_cb,
                                       /*password_data*/NULL,
                                       /*error_cb*/NULL,
                                       /*error_data*/NULL);
  if (reopen == NULL) {
    fprintf(stderr, "FAIL: pdfioFileOpen returned NULL\n");
    unlink("test_pdfio_output.pdf");
    return 1;
  }
  printf("OK: pdfioFileOpen\n");

  /* 关闭重新打开的 PDF */
  if (!pdfioFileClose(reopen)) {
    fprintf(stderr, "FAIL: pdfioFileClose (reopen) returned false\n");
    unlink("test_pdfio_output.pdf");
    return 1;
  }

  /* 清理生成的 PDF 文件 */
  unlink("test_pdfio_output.pdf");

  /* === 测试 6:版本宏校验 === */
  printf("OK: pdfio version: %s\n", PDFIO_VERSION);
  if (PDFIO_VERSION_MAJOR != 1 || PDFIO_VERSION_MINOR != 6) {
    fprintf(stderr,
            "FAIL: PDFIO_VERSION_* macros wrong: %d.%d\n",
            PDFIO_VERSION_MAJOR, PDFIO_VERSION_MINOR);
    return 1;
  }
  printf("OK: PDFIO_VERSION_MAJOR/MINOR macros\n");

  printf("\n=== pdfio 1.6.5 test_package 全部通过 ===\n");
  return 0;
}
