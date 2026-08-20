#include <cassert>
#include <cstdint>
#include <iostream>
#include <string>
#include <vector>

#include "entityx/entityx.h"

using namespace entityx;

// A simple Position component (matches upstream Entity_test.cc pattern)
struct Position {
  Position(float x = 0.0f, float y = 0.0f) : x(x), y(y) {}
  float x, y;
};

// A Direction component
struct Direction {
  Direction(float x = 0.0f, float y = 0.0f) : x(x), y(y) {}
  float x, y;
};

int main() {
  EntityX ex;

  // Create entities and assign components (R34: assign + component)
  Entity e1 = ex.entities.create();
  e1.assign<Position>(1.0f, 2.0f);
  e1.assign<Direction>(0.5f, 0.5f);

  Entity e2 = ex.entities.create();
  e2.assign<Position>(3.0f, 4.0f);

  Entity e3 = ex.entities.create();
  // e3 has no components

  // Verify component assignment
  ComponentHandle<Position> pos1 = e1.component<Position>();
  assert(pos1.valid());
  assert(pos1->x == 1.0f);
  assert(pos1->y == 2.0f);

  ComponentHandle<Position> pos2 = e2.component<Position>();
  assert(pos2.valid());
  assert(pos2->x == 3.0f);
  assert(pos2->y == 4.0f);

  // e3 should not have a Position
  ComponentHandle<Position> pos3 = e3.component<Position>();
  assert(!pos3.valid());

  // Iterate entities with Position component (R34: component traversal / query)
  int count = 0;
  for (auto entity : ex.entities.entities_with_components<Position>()) {
    (void)entity;
    ++count;
  }
  assert(count == 2);  // e1 and e2 have Position

  // Verify entity count via EntityManager::size()
  assert(ex.entities.size() == 3);  // e1, e2, e3

  std::cout << "entityx 1.3.0 test PASSED: "
            << "created " << ex.entities.size() << " entities, "
            << count << " with Position component" << std::endl;
  return 0;
}
