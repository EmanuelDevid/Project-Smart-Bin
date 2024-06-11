#include <Servo.h>

int inputPin = 10;  // Pino do sensor enviando a informação                        
#define SERVO 7     // Pino do servo motor recebendo a informação

Servo servo;

const unsigned long intervaloDeteccao = 5000; // Tempo de espera sem movimento para fechar a tampa (em milissegundos)
unsigned long tempoUltimoMovimento = 0;       // Armazena o tempo do último movimento detectado
bool tampaAberta = false;                     // Indica se a tampa está aberta ou fechada

void setup() {
  pinMode(inputPin, INPUT); // Define o pino do sensor como entrada
  servo.attach(SERVO);      // Anexa o servo ao pino definido
  pararServo();      // Para o servo no início
  Serial.begin(9600);       // Inicializa a comunicação serial
}

void loop() {
  if (digitalRead(inputPin) == HIGH) { // Se movimento for detectado
    tempoUltimoMovimento = millis();   // Atualiza o tempo do último movimento
    if (!tampaAberta) {                // Se a tampa estiver fechada
      abrirTampa();                    // Abre a tampa
      Serial.println("Motion detected!"); 
    }
  }

  if (tampaAberta && (millis() - tempoUltimoMovimento >= intervaloDeteccao)) { // Se a tampa estiver aberta e já passou o tempo de espera
    fecharTampa();                     // Fecha a tampa
    Serial.println("No motion detected for a while, closing the lid."); // Print para indicar fechamento da tampa
  }
}

void abrirTampa() {
  moverServo(25, 500);  // Gira o servo em uma direção por 1 segundo
  pararServo();          // Para o servo
  tampaAberta = true;    // Atualiza o estado da tampa para aberta
}

void fecharTampa() {
  moverServo(-20, 500); // Gira o servo na direção oposta por 1 segundo
  pararServo();          // Para o servo
  tampaAberta = false;   // Atualiza o estado da tampa para fechada
}

// Função para mover o servo motor
void moverServo(int velocidade, int duracao) {
  int comando = map(velocidade, -90, 90, 0, 180); // Converte a velocidade em um comando de servo
  servo.write(comando);  // Define a velocidade de rotação
  delay(duracao);        // Aguarda pelo tempo de duração da rotação
}

void pararServo() {
  servo.write(90); // Para o servo motor
}
