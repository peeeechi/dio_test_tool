// デジタル出力ピンの定義
const int OUTPUT_PINS[] = {22, 23, 24, 25, 26, 27, 28, 29};
// const int OUTPUT_PINS[] = {22, 23, 24, 25, 26, 27, 28, 13};
const int NUM_OUTPUTS = 8;

// デジタル入力ピンの定義
const int INPUT_PINS[] = {30, 31, 32, 33, 34, 35, 36, 37};
const int NUM_INPUTS = 8;

// 入力状態を格納する配列
int inputStates[NUM_INPUTS];
// 出力状態を格納する配列
int outputStates[NUM_OUTPUTS];

void setup() {
  // シリアル通信の初期化
  Serial.begin(9600);
  
  // 出力ピンの初期化
  for (int i = 0; i < NUM_OUTPUTS; i++) {
    pinMode(OUTPUT_PINS[i], OUTPUT);
    digitalWrite(OUTPUT_PINS[i], LOW);  // 初期状態はLOW
  }
  
  // 入力ピンの初期化
  for (int i = 0; i < NUM_INPUTS; i++) {
    pinMode(INPUT_PINS[i], INPUT_PULLUP);  // プルアップ抵抗を有効化
  }
}

void loop() {
  // シリアルコマンドの処理
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    processCommand(command);
  }
  
  // 入力状態の読み取りと変化の検出
  bool is_status_changed = readDIO();
  if (is_status_changed) {
    printStatus();
  }
  // printStatus();

  
  // 短い遅延
  delay(100);
}

// DIOの状態を読み取る関数
bool readDIO() {
  // read digital input
  bool is_changed = false;
  for (int i = 0; i < NUM_INPUTS; i++) {
    int currentState = digitalRead(INPUT_PINS[i]);
    if (currentState != inputStates[i]) {
      inputStates[i] = currentState;
      is_changed = true;
    }
  }
  // read digital output
  for (int i = 0; i < NUM_INPUTS; i++) {
    int currentState = digitalRead(OUTPUT_PINS[i]);
    if (currentState != outputStates[i]) {
      outputStates[i] = currentState;
      is_changed = true;
    }
  }

  return is_changed;
}

// 数値配列を文字列に変換して結合する関数
String joinInts(int arr[], int size, const char delimiter) {
  String result = "";
  
  for (int i = 0; i < size; i++) {
    result += String(arr[i]);  // 数値を文字列に変換
    if (i < size - 1) {
      result += delimiter;
    }
  }
  
  return result;
}

// シリアルコマンドを処理する関数
void processCommand(const String& input) {
  // 1. "command-"で始まっているか確認
  if (!input.startsWith("command-")) {
    return;
  }
  
  // 2. "-end"で終わっているか確認
  if (!input.endsWith("-end")) {
    return;
  }
  

  // 3. 中間部分の抽出
  int startPos = String("command-").length();
  int endPos = input.length() - String("-end").length();
  String valuesStr = input.substring(startPos, endPos);
  
  // 4. カンマ区切りの値を解析
  int currentIndex = 0;
  int lastCommaIndex = -1;
  
  while (true) {
    int nextCommaIndex = valuesStr.indexOf(',', lastCommaIndex + 1);
    String valueStr;
    
    if (nextCommaIndex == -1) {
      // 最後の値を処理
      valueStr = valuesStr.substring(lastCommaIndex + 1);
      int val = valueStr.toInt();
      digitalWrite(OUTPUT_PINS[currentIndex], val);
      currentIndex++;
      break;
    } else {
      valueStr = valuesStr.substring(lastCommaIndex + 1);
      int val = valueStr.toInt();
      digitalWrite(OUTPUT_PINS[currentIndex], val);
      currentIndex++;
      lastCommaIndex = nextCommaIndex;
    }
    
    if (currentIndex >= NUM_OUTPUTS) {
      break;
    }
  }
}

// 現在の状態を出力する関数
void printStatus() {
  String input_str = joinInts(inputStates, NUM_INPUTS, ',');   // "1-2-3"
  String output_str = joinInts(outputStates, NUM_INPUTS, ',');   // "1-2-3" 
  Serial.println("dio-" + input_str + "-" + output_str + "-end");
}