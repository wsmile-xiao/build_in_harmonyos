// Consumer test for svgpp/1.3.1.
//
// Exercises the two public Boost.Spirit grammars of the package -
// svgpp::path_data_grammar and svgpp::transform_grammar - through a parse
// context and verifies the geometry actually produced by the parser
// (coordinates, relative/absolute flags, arc flags), not just that headers
// compile.  The API usage mirrors upstream src/test/path_grammar_test.cpp and
// src/test/transform_grammar_test.cpp (same grammar types, same context
// member functions), so a green run proves the installed headers are
// complete and usable from a Conan consumer.
#include <svgpp/parser/grammar/path_data.hpp>
#include <svgpp/parser/grammar/transform.hpp>

#include <boost/array.hpp>
#include <boost/phoenix.hpp>
#include <boost/spirit/include/qi.hpp>

#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <initializer_list>
#include <iostream>
#include <string>
#include <vector>

namespace {

unsigned g_checks = 0;
unsigned g_failures = 0;

void check(bool value, const char *what, int line)
{
    ++g_checks;
    if (!value) {
        ++g_failures;
        std::cerr << "FAILED at line " << line << ": " << what << '\n';
    }
}

#define CHECK(expr) check(static_cast<bool>(expr), #expr, __LINE__)
#define CHECK_NEAR(a, b) \
    check(std::fabs((a) - (b)) < 1e-9, #a " ~= " #b, __LINE__)

struct event
{
    std::string name;
    std::vector<double> values;
    bool absolute;
};

bool same_event(const event &e, const char *name,
                std::initializer_list<double> values, bool absolute = true)
{
    return e.name == name && e.absolute == absolute
        && e.values.size() == values.size()
        && std::equal(e.values.begin(), e.values.end(), values.begin(),
                      [](double x, double y) { return std::fabs(x - y) < 1e-9; });
}

// Upstream test_path_context.hpp compatible path sink (src/test/test_path_context.hpp).
struct path_recorder
{
    std::vector<event> events;

    template<class AbsoluteTag>
    void path_move_to(double x, double y, AbsoluteTag tag)
    { push("move_to", {x, y}, tag.is_absolute); }

    template<class AbsoluteTag>
    void path_line_to(double x, double y, AbsoluteTag tag)
    { push("line_to", {x, y}, tag.is_absolute); }

    template<class AbsoluteTag>
    void path_line_to_ortho(double coord, bool horizontal, AbsoluteTag tag)
    { push(horizontal ? "ortho_h" : "ortho_v", {coord}, tag.is_absolute); }

    template<class AbsoluteTag>
    void path_cubic_bezier_to(double x1, double y1, double x2, double y2,
                              double x, double y, AbsoluteTag tag)
    { push("cubic", {x1, y1, x2, y2, x, y}, tag.is_absolute); }

    template<class AbsoluteTag>
    void path_cubic_bezier_to(double x2, double y2, double x, double y,
                              AbsoluteTag tag)
    { push("cubic_smooth", {x2, y2, x, y}, tag.is_absolute); }

    template<class AbsoluteTag>
    void path_quadratic_bezier_to(double x1, double y1, double x, double y,
                                  AbsoluteTag tag)
    { push("quadratic", {x1, y1, x, y}, tag.is_absolute); }

    template<class AbsoluteTag>
    void path_quadratic_bezier_to(double x, double y, AbsoluteTag tag)
    { push("quadratic_smooth", {x, y}, tag.is_absolute); }

    template<class AbsoluteTag>
    void path_elliptical_arc_to(double rx, double ry, double x_axis_rotation,
                                bool large_arc_flag, bool sweep_flag,
                                double x, double y, AbsoluteTag tag)
    {
        push("arc", {rx, ry, x_axis_rotation, large_arc_flag ? 1.0 : 0.0,
                     sweep_flag ? 1.0 : 0.0, x, y}, tag.is_absolute);
    }

    void path_close_subpath()
    { push("close", {}); }

    void path_exit() {}

private:
    void push(const char *name, std::initializer_list<double> values,
              bool absolute = true)
    {
        event e;
        e.name = name;
        e.values.assign(values.begin(), values.end());
        e.absolute = absolute;
        events.push_back(e);
    }
};

// Upstream test_transform_context (src/test/transform_grammar_test.cpp).
struct transform_recorder
{
    std::vector<event> events;

    void transform_matrix(boost::array<double, 6> const &m)
    { push("matrix", {m[0], m[1], m[2], m[3], m[4], m[5]}); }
    void transform_translate(double tx, double ty) { push("translate", {tx, ty}); }
    void transform_translate(double tx) { push("translate_1arg", {tx}); }
    void transform_scale(double sx, double sy) { push("scale", {sx, sy}); }
    void transform_scale(double sx) { push("scale_1arg", {sx}); }
    void transform_rotate(double a, double cx, double cy) { push("rotate", {a, cx, cy}); }
    void transform_rotate(double a) { push("rotate_1arg", {a}); }
    void transform_skew_x(double a) { push("skew_x", {a}); }
    void transform_skew_y(double a) { push("skew_y", {a}); }

private:
    void push(const char *name, std::initializer_list<double> values)
    {
        event e;
        e.name = name;
        e.values.assign(values.begin(), values.end());
        e.absolute = true;
        events.push_back(e);
    }
};

template<class Grammar, class Context>
bool parse(const std::string &text, Grammar &grammar, Context &context,
           std::string::const_iterator &parsed_upto)
{
    parsed_upto = text.begin();
    return boost::spirit::qi::phrase_parse(
        parsed_upto, text.end(), grammar(boost::phoenix::ref(context)),
        boost::spirit::ascii::space);
}

} // namespace

int main()
{
    // 1. Absolute and relative line commands, orthographic command, close.
    {
        const std::string data("M300,200 L100,200 h-150 z");
        path_recorder context;
        svgpp::path_data_grammar<std::string::const_iterator, path_recorder>
            grammar;
        std::string::const_iterator upto;
        const bool ok = parse(data, grammar, context, upto);
        CHECK(ok);
        CHECK(upto == data.end());
        CHECK(context.events.size() == 4);
        if (context.events.size() == 4) {
            CHECK(same_event(context.events[0], "move_to", {300, 200}, true));
            CHECK(same_event(context.events[1], "line_to", {100, 200}, true));
            CHECK(same_event(context.events[2], "ortho_h", {-150}, false));
            CHECK(same_event(context.events[3], "close", {}, true));
        }
    }

    // 2. Cubic, quadratic and elliptical arc geometry (SVG 1.1 "A" flags).
    {
        const std::string data("M300,200 C100,100 250,100 250,200 "
                               "Q50,50 100,100 "
                               "a150,151 0 1,0 150,-150");
        path_recorder context;
        svgpp::path_data_grammar<std::string::const_iterator, path_recorder>
            grammar;
        std::string::const_iterator upto;
        const bool ok = parse(data, grammar, context, upto);
        CHECK(ok);
        CHECK(upto == data.end());
        CHECK(context.events.size() == 4);
        if (context.events.size() == 4) {
            CHECK(same_event(context.events[0], "move_to", {300, 200}, true));
            CHECK(same_event(context.events[1], "cubic",
                             {100, 100, 250, 100, 250, 200}, true));
            CHECK(same_event(context.events[2], "quadratic",
                             {50, 50, 100, 100}, true));
            // rx, ry, rotation, large-arc, sweep, x, y - relative.
            CHECK(same_event(context.events[3], "arc",
                             {150, 151, 0, 1, 0, 150, -150}, false));
        }
    }

    // 3. Transform list shorthand forms.
    {
        const std::string data(
            "translate(-10,-20)scale(2)rotate(45 1 2)matrix(1 2 3 4 5 6)skewX(3.2)");
        transform_recorder context;
        svgpp::transform_grammar<std::string::const_iterator, transform_recorder>
            grammar;
        std::string::const_iterator upto;
        const bool ok = parse(data, grammar, context, upto);
        CHECK(ok);
        CHECK(upto == data.end());
        CHECK(context.events.size() == 5);
        if (context.events.size() == 5) {
            CHECK(same_event(context.events[0], "translate", {-10, -20}));
            CHECK(same_event(context.events[1], "scale_1arg", {2}));
            CHECK(same_event(context.events[2], "rotate", {45, 1, 2}));
            CHECK(same_event(context.events[3], "matrix", {1, 2, 3, 4, 5, 6}));
            CHECK(same_event(context.events[4], "skew_x", {3.2}));
        }
    }

    // 4. A truncated path must not be reported as a complete parse.
    {
        const std::string data("M300,200 L");
        path_recorder context;
        svgpp::path_data_grammar<std::string::const_iterator, path_recorder>
            grammar;
        std::string::const_iterator upto;
        const bool ok = parse(data, grammar, context, upto);
        CHECK(!ok || upto != data.end());
    }

    // 5. A leading separator is invalid in a transform list
    //    (upstream transform_grammar_test.cpp, case t4).
    {
        const std::string data(",12.3 14.7");
        transform_recorder context;
        svgpp::transform_grammar<std::string::const_iterator, transform_recorder>
            grammar;
        std::string::const_iterator upto;
        const bool ok = parse(data, grammar, context, upto);
        CHECK(!ok || upto != data.end());
    }

    std::cout << "svgpp consumer test: checks=" << g_checks
              << " failures=" << g_failures << std::endl;
    return g_failures == 0 ? EXIT_SUCCESS : EXIT_FAILURE;
}
