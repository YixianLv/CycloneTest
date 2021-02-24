from pycdr import cdr
from enum import Enum

@cdr
class TemperatureScale(Enum):
  CELSIUS = 1
  FAHERENHEIT = 2
  KELVIN = 3

@cdr 
class TempSensor:
    id: int
    temp: float
    hum: float
    scale: TemperatureScale
    time_stamp: str