use v6.d;
use Test;
use Log;
use Log::Implementation;
use Log::Level;

class CapturingLogger does Log::Implementation {
    has @.messages;
    multi method info(Str:D $message) { @!messages.push($message) }
    multi method add-output(IO::Handle:D $, Int() $, Callable $?) { self }
}

plan 6;

# Verify the enumerated severity scale is contiguous and ordered, not just two
# constants echoed back.
my @levels = Log::Level::Emergency, Log::Level::Alert, Log::Level::Critical,
    Log::Level::Error, Log::Level::Warning, Log::Level::Notice,
    Log::Level::Info, Log::Level::Debug;
is @levels».value.join(','), '0,1,2,3,4,5,6,7',
    'severity values run contiguously from Emergency to Debug';

ok Log::Implementation.HOW.^name.contains('Role'), 'implementation API is a role';

# The documented usage relies on `with $Log::instance` guarding unset
# applications, so the shared instance must start undefined.
nok $Log::instance.defined,
    'shared instance starts undefined so the documented `with` guard applies';

my $logger = CapturingLogger.new;
$logger.info('module loaded');
is $logger.messages, ['module loaded'],
    'consumer can implement the role and receive a plain message';

# Every documented log level must resolve on a consumer that only overrides one
# of them; a missing candidate would raise "Method not found".
my @required = <emergency alert critical error warning notice info debug>;
my $probe = CapturingLogger.new;
my $all-callable = True;
for @required -> $method {
    try { $probe."$method"('x') }
    $all-callable = False if $!;
}
ok $all-callable, 'role supplies callable implementations for all eight log levels';

$Log::instance = $logger;
my $seen;
with $Log::instance { $seen = .messages.elems }
is $seen, 1, 'documented `with $Log::instance` idiom reaches the shared instance';

done-testing;
