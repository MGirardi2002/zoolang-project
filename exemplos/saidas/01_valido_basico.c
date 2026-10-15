/* Gerado pelo transpilador ZooLang (zooc). */
#include <stdio.h>
#include <stdbool.h>

int main(void) {
    char bicho[256] = "Leao Simba";
    int idade = 5;
    double kg_de_carne = 12.5;
    bool ta_na_jaula = true;
    idade = idade + 1;
    kg_de_carne = kg_de_carne + 2.5;
    printf("ROARRR! BEM-VINDO AO ZOOLOGICO DA ZOOLANG!\n");
    printf("%s\n", bicho);
    printf("%d\n", idade);
    printf("%g\n", kg_de_carne);
    printf("%s\n", ta_na_jaula ? "vivo" : "morto");
    return 0;
}
