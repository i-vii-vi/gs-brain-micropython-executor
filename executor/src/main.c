#include <Python.h>

// run 
// gcc main.c -o main -I/usr/include/python3.x -lpython3.x 
// before compiling

int main() {
    Py_Initialize();

    FILE* file = fopen("\src\main.py", "r");
    if (file != NULL) {
        PyRun_SimpleFile(file, "main.py");
        fclose(file);
    } else {
        fprintf(stderr, "Failed to open script.py\n");
    }

    // Clean up and close the Python interpreter
    Py_Finalize();
    
    return 0;
}
