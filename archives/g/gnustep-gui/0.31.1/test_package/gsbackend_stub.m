/*
 * gsbackend_stub.m — test 消费者侧的最小 GSBackend 后端类桩。

 * GNUstep 架构中 GSBackend 抽象类由应用链接的后端库(如 gnustep-back)
 * 提供实现; 本 test 程序作为最小消费者, 按上游惯例(NGApplication.m 注释
 * "GSBackend will be in a separate library linked in with the app")
 * 自行提供类符号, 使 libgnustep-gui.so 可加载并运行, 同时不阻碍远端
 * gnustep-back 语言的完整后端替换。
 */
#import <Foundation/NSObject.h>

@interface GSBackend : NSObject
@end

@implementation GSBackend
@end
