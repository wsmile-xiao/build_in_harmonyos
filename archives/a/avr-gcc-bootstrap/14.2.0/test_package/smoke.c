typedef unsigned short uint16_t;

volatile uint16_t dividend = 1000;
volatile uint16_t divisor = 7;

static uint16_t quotient(void)
{
    return dividend / divisor;
}

int main(void)
{
    return quotient() == 142 ? 0 : 1;
}
