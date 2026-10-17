# Typobuster 1.0.0 notes

Upstream is a Python 3 GTK3 application despite the task-board C++ label. The
recipe packages its setuptools installation and desktop integration files.
The source URL uses GitHub's codeload endpoint without a suffix, so the recipe
passes `filename="v1.0.0.tar.gz"` to Conan's `get()` helper explicitly.

The target runtime for the GUI must provide GTK3, GtkSourceView 4, PyGObject
and PyCairo. Gspell is handled by upstream as an optional feature. Following
the repository's Terminator precedent, test_package validates the installable
pure-Python tools module and bundled language data without importing GTK. The
GTK window path remains a documented runtime prerequisite and is not claimed
as validated on the bare device image.
---

**编译结束**: 2026-08-20 15:55
**最终状态**: built
