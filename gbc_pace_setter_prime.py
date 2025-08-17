from pybricks.pupdevices import Motor, ColorSensor
from pybricks.parameters import Port, Color, Button, Side
from pybricks.tools import StopWatch
from pybricks.hubs import PrimeHub
import urandom

# --- Ball Flow Target Configuration ---
TARGET_RATE         =      1.00   # Target Balls per second
TARGET_TOLERANCE    =      0.05   # To avoid permament adjustments, allow 5% tolerance
# --- Failure Simulation Configuration ---
FAILURE_PROBABILITY =      0      # Aim to spend this FRACTION of time in any failure mode
                                  # (e.g., 0.10 => ~10% of the runtime in failure). 
                                  # Set to 0 disable 
FAILURE_MIN_MS      =  30000      # Min duration of a problem is 30 seconds
FAILURE_MAX_MS      = 180000      # Max duration of a problem is 3 minutes
NORMAL_DURATION_MS  = 300000      # Min Time between problems is 5 minutes
# --- Motor Speed Configuration. Change these depending on your MOC ---
INITIAL_SPEED = 155 * TARGET_RATE  # Base motor speed at target rate.
MIN_SPEED = INITIAL_SPEED / 1.33
MAX_SPEED = INITIAL_SPEED * 1.33
ADJUSTMENT_STEP = TARGET_RATE * 5 # Speed change step +/- in degrees.
# --- Anti Blocking System Configuration. Change these depending on your MOC ---
BLOCKED_THRESHOLD_DEGREES =     5 # If less than this, blocking is assumed
UNBLOCK_REVERSE_DEGREES   =    45 # How many degrees to move back to resolve blocking?
UNBLOCK_SPEED             =  -200 # ... at which speed to reverse?
# --- Monitoring and Detection Parameters. Change these depending on your MOC ---
CHECK_INTERVAL_MS   = 100
AVG_INTERVAL_SEC    = 5
BALL_THRESHOLD      = 8
BALL_COOLDOWN_MS    = 100

# --- Derived Tolerance Bounds ---
TARGET_RATE_LOWER   = TARGET_RATE - (TARGET_RATE * TARGET_TOLERANCE)
TARGET_RATE_UPPER   = TARGET_RATE + (TARGET_RATE * TARGET_TOLERANCE)

FAILURE_MODES = [
    ("JAM", 0),
    ("STARVATION", MIN_SPEED/2),
    ("BURST", MAX_SPEED*2),
]

# Init peripherals
hub = PrimeHub(broadcast_channel=None)
motor = Motor(Port.A)
sensor = ColorSensor(Port.C)

# Init ABS
block_watch = StopWatch()
last_angle = motor.angle()
BLOCK_CHECK_INTERVAL_MS = 1000

# Initial Motor Speed
last_normal_motor_speed = motor_speed = INITIAL_SPEED
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

def pick_failure_mode():
    return urandom.choice(FAILURE_MODES)

last_displayed_target_rate = None
last_displayed_total_avg_rate = None
# Start in NORMAL mode
mode = "NORMAL"
# Init failure timer & stats collection only when FAILURE_PROBABILITY > 0
if FAILURE_PROBABILITY > 0:
    mode_start = StopWatch()
    next_duration = NORMAL_DURATION_MS
    stats = {m[0] if isinstance(m, tuple) else m: {"count": 0, "duration": 0} for m in ["NORMAL"] + FAILURE_MODES}
    # track time spent in modes to match target share
    failure_time_accum = 0.0
    normal_time_accum = 0.0

