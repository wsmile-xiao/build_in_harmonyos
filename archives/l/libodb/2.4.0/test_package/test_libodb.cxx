// file      : test_libodb.cxx
// copyright : Not copyrighted; provided as public domain consumer test.
//
// Consumer test for the libodb 2.4.0 core runtime. Exercises the real API
// surface without a database profile: version contract macros, the
// intrusive details::shared_ptr reference counting (inc/dec through copy
// and assignment), and the polymorphic odb::exception hierarchy (what()/
// clone()) whose implementations live in libodb itself.

#include <odb/version.hxx>
#include <odb/details/shared-ptr.hxx>
#include <odb/exceptions.hxx>

#include <iostream>
#include <string>

// Class held by the intrusive odb::details::shared_ptr (derives
// shared_base, whose inc/dec implementations live in libodb).
//
struct object: odb::details::shared_base
{
  int value;
};

static std::string
exception_what (const odb::exception& e)
{
  // Polymorphic call into libodb's exported exception implementations.
  //
  std::string r (e.what ());

  // clone() is also a real libodb symbol; the clone must preserve the
  // dynamic type and message.
  //
  odb::null_pointer* c (dynamic_cast<odb::null_pointer*> (e.clone ()));
  if (c != 0)
  {
    r += "|";
    r += c->what ();
    delete c;
  }
  else
    return r;  // clone type check failed; caller reports
  return r;
}

int
main ()
{
  // 1. Version contract between the headers and the library.
  //
#if ODB_VERSION != 20400 || LIBODB_VERSION != 2040000
#  error incompatible libodb interface version
#endif

  // 2. Intrusive shared_ptr reference counting through the exported
  //    odb::details::shared_base symbols.
  //
  odb::details::shared_ptr<object> p (new object);
  p->value = 42;

  {
    odb::details::shared_ptr<object> q (p);
    if (q->_ref_count () != 2 || p->_ref_count () != 2)
    {
      std::cerr << "unexpected refcount after copy" << std::endl;
      return 1;
    }
  }

  if (p->_ref_count () != 1)
  {
    std::cerr << "unexpected refcount after scope exit" << std::endl;
    return 2;
  }

  if (p->value != 42)
  {
    std::cerr << "unexpected object value" << std::endl;
    return 3;
  }

  // 3. Polymorphic exception hierarchy implemented in libodb.
  //
  odb::null_pointer np;
  std::string w (exception_what (np));
  if (w.find ("NULL pointer") == std::string::npos ||
      w.find ("|NULL pointer") == std::string::npos)
  {
    std::cerr << "unexpected null_pointer message: " << w << std::endl;
    return 4;
  }

  std::cout << "libodb " << LIBODB_VERSION_STR
            << " (odb " << ODB_VERSION_STR << ")"
            << " consumer test passed: refcount ok, exception "
            << w << std::endl;
  return 0;
}
