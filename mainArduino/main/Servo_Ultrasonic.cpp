#include <Servo.h>
#include <Arduino.h>

int trigPin1 = 5;
int echoPin1 = 6;

int servoPin1 = 7;
int servoPin2 = 8;

long duration;
float dist, distLixeira;
float aver[3];

const unsigned long intervaloDeteccao = 5000;
unsigned long ultimoTempo = 0;
bool tampaAberta = false;

Servo servo1;
Servo servo2;

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
  servo1.attach(servoPin1); 
  servo2.attach(servoPin2); 
  pinMode(trigPin1, OUTPUT); 
  pinMode(echoPin1, INPUT); 
  
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
      ultimoTempo = millis();
  } else if(tampaAberta && (millis() - ultimoTempo > intervaloDeteccao)){
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

  Serial.print(dist);
  Serial.println(" cm");

}