#define BLYNK_TEMPLATE_ID "TMPL23_DeOvW0"
#define BLYNK_TEMPLATE_NAME "Bumblebee"
#define BLYNK_AUTH_TOKEN "aEMj2BSxHnip3ZZyZqVnBzrAlQsCEoBY"
#include <WiFi.h>
#include <BlynkSimpleEsp32.h>
#include <SoftwareSerial.h>
// #include "BluetoothSerial.h"

// #if !defined(CONFIG_BT_ENABLED) || !defined(CONFIG_BLUEDROID_ENABLED)
// #error Bluetooth is not enabled! Please run make menuconfig to and enable it
// #endif

// BluetoothSerial SerialBT;



// Definição das variáveis globais de WiFi e autenticação
char auth[] = BLYNK_AUTH_TOKEN;
char ssid[] = "brisa-688923";
char pass[] = "akjd2t58";

// Definições dos pinos virtuais do Blynk
#define VPIN_TEMP V0
#define VPIN_HUMID V1
#define VPIN_SWITCH_DHT V2
#define VPIN_SWITCH_ULTRASONIC V3
#define VPIN_DIST V4

// Definição dos pinos para as portas seriais
#define RXD1 16 // RX pin for mySerial1
#define TXD1 17 // TX pin for mySerial1
#define RXD2 18 // RX pin for mySerial2
#define TXD2 19 // TX pin for mySerial2

SoftwareSerial mySerial1(RXD1, TXD1); // RX, TX for data communication
SoftwareSerial mySerial2(RXD2, TXD2); // RX, TX for command communication
int temp, humid, percent;

// Variáveis de estado
bool dhtActive = true;
bool ultrasonicActive = true;



BLYNK_WRITE(VPIN_SWITCH_DHT) {
  dhtActive = param.asInt(); // Recebe comando do Blynk para ativar/desativar DHT
}

BLYNK_WRITE(VPIN_SWITCH_ULTRASONIC) {
  ultrasonicActive = param.asInt(); // Recebe comando do Blynk para ativar/desativar Ultrassônico
}

void setup() {
  Serial.begin(9600);
  mySerial1.begin(9600);
  mySerial2.begin(9600);

  // Conexão WiFi e Blynk
  WiFi.begin(ssid, pass);
  Blynk.begin(auth, ssid, pass);

  // Sincroniza os estados iniciais dos pinos virtuais do Blynk
  Blynk.syncVirtual(VPIN_SWITCH_DHT);
  Blynk.syncVirtual(VPIN_SWITCH_ULTRASONIC);
}

void loop() {
  Blynk.run();

  if (mySerial1.available() > 0) {
    String data = mySerial1.readStringUntil('\n');
    Serial.print(">");
    Serial.println(data);

    if (data.startsWith("DAT:")) {
      data.remove(0, 4);
      sscanf(data.c_str(), "%d,%d,%d", &temp, &humid, &percent);

      Blynk.virtualWrite(VPIN_TEMP, temp);
      Blynk.virtualWrite(VPIN_HUMID, humid);
      Blynk.virtualWrite(VPIN_DIST, percent);
    }
  }

  mySerial2.print("CMD:");
  mySerial2.print(dhtActive);
  mySerial2.print(",");
  mySerial2.println(ultrasonicActive);
  delay(300);
}
