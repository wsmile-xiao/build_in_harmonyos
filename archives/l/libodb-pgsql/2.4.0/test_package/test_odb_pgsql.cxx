// file      : test_odb_pgsql.cxx
// copyright : Not copyrighted; provided as public domain consumer test.
//
// Consumer test for the bundled libodb-pgsql 2.4.0 + libodb 2.4.0 package.
// Exercises the real API surface without requiring a live PostgreSQL
// server: constructs an odb::pgsql::database (which instantiates the
// connection factory from the core runtime), reads back the parsed
// connection info, verifies the ODB interface version contract, and calls
// PQlibVersion() to prove libpq resolves and runs.

#include <odb/pgsql/database.hxx>
#include <odb/pgsql/version.hxx>

#include <odb/version.hxx>

#include <iostream>
#include <string>

extern "C" int PQlibVersion (void);

int
main ()
{
  // Version contract between the two bundled runtimes and the consumer.
  //
#if ODB_VERSION != 20400
#  error incompatible odb interface version
#endif
  if (LIBODB_PGSQL_VERSION != 2040000)
  {
    std::cerr << "unexpected LIBODB_PGSQL_VERSION" << std::endl;
    return 1;
  }

  // Real odb-pgsql API: parses the connection info and instantiates the
  // default connection factory (no server connection is attempted).
  //
  odb::pgsql::database db ("host=127.0.0.1 port=1 dbname=odb_pgsql_smoke");

  if (db.conninfo () != "host=127.0.0.1 port=1 dbname=odb_pgsql_smoke")
  {
    std::cerr << "unexpected conninfo round-trip" << std::endl;
    return 2;
  }

  // Real libpq API through the transitive postgresql dependency.
  //
  if (PQlibVersion () < 90000)
  {
    std::cerr << "unexpected libpq version" << std::endl;
    return 3;
  }

  std::cout << "libodb-pgsql " << LIBODB_PGSQL_VERSION_STR
            << " (odb " << (ODB_VERSION / 10000) << "."
            << (ODB_VERSION / 100 % 100) << "."
            << (ODB_VERSION % 100) << ")"
            << ", libpq " << (PQlibVersion () / 10000) << "."
            << (PQlibVersion () / 100 % 100) << "."
            << (PQlibVersion () % 100)
            << " consumer test passed" << std::endl;
  return 0;
}
