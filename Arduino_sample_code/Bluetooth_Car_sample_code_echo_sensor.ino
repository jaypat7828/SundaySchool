char t;
int h;
int distance;

void setup() {
  pinMode(13, OUTPUT);  //left motors  forward
  pinMode(12, OUTPUT);  //left motors reverse
  pinMode(11, OUTPUT);  //right  motors forward
  pinMode(10, OUTPUT);  //right motors reverse
  pinMode(9, OUTPUT);   //Led
  pinMode(3, OUTPUT);   // Buzzer (Horn) on Pin 3
  h = pulseIn(2, HIGH);  // Read the distance from the ultrasonic sensor on Pin 2
  Serial.begin(9600);
  distance = h * 0.034 / 2;  // Calculate distance in centimeters
}

void EmergencyStop() {
  if (distance < 20) {  // If an obstacle is detected within 20 cm
    digitalWrite(13, LOW);
    digitalWrite(12, LOW);
    digitalWrite(11, LOW);
    digitalWrite(10, LOW);
    digitalWrite(3, LOW); 
    Serial.println("Emergency Stop Activated! Obstacle Detected.");
  }
}

void loop() {
  if (Serial.available()) {
    t = Serial.read();
    Serial.println(t);
  }

  if (t == 'F') {  //move  forward(all motors rotate in forward direction)
    digitalWrite(13, HIGH);
    digitalWrite(11, HIGH);
    EmergencyStop();
  }

  else if (t == 'B') {  //move reverse (all  motors rotate in reverse direction)
    digitalWrite(12, HIGH);
    digitalWrite(10, HIGH);
  }

  else if (t == 'L') {  //turn left (left side motors rotate in forward direction,  right side motors doesn't rotate)
    digitalWrite(11, HIGH);
    EmergencyStop();
  }

  else if (t == 'R') {  //turn right (right side motors rotate in forward direction, left  side motors doesn't rotate)
    digitalWrite(13, HIGH);
    EmergencyStop();
  }

  else if (t == 'W') {  //turn led on or off)
    digitalWrite(9, HIGH);
  } else if (t == 'w') {
    digitalWrite(9, LOW);
  }

  else if (t == 'S') {  //STOP (all motors stop)
    digitalWrite(13, LOW);
    digitalWrite(12, LOW);
    digitalWrite(11, LOW);
    digitalWrite(10, LOW);
    digitalWrite(3, LOW); 
  }

  // Horn (Buzzer) activation ('V')
  else if (t == 'V') {
    digitalWrite(3, HIGH);

    delay(100);             // Buzzer sounds for 500 milliseconds
    digitalWrite(3, LOW);   // Turn off the buzzer
  }
  delay(100);
}
