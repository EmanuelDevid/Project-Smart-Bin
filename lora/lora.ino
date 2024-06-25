#include <Wire.h>  
#include "HT_SSD1306Wire.h"
#include "BluetoothSerial.h"

// Definindo o display OLED
SSD1306Wire factory_display(0x3c, 500000, SDA_OLED, SCL_OLED, GEOMETRY_128_64, RST_OLED);

// Definindo o Bluetooth
BluetoothSerial SerialBT;

// Variáveis para armazenar a mensagem recebida
String incomingMessage = "";

void VextON(void)
{
  pinMode(Vext, OUTPUT);
  digitalWrite(Vext, LOW);
}

void VextOFF(void) // Vext default OFF
{
  pinMode(Vext, OUTPUT);
  digitalWrite(Vext, HIGH);
}

void setup()
{
  Serial.begin(115200);
  VextON();
  delay(100);
  factory_display.init();
  factory_display.clear();
  factory_display.display();

  // Inicializando o Bluetooth
  SerialBT.begin("ESP32_Bluetooth"); // Nome do dispositivo Bluetooth
  
  // Configurando o LED
  pinMode(LED, OUTPUT);
  digitalWrite(LED, LOW);
}

void loop()
{
  // Verificando se há dados recebidos via Bluetooth
  if (SerialBT.available()) {
    char incomingChar = SerialBT.read();
    if (incomingChar == '\n') { // Se receber uma nova linha, atualiza a mensagem no display
      updateDisplay();
      incomingMessage = ""; // Limpa a mensagem após atualizar o display
    } else {
      incomingMessage += incomingChar; // Adiciona o caractere à mensagem
    }
  }
}

void updateDisplay() {
  factory_display.clear();

  // Definindo tamanhos de fonte disponíveis
  const uint8_t* fonts[] = {ArialMT_Plain_10, ArialMT_Plain_16, ArialMT_Plain_24};

  // Determinando o tamanho da fonte com base no comprimento da mensagem
  int fontSizeIndex = 0; // Índice inicial da fonte (a menor disponível)
  int messageLength = incomingMessage.length();
  
  if (messageLength > 32) { // Se o comprimento da mensagem for maior que 20 caracteres
    fontSizeIndex = 0; // Usar a maior fonte disponível
  } else if (messageLength > 14) { // Se o comprimento da mensagem for maior que 10 caracteres
    fontSizeIndex = 1; // Usar a fonte média disponível
  } else{
    fontSizeIndex = 2;
  }

  // Aplicando a fonte e alinhamento ao display
  factory_display.setFont(fonts[fontSizeIndex]);
  factory_display.setTextAlignment(TEXT_ALIGN_LEFT);
  factory_display.drawStringMaxWidth(0, 0, 128, incomingMessage); // Exibe a mensagem no display
  factory_display.display();
}
