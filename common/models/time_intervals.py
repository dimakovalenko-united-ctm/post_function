#!/usr/bin/env python
from enum import Enum

class TimeInterval(str, Enum):
    MILLISECOND = 'millisecond'
    SECOND = 'second'
    MINUTE = 'minute'
    HOUR = 'hour'
