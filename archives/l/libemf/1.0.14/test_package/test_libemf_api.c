/*
 * Consumer test for the installed libEMF package (L1 test_package).
 *
 * Exercises the public C API the way the upstream tests do
 *   CreateEnhMetaFile -> GDI drawing calls -> CloseEnhMetaFile
 * and then verifies the produced artifact from the outside:
 *   - the on-disk EMF header (magic, version, size accounting, record count,
 *     hard-copy frame and drawing bounds),
 *   - reopening the file through GetEnhMetaFile and replaying it with
 *     PlayEnhMetaFile into a second metafile,
 *   - the documented error path for a missing file.
 *
 * Documented libEMF quirks asserted here (verified against the 1.0.14 sources
 * and a device probe, see the task evidence logs):
 *   - SetPixel returns the dummy value RGB(0,0,0), it is not an error code;
 *   - SetTextColor returns the *previous* colour;
 *   - DeleteEnhMetaFile must be called before DeleteDC: both take the same
 *     object from libEMF's handle table, so deleting the DC first makes the
 *     later DeleteEnhMetaFile fail;
 *   - GetDesktopWindow/GetDC return dummy handles (0): a graphics system
 *     is not required;
 *   - GetEnhMetaFileHeader copies libEMF's internal header object, so the
 *     call contract (returned size) is checked, not the struct fields.
 *
 * Exits non-zero with a message per failed assertion.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <libEMF/emf.h>

#define DEFAULT_METAFILE "consumer.emf"

/* Hard-copy frame passed to CreateEnhMetaFile, in .01 mm units (10cm x 20cm). */
#define FRAME_RIGHT 10000
#define FRAME_BOTTOM 20000

static int failures = 0;

static void check(int condition, const char* what)
{
  if (condition) {
    printf("  ok   : %s\n", what);
  } else {
    printf("  FAIL : %s\n", what);
    failures++;
  }
}

static long file_size(const char* path)
{
  FILE* fp = fopen(path, "rb");
  long size;

  if (fp == NULL) {
    return -1;
  }
  if (fseek(fp, 0, SEEK_END) != 0) {
    fclose(fp);
    return -1;
  }
  size = ftell(fp);
  fclose(fp);
  return size;
}

static int read_header(const char* path, ENHMETAHEADER* header)
{
  FILE* fp = fopen(path, "rb");
  size_t got;

  if (fp == NULL) {
    return 0;
  }
  got = fread(header, 1, sizeof(*header), fp);
  fclose(fp);
  return got == sizeof(*header);
}

