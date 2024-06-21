#include "Servo_Ultrasonic.h"

void setup() {

  initServoUltrasonic();
}

void loop() {
  updateServoUltrasonic();
  
  delay(100); 
}
