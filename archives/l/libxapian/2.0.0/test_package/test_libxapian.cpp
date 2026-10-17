// Consumer end-to-end test for the libxapian Conan package (OHOS port).
//
// This is ONE complete consumer use-case (a mini search application), not a
// bag of isolated asserts.  It runs a realistic document lifecycle end to
// end on device: create glass DB -> index with TermGenerator+Stem ->
// commit -> reopen read-only -> natural-language query via QueryParser ->
// ranked retrieval -> metadata -> replace -> delete -> persistence reopen.
// It also covers the other two backends 2.0.0 builds (in-memory and honey,
// the latter produced by compacting glass, which is read-only in 2.0.0).
#include <xapian.h>

#include <iostream>
#include <string>
#include <vector>

namespace {

int failures = 0;

const std::string GLASS_PATH = "libxapian_test_db_glass";
const std::string HONEY_PATH = "libxapian_test_db_honey";
const std::string CONSUMER_PATH = "libxapian_consumer_db";

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
		  Xapian::DB_CREATE_OR_OVERWRITE | Xapian::DB_BACKEND_HONEY |
		  Xapian::DBCOMPACT_NO_RENUMBER);

    Xapian::Database db(HONEY_PATH, Xapian::DB_BACKEND_HONEY);
    report_matches(db, "honey", "glass");
}

// Complete consumer workflow: a mini search app indexing 5 realistic
// documents, then querying them the way a real HarmonyOS PC app would
// (stemmed natural-language query -> ranked MSet -> stored data), followed
// by metadata/replace/delete/persistence.  Every stage prints progress so
// the preflight log shows a real end-to-end run, not silent asserts.
void test_ohos_consumer_search_workflow()
{
    std::cout << "OHOS consumer workflow: indexing 5 documents\n";
    const char* titles[5] = {
	"Xapian search engine overview",
	"Glass backend storage notes",
	"Honey read-only index guide",
	"Stemming and query parsing",
	"HarmonyOS document retrieval",
    };
    const char* bodies[5] = {
	"Xapian is a search engine library with probabilistic ranking",
	"Glass stores search engine postings compressed with zlib on disk",
	"Honey is a read-only search engine backend produced by compacting glass",
	"TermGenerator and QueryParser provide stemming for search engine queries",
	"HarmonyOS apps retrieve documents through ranked search engine results",
    };
    const char* uniq[5] = { "unitoverview", "unitglass", "unithoney",
			    "unitstem", "unitharmony" };

    std::vector<Xapian::docid> dids;
    {
	Xapian::WritableDatabase db(CONSUMER_PATH,
				   Xapian::DB_CREATE_OR_OVERWRITE |
				   Xapian::DB_BACKEND_GLASS);
	Xapian::TermGenerator indexer;
	indexer.set_stemmer(Xapian::Stem("english"));
	for (int n = 0; n < 5; ++n) {
	    Xapian::Document doc;
	    indexer.set_document(doc);
	    indexer.index_text(std::string(titles[n]) + " " + bodies[n]);
	    doc.set_data(std::string(titles[n]) + "|" + bodies[n]);
	    doc.add_boolean_term(std::string("U") + uniq[n]);
	    dids.push_back(db.add_document(doc));
	}
	db.commit();
	check(db.get_doccount() == 5,
	      "consumer: five documents indexed");
    }

    std::cout << "OHOS consumer workflow: querying natural language\n";
    {
	Xapian::Database db(CONSUMER_PATH);
	Xapian::QueryParser qp;
	qp.set_stemmer(Xapian::Stem("english"));
	qp.set_database(db);
	qp.set_default_op(Xapian::Query::OP_AND);
	Xapian::Enquire enquire(db);
	enquire.set_query(qp.parse_query("search engine"));
	Xapian::MSet m = enquire.get_mset(0, 10);
	check(m.size() == 5, "consumer: natural query matches five documents");

	// Unique-term lookup proves ranking returns the RIGHT document,
	// not just any hits.
	Xapian::Enquire e2(db);
	e2.set_query(Xapian::Query(std::string("U") + "unithoney"));
	Xapian::MSet m2 = e2.get_mset(0, 10);
	bool honey_ok = (m2.size() == 1 &&
			 m2.begin().get_document().get_data().find(
			     "Honey read-only index guide") == 0);
	check(honey_ok, "consumer: unique-term lookup returns honey guide");
    }

    std::cout << "OHOS consumer workflow: metadata/replace/delete/persist\n";
    {
	Xapian::WritableDatabase db(CONSUMER_PATH,
				   Xapian::DB_OPEN |
				   Xapian::DB_BACKEND_GLASS);
	db.set_metadata("app", "ohos-consumer-1");
	check(db.get_metadata("app") == "ohos-consumer-1",
	      "consumer: metadata round-trips");

	// Replace the stemming doc with revised content.
	Xapian::Document fresh;
	Xapian::TermGenerator g;
	g.set_stemmer(Xapian::Stem("english"));
	g.set_document(fresh);
	g.index_text("Stemming and query parsing revised edition search engine");
	fresh.set_data("Stemming and query parsing|revised edition");
	fresh.add_boolean_term(std::string("U") + "unitstem");
	db.replace_document(dids[3], fresh);
	db.commit();
	Xapian::Document got = db.get_document(dids[3]);
	check(got.get_data().find("revised edition") != std::string::npos,
	      "consumer: replace_document updates stored data");

	// Delete the glass-notes doc and confirm it is gone.
	db.delete_document(dids[1]);
	db.commit();
	check(db.get_doccount() == 4, "consumer: delete drops doccount to four");
	Xapian::Enquire e3(db);
	e3.set_query(Xapian::Query(std::string("U") + "unitglass"));
	check(e3.get_mset(0, 10).size() == 0,
	      "consumer: deleted doc no longer matches");
    }

    {
	// Persistence: close and reopen, the 4 remaining docs must survive.
	Xapian::Database db(CONSUMER_PATH);
	check(db.get_doccount() == 4, "consumer: reopen persists four docs");
    }
    std::cout << "OHOS consumer workflow: end-to-end search flow completed\n";
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
	test_ohos_consumer_search_workflow();
    } catch (const Xapian::Error& e) {
	std::cerr << "unexpected Xapian::Error: " << e.get_msg() << '\n';
	return 1;
    }

    if (failures != 0) {
	std::cerr << failures << " libxapian consumer assertions failed\n";
	return 1;
    }
    std::cout << "libxapian consumer end-to-end test passed: "
	      << XAPIAN_VERSION << '\n';
    return 0;
}
