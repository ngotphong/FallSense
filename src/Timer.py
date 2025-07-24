# coding=utf-8
from threading import Thread, Event  # Threading components
import time                          # Time functions

class Timer(Thread):
    """
    # Call a _function after a specified number of seconds:
    t = timer.Timer("repeat_th", False, 5.0, quick_test, "repeat", args=[], kwargs={})
    t.start()
    # reset the timer
    t.reset()
    # stop the timer"s action if it"s still waiting
    t.cancel()
    """

    def __init__(self, function, name, args=(), kwargs={}, daemon=True, type="before", interval=0, forever=False):
        # Initialize thread with name and daemon status
        Thread.__init__(self, name=name, daemon=daemon)
        # Store interval (time in seconds)
        self._interval = interval
        # Store function to call
        self._function = function
        # Type of timer: "before", "after", or "repeat"
        self._type = type
        # Arguments to pass to the function
        self._args = args
        self._kwargs = kwargs
        # Event to signal when timer is finished or reset
        self._finished = Event()
        # Flag to track if timer was reset
        self._resetted = True
        # Flag to track if timer was canceled
        self._canceled = False
        # Flag to run timer forever
        self._forever = forever

    # Cancel the timer
    def cancel(self):
        self._canceled = True
        self._finished.set()

    # Main thread execution
    def run(self):
        # Choose execution mode based on type
        if self._type == "before":
            self._run_before()
        elif self._type == "after":
            self._run_after()
        elif self._type == "repeat":
            self._run_repeat()

    # Reset the timer with optional new interval
    def reset(self, interval=None):
        if interval:
            self._interval = interval
        self._resetted = True
        self._finished.set()
        self._finished.clear()

    # Execute function before waiting
    def _run_before(self):
        if not self._finished.isSet():
            # Call the function immediately
            self._function(*self._args, **self._kwargs)
        while self._resetted:
            self._resetted = False
            # Wait for interval
            self._finished.wait(self._interval)

    # Execute function after waiting
    def _run_after(self):
        while self._resetted:
            self._resetted = False
            # Wait for interval
            self._finished.wait(self._interval)
        if not self._finished.isSet():
            # Call the function after waiting
            self._function(*self._args, **self._kwargs)

    # Execute function repeatedly at interval
    def _run_repeat(self):
        while not self._finished.isSet():
            # Wait for interval
            self._finished.wait(self._interval)
            # Call function if not canceled
            if self._canceled == False:
                self._function(*self._args, **self._kwargs)