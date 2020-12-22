import time
import mysql.connector
from mysql.connector import Error
import RPi.GPIO as GPIO

DELAY = 0.5
PIN_LIST = [3, 4, 17, 27, 22, 10, 9, 11]
MOST_RECENT_STATE_CHANGE_REQUEST_QUERY = "select * from relay_setting order by created_at desc limit 1"
DATABASE_HOST = "localhost"
DATABASE_NAME = "worker"
DATABASE_USER = "cp630"
DATABASE_PASSWORD = "cp630"

GPIO.setmode(GPIO.BCM)
GPIO.setup(PIN_LIST, GPIO.OUT)
GPIO.output(PIN_LIST, GPIO.HIGH)

connection = None
cursor = None
lastPattern = ""
try:
    connection = mysql.connector.connect(host=DATABASE_HOST, database=DATABASE_NAME, user=DATABASE_USER, password=DATABASE_PASSWORD)
    if connection.is_connected():
        print('Connected to worker database')

        # open cursor and update transaction isolation level so we can see results from others
        cursor = connection.cursor()
        cursor.execute("set session transaction isolation level read committed")

        while True:

            # fetch most recent state change request
            cursor.execute(MOST_RECENT_STATE_CHANGE_REQUEST_QUERY)
            mostRecent = cursor.fetchone()

            if mostRecent is not None:
                pattern = mostRecent[3]
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
                    print(f"updating relay states to -> {pattern}")
                    GPIO.output(off, GPIO.HIGH)
                    GPIO.output(on, GPIO.LOW)

                    # save last pattern to reduce unnecessary calls to gpio
                    lastPattern = pattern

            time.sleep(DELAY)
    else:
        print("Couldn't connect to to worker database")

except Error as e:
    print(e)

finally:
    # cleanup
    if cursor is not None:
        cursor.close()
    if connection is not None and connection.is_connected():
        connection.close()
    GPIO.output(PIN_LIST, GPIO.HIGH)
    GPIO.cleanup()