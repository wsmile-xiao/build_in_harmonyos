// test.v — minimal design for the yosys test_package synthesis smoke test.
module top (
    input  a,
    input  b,
    output y
);
    assign y = (a & b) | (~a & ~b);
endmodule
