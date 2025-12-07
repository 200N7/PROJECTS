#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <limits.h>
#include <float.h>

// Forward declarations of all teaching modules
void dataTypeExplorer();
void operatorDemo();
void array1DVisualizer();
void array2DVisualizer();
void stringPointerDemo();
void structUnionVisualizer();
void pointerPlayground();
void dynamicMemoryDemo();
void errorTeachingAssistant();

int main() {
    int choice;

    while(1) {  // Infinite loop - creates persistent interactive console
        printf("\n======= C Concept Visual Learning Console =======\n");
        printf("1. Data Types & Memory Explorer\n");
        printf("2. Operator Demonstrator\n");
        printf("3. 1D Array Visualizer\n");
        printf("4. 2D Array Visualizer\n");
        printf("5. String & Pointer Demo\n");
        printf("6. Structure & Union Visualizer\n");
        printf("7. Pointer Playground\n");
        printf("8. Dynamic Memory Demo\n");
        printf("9. Error Teaching Assistant\n");
        printf("10. Exit\n");
        printf("Enter your choice: ");
        scanf("%d", &choice);
        getchar(); // Consume the leftover newline character from input buffer

        switch(choice) {    
            case 1: dataTypeExplorer(); break;    
            case 2: operatorDemo(); break;    
            case 3: array1DVisualizer(); break;    
            case 4: array2DVisualizer(); break;    
            case 5: stringPointerDemo(); break;    
            case 6: structUnionVisualizer(); break;    
            case 7: pointerPlayground(); break;    
            case 8: dynamicMemoryDemo(); break;    
            case 9: errorTeachingAssistant(); break;    
            case 10: printf("Exiting...\n"); exit(0);    
            default: printf("Invalid choice! Try again.\n");    
        }
    }

    return 0; // Never reached due to infinite loop and exit()
}

// ===== Module 1: Data Types & Memory Explorer =====
void dataTypeExplorer() {
    printf("\n--- Data Type Explorer ---\n");
    printf("Select type: 1-int 2-float 3-double 4-char\n");
    int type;
    scanf("%d", &type);
    getchar(); // Clear newline after reading integer

    switch(type) {
        case 1: {
            int x;
            printf("Enter an int value: ");
            scanf("%d", &x);
            int *ptr = &x; // Pointer to demonstrate address
            printf("Value = %d, Address = %p, Size = %zu bytes\n", x, (void*)ptr, sizeof(x));
            break;
        }
        case 2: {
            float x;
            printf("Enter a float value: ");
            scanf("%f", &x);
            float *ptr = &x;
            printf("Value = %.2f, Address = %p, Size = %zu bytes\n", x, (void*)ptr, sizeof(x));
            break;
        }
        case 3: {
            double x;
            printf("Enter a double value: ");
            scanf("%lf", &x);
            double *ptr = &x;
            printf("Value = %.2lf, Address = %p, Size = %zu bytes\n", x, (void*)ptr, sizeof(x));
            break;
        }
        case 4: {
            char x;
            printf("Enter a char value: ");
            scanf(" %c", &x); // Space before %c skips whitespace
            char *ptr = &x;
            printf("Value = %c, Address = %p, Size = %zu bytes\n", x, (void*)ptr, sizeof(x));
            break;
        }
        default: printf("Invalid choice!\n");
    }
}

