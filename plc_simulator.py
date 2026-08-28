#!/usr/bin/env python3
import time
import random
import json
import paho.mqtt.client as mqtt

MQTT_BROKER = "mosquitto"
MQTT_PORT = 1883
BASE_TOPIC = "coficab/surpresseur"

P1_MAX = 4.5
P1_MIN = 1.5
P2_MAX = 4.3

T1_DURATION = 3
T2_DURATION = 2

client = mqtt.Client(client_id="coficab-plc-simulator")


def connect_mqtt():
    while True:
        try:
            client.connect(MQTT_BROKER, MQTT_PORT, 60)
            print(f"[OK] Connected to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}")
            return
        except Exception as e:
            print(f"[WAIT] MQTT broker not ready yet ({e}), retrying in 3s...")
            time.sleep(3)


def publish(topic_suffix, value):
    topic = f"{BASE_TOPIC}/{topic_suffix}"
    payload = json.dumps(value) if not isinstance(value, (str, int, float, bool)) else value
    client.publish(topic, payload, retain=True)


def simulate_pressure(base, noise=0.3):
    return round(base + random.uniform(-noise, noise), 2)


def run_grafcet():
    state = "X0"
    A = True
    P = True

    print("=== COFICAB Surpresseur Simulator started ===")
    publish("inputs/A", A)
    publish("inputs/P", P)

    while True:
        publish("state", state)

        if state == "X0":
            print("[X0] Idle. Waiting for start conditions...")
            publish("outputs/Mt1", False)
            publish("outputs/Mt2", False)
            publish("outputs/fault", False)
            time.sleep(2)

            p1 = simulate_pressure(P1_MIN)
            publish("inputs/P1", p1)

            if A and P and p1 <= P1_MIN:
                state = "X1"
            continue

        if state == "X1":
            print("[X1] Mt1 ON. Timer t1 running (3s)...")
            publish("outputs/Mt1", True)

            reached_p1max = False
            for _ in range(T1_DURATION * 2):
                p1 = simulate_pressure((P1_MIN + P1_MAX) / 2, noise=1.0)
                publish("inputs/P1", p1)
                if p1 >= P1_MAX:
                    reached_p1max = True
                    break
                time.sleep(0.5)

            if reached_p1max:
                print("[X1] P1max reached -> cycle repeats (back to X0)")
                state = "X0"
            else:
                print("[X1] Timer expired, P1max not reached -> go to X2")
                state = "X2"
            continue

        if state == "X2":
            print("[X2] Mt1 + Mt2 ON. Timer t2 running (2s)...")
            publish("outputs/Mt1", True)
            publish("outputs/Mt2", True)

            reached_p2max = False
            for _ in range(T2_DURATION * 2):
                p2 = simulate_pressure(P2_MAX - 0.5, noise=1.0)
                publish("inputs/P2", p2)
                if p2 >= P2_MAX:
                    reached_p2max = True
                    break
                time.sleep(0.5)

            if reached_p2max:
                state = "X3"
            else:
                state = "X4"
            continue

        if state == "X3":
            print("[X3] P2max reached. Mt1 running normally.")
            publish("outputs/Mt1", True)
            publish("outputs/Mt2", False)
            publish("outputs/fault", False)

            p1 = simulate_pressure((P1_MIN + P1_MAX) / 2, noise=1.0)
            publish("inputs/P1", p1)
            time.sleep(1)

            if p1 >= P1_MAX:
                print("[X3] P1max reached -> back to X0")
                state = "X0"
            continue

        if state == "X4":
            print("[X4] FAULT DETECTED: P2max not reached in time. V_R ON.")
            publish("outputs/fault", True)
            time.sleep(2)

            p1 = simulate_pressure((P1_MIN + P1_MAX) / 2, noise=1.0)
            publish("inputs/P1", p1)

            if p1 >= P1_MAX:
                print("[X4] P1max reached -> fault cleared, back to X0")
                state = "X0"
            continue


if __name__ == "__main__":
    connect_mqtt()
    client.loop_start()
    try:
        run_grafcet()
    except KeyboardInterrupt:
        print("Simulator stopped.")
    finally:
        client.loop_stop()
        client.disconnect()
