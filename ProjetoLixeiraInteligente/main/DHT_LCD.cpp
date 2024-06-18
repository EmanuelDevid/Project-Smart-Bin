#include "DHT.h"
#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <Arduino.h>

#define DHTPIN 2
#define DHTTYPE DHT22

#define col 16
#define lin 2
#define ende 0x3F

DHT dht(DHTPIN, DHTTYPE);
LiquidCrystal_I2C lcd(ende, col, lin);

float previousTemperature = 0;
float previousHumidity = 0;
int previousAnalogValue = 0;

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

void initDHT_LCD() {
  lcd.init();
  lcd.backlight();
  lcd.clear();
  dht.begin();
  lcd.createChar(0, degreeSymbol);
}

void updateDHT_LCD() {
  float currentHumidity = dht.readHumidity();
  float currentTemperature = dht.readTemperature();


  if (isnan(currentHumidity) || isnan(currentTemperature)) {
    Serial.println("Erro ao ler DHT!");
  }

  // Atualiza apenas se a temperatura mudou
  if (currentTemperature != previousTemperature) {
    lcd.setCursor(0, 0);
    lcd.print("T:");
    lcd.print(currentTemperature);
    lcd.write(0); 
    lcd.print("C");
    previousTemperature = currentTemperature;
  }

  // Atualiza apenas se a umidade mudou
  if (currentHumidity != previousHumidity) {
    lcd.setCursor(0, 1);
    lcd.print("U:");
    lcd.print(currentHumidity);
    lcd.print("% ");
    previousHumidity = currentHumidity;
  }
}

