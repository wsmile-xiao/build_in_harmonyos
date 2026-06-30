# OMPL (Open Motion Planning Library)

OMPL is an open source sampling-based motion planning library.

## Description

The Open Motion Planning Library (OMPL) is a powerful C++ library for motion planning, widely used in robotics and automation. It provides over 40 sampling-based planning algorithms including RRT-Connect, PRM, KPIECE, RRT*, and many more across more than 20 state spaces.

## Key Features

- Over 40 sampling-based planning algorithms
- SIMD-accelerated planning with VAMP for millisecond planning
- Easily extensible to custom planners (Python and C++) and state spaces (C++)
- Support for multiple state spaces (SE(3), Euclidean space, and others)

## Dependencies

### Required
- Boost (version 1.68 or higher)
- CMake (version 3.12 or higher)
- Eigen (version 3.3 or higher)

### Optional
- VAMP (Vector-Accelerated Motion Planning for high-performance collision checking)
- Doxygen (for documentation)
- Flann (for nearest neighbor queries)
- Spot (for constructing finite automata from LTL formulae)
- yaml-cpp (for reading and writing YAML world descriptions)

## License

BSD-3-Clause

## Website

https://ompl.kavrakilab.org/