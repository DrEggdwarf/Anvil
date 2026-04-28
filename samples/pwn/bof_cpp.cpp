/* bof_cpp.cpp — C++ vtable overwrite */
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <unistd.h>

class Animal {
public:
    char name[32];
    virtual void speak() { printf("%s says: meow\n", name); }
    virtual ~Animal() = default;
};

class WinAnimal : public Animal {
public:
    void speak() override {
        puts("[*] Flag: ANVIL{cpp_vt4ble_pwn}");
        exit(0);
    }
};

int main() {
    setvbuf(stdout, nullptr, _IONBF, 0);

    auto *a = new Animal();
    strcpy(a->name, "cat");
    a->speak();

    printf("Rename (overflow the vtable!): ");
    read(0, a, 256);  /* overwrite vtable pointer */
    a->speak();        /* call through corrupted vtable */

    delete a;
    return 0;
}