// ===== Module 2: Operator Demonstrator =====
void operatorDemo() {
    printf("\n--- Operator Demonstrator ---\n");
    printf("Select datatype: 1-int 2-float 3-double 4-char\n");
    int type;
    scanf("%d", &type);
    getchar(); // Clear input buffer

    switch(type) {
        case 1: { // INT
            int a, b;
            printf("Enter two integers (a b): ");
            scanf("%d %d", &a, &b);

            printf("\nArithmetic: a+b=%d, a-b=%d, a*b=%d, a/b=%d, a%%b=%d\n",
                   a+b, a-b, a*b, b!=0?a/b:0, b!=0?a%b:0);
            printf("Relational: a==b=%d, a!=b=%d, a>b=%d, a<b=%d\n",
                   a==b, a!=b, a>b, a<b);
            printf("Logical: a&&b=%d, a||b=%d, !a=%d, !b=%d\n",
                   a&&b, a||b, !a, !b);
            printf("Bitwise: a&b=%d, a|b=%d, a^b=%d, ~a=%d, a<<1=%d, a>>1=%d\n",
                   a&b, a|b, a^b, ~a, a<<1, a>>1);
            break;
        }
        case 2: { // FLOAT
            float a, b;
            printf("Enter two floats (a b): ");
            scanf("%f %f", &a, &b);
            printf("\nArithmetic: a+b=%.2f, a-b=%.2f, a*b=%.2f, a/b=%.2f\n",
                   a+b, a-b, a*b, b!=0?a/b:0);
            printf("Relational: a==b=%d, a!=b=%d, a>b=%d, a<b=%d\n",
                   a==b, a!=b, a>b, a<b);
            printf("Logical: a&&b=%d, a||b=%d, !a=%d, !b=%d\n",
                   a&&b, a||b, !a, !b);
            break;
        }
        case 3: { // DOUBLE
            double a, b;
            printf("Enter two doubles (a b): ");
            scanf("%lf %lf", &a, &b);
            printf("\nArithmetic: a+b=%.2lf, a-b=%.2lf, a*b=%.2lf, a/b=%.2lf\n",
                   a+b, a-b, a*b, b!=0?a/b:0);
            printf("Relational: a==b=%d, a!=b=%d, a>b=%d, a<b=%d\n",
                   a==b, a!=b, a>b, a<b);
            printf("Logical: a&&b=%d, a||b=%d, !a=%d, !b=%d\n",
                   a&&b, a||b, !a, !b);
            break;
        }
        case 4: { // CHAR
            char a, b;
            printf("Enter two characters (a b): ");
            scanf(" %c %c", &a, &b);
            printf("\nArithmetic (ASCII): a+b=%d, a-b=%d, a*b=%d, a/b=%d, a%%b=%d\n",
                   a+b, a-b, a*b, b!=0?a/b:0, b!=0?a%b:0);
            printf("Relational: a==b=%d, a!=b=%d, a>b=%d, a<b=%d\n",
                   a==b, a!=b, a>b, a<b);
            printf("Logical: a&&b=%d, a||b=%d, !a=%d, !b=%d\n",
                   a&&b, a||b, !a, !b);
            printf("Bitwise: a&b=%d, a|b=%d, a^b=%d, ~a=%d, a<<1=%d, a>>1=%d\n",
                   a&b, a|b, a^b, ~a, a<<1, a>>1);
            break;
        }
        default:
            printf("Invalid datatype choice!\n");
    }
}

// ===== Module 3: 1D Array Visualizer =====
void array1DVisualizer() {
    int n;
    printf("\n--- 1D Array Visualizer ---\n");
    printf("Enter size of array: ");
    scanf("%d", &n);
    int arr[n]; // Variable Length Array (VLA) - C99 feature
    printf("Enter %d integers:\n", n);
    for(int i = 0; i < n; i++) 
        scanf("%d", &arr[i]);

    printf("\nIndex:   ");
    for(int i = 0; i < n; i++) printf("%d\t", i);
    printf("\nValue:   ");
    for(int i = 0; i < n; i++) printf("%d\t", arr[i]);
    printf("\nAddress: ");
    for(int i = 0; i < n; i++) printf("%p\t", (void*)&arr[i]);
    printf("\n");
}

// ===== Module 4: 2D Array Visualizer =====
void array2DVisualizer() {
    int r, c;
    printf("\n--- 2D Array Visualizer ---\n");
    printf("Enter rows and columns: ");
    scanf("%d %d", &r, &c);
    int arr[r][c]; // 2D VLA - stored in row-major order
    printf("Enter elements row-wise:\n");
    for(int i = 0; i < r; i++)
        for(int j = 0; j < c; j++)
            scanf("%d", &arr[i][j]);

    for(int i = 0; i < r; i++) {
        for(int j = 0; j < c; j++) {
            printf("arr[%d][%d]=%d (Addr=%p)  ", i, j, arr[i][j], (void*)&arr[i][j]);
        }
        printf("\n");
    }
}

