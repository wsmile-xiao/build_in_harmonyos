// Consumer smoke test for the xapian-core Conan package (OHOS port).
//
// Exercises the public C++ API on the three backends that 2.0.0 builds:
// in-memory, glass (zlib-compressed postings) and honey.  Honey databases are
// read-only in 2.0.0 and have to be produced by compacting a glass database,
// so this test also covers the compaction path.
#include <xapian.h>

#include <iostream>
#include <string>

namespace {

int failures = 0;

const std::string GLASS_PATH = "xapian_test_db_glass";
const std::string HONEY_PATH = "xapian_test_db_honey";

void check(bool ok, const std::string& what)
{
    std::cout << (ok ? "PASS " : "FAIL ") << what << '\n';
    if (!ok)
	++failures;
}

// Index three documents and read their data back through a query.
void index_documents(Xapian::WritableDatabase& db, const std::string& prefix)
{
    for (int n = 0; n < 3; ++n) {
	Xapian::Document doc;
	doc.set_data(prefix + " document " + std::to_string(n));
	doc.add_posting("Q" + prefix + std::to_string(n), 1);
	db.add_document(doc);
    }
    db.commit();
}

void report_matches(const Xapian::Database& db, const std::string& name,
		    const std::string& prefix)
{
    check(db.get_doccount() == 3, name + ": document count");

    Xapian::Enquire enquire(db);
    enquire.set_query(Xapian::Query(Xapian::Query::OP_OR,
				    Xapian::Query("Q" + prefix + "1"),
				    Xapian::Query("Q" + prefix + "2")));
    Xapian::MSet matches = enquire.get_mset(0, 10);
    check(matches.size() == 2, name + ": boolean query matches two documents");

    std::string data;
    for (Xapian::MSetIterator i = matches.begin(); i != matches.end(); ++i)
	data = i.get_document().get_data();
    check(data.rfind(prefix + " document ", 0) == 0,
	  name + ": document data round-trips");
}

void test_inmemory_backend()
{
    Xapian::WritableDatabase db("", Xapian::DB_BACKEND_INMEMORY);
    index_documents(db, "inmemory");
    report_matches(db, "inmemory", "inmemory");
}

void test_glass_backend()
{
    {
	Xapian::WritableDatabase db(GLASS_PATH,
				   Xapian::DB_CREATE_OR_OVERWRITE |
				   Xapian::DB_BACKEND_GLASS);
	index_documents(db, "glass");
    }

    Xapian::Database db(GLASS_PATH);
    report_matches(db, "glass", "glass");

    // glass is the backend honey is built from, so keep it open-able read-only
    // and hand the path over to the compaction check below.
}

void test_honey_backend()
{
    Xapian::Database glass(GLASS_PATH);
    glass.compact(HONEY_PATH,
		  Xapian::DB_BACKEND_HONEY | Xapian::DBCOMPACT_NO_RENUMBER);

    Xapian::Database db(HONEY_PATH, Xapian::DB_BACKEND_HONEY);
    report_matches(db, "honey", "glass");
}

}

int main()
{
    try {
	check(std::string(XAPIAN_VERSION) == "2.0.0",
	      std::string("version header reports ") + XAPIAN_VERSION);

	test_inmemory_backend();
	test_glass_backend();
	test_honey_backend();
    } catch (const Xapian::Error& e) {
	std::cerr << "unexpected Xapian::Error: " << e.get_msg() << '\n';
	return 1;
    }

    if (failures != 0) {
	std::cerr << failures << " xapian-core smoke assertions failed\n";
	return 1;
    }
    std::cout << "xapian-core smoke test passed: " << XAPIAN_VERSION << '\n';
    return 0;
}
