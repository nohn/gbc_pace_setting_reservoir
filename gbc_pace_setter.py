from pybricks.pupdevices import Motor, ColorSensor
from pybricks.parameters import Port
from pybricks.tools import StopWatch

TARGET_RATE       = 1.00 # Balls per second
TARGET_TOLERANCE  = 0.10 # To avoid permament adjustments, allow 10% tolerance
ADJUSTMENT_STEP   = 10
MIN_SPEED         = 10
MAX_SPEED         = 500
CHECK_INTERVAL_MS = 100
AVG_INTERVAL_SEC  = 5    # You may want to set this lower for smaller adjustment steps
BALL_THRESHOLD    = 5
BALL_COOLDOWN_MS  = 100  # Cooldown period for flank detection

# Calculate lower and upper rate boundaries using TARGET_TOLERANCE
TARGET_RATE_LOWER = TARGET_RATE-(TARGET_RATE*TARGET_TOLERANCE)
TARGET_RATE_UPPER = TARGET_RATE+(TARGET_RATE*TARGET_TOLERANCE)

# Init peripherals
motor = Motor(Port.A)
sensor = ColorSensor(Port.B)

# Init ABS
block_watch = StopWatch()
last_angle = motor.angle()
BLOCK_CHECK_INTERVAL_MS = 300
BLOCKED_THRESHOLD_DEGREES = 5  # if movement is less than this
UNBLOCK_REVERSE_DEGREES = 20
UNBLOCK_SPEED = -200

# Initial Motor Speed
motor_speed = (MAX_SPEED - MIN_SPEED) / 2
motor.run(motor_speed)

event_count = 0
total_events = 0
total_time = 0.0
cycle_events = 0
cycle_time = 0.0

adjust_watch = StopWatch()
cooldown_watch = StopWatch()
cooldown_watch.reset()

while True:
    reflection = sensor.reflection()
    # print(f"{reflection}")
    ball_detected = reflection > BALL_THRESHOLD

    # Count ball only if cooldown period has passed
    if ball_detected and cooldown_watch.time() >= BALL_COOLDOWN_MS:
        # print(f"{reflection}")
        event_count += 1
        cooldown_watch.reset()

    # Check Cycle
    if adjust_watch.time() >= CHECK_INTERVAL_MS:
        elapsed = adjust_watch.time() / 1000
        adjust_watch.reset()

        total_events += event_count
        cycle_events += event_count
        total_time += elapsed
        cycle_time += elapsed
        event_count = 0

        if cycle_time >= AVG_INTERVAL_SEC:
            cycle_avg_rate = cycle_events / cycle_time
            total_avg_rate = total_events / total_time

            if cycle_avg_rate > TARGET_RATE_UPPER:
                motor_speed = max(MIN_SPEED, motor_speed - ADJUSTMENT_STEP)
            elif cycle_avg_rate < TARGET_RATE_LOWER:
                motor_speed = min(MAX_SPEED, motor_speed + ADJUSTMENT_STEP)

            motor.run(motor_speed)

            print(f"Cycle Rate: {cycle_avg_rate:.2f} bps | Target Rate: {TARGET_RATE_LOWER:.2f}<{TARGET_RATE:.2f}<{TARGET_RATE_UPPER:.2f} bps) | Speed: {motor_speed} deg/s | Total Rate: {total_avg_rate:.2f} bps | Total Time: {total_time:.1f}s | Total Balls: {total_events}")

            cycle_events = 0
            cycle_time = 0.0

    # Anti Blocking System
    if block_watch.time() >= BLOCK_CHECK_INTERVAL_MS:
        current_angle = motor.angle()
        delta = abs(current_angle - last_angle)

        if delta < BLOCKED_THRESHOLD_DEGREES and motor_speed > 0:
            print("Motor seems blocked — attempting to unblock.")
            motor.stop()
            motor.run_angle(UNBLOCK_SPEED, UNBLOCK_REVERSE_DEGREES)
            motor.run(motor_speed)

        last_angle = current_angle
        block_watch.reset()
