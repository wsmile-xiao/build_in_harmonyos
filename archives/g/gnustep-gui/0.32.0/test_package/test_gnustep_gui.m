#import <Foundation/Foundation.h>
#import <AppKit/AppKit.h>

extern int gnustep_test_support_value(void);

int main(void)
{
  NSAutoreleasePool *pool = [NSAutoreleasePool new];

  if (gnustep_test_support_value() != 42) {
    [pool drain];
    return 9;
  }

  NSImage *image = [[NSImage alloc] initWithSize: NSMakeSize(16.0, 16.0)];
  if (image == nil || [image size].width != 16.0 || [image size].height != 16.0) {
    [pool drain];
    return 1;
  }

  NSBezierPath *path = [NSBezierPath bezierPathWithRect: NSMakeRect(1.0, 2.0, 3.0, 4.0)];
  NSRect bounds = [path bounds];
  if (bounds.size.width <= 0.0 || bounds.size.height <= 0.0) {
    [image release];
    [pool drain];
    return 2;
  }

  NSColor *color = [NSColor colorWithCalibratedRed: 0.25
                                             green: 0.50
                                              blue: 0.75
                                             alpha: 1.00];
  if (color == nil || [color alphaComponent] <= 0.0) {
    [image release];
    [pool drain];
    return 3;
  }

  NSString *summary = NSStringFromSize([image size]);
  int result = ([summary rangeOfString: @"16"].location == NSNotFound) ? 4 : 0;

  [image release];
  [pool drain];
  return result;
}
