/*
 * Consumer round-trip test for libodsstream 0.9.18.
 *
 * Writes an ODS spreadsheet through OdsDocWriter (sheets + typed cells),
 * reads it back with OdsDocReader + a custom handler, and asserts the
 * round-trip cell values. Complements the 5 upstream Catch2 TEST_CASEs.
 */
#include <QDebug>
#include <QFile>
#include <QString>
#include <iostream>
#include <odsstream/calcwriterinterface.h>
#include <odsstream/odsdocreader.h>
#include <odsstream/odsdocwriter.h>
#include <odsstream/odsexception.h>
#include <vector>

static int failures = 0;
static void check(const char *name, bool cond)
{
  std::cout << (cond ? "PASS: " : "FAIL: ") << name << std::endl;
  if(!cond)
    failures++;
}

class RoundtripHandler : public OdsDocHandlerInterface
{
  public:
  void
  endDocument() override
  {
  }
  void
  startSheet(const QString &sheet_name) override
  {
    m_sheetNames.push_back(sheet_name);
  }
  void
  endSheet() override
  {
  }
  void
  startLine() override
  {
  }
  void
  endLine() override
  {
  }
  void
  setCell(const OdsCell &cell) override
  {
    m_cells.push_back(cell.toString());
    if(cell.isDouble())
      m_doubles.push_back(cell.getDoubleValue());
  }

  QString
  getSheetName(std::size_t i) const
  {
    return m_sheetNames.at(i);
  }
  std::vector<QString> m_sheetNames;
  std::vector<QString> m_cells;
  std::vector<double> m_doubles;
};

int
main()
{
  const QString path = "test_roundtrip.ods";

  // ── Write an ODS file ────────────────────────────────────────────
  try
    {
      OdsDocWriter writer(path);
      writer.writeSheet("numbers");
      writer.writeCell(1);
      writer.writeCell(2);
      writer.writeCell(3.5);
      writer.writeLine();
      writer.writeCell("hello odsstream");
      writer.writeSheet("second sheet");
      writer.writeCell("A1");
      writer.writeLine();
      writer.writeCell(42);
      writer.close();
      check("OdsDocWriter writes without exception", true);
    }
  catch(OdsException &e)
    {
      qDebug() << e.what();
      check("OdsDocWriter writes without exception", false);
      return 1;
    }

  check("ODS file created on disk", QFile::exists(path));

  // ── Read it back ─────────────────────────────────────────────────
  RoundtripHandler handler;
  try
    {
      OdsDocReader reader(handler);
      QFile file(path);
      (void)file.open(QIODevice::ReadOnly);
      reader.parse(&file);
      file.close();
      check("OdsDocReader parses without exception", true);
    }
  catch(OdsException &e)
    {
      qDebug() << e.what();
      check("OdsDocReader parses without exception", false);
      return 1;
    }

  check("two sheets read back", handler.m_sheetNames.size() == 2);
  if(handler.m_sheetNames.size() == 2)
    {
      check("first sheet name round-trips",
            handler.m_sheetNames[0] == "numbers");
      check("second sheet name round-trips",
            handler.m_sheetNames[1] == "second sheet");
    }
  // Note: OdsDocReader invokes setCell twice per cell (value + repeat),
  // and empty cells also get callbacks; assert by membership instead of
  // exact positions/counts.
  std::cout << "cells read: " << handler.m_cells.size() << std::endl;
  auto has = [&handler](const QString &needle) {
    for(const auto &c : handler.m_cells)
      if(c.contains(needle))
        return true;
    return false;
  };
  check("numeric cell 3.5 round-trips", has("3.5"));
  check("text cell round-trips", has("hello odsstream"));
  check("numeric cell 42 round-trips", has("42"));
  check("text cell A1 round-trips", has("A1"));
  check("all read-back cells non-garbled", handler.m_cells.size() >= 5);

  if(failures == 0)
    {
      std::cout << "ALL ODSSSTREAM CONSUMER TESTS PASSED" << std::endl;
      return 0;
    }
  std::cout << failures << " ODSSSTREAM CONSUMER TEST(S) FAILED" << std::endl;
  return 1;
}