// ===== Module 5: String & Pointer Demo =====
void stringPointerDemo() {
    char str[100];
    printf("\n--- String & Pointer Demo ---\n");
    printf("Enter a string: ");
    getchar(); // Clear leftover newline from previous input
    fgets(str, sizeof(str), stdin);
    str[strcspn(str, "\n")] = 0; // Remove trailing newline from fgets

    char *ptr = str; // Pointer to the first character of string
    printf("String: %s\n", str);
    printf("Pointer traversal:\n");
    for(int i = 0; i < strlen(str); i++)
        printf("(ptr+%d) = %c at address %p\n", i, *(ptr + i), (void*)(ptr + i));
        // Demonstrates pointer arithmetic and dereferencing
}

// ===== Module 6: Structure & Union Visualizer =====
void structUnionVisualizer() {
    printf("\n--- Structure & Union Visualizer ---\n");

    struct Student {
        int roll;
        float marks;
        char grade;
    } s;

    printf("Enter student roll, marks, grade: ");
    scanf("%d %f %c", &s.roll, &s.marks, &s.grade);

    printf("Struct size = %zu bytes\n", sizeof(s));
    printf("roll=%d at %p\nmarks=%.2f at %p\ngrade=%c at %p\n", 
           s.roll, &s.roll, s.marks, &s.marks, s.grade, &s.grade);
    // Shows memory layout, padding, and alignment

    union Data {
        int id;
        float marks;
    } u;

    printf("Enter union id: ");
    scanf("%d", &u.id);
    printf("Union size = %zu bytes, id=%d at %p\n", sizeof(u), u.id, &u);
    // All members share the same memory address
}

// ===== Module 7: Pointer Playground =====
void pointerPlayground() {
    printf("\n--- Pointer Playground ---\n");
    int x;
    printf("Enter an integer x: ");
    scanf("%d", &x);

    int *p = &x;      // Single pointer
    int **pp = &p;    // Double pointer (pointer to pointer)

    printf("x=%d, Address of x=%p\n", x, &x);
    printf("*p=%d, Address of pointer p=%p\n", *p, &p);
    printf("**pp=%d, Address of double pointer pp=%p\n", **pp, &pp);

    int arr[5];
    printf("Enter 5 integers for array: ");
    for(int i = 0; i < 5; i++) scanf("%d", &arr[i]);
    printf("Array traversal via pointer: ");
    for(int i = 0; i < 5; i++) printf("%d ", *(arr + i));
    // arr[i] ≡ *(arr + i) - classic pointer-array equivalence
    printf("\n");
}

// ===== Module 8: Dynamic Memory Demo =====
void dynamicMemoryDemo() {
    int n;
    printf("\n--- Dynamic Memory Demo ---\n");
    printf("How many integers to allocate dynamically? ");
    scanf("%d", &n);

    int *ptr = (int*)malloc(n * sizeof(int)); // Heap allocation
    if(!ptr) { 
        printf("Memory allocation failed!\n"); 
        return; 
    }

    printf("Enter %d integers:\n", n);
    for(int i = 0; i < n; i++) scanf("%d", &ptr[i]);

    printf("Allocated memory values:\n");
    for(int i = 0; i < n; i++) 
        printf("ptr[%d] = %d at %p\n", i, ptr[i], (void*)&ptr[i]);

    free(ptr); // Mandatory deallocation - prevents memory leak
    printf("Memory freed.\n");
}

// ===== Module 9: Error Teaching Assistant =====
void errorTeachingAssistant() {
    printf("\n--- Error Teaching Assistant ---\n");
    printf("Select error to understand:\n");
    printf("1. Uninitialized variable\n2. Array out-of-bound\n3. Null pointer\n4. Type mismatch\n5. Missing semicolon\n");
    int choice;
    scanf("%d", &choice);

    switch(choice){
        case 1: printf("Uninitialized variable: Using a variable without assigning value gives garbage value.\n"); break;
        case 2: printf("Array out-of-bound: Accessing arr[index] where index>=size leads to undefined behavior.\n"); break;
        case 3: printf("Null pointer: Dereferencing NULL pointer causes crash.\n"); break;
        case 4: printf("Type mismatch: Assigning float to int pointer or incompatible types causes warning/error.\n"); break;
        case 5: printf("Missing semicolon: Each statement must end with ; else compilation error.\n"); break;
        default: printf("Invalid choice.\n");
    }
}