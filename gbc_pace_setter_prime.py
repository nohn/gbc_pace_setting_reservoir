from pybricks.pupdevices import Motor, ColorSensor
from pybricks.parameters import Port, Color, Button, Side
from pybricks.tools import StopWatch
from pybricks.hubs import PrimeHub

TARGET_RATE       = 0.95  # Balls per second
TARGET_TOLERANCE  = 0.05  # 5% tolerance
ADJUSTMENT_STEP   = TARGET_RATE * 5
INITAL_SPEED      = 125 * TARGET_RATE
MIN_SPEED         = INITAL_SPEED / 2
MAX_SPEED         = INITAL_SPEED * 2
CHECK_INTERVAL_MS = 100
AVG_INTERVAL_SEC  = 5     # You may want to set this lower for smaller adjustment steps
BALL_THRESHOLD    = 8
BALL_COOLDOWN_MS  = 100   # Cooldown period for flank detection

# Calculate lower and upper rate boundaries using TARGET_TOLERANCE
TARGET_RATE_LOWER = TARGET_RATE - (TARGET_RATE * TARGET_TOLERANCE)
TARGET_RATE_UPPER = TARGET_RATE + (TARGET_RATE * TARGET_TOLERANCE)

# Init peripherals
hub = PrimeHub()
motor = Motor(Port.B)
sensor = ColorSensor(Port.A)

# Init ABS
block_watch = StopWatch()
last_angle = motor.angle()
BLOCK_CHECK_INTERVAL_MS = 1000
BLOCKED_THRESHOLD_DEGREES = 5  # if movement is less than this
UNBLOCK_REVERSE_DEGREES = 20
UNBLOCK_SPEED = -200

# Initial Motor Speed
motor_speed = INITAL_SPEED
motor.run(motor_speed)

ball_count = 0
total_balls = 0
total_time = 0.0
cycle_balls = 0
cycle_time = 0.0
bpm_balls = 0
bpm_time = 0.0
bpm_avg_rate = False

display_watch = StopWatch()
adjust_watch = StopWatch()
cooldown_watch = StopWatch()
display_watch.reset()
cooldown_watch.reset()

total_avg_rate = 0

last_displayed_target_rate = None
last_displayed_total_avg_rate = None

paused = False

while True:
    reflection = sensor.reflection()
    # print(f"{reflection}")
    ball_detected = reflection > BALL_THRESHOLD

    # Count ball only if cooldown period has passed
    if ball_detected and cooldown_watch.time() >= BALL_COOLDOWN_MS:
        # print(f"{reflection}")
        ball_count += 1
        cooldown_watch.reset()

    buttons = hub.buttons.pressed()
    # Decrease speed
    if Button.LEFT in buttons:
        TARGET_RATE = max(0.05, TARGET_RATE - 0.05)
        print(f"TARGET_RATE decreased: {TARGET_RATE:.2f} bps")
        ADJUSTMENT_STEP = TARGET_RATE * 5
        INITAL_SPEED = 125 * TARGET_RATE
        MIN_SPEED = INITAL_SPEED / 2
        MAX_SPEED = INITAL_SPEED * 2
        TARGET_RATE_LOWER = TARGET_RATE - (TARGET_RATE * TARGET_TOLERANCE)
        TARGET_RATE_UPPER = TARGET_RATE + (TARGET_RATE * TARGET_TOLERANCE)

    # Increase speed
    if Button.RIGHT in buttons:
        TARGET_RATE = TARGET_RATE + 0.05
        print(f"TARGET_RATE increased: {TARGET_RATE:.2f} bps")
        ADJUSTMENT_STEP = TARGET_RATE * 5
        INITAL_SPEED = 125 * TARGET_RATE
        MIN_SPEED = INITAL_SPEED / 2
        MAX_SPEED = INITAL_SPEED * 2
        TARGET_RATE_LOWER = TARGET_RATE - (TARGET_RATE * TARGET_TOLERANCE)
        TARGET_RATE_UPPER = TARGET_RATE + (TARGET_RATE * TARGET_TOLERANCE)

    # Pause/Unpause Motor
    if Button.BLUETOOTH in buttons:
        paused = not paused
        if paused:
            print("Motor paused.")
            motor.stop()
            hub.display.text(f"R:{total_avg_rate:.3f}B:{total_balls}")
        else:
            print("Motor resumed.")
            hub.display.text(f"T:{TARGET_RATE:.2f}")
            motor.run(motor_speed)        

    # Check Cycle
    if last_displayed_target_rate != TARGET_RATE:
        hub.display.text(f"{TARGET_RATE:.2f}")
        last_displayed_target_rate = TARGET_RATE

    if adjust_watch.time() >= CHECK_INTERVAL_MS:
        elapsed = adjust_watch.time() / 1000
        adjust_watch.reset()

        total_balls += ball_count
        cycle_balls += ball_count
        bpm_balls += ball_count
        total_time += elapsed
        cycle_time += elapsed
        bpm_time += elapsed
        ball_count = 0

        if cycle_time >= AVG_INTERVAL_SEC:
            cycle_avg_rate = cycle_balls / cycle_time
            total_avg_rate = total_balls / total_time

            if cycle_avg_rate > TARGET_RATE_UPPER:
                motor_speed = max(MIN_SPEED, motor_speed - ADJUSTMENT_STEP)
            elif cycle_avg_rate < TARGET_RATE_LOWER:
                motor_speed = min(MAX_SPEED, motor_speed + ADJUSTMENT_STEP)

            if not paused:
                motor.run(motor_speed)

            print(f"CR: {cycle_avg_rate:.3f} bps | 60sAR: {bpm_avg_rate:.3f} bps | TAR: {total_avg_rate:.3f} bps | TR: {TARGET_RATE_LOWER:.2f}<{TARGET_RATE:.2f}<{TARGET_RATE_UPPER:.2f} bps) | NCS: {motor_speed} deg/s | AS: {motor.angle()/total_time:.0f} deg/s | TT: {total_time:.1f}s | TB: {total_balls}")

            cycle_balls = 0
            cycle_time = 0.0

        if bpm_time >= 60:
            bpm_avg_rate = bpm_balls / bpm_time
            bpm_balls = 0
            bpm_time = 0.0

        if bpm_avg_rate:
            if bpm_avg_rate > TARGET_RATE_UPPER:
                hub.light.on(Color.RED)
                if bpm_avg_rate > 2 * TARGET_RATE_UPPER:
                    hub.light.blink(Color.RED, [500, 500])
            elif bpm_avg_rate < TARGET_RATE_LOWER:
                hub.light.on(Color.BLUE)
                if bpm_avg_rate < 2 * TARGET_RATE_LOWER:
                    hub.light.blink(Color.BLUE, [500, 500])
            else:
                hub.light.on(Color.GREEN)

    # Anti Blocking System
    if not paused and block_watch.time() >= BLOCK_CHECK_INTERVAL_MS:
        current_angle = motor.angle()
        delta = abs(current_angle - last_angle)
        # print(f"Delta: {delta}")

        if delta < BLOCKED_THRESHOLD_DEGREES and motor_speed > 0:
            print("Motor seems blocked — attempting to unblock.")
            hub.light.blink(Color.RED, [500, 500])
            motor.stop()
            motor.run_angle(UNBLOCK_SPEED, UNBLOCK_REVERSE_DEGREES)
            motor.run(motor_speed)
            hub.light.blink(Color.BLUE, [500, 500])

        last_angle = current_angle
        block_watch.reset()