paused = False
print(f"Starting paced NORMAL mode targeting {TARGET_RATE} balls per second @ {motor_speed} deg...")

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
        INITAL_SPEED = 155 * TARGET_RATE
        MIN_SPEED = INITAL_SPEED / 2
        MAX_SPEED = INITAL_SPEED * 2
        TARGET_RATE_LOWER = TARGET_RATE - (TARGET_RATE * TARGET_TOLERANCE)
        TARGET_RATE_UPPER = TARGET_RATE + (TARGET_RATE * TARGET_TOLERANCE)

    # Increase speed
    if Button.RIGHT in buttons:
        TARGET_RATE = TARGET_RATE + 0.05
        print(f"TARGET_RATE increased: {TARGET_RATE:.2f} bps")
        ADJUSTMENT_STEP = TARGET_RATE * 5
        INITAL_SPEED = 155 * TARGET_RATE
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

            if mode == "NORMAL":
                if cycle_avg_rate > TARGET_RATE_UPPER:
                    motor_speed = max(MIN_SPEED, motor_speed - ADJUSTMENT_STEP)
                elif cycle_avg_rate < TARGET_RATE_LOWER:
                    motor_speed = min(MAX_SPEED, motor_speed + ADJUSTMENT_STEP)

                last_normal_motor_speed = motor_speed
                motor.run(motor_speed)

            print(f"CR: {cycle_avg_rate:.2f} bps | 60sAR: {bpm_avg_rate:.2f} bps | TAR: {total_avg_rate:.3f} bps ({total_avg_rate/TARGET_RATE*100:.2f}%) | TR: {TARGET_RATE_LOWER:.2f}<{TARGET_RATE:.2f}<{TARGET_RATE_UPPER:.2f} bps) | NCS: {motor_speed} deg/s | AS: {motor.angle()/total_time:.0f} deg/s | TT: {total_time:.1f}s | TB: {total_balls}")

            cycle_balls = 0
            cycle_time = 0.0

        if bpm_time >= 60:
            bpm_avg_rate = bpm_balls / bpm_time
            if bpm_avg_rate > TARGET_RATE_UPPER:
                hub.light.on(Color.RED)
                if bpm_avg_rate > 2 * TARGET_RATE_UPPER:
                    hub.light.blink(Color.RED, [500, 500])
            elif bpm_avg_rate < TARGET_RATE_LOWER:
                hub.light.on(Color.BLUE)
                if bpm_avg_rate < TARGET_RATE_LOWER / 2:
                    hub.light.blink(Color.BLUE, [500, 500])
            else:
                hub.light.on(Color.GREEN)
            bpm_balls = 0
            bpm_time = 0.0

    # Failure simulation
    # Execute this block only when FAILURE_PROBABILITY > 0
    if FAILURE_PROBABILITY > 0:
        if mode_start.time() >= next_duration:
            # Update stats
            stats[mode]["count"] += 1
            stats[mode]["duration"] += mode_start.time() / 1000
            chunk_ms = mode_start.time()
            mode_start.reset()
            # Accumulate time by category
            if mode == "NORMAL":
                normal_time_accum += chunk_ms
            else:
                failure_time_accum += chunk_ms
            total_run_time = failure_time_accum + normal_time_accum
            failure_ratio = (failure_time_accum / total_run_time) if total_run_time > 0 else 0.0

            # Decide next mode to steer toward target share
            if failure_ratio < FAILURE_PROBABILITY:
                next_mode, speed = pick_failure_mode()
                next_duration = urandom.randint(FAILURE_MIN_MS, FAILURE_MAX_MS)
            else:
                next_mode = "NORMAL"
                speed = last_normal_motor_speed
                next_duration = NORMAL_DURATION_MS

            mode = next_mode
            if mode == "JAM":
                motor.stop()
                hub.light.on(Color.RED)
            else:
                motor_speed = speed
                motor.run(motor_speed)
                if mode == "BURST":
                    hub.light.on(Color.ORANGE)
                elif mode == "STARVATION":
                    hub.light.on(Color.BLUE)
                else:
                    hub.light.on(Color.GREEN)

            print(f"\n--- MODE SWITCH ---")
            print(f"\nNow simulating: {mode} for {next_duration/1000:.1f}s | Failure ratio: {failure_ratio:.2%}")
            print(f"Total balls detected: {total_balls}")
            # Calculate total runtime from stats
            total_mode_time = sum(s["duration"] for s in stats.values())
            for m in stats:
                s = stats[m]
                percent = (s["duration"] / total_mode_time * 100) if total_mode_time > 0 else 0
                print(f"  {m:<11} | Count: {s['count']:2d} | Total Time: {s['duration']:10.1f}s | {percent:5.1f}%")

    # Anti Blocking System
    if not paused and block_watch.time() >= BLOCK_CHECK_INTERVAL_MS and mode != "JAM":
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
