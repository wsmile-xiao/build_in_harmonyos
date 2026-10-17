#!/usr/bin/env python3
"""Consumer smoke test for the rdflib Python import used by libzeitgeist."""

from rdflib import Graph, Namespace


def main() -> int:
    graph = Graph()
    EX = Namespace("https://example.invalid/")
    graph.add((EX.subject, EX.predicate, EX.object))
    assert len(graph) == 1, f"expected 1 triple, got {len(graph)}"
    print("rdflib consumer test: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
