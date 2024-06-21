#include "DHT_LCD.h"
#include "Servo_Ultrasonic.h"

void setup() {
  // Inicialização dos componentes
  initDHT_LCD();
  initServoUltrasonic();
}

void loop() {

  updateDHT_LCD();

  updateServoUltrasonic();
  
  delay(100); 
}
