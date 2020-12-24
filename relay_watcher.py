import re
import signal
import sys
import time
from datetime import datetime

import RPi.GPIO as GPIO
import mysql.connector

POLLING_INTERVAL = 1
ACTIVE_LOW = True
FULL_PIN_LIST = [3, 4, 17, 27, 22, 10, 9, 11]
STATES_VALIDATION_REGEX = "^[01_]{8}$"
DATABASE_HOST = "localhost"
DATABASE_NAME = "worker"
DATABASE_USER = "cp630"
DATABASE_PASSWORD = "cp630"
MOST_RECENT_RELAY_SETTINGS_RECORD_SELECT_COMMAND = "select * from relay_setting order by created_at desc limit 1"
MOST_RECENT_RELAY_SETTINGS_RECORD_UPDATE_COMMAND = "update relay_setting set processed_at = %s where id = %s"


def signal_handler(sig, frame):
    print('Script terminating')
    sys.exit(0)


# register for clean exit
signal.signal(signal.SIGINT, signal_handler)

# initialize and set pins to off
GPIO.setmode(GPIO.BCM)
GPIO.setup(FULL_PIN_LIST, GPIO.OUT)
GPIO.output(FULL_PIN_LIST, GPIO.HIGH if ACTIVE_LOW else GPIO.LOW)

cursor = None
connection = None
lastPattern = ""
try:

    # connect to database
    connection = mysql.connector.connect(host=DATABASE_HOST, database=DATABASE_NAME, user=DATABASE_USER,
                                         password=DATABASE_PASSWORD, auth_plugin='mysql_native_password')

    if connection.is_connected():
        print("Connected to worker database")

        # open cursor and update transaction isolation level so we can see results from other processes
        cursor = connection.cursor(dictionary=True)
        cursor.execute("set session transaction isolation level read committed")

        # main relay watcher loop
        print("Starting main relay watcher loop")
        while True:

            # fetch most recent relay settings record
            cursor.execute(MOST_RECENT_RELAY_SETTINGS_RECORD_SELECT_COMMAND)
            mostRecentRSR = cursor.fetchone()

            if mostRecentRSR is not None:

                # fetch pattern and validate
                pattern = mostRecentRSR["states"]
                if pattern is None:
                    raise Exception("Empty pattern value")
                elif not re.search(STATES_VALIDATION_REGEX, pattern):
                    raise Exception(f"Illegal pattern {pattern}")

                if pattern != lastPattern:
                    # construct on/off lists
                    onList = []
                    offList = []
                    for i in range(0, 8):
                        if pattern[i] == "0":
                            offList.append(FULL_PIN_LIST[i])
                        elif pattern[i] == "1":
                            onList.append(FULL_PIN_LIST[i])

                    # set relay states, applying off list first to minimize the
                    # chance of two incompatible things being on simultaneously
                    print(f"Updating relay states to -> {pattern}")
                    GPIO.output(offList, GPIO.HIGH if ACTIVE_LOW else GPIO.LOW)
                    GPIO.output(onList, GPIO.LOW if ACTIVE_LOW else GPIO.HIGH)

                    if mostRecentRSR["processed_at"] is None:
                        # update processed time
                        cursor.execute(MOST_RECENT_RELAY_SETTINGS_RECORD_UPDATE_COMMAND,
                                       (datetime.now(), mostRecentRSR["id"]))
                        connection.commit()

                    # save last pattern to allow for reducing unnecessary calls to gpio
                    lastPattern = pattern

            # sleep
            time.sleep(POLLING_INTERVAL)

    else:
        print("Couldn't connect to to worker database")

except Exception as error:
    print(f'Exception = {error.args[0]}')

finally:
    # cleanup
    print("Cleaning up")
    if cursor is not None:
        cursor.close()
    if connection is not None and connection.is_connected():
        connection.close()
    GPIO.output(FULL_PIN_LIST, GPIO.HIGH if ACTIVE_LOW else GPIO.LOW)
    GPIO.cleanup()

print("Script has completed")
