// test_echo.cpp — consumer test for omniorb 4.3.4.
//
// Adapted from the upstream single-process example
// src/examples/echo/eg1.cc: initialise the ORB, activate a collocated
// Echo servant on the RootPOA, perform the call and require the exact
// reply string. Any CORBA exception or reply mismatch exits non-zero.
#include "echo.hh"

#include <cstring>
#include <iostream>

class Echo_i : public POA_Echo
{
public:
  inline Echo_i() {}
  virtual ~Echo_i() {}
  virtual char* echoString(const char* mesg);
};

char* Echo_i::echoString(const char* mesg)
{
  // Memory management rules require a freshly allocated string.
  return CORBA::string_dup(mesg);
}

int main(int argc, char** argv)
{
  try {
    CORBA::ORB_var orb = CORBA::ORB_init(argc, argv);

    CORBA::Object_var obj = orb->resolve_initial_references("RootPOA");
    PortableServer::POA_var poa = PortableServer::POA::_narrow(obj);

    PortableServer::Servant_var<Echo_i> servant = new Echo_i();
    PortableServer::ObjectId_var oid = poa->activate_object(servant);
    (void)oid;

    Echo_var ref = servant->_this();

    PortableServer::POAManager_var mgr = poa->the_POAManager();
    mgr->activate();

    CORBA::String_var reply = ref->echoString("Hello, HarmonyOS!");
    if (std::strcmp(reply.in(), "Hello, HarmonyOS!") != 0) {
      std::cerr << "echo reply mismatch: " << reply.in() << std::endl;
      orb->destroy();
      return 1;
    }
    std::cout << "echo reply verified: " << reply.in() << std::endl;

    orb->destroy();
  }
  catch (const CORBA::Exception& ex) {
    std::cerr << "CORBA exception: " << ex._name() << std::endl;
    return 1;
  }
  return 0;
}
