from machine import Pin, PWM
import time

# === 設定 ===
PWM_PIN = 0
FREQ_HZ = 50            # FS90Rは50Hz
PERIOD_US = 20_000      # 50Hz の周期(20ms)
CENTER_US = 1500        # 理論上の停止パルス幅
SPAN_US = 500           # 1.0 のとき ±500us（= 1000〜2000us）
TRIM_US = 0            # 個体差で停止しない時の微調整(+/- 50〜100us程度)

DEADBAND_US = 10        # 中立付近の遊び（停止の安定化）

# === 初期化 ===
pwm = PWM(Pin(PWM_PIN))
pwm.freq(FREQ_HZ)

def pulse_us_to_u16(pulse_us: int) -> int:
    """パルス幅[us] -> duty_u16(0-65535)に変換"""
    # 安全のため 0〜PERIOD_US にクリップ
    if pulse_us < 0:
        pulse_us = 0
    elif pulse_us > PERIOD_US:
        pulse_us = PERIOD_US
    return int(65535 * (pulse_us / PERIOD_US))

def set_speed(speed: float):
    """
    speed: -1.0(全速逆) 〜 0(停止) 〜 +1.0(全速正)
    ニュートラル調整(TRIM_US)とデッドバンドで停止を安定化
    """
    # クリップ
    if speed > 1.0: speed = 1.0
    if speed < -1.0: speed = -1.0

    # 速度 -> パルス幅へ
    pulse = CENTER_US + TRIM_US + int(speed * SPAN_US)

    # 中立付近は完全停止に丸める（停止がズルズル動くのを防ぐ）
    if abs((CENTER_US + TRIM_US) - pulse) <= DEADBAND_US:
        pulse = CENTER_US + TRIM_US

    pwm.duty_u16(pulse_us_to_u16(pulse))

# === デモ: 1秒ずつ 低速→中速→高速→停止→逆回転 ===
try:
    set_speed(+0.6);
    
    while True:
        time.sleep(1)  # 回転維持
        

except KeyboardInterrupt:
    print("\nCtrl+Cで停止しました。")

finally:
    # 安全にPWMを停止
    set_speed(0)
    time.sleep(0.3)
    pwm.deinit()
    print("PWM信号を停止しました。安全に終了します。")