char t;

void setup() {
  pinMode(13, OUTPUT);  //left motors  forward
  pinMode(12, OUTPUT);  //left motors reverse
  pinMode(11, OUTPUT);  //right  motors forward
  pinMode(10, OUTPUT);  //right motors reverse
  pinMode(9, OUTPUT);   //Led
  pinMode(3, OUTPUT);   // Buzzer (Horn) on Pin 3
  Serial.begin(9600);
}

void loop() {
  if (Serial.available()) {
    t = Serial.read();
    Serial.println(t);
  }

  if (t == 'F') {  //move  forward(all motors rotate in forward direction)
    digitalWrite(13, HIGH);
    digitalWrite(11, HIGH);
  }

  else if (t == 'B') {  //move reverse (all  motors rotate in reverse direction)
    --Write your code here --
  }

  else if (t == 'L') {  //turn right (left side motors rotate in forward direction,  right side motors doesn't rotate)
    digitalWrite(11, HIGH);
  }

  else if (t == 'R') {  //turn left (right side motors rotate in forward direction, left  side motors doesn't rotate)
    --Write your code here --
  }

  else if (t == 'W') {  //turn led on or off)
    digitalWrite(9, HIGH);
  } else if (t == 'w') {
    --Write your code here --
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
    --Write your code here --
    delay(100);             // Buzzer sounds for 500 milliseconds
    digitalWrite(3, LOW);   // Turn off the buzzer
  }
  delay(100);
}
