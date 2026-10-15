/* Gerado pelo transpilador ZooLang (zooc). */
#include <stdio.h>
#include <math.h>

int main(void) {
    const int ESTOQUE_IDEAL = 100;
    int bananas = 0;
    int refeicao = 1;
    double consumo = 0.0;
    int resultado = 0;
    resultado = 2 + 3 * 4;
    printf("%d\n", resultado);
    resultado = (2 + 3) * 4;
    printf("%d\n", resultado);
    printf("Quantas bananas chegaram para os macacos?\n");
    scanf("%d", &bananas);
    if (bananas >= ESTOQUE_IDEAL) {
        printf("BANANA PRA TODO MUNDO! OS MACACOS FIZERAM FESTA!\n");
    } else if (bananas >= 50) {
        printf("Da pro gasto, mas o gorila ficou de olho.\n");
    } else {
        printf("Pouca banana! Os macacos entraram em greve!\n");
    }
    while (refeicao <= 3) {
        consumo = consumo + bananas * 0.5;
        printf("Refeicao %d dos macacos servida!\n", refeicao);
        refeicao = refeicao + 1;
    }
    for (int i = 10; i > 0; i = i - 1) {
        if (i == 5) {
            printf("O leao escapou! Todo mundo foge!\n");
            break;
        }
        printf("%d\n", i);
    }
    printf("Bananas consumidas: %g\n", consumo);
    printf("ZOOLOGICO FECHADO! BOA NOITE, BICHOS!\n");
    return 0;
}
