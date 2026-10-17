#import <Foundation/Foundation.h>

extern int gnustep_test_support_value(void);

int main(void)
{
  NSAutoreleasePool *pool = [NSAutoreleasePool new];

  if (gnustep_test_support_value() != 42) {
    [pool drain];
    return 9;
  }

  NSString *library = @"gnustep-base";
  NSArray *parts = [NSArray arrayWithObjects: @"HarmonyOS", library, nil];
  NSString *joined = [parts componentsJoinedByString: @":"];
  NSData *data = [joined dataUsingEncoding: NSUTF8StringEncoding];

  if ([data length] == 0) {
    [pool drain];
    return 1;
  }

  NSDictionary *dict = [NSDictionary dictionaryWithObject: joined
                                                   forKey: @"probe"];
  if (![[dict objectForKey: @"probe"] isEqualToString: @"HarmonyOS:gnustep-base"]) {
    [pool drain];
    return 2;
  }

  if ([joined rangeOfString: library].location == NSNotFound) {
    [pool drain];
    return 3;
  }

  [pool drain];
  return 0;
}
