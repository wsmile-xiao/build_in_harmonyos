#include <xapian.h>

#include <iostream>
#include <string>

int main() {
    Xapian::WritableDatabase db("", Xapian::DB_BACKEND_INMEMORY);

    Xapian::Document doc;
    doc.set_data("HarmonyOS Xapian smoke test");
    doc.add_term("Qharmonyos");
    doc.add_term("Zxapian");
    db.add_document(doc);
    db.commit();

    Xapian::Enquire enquire(db);
    enquire.set_query(Xapian::Query("Qharmonyos"));
    Xapian::MSet matches = enquire.get_mset(0, 10);

    if (matches.size() != 1) {
        std::cerr << "expected one match, got " << matches.size() << '\n';
        return 1;
    }
    if (matches.begin().get_document().get_data() != "HarmonyOS Xapian smoke test") {
        std::cerr << "matched document data mismatch\n";
        return 1;
    }
    if (Xapian::version_string() != std::string("1.4.22")) {
        std::cerr << "unexpected Xapian version: " << Xapian::version_string() << '\n';
        return 1;
    }

    std::cout << "xapian-core smoke test passed: " << Xapian::version_string() << '\n';
    return 0;
}
