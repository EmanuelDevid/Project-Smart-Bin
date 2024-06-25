#include "DHT.h"
#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <Servo.h>
#include <SoftwareSerial.h>
#include <Arduino.h>

// Definições
#define DHTPIN 2
#define DHTTYPE DHT22
#define MAX_DISTANCE 25

int trigPin1 = 5;
int echoPin1 = 6;
int trigPin2 = 3;
int echoPin2 = 4;
int servoPin1 = 7;
int servoPin2 = 8;

SoftwareSerial mySerial1(9, 10); // RX, TX for data communication with ESP32
SoftwareSerial mySerial2(11, 12); // RX, TX for command communication with ESP32

// Variáveis
long duration;
int dist, currentHumidity, currentTemperature, porcentagem = 0;

float distLixeira = 0;
float aver[3];
float aver2[3];
float previousTemperature = 0;
float previousHumidity = 0;

const unsigned long intervaloDeteccao = 5000;
unsigned long ultimoTempo = 0;
bool tampaAberta = false;
bool dhtActive = true;
bool ultrasonicActive = true;

// Objetos
DHT dht(DHTPIN, DHTTYPE);
LiquidCrystal_I2C lcd(0x3F, 16, 2);
Servo servo1;
Servo servo2;

// Símbolo de grau para o LCD
byte degreeSymbol[8] = {
  0b00111,
  0b00101,
  0b00111,
  0b00000,
  0b00000,
  0b00000,
  0b00000,
  0b00000
};

void initDHT_LCD() {
  lcd.init();
  lcd.backlight();
  lcd.clear();
  dht.begin();
  lcd.createChar(0, degreeSymbol);
}

void updateDHT_LCD() {

   if (dhtActive) {
  currentHumidity = dht.readHumidity();
  currentTemperature = dht.readTemperature();

   }



  if (isnan(currentHumidity) || isnan(currentTemperature)) {
    Serial.println("Erro ao ler DHT!");
    return;
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
}

float measure(int trigPin, int echoPin) {
  digitalWrite(trigPin, LOW);
  delayMicroseconds(5);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(15);
  digitalWrite(trigPin, LOW);
  pinMode(echoPin, INPUT);
  duration = pulseIn(echoPin, HIGH);
  return (duration / 2.0) / 29.1;
}

void initServoUltrasonic() {
  Serial.begin(9600);
  mySerial1.begin(9600);
  mySerial2.begin(9600);
  servo1.attach(servoPin1);
  servo2.attach(servoPin2);
  pinMode(trigPin1, OUTPUT);
  pinMode(echoPin1, INPUT);
  pinMode(trigPin2, OUTPUT);
  pinMode(echoPin2, INPUT);

  servo1.write(0);
  servo2.write(180);
  delay(100);
  servo1.detach();
  servo2.detach();


}

void updateServoUltrasonic() {
  for (int i = 0; i <= 2; i++) {
    aver[i] = measure(trigPin1, echoPin1);
    delay(10);
  }
  dist = (aver[0] + aver[1] + aver[2]) / 3;

  if (dist < 30) {
    ultimoTempo = millis();
  }

  if (dist < 30 && !tampaAberta) {
    servo1.attach(servoPin1);
    servo2.attach(servoPin2);
    delay(40);
    servo1.write(60);
    servo2.write(120);
    delay(500);
    servo1.detach();
    servo2.detach();
    tampaAberta = true;

  } else if (tampaAberta && (millis() - ultimoTempo > intervaloDeteccao) && dist > 30) {
    servo1.attach(servoPin1);
    servo2.attach(servoPin2);
    delay(40);
    servo1.write(0);
    servo2.write(180);
    delay(1000);
    servo1.detach();
    servo2.detach();
    tampaAberta = false;
  }

  if (ultrasonicActive && !tampaAberta) {
  for (int i = 0; i <= 2; i++) {
    aver2[i] = measure(trigPin2, echoPin2);
    delay(10);
  }
  distLixeira = (aver2[0] + aver2[1] + aver2[2]) / 3;
  distLixeira = max(0,distLixeira - 5);
  porcentagem = (int)max(0,(21-distLixeira) / 21 * 100);

}

  
}

void setup() {
  Serial.begin(9600);
  Serial.println("Iniciando...");
  initDHT_LCD();
  initServoUltrasonic();
  Serial.println("Setup concluído.");
}

void loop() {
  updateDHT_LCD();
  updateServoUltrasonic();

  if (mySerial2.available() > 0) {
    String command = mySerial2.readStringUntil('\n');
    Serial.print("Comando recebido: ");
    Serial.println(command);
    if (command.startsWith("CMD:")) {
      command.remove(0, 4); // Remove o prefixo "CMD,"
      sscanf(command.c_str(), "%d,%d", &dhtActive, &ultrasonicActive);
    }
  }

  // Serial.print("Enviando dados: ");
  // Serial.print(currentTemperature);
  // Serial.print(",");
  // Serial.print(currentHumidity);
  // Serial.print(",");
  // Serial.println(porcentagem);

  mySerial1.print("DAT:");
  mySerial1.print(currentTemperature);
  mySerial1.print(",");
  mySerial1.print(currentHumidity);
  mySerial1.print(",");
  mySerial1.println(porcentagem);

  delay(300);
}
