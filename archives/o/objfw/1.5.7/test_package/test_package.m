#import <ObjFW/OFArray.h>
#import <ObjFW/OFData.h>
#import <ObjFW/OFNumber.h>
#import <ObjFW/OFString.h>

int main()
{
    OFString *str = [OFString stringWithUTF8String: "Hello, HarmonyOS!"];
    OFNumber *num = [OFNumber numberWithLongLong: 42];

    if (str == nil || num == nil)
        return 1;

    if ([num longLongValue] != 42)
        return 2;

    if (![[str description] containsString: @"HarmonyOS"])
        return 3;

    OFArray *arr = [OFArray arrayWithObjects: str, num, nil];
    if ([arr count] != 2)
        return 4;

    OFData *data = [str dataWithEncoding: OFStringEncodingUTF8];
    if (data == nil || [data count] == 0)
        return 5;

    return 0;
}
