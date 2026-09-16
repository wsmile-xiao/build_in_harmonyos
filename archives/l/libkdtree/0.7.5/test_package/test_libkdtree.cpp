// test_package/test_libkdtree.cpp — consumer test for libkdtree++ 0.7.5
//
// Compiles against the packaged headers only (#include <kdtree++/kdtree.hpp>)
// and exercises the real public API: default accessor KDTree<3, point>,
// insert / size / iteration / find / find_nearest / find_within_range /
// erase / optimise / copy construction.  Every check is an assert against a
// value that is computed independently in this file, so the test genuinely
// depends on the packaged library (R34).

#include <kdtree++/kdtree.hpp>

#include <cassert>
#include <cstddef>
#include <iostream>
#include <iterator>
#include <utility>
#include <vector>

// The default accessor is _Bracket_accessor, so a value type only needs
// value_type + operator[] to be usable with the default KDTree template.
struct point
{
  typedef double value_type;

  double d[3];

  point(double a = 0.0, double b = 0.0, double c = 0.0)
  {
    d[0] = a;
    d[1] = b;
    d[2] = c;
  }

  value_type operator[](std::size_t n) const { return d[n]; }
};

typedef KDTree::KDTree<3, point> tree_type;

int main()
{
  const point p1(1.0, 2.0, 3.0);
  const point p2(4.0, 5.0, 6.0);
  const point p3(-7.0, 8.0, -9.0);

  tree_type tree;
  assert(tree.size() == 0);

  tree.insert(p1);
  tree.insert(p2);
  tree.insert(p3);
  assert(tree.size() == 3);

  // exact lookup of an inserted value
  tree_type::const_iterator it = tree.find(p1);
  assert(it != tree.end());
  assert((*it)[0] == 1.0 && (*it)[1] == 2.0 && (*it)[2] == 3.0);

  // nearest neighbour: the probe sits next to p1 and far away from p2/p3.
  // find_nearest() returns std::pair<const_iterator, distance_type>.
  std::pair<tree_type::const_iterator, tree_type::distance_type> near =
      tree.find_nearest(point(1.1, 2.1, 3.1));
  assert(near.first != tree.end());
  assert((*near.first)[0] == 1.0 && (*near.first)[1] == 2.0 && (*near.first)[2] == 3.0);

  // full iteration covers every inserted element exactly once
  std::size_t visited = 0;
  for (tree_type::const_iterator i = tree.begin(); i != tree.end(); ++i)
    ++visited;
  assert(visited == tree.size());

  // zero-range query: only the point at the query location qualifies
  std::vector<point> hits;
  tree.find_within_range(p2, 0.0, std::back_inserter(hits));
  assert(hits.size() == 1);
  assert(hits[0][0] == 4.0 && hits[0][1] == 5.0 && hits[0][2] == 6.0);

  // erase() drops exactly the matching element
  tree.erase(p3);
  assert(tree.size() == 2);
  assert(tree.find(p3) == tree.end());

  // optimise() keeps the container consistent for later lookups
  tree.optimise();
  assert(tree.size() == 2);
  assert(tree.find(p2) != tree.end());

  // copy construction preserves the contents
  tree_type duplicate(tree);
  assert(duplicate.size() == 2);
  assert(duplicate.find(p1) != duplicate.end());

  // KDTREE_VERSION layout: major = /100000, minor = /100 %1000, patch = %100
  std::cout << "libkdtree++ " << (KDTREE_VERSION / 100000)
            << "." << ((KDTREE_VERSION / 100) % 1000)
            << "." << (KDTREE_VERSION % 100)
            << " consumer checks passed (" << tree.size() << " nodes)" << std::endl;
  return 0;
}
