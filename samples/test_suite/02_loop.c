/* 02_loop.c — Simple loop with conditionals
 * Tests: ASM mode stepping, breakpoints, register watch, CFG branches in RE
 */
#include <stdio.h>

int sum_to(int n) {
    int total = 0;
    for (int i = 1; i <= n; i++) {
        if (i % 2 == 0)
            total += i * 2;
        else
            total += i;
    }
    return total;
}

int main(void) {
    int result = sum_to(10);
    printf("Sum = %d\n", result);
    return (result == 65) ? 0 : 1;
}
