# Raspberry Pi Pico と MicroPython によるハードウェア制御ガイド

このドキュメントは、Thonny IDE と MicroPython を使用して Raspberry Pi Pico のハードウェアを制御するための技術的な知識をまとめたものです。

## 1. Raspberry Pi と Raspberry Pi Pico の違い

まず最も重要な点として、「Raspberry Pi」と「Raspberry Pi Pico」は全く異なるデバイスです。

| 特性 | Raspberry Pi (SBC) | Raspberry Pi Pico (MCU) |
| :--- | :--- | :--- |
| **種別** | シングルボードコンピュータ (SBC) | マイクロコントローラボード (MCU) |
| **OS** | Linux (Raspberry Pi OS) が動作 | OSは搭載しない（ベアメタルに近い） |
| **Python環境** | CPython (標準Python) | MicroPython (組み込み向け) |
| **主な用途** | PCのような高レベルな処理 | リアルタイムなハードウェア制御 |
| **GPIO制御** | `RPi.GPIO` ライブラリ (OS経由) | `machine` モジュール (直接制御) |

**結論**: `machine` モジュールを使用するコードは、Raspberry Pi Pico を対象としています。

## 2. Raspberry Pi Pico の基本

### MicroPython と Thonny IDE

Picoは、組み込みデバイス向けに最適化されたPythonである **MicroPython** で開発を行います。**Thonny** は、Picoへのプログラムの書き込みや実行を簡単に行える、初心者にも推奨されるIDEです。

### GPIOの基本

- **ピン配置**: Picoには物理的なピン番号（1〜40）と、プログラムで指定するGPIO番号（GP0〜GP28）があります。コーディングの際は **GPIO番号** を使用します。
- **3.3Vロジック**: PicoのGPIOは **3.3V** で動作します。5Vのデバイスを直接接続すると破損の原因となるため、**ロジックレベルシフタ** を使用してください。

## 3. ハードウェア制御の実践

### 3.1. Lチカ (LED点滅)

LEDの点滅は、ハードウェア制御の第一歩です。

#### `machine.Pin` モジュール

GPIOピンを操作するには `machine.Pin` クラスを使用します。

```python
from machine import Pin
import time

# GP25を「出力モード」で初期化
led = Pin(25, Pin.OUT)

while True:
    led.on()      # LEDを点灯 (3.3V出力)
    time.sleep(1)
    led.off()     # LEDを消灯 (0V出力)
    time.sleep(1)
```

#### オンボードLEDの利用

Picoの基板上にはLEDが実装されており、`'LED'` という特別な名前（エイリアス）で簡単にアクセスできます。この方法は、PicoとPico Wのハードウェア的な違いを吸収してくれるため、推奨されます。

```python
led = Pin('LED', Pin.OUT) # ← これだけでOK
```

#### 外部LEDの接続と電流制限抵抗

外部にLEDを接続する場合、PicoのGPIOピンを保護するために **必ず電流制限抵抗を直列に接続してください**。抵抗値はオームの法則で計算します（一般的に220Ω〜330Ω程度が使われます）。

- **回路**: `GPx -> 抵抗 -> LEDのアノード -> LEDのカソード -> GND`

### 3.2. サーボモーターの制御

サーボモーターの制御には、**PWM (Pulse Width Modulation)** という技術を使用します。

#### PWMの原理

PWMは、デジタル信号のON/OFFを高速で繰り返し、ONの時間（パルス幅）を変化させることで、アナログ的な制御を実現する技術です。サーボモーターの場合、このパルス幅によって回転角度や回転速度を指示します。

- **標準的なサーボ制御信号**:
    - **周波数**: 50Hz (周期20ms)
    - **パルス幅**:
        - 1.0ms (1000us): -90° (または最大逆回転)
        - 1.5ms (1500us): 0° (または停止)
        - 2.0ms (2000us): +90° (または最大正回転)

#### `machine.PWM` モジュール

PicoでPWM信号を生成するには `machine.PWM` クラスを使います。

```python
from machine import Pin, PWM

# GP0をPWMピンとして設定
pwm = PWM(Pin(0))

# 周波数を50Hzに設定
pwm.freq(50)
```

#### パルス幅[us]から`duty_u16`への変換

PicoのPWM API `pwm.duty_u16(value)` は、パルス幅を直接指定するのではなく、デューティ比を0〜65535の16ビット整数で指定します。

そのため、サーボが要求する「パルス幅（us）」を、Picoが要求する「`duty_u16`値」に変換する関数が必要です。

```python
# 周期は 20ms = 20,000us
PERIOD_US = 20_000

def pulse_us_to_u16(pulse_us: int) -> int:
    """パルス幅[us]をduty_u16(0-65535)に変換する"""
    return int(65535 * (pulse_us / PERIOD_US))

# 例: 1500us (停止信号) を変換
stop_duty = pulse_us_to_u16(1500) # 約4915
pwm.duty_u16(stop_duty)
```

#### 実践的なサーボドライバ

安価なアナログサーボには「個体差」があり、理論値通りに動作しないことがよくあります。以下の要素をソフトウェアで補正することで、より正確な制御が可能になります。

- **トリム調整 (`TRIM_US`)**: 停止点のズレを補正するオフセット値。
- **不感帯 (`DEADBAND_US`)**: 停止点付近の微振動（ジッター）を防ぐための範囲。

#### 安全な停止処理 (`try...finally`)

ハードウェアを制御するプログラムでは、予期せぬ終了時にもデバイスを安全な状態に保つことが重要です。`try...finally` ブロックを使うことで、プログラムが停止した際に必ずモーターを止め、PWM信号を解放できます。

```python
try:
    # メインの処理
    set_speed(0.5)
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("プログラムが停止されました。")
finally:
    # この処理は必ず実行される
    set_speed(0)  # モーターを停止
    pwm.deinit()  # PWMを解放
    print("安全に終了しました。")
```

## 4. 安全な電源供給

### モーターなどへの電源供給

サーボモーターのように大きな電流を必要とするデバイスをPicoのGPIOピンから直接駆動してはいけません。Picoの電源ピン（VBUSやVSYS）や、外部の安定した電源（バッテリー、ACアダプタなど）を使用してください。

- **重要な注意**: 外部電源を使用する場合、**必ずPicoのGNDと外部電源のGNDを接続（共通接地）** してください。これを怠ると、制御信号が正しく伝わらず、デバイスが予期せぬ動作をします。