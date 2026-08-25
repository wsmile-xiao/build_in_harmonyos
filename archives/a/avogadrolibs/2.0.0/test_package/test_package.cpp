#include <avogadro/core/molecule.h>
#include <avogadro/io/cjsonformat.h>
#include <avogadro/io/cmlformat.h>
#include <avogadro/io/dcdformat.h>

#include <iostream>
#include <sstream>
#include <string>

int main()
{
  Avogadro::Core::Molecule molecule;
  auto oxygen = molecule.addAtom(8);
  auto hydrogen1 = molecule.addAtom(1);
  auto hydrogen2 = molecule.addAtom(1);
  molecule.addBond(oxygen, hydrogen1, 1);
  molecule.addBond(oxygen, hydrogen2, 1);

  if (molecule.atomCount() != 3 || molecule.bondCount() != 2)
    return 1;

  Avogadro::Io::CjsonFormat format;
  std::stringstream output;
  if (!format.write(output, molecule))
    return 2;
  const std::string json = output.str();
  if (json.find("atoms") == std::string::npos || json.find("elements") == std::string::npos)
    return 3;

  Avogadro::Io::CmlFormat cml;
  std::stringstream cmlOutput;
  if (!cml.write(cmlOutput, molecule))
    return 4;
  if (cmlOutput.str().find("atomArray") == std::string::npos)
    return 5;

  Avogadro::Io::DcdFormat dcd;
  std::stringstream malformedDcd(std::string("not-a-dcd"));
  if (dcd.read(malformedDcd, molecule))
    return 6;

  std::cout << "avogadrolibs consumer test passed\n";
  return 0;
}
