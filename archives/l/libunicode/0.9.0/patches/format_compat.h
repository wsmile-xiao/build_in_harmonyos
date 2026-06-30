#pragma once

#include <sstream>
#include <iomanip>
#include <string>
#include <string_view>
#include <cstdint>
#include <tuple>
#include <type_traits>
#include <array>

namespace compat {

// Helper to output one argument with possible format spec
template<typename T>
void output_arg(std::ostringstream& oss, std::string_view spec, T&& arg) {
    // Special handling for integral types: always output as integer, not as character
    if constexpr (std::is_integral_v<std::decay_t<T>>) {
        using LargeIntType = std::conditional_t<std::is_signed_v<std::decay_t<T>>, int64_t, uint64_t>;

        // Parse spec: e.g., "04X" or "X" or "04x" or "d"
        int width = 0;
        bool hex_upper = false;
        bool hex_lower = false;
        bool octal = false;

        if (!spec.empty()) {
            size_t pos = 0;
            while (pos < spec.size() && std::isdigit(static_cast<unsigned char>(spec[pos]))) {
                pos++;
            }
            if (pos > 0) {
                width = std::stoi(std::string(spec.substr(0, pos)));
            }

            for (size_t j = pos; j < spec.size(); j++) {
                if (spec[j] == 'X') hex_upper = true;
                else if (spec[j] == 'x') hex_lower = true;
                else if (spec[j] == 'o') octal = true;
                else if (spec[j] == 'd') { hex_upper = hex_lower = octal = false; }
            }
        }

        if (hex_upper) {
            oss << std::hex << std::uppercase;
            if (width > 0) oss << std::setw(width) << std::setfill('0');
            oss << static_cast<LargeIntType>(arg);
            oss << std::dec << std::nouppercase;
        } else if (hex_lower) {
            oss << std::hex << std::nouppercase;
            if (width > 0) oss << std::setw(width) << std::setfill('0');
            oss << static_cast<LargeIntType>(arg);
            oss << std::dec;
        } else if (octal) {
            oss << std::oct;
            if (width > 0) oss << std::setw(width) << std::setfill('0');
            oss << static_cast<LargeIntType>(arg);
            oss << std::dec;
        } else {
            // Default: output as integer (not as character)
            oss << static_cast<LargeIntType>(arg);
        }
    } else {
        // Non-integral types: just output directly
        oss << arg;
    }
}

// Generic visitor for tuple at runtime index using function pointer array
template<typename Tuple, typename F, size_t... Is>
void visit_tuple_at_index(Tuple&& tuple, size_t index, F&& func, std::index_sequence<Is...>) {
    using FuncPtr = void(*)(Tuple&&, F&&);
    static constexpr std::array<FuncPtr, sizeof...(Is)> visitors = {
        [](Tuple&& t, F&& f) { f(std::get<Is>(std::forward<Tuple>(t))); }...
    };

    if (index < sizeof...(Is)) {
        visitors[index](std::forward<Tuple>(tuple), std::forward<F>(func));
    }
}

// Helper lambda creator for output
template<typename Tuple>
auto make_output_visitor(std::ostringstream& oss, std::string_view spec) {
    return [&oss, spec](auto&& elem) {
        output_arg(oss, spec, elem);
    };
}

// Main format implementation using tuple for indexed access
template<typename... Args>
std::string format(std::string_view fmt, Args&&... args) {
    std::ostringstream oss;
    auto args_tuple = std::make_tuple(std::forward<Args>(args)...);

    size_t i = 0;
    size_t sequential_index = 0;

    while (i < fmt.size()) {
        if (fmt[i] == '{') {
            if (i + 1 < fmt.size() && fmt[i + 1] == '{') {
                // Escaped {{ -> output single {
                oss << '{';
                i += 2;
            } else {
                // Find the closing }
                size_t start = i + 1;
                size_t end = fmt.find('}', start);
                if (end == std::string_view::npos) {
                    oss << fmt[i];
                    i++;
                } else {
                    // Extract format spec (e.g., "0:" or ":" or "04X")
                    std::string_view inner = fmt.substr(start, end - start);

                    // Parse index (if present) and spec
                    size_t arg_index = sequential_index;
                    std::string_view spec;

                    size_t colon_pos = inner.find(':');
                    if (colon_pos != std::string_view::npos) {
                        // Has colon: could be "0:" or ":" or "0:04X"
                        std::string_view before_colon = inner.substr(0, colon_pos);
                        spec = inner.substr(colon_pos + 1);

                        // Parse index if present
                        if (before_colon.size() > 0) {
                            // Positional argument: "0" means first arg
                            arg_index = static_cast<size_t>(std::stoi(std::string(before_colon)));
                        } else {
                            // Empty before colon -> use sequential
                            arg_index = sequential_index;
                            sequential_index++;
                        }
                    } else if (inner.empty()) {
                        // "{}" -> sequential
                        arg_index = sequential_index;
                        sequential_index++;
                    } else {
                        // "{04X}" without colon - treat entire as spec
                        spec = inner;
                        arg_index = sequential_index;
                        sequential_index++;
                    }

                    // Output the argument at arg_index using visitor
                    auto visitor = make_output_visitor<decltype(args_tuple)>(oss, spec);
                    visit_tuple_at_index(args_tuple, arg_index, visitor, std::index_sequence_for<Args...>{});

                    i = end + 1;
                }
            }
        } else if (fmt[i] == '}') {
            if (i + 1 < fmt.size() && fmt[i + 1] == '}') {
                // Escaped }}
                oss << '}';
                i += 2;
            } else {
                oss << fmt[i];
                i++;
            }
        } else {
            oss << fmt[i];
            i++;
        }
    }

    return oss.str();
}

} // namespace compat

// Alias std::format to compat::format
#define std_format compat::format