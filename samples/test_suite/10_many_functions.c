/* 10_many_functions.c — 20+ functions for RE sidebar stress test
 * Tests: RE function list scrolling, xref graph, sidebar filter
 * Compile: gcc -g -o 10_many_functions 10_many_functions.c
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int add(int a, int b) { return a + b; }
int sub(int a, int b) { return a - b; }
int mul(int a, int b) { return a * b; }
int div_safe(int a, int b) { return b ? a / b : 0; }
int mod(int a, int b) { return b ? a % b : 0; }
int square(int x) { return x * x; }
int cube(int x) { return x * x * x; }
int abs_val(int x) { return x < 0 ? -x : x; }
int max(int a, int b) { return a > b ? a : b; }
int min(int a, int b) { return a < b ? a : b; }
int clamp(int x, int lo, int hi) { return max(lo, min(x, hi)); }
int factorial(int n) { return n <= 1 ? 1 : n * factorial(n - 1); }
int fib(int n) { return n <= 1 ? n : fib(n - 1) + fib(n - 2); }
int gcd(int a, int b) { return b == 0 ? a : gcd(b, a % b); }
int lcm(int a, int b) { return a / gcd(a, b) * b; }
int is_prime(int n) {
    if (n < 2) return 0;
    for (int i = 2; i * i <= n; i++)
        if (n % i == 0) return 0;
    return 1;
}
int count_primes(int max_n) {
    int count = 0;
    for (int i = 2; i <= max_n; i++)
        if (is_prime(i)) count++;
    return count;
}
void reverse_string(char *s) {
    int len = strlen(s);
    for (int i = 0; i < len / 2; i++) {
        char tmp = s[i];
        s[i] = s[len - 1 - i];
        s[len - 1 - i] = tmp;
    }
}
int sum_array(int *arr, int n) {
    int s = 0;
    for (int i = 0; i < n; i++) s += arr[i];
    return s;
}
void bubble_sort(int *arr, int n) {
    for (int i = 0; i < n - 1; i++)
        for (int j = 0; j < n - 1 - i; j++)
            if (arr[j] > arr[j + 1]) {
                int tmp = arr[j];
                arr[j] = arr[j + 1];
                arr[j + 1] = tmp;
            }
}

int main(void) {
    printf("add(3,4) = %d\n", add(3, 4));
    printf("factorial(6) = %d\n", factorial(6));
    printf("fib(10) = %d\n", fib(10));
    printf("gcd(48,18) = %d\n", gcd(48, 18));
    printf("primes < 100 = %d\n", count_primes(100));

    char s[] = "LIVNA";
    reverse_string(s);
    printf("reversed = %s\n", s);

    int arr[] = {5, 3, 8, 1, 9, 2};
    bubble_sort(arr, 6);
    printf("sorted = ");
    for (int i = 0; i < 6; i++) printf("%d ", arr[i]);
    printf("\nsum = %d\n", sum_array(arr, 6));

    printf("clamp(15, 0, 10) = %d\n", clamp(15, 0, 10));
    printf("lcm(12,8) = %d\n", lcm(12, 8));
    return 0;
}
