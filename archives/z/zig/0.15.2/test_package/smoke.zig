pub fn main() !void {
    const answer = comptime 40 + 2;
    if (answer != 42) return error.BadMath;
}
