#include <lv2/core/lv2.h>
#include <lv2/core/lv2_util.h>
#include <lv2/urid/urid.h>
#include <string.h>

#ifndef LV2_CORE__Plugin
#error "LV2 core plugin URI macro is missing"
#endif

static const LV2_Feature urid_map_feature = {
    LV2_URID__map,
    0,
};

static const LV2_Feature *const features[] = {
    &urid_map_feature,
    0,
};

const LV2_Feature *const *lv2_test_features(void)
{
    return features;
}

int main(void)
{
    const LV2_Feature *const *consumer_features = lv2_test_features();
    if (!consumer_features || !consumer_features[0]) {
        return 1;
    }
    if (strcmp(consumer_features[0]->URI, LV2_URID__map) != 0) {
        return 2;
    }
    return 0;
}
