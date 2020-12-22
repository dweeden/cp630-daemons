import time
import mysql.connector
from mysql.connector import Error
import RPi.GPIO as GPIO

LOOP_SLEEP = 0.5
PIN_LIST = [3, 4, 17, 27, 22, 10, 9, 11]
DATABASE_HOST = "localhost"
DATABASE_NAME = "worker"
DATABASE_USER = "cp630"
DATABASE_PASSWORD = "cp630"
MOST_RECENT_STATE_CHANGE_REQUEST_QUERY = "select * from relay_setting order by created_at desc limit 1"

# initialize pins to off
GPIO.setmode(GPIO.BCM)
GPIO.setup(PIN_LIST, GPIO.OUT)
GPIO.output(PIN_LIST, GPIO.HIGH)

cursor = None
connection = None
lastPattern = ""
try:

    # connect to database
    connection = mysql.connector.connect(host=DATABASE_HOST, database=DATABASE_NAME, user=DATABASE_USER, password=DATABASE_PASSWORD, auth_plugin='mysql_native_password')

    if connection.is_connected():
        print("Connected to worker database")

        # open cursor and update transaction isolation level so we can see results from other processes
        cursor = connection.cursor()
        cursor.execute("set session transaction isolation level read committed")

        while True:

            # fetch most recent state change request
            cursor.execute(MOST_RECENT_STATE_CHANGE_REQUEST_QUERY)
            mostRecentSCR = cursor.fetchone()

            if mostRecentSCR is not None:
                pattern = mostRecentSCR[3]
                if pattern != lastPattern:
                    # determine on/off lists
                    on = []
                    off = []
                    for i in range(0, 8):
                        if pattern[i] == "1":
                            on.append(PIN_LIST[i])
                        else:
                            off.append(PIN_LIST[i])

                    # set relay states, applying off list first to minimize the
                    # chance of two incompatible things being on simultaneously
                    # NOTE: relay board is active low
                    print(f"Updating relay states to -> { pattern }")
                    GPIO.output(off, GPIO.HIGH)
                    GPIO.output(on, GPIO.LOW)

                    # save last pattern to reduce unnecessary calls to gpio
                    lastPattern = pattern

            time.sleep(LOOP_SLEEP)

    else:
        print("Couldn't connect to to worker database")

except Error as e:
    print("Exception encountered")
    print(e)

finally:
    # cleanup
    print("Cleaning up")
    if cursor is not None:
        cursor.close()
    if connection is not None and connection.is_connected():
        connection.close()
    GPIO.output(PIN_LIST, GPIO.HIGH)
    GPIO.cleanup()

print("Script has completed")