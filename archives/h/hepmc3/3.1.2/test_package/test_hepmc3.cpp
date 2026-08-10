#include "HepMC3/GenEvent.h"
#include "HepMC3/GenVertex.h"
#include "HepMC3/GenParticle.h"
#include <iostream>
#include <memory>

int main() {
    // Create an event with GEV/MM units
    HepMC3::GenEvent evt(HepMC3::Units::GEV, HepMC3::Units::MM);
    evt.set_event_number(42);

    // Create incoming particles (two protons)
    auto p_in1 = std::make_shared<HepMC3::GenParticle>(
        HepMC3::FourVector(0, 0, 7000, 7000), 2212, 4);
    auto p_in2 = std::make_shared<HepMC3::GenParticle>(
        HepMC3::FourVector(0, 0, -7000, 7000), 2212, 4);

    // Create a vertex and add incoming particles
    auto v = std::make_shared<HepMC3::GenVertex>();
    v->add_particle_in(p_in1);
    v->add_particle_in(p_in2);

    // Add outgoing particle (electron)
    auto p_out = std::make_shared<HepMC3::GenParticle>(
        HepMC3::FourVector(-0.750, -1.569, 32.191, 32.238), 1, 1);
    v->add_particle_out(p_out);

    // Add vertex to event
    evt.add_vertex(v);

    // Verify event structure
    if (evt.event_number() != 42) {
        std::cerr << "FAIL: event number mismatch (got " << evt.event_number() << ")" << std::endl;
        return 1;
    }
    if (evt.vertices().size() != 1) {
        std::cerr << "FAIL: vertex count mismatch (got " << evt.vertices().size() << ")" << std::endl;
        return 1;
    }
    if (evt.particles().size() != 3) {
        std::cerr << "FAIL: particle count mismatch (got " << evt.particles().size() << ")" << std::endl;
        return 1;
    }

    std::cout << "test hepmc3 3.1.2: OK (event=" << evt.event_number()
              << ", vertices=" << evt.vertices().size()
              << ", particles=" << evt.particles().size() << ")" << std::endl;
    return 0;
}
