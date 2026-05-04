/* 03_structs.c — Multi-function with structs, pointers, arrays
 * Tests: RE functions list, xrefs, strings, CFG with multiple blocks
 */
#include <stdio.h>
#include <string.h>

typedef struct {
    char name[32];
    int id;
    float score;
} Student;

void print_student(const Student *s) {
    printf("[%d] %s — %.1f\n", s->id, s->name, s->score);
}

Student make_student(const char *name, int id, float score) {
    Student s;
    strncpy(s.name, name, sizeof(s.name) - 1);
    s.name[sizeof(s.name) - 1] = '\0';
    s.id = id;
    s.score = score;
    return s;
}

int find_best(Student arr[], int count) {
    int best = 0;
    for (int i = 1; i < count; i++) {
        if (arr[i].score > arr[best].score)
            best = i;
    }
    return best;
}

int main(void) {
    Student class[] = {
        make_student("Alice", 1, 85.5f),
        make_student("Bob", 2, 92.3f),
        make_student("Charlie", 3, 78.1f),
        make_student("Diana", 4, 95.7f),
    };
    int n = sizeof(class) / sizeof(class[0]);

    printf("=== Class ===\n");
    for (int i = 0; i < n; i++)
        print_student(&class[i]);

    int best = find_best(class, n);
    printf("\nBest: ");
    print_student(&class[best]);

    return 0;
}