int main(int argc, char* argv[])
{
  const char* metafile_name = (argc > 1) ? argv[1] : DEFAULT_METAFILE;
  char replay_name[4096];
  char missing_name[4096];
  HWND desktop;
  HDC dc;
  HDC meta_dc;
  HDC replay_dc;
  RECT frame;
  HPEN pen;
  HBRUSH brush;
  HENHMETAFILE metafile;
  HENHMETAFILE reread;
  HENHMETAFILE replayed;
  ENHMETAHEADER header;
  ENHMETAHEADER replay_header;
  COLORREF second_color;
  long size;

  printf("libEMF consumer test\n");
  snprintf(replay_name, sizeof(replay_name), "%s.replay", metafile_name);
  snprintf(missing_name, sizeof(missing_name), "%s.missing", metafile_name);

  /* ---- 1. create + draw through the public C API ------------------ */

  /* libEMF does not require a graphics system: GetDesktopWindow/GetDC
   * return dummy handles (documented as 0) and CreateEnhMetaFile still
   * produces a usable metafile context from them. */
  desktop = GetDesktopWindow();
  check(desktop == 0, "GetDesktopWindow returns the documented dummy handle");

  dc = GetDC(desktop);
  check(dc == 0, "GetDC returns the documented dummy context");

  frame.left = 0;
  frame.top = 0;
  frame.right = FRAME_RIGHT;
  frame.bottom = FRAME_BOTTOM;

  meta_dc = CreateEnhMetaFile(dc, metafile_name, &frame,
                              "libEMF consumer test\0");
  check(meta_dc != 0, "CreateEnhMetaFile returns a metafile device context");

  check(SetMapMode(meta_dc, MM_ANISOTROPIC) != 0,
        "SetMapMode(MM_ANISOTROPIC) succeeds");

  pen = CreatePen(PS_SOLID, 10, RGB(0, 0, 0));
  check(pen != 0, "CreatePen returns a pen handle");
  check(SelectObject(meta_dc, pen) != 0, "SelectObject(pen) succeeds");

  brush = CreateSolidBrush(RGB(0x80, 0x80, 0x80));
  check(brush != 0, "CreateSolidBrush returns a brush handle");
  check(SelectObject(meta_dc, brush) != 0, "SelectObject(brush) succeeds");

  check(MoveToEx(meta_dc, 0, 0, NULL) != 0, "MoveToEx succeeds");
  check(LineTo(meta_dc, 1000, 1000) != 0, "LineTo succeeds");
  check(Rectangle(meta_dc, 100, 100, 900, 900) != 0, "Rectangle succeeds");
  check(Ellipse(meta_dc, 200, 200, 800, 800) != 0, "Ellipse succeeds");

  /* SetTextColor returns the previous colour: the second call must report
   * the colour selected by the first one. */
  SetTextColor(meta_dc, RGB(0x12, 0x34, 0x56));
  second_color = SetTextColor(meta_dc, RGB(0xaa, 0xbb, 0xcc));
  check(second_color == RGB(0x12, 0x34, 0x56),
        "SetTextColor returns the previously set text colour");

  check(SetPixel(meta_dc, 500, 500, RGB(0xff, 0, 0)) == RGB(0, 0, 0),
        "SetPixel returns the documented dummy colour");
  check(SetTextAlign(meta_dc, TA_CENTER) != 0, "SetTextAlign succeeds");
  check(SetBkMode(meta_dc, TRANSPARENT) != 0, "SetBkMode succeeds");
  check(TextOutA(meta_dc, 500, 50, "libEMF", 6) != 0, "TextOutA succeeds");
  check(SelectObject(meta_dc, GetStockObject(WHITE_BRUSH)) != 0,
        "SelectObject(GetStockObject(WHITE_BRUSH)) succeeds");

  metafile = CloseEnhMetaFile(meta_dc);
  check(metafile != 0, "CloseEnhMetaFile returns a metafile handle");
  /* libEMF keeps DCs and metafiles in one handle table: the metafile must be
   * deleted before the DC it came from. */
  check(DeleteEnhMetaFile(metafile) != 0,
        "DeleteEnhMetaFile releases the metafile");
  check(DeleteDC(meta_dc) != 0, "DeleteDC releases the metafile DC");
  check(GetLastError() == 0, "GetLastError returns NO_ERROR");

  /* ---- 2. artifact assertions ------------------------------------- */

  size = file_size(metafile_name);
  check(size > 0, "the metafile was written to disk");

  check(read_header(metafile_name, &header),
        "the metafile starts with a full ENHMETAHEADER");

  check(header.iType == EMR_HEADER, "header record type is EMR_HEADER");
  check(header.dSignature == ENHMETA_SIGNATURE,
        "header carries the EMF signature");
  check(header.nVersion == 0x10000, "header version is 1.0 (0x10000)");
  check((long)header.nBytes == size,
        "header nBytes matches the file size on disk");
  check((long)header.nSize <= size,
        "header record size does not exceed the file");
  check(header.nRecords >= 5,
        "the metafile holds at least 5 records (header + drawing)");
  check(header.rclFrame.right == FRAME_RIGHT &&
        header.rclFrame.bottom == FRAME_BOTTOM,
        "header hard-copy frame matches the requested 10cm x 20cm");
  check(header.rclBounds.right > header.rclBounds.left &&
        header.rclBounds.bottom > header.rclBounds.top,
        "header drawing bounds are non-degenerate");
  check(header.rclBounds.right <= header.rclFrame.right &&
        header.rclBounds.bottom <= header.rclFrame.bottom,
        "drawing bounds stay inside the hard-copy frame");

  /* ---- 3. reopen + replay through the library ---------------------- */

  reread = GetEnhMetaFile(metafile_name);
  check(reread != 0, "GetEnhMetaFile reopens the written metafile");

  check(GetEnhMetaFileHeader(reread, sizeof(header), &header) ==
        sizeof(ENHMETAHEADER),
        "GetEnhMetaFileHeader reports the header size");

  replay_dc = CreateEnhMetaFile(dc, replay_name, &frame,
                                "libEMF replay test\0");
  check(replay_dc != 0, "CreateEnhMetaFile returns a replay context");
  check(PlayEnhMetaFile(replay_dc, reread, &frame) != 0,
        "PlayEnhMetaFile replays the reopened metafile");
  replayed = CloseEnhMetaFile(replay_dc);
  check(replayed != 0, "CloseEnhMetaFile returns the replayed metafile");
  check(DeleteEnhMetaFile(replayed) != 0,
        "DeleteEnhMetaFile releases the replayed metafile");
  check(DeleteDC(replay_dc) != 0, "DeleteDC releases the replay context");
  check(DeleteEnhMetaFile(reread) != 0,
        "DeleteEnhMetaFile releases the reopened metafile");

  check(read_header(replay_name, &replay_header),
        "the replayed metafile starts with a full ENHMETAHEADER");
  check(replay_header.iType == EMR_HEADER &&
        replay_header.dSignature == ENHMETA_SIGNATURE,
        "the replayed metafile is a valid EMF");
  check(replay_header.nRecords >= 5,
        "the replayed metafile keeps the drawing records");

  /* ---- 4. documented error paths ---------------------------------- */

  check(GetEnhMetaFile(missing_name) == 0,
        "GetEnhMetaFile returns 0 for a missing file");

  if (failures != 0) {
    printf("FAILED: %d assertion(s)\n", failures);
    return EXIT_FAILURE;
  }
  printf("PASS: all libEMF consumer assertions held\n");
  return EXIT_SUCCESS;
}
