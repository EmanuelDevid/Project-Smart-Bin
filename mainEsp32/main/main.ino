#define BLYNK_TEMPLATE_ID "TMPL23_DeOvW0"
#define BLYNK_TEMPLATE_NAME "Bumblebee"
#define BLYNK_AUTH_TOKEN "aEMj2BSxHnip3ZZyZqVnBzrAlQsCEoBY"
#define MAX_DISTANCE 25.0

#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <WiFi.h>
#include <BlynkSimpleEsp32.h>
#include <DHTesp.h>

#define DHTPIN 4

int trigPin = 5; 
int echoPin = 18; 


long duration, dist;
long aver[3];

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

BlynkTimer timer;
LiquidCrystal_I2C lcd(0x3F, 16, 2); // Endereço do LCD, colunas e linhas
DHTesp dht;

byte degreeSymbol[8] = {
  B00110,
  B01001,
  B01001,
  B00110,
  B00000,
  B00000,
  B00000,
  B00000
};

// Variáveis de estado
bool dhtActive = true;
bool ultrasonicActive = true;


float previousTemperature = 0;
float previousHumidity = 0;



// Função de inicialização do DHT e LCD
void initDHT_LCD() {
   lcd.init();
  lcd.backlight();
  lcd.print("Iniciando...");
  delay(2000);
  lcd.clear();
  dht.setup(DHTPIN, DHTesp::DHT22);
   lcd.createChar(0, degreeSymbol);
}

// Função de atualização do DHT e LCD
void updateDHT_LCD() {
  if (dhtActive) {
   float currentHumidity = dht.getHumidity();
  float currentTemperature = dht.getTemperature();
    if (isnan(currentTemperature) || isnan(currentHumidity)) {
       Serial.println("Erro ao ler DHT!");
    }

    if (currentTemperature != previousTemperature) {
    lcd.setCursor(0, 0);
    lcd.print("T:");
    lcd.print(currentTemperature);
    lcd.write(0);
    lcd.print("C");
    previousTemperature = currentTemperature;
  }

    if (currentHumidity != previousHumidity) {
    lcd.setCursor(0, 1);
    lcd.print("U:");
    lcd.print(currentHumidity);
    lcd.print("% ");
    previousHumidity = currentHumidity;
  }

    Blynk.virtualWrite(VPIN_TEMP, currentTemperature);
    Blynk.virtualWrite(VPIN_HUMID, currentHumidity);
  }
}

// Função de inicialização do servo e sensor ultrassônico
void initServoUltrasonic() {
   Serial.begin(115200);
  pinMode(trigPin, OUTPUT);
  pinMode(echoPin, INPUT);
}

void measure() {
  digitalWrite(trigPin, LOW);
  delayMicroseconds(5);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(15);
  digitalWrite(trigPin, LOW);
  pinMode(echoPin, INPUT);
  duration = pulseIn(echoPin, HIGH);
  dist = (duration / 2) / 29.1;
}

// Função de atualização do servo e sensor ultrassônico
void updateServoUltrasonic() {
  if (ultrasonicActive) {
 for (int i = 0; i <= 2; i++) {
    measure();
    aver[i] = dist;
    delay(10);
  }
  dist = (aver[0] + aver[1] + aver[2]) / 3 - 10;
  if (dist < 25) {
    Serial.print(dist);
    Serial.println(" cm");

float porcentagem = (1 - dist / MAX_DISTANCE) * 100;
    Serial.print(porcentagem);
    Serial.println(" %");
    Blynk.virtualWrite(VPIN_DIST, porcentagem);
  }
 
    
  }
}

BLYNK_WRITE(VPIN_SWITCH_DHT) {
  dhtActive = param.asInt();
}

BLYNK_WRITE(VPIN_SWITCH_ULTRASONIC) {
  ultrasonicActive = param.asInt();
}

void setup() {
  Serial.begin(115200);
  initDHT_LCD();
  initServoUltrasonic();

  // Conectando ao WiFi e Blynk
  WiFi.begin(ssid, pass);
  Blynk.begin(auth, ssid, pass);

  // Configuração do timer para atualizar DHT e Ultrassônico
  timer.setInterval(2000L, updateDHT_LCD);
  timer.setInterval(2000L, updateServoUltrasonic);
}

void loop() {
  Serial.begin(115200);
  Blynk.run();
  timer.run();
}
