#!/usr/bin/python

import scipy.optimize as optimization
import numpy as np
import matplotlib.pyplot as plt
import pylab


inf = float('inf')


# Reads measurement file (CSV) into two numpy arrays.
# Expects and returns time seconds.
def read_measurement_array(infile):
  t = list()
  U_Batt = list()
  with open(infile, "r") as rfile:
    for line in rfile:
      if not line.strip(): continue
      fields = line.split(',');        
      t.append(float(fields[0]))
      U_Batt.append(float(fields[1]))
  return np.array(t), np.array(U_Batt)


# Saves two float numpy arrays as CSV.

def save_measurement_array(outfile, xdata, ydata):
  with open(outfile, "w") as wfile:
    for x,y in np.c_[xdata,ydata]:
      wfile.write("%f,%f\n" % (x,y))


# Extract starting voltage by averaging the first n time units of measurement
# conducted without load.
# Expects time in same units.   
def get_starting_voltage(t, U_Batt, n):
  _, y = get_interval(t, U_Batt, 0, n)
  return np.mean(np.array(y))


# Get time at which the cutoff voltage is reached.    
def get_cutoff_time(t, U_Batt, U_cutoff):   
  i = 0
  while True:
    if U_Batt[i] < U_cutoff: return t[i]
    i += 1
    if i == len(t): return t[i-1]


# Get interval from start time to end time.
# Expects time same units.
def get_interval(t, U_Batt, start, end = inf):
  assert start < end
  assert start >= 0
  i = 0
  istart = 0
  iend = len(t)
  while True:
    if t[i] >= start:
      istart = i
      break
    i += 1
  while True:
    if i == iend: break
    if t[i] > end:
      iend = i - 1
      break
    i += 1
  return t[istart:iend] - start, U_Batt[istart:iend] 


# Returns drawn charge in mAs during given measurement interval.
# Expects time (t) in seconds.
def get_used_capacity_in_interval(t, U_Batt, R): # [mAs]
  C = 0.0
  last_t = 0
  for i in range(len(t)):
    step = t[i] - last_t
    last_t = t[i]
    
    U = U_Batt[i]
    I = (U * 1000.0) / float(R) # [mA]
    
    C += I  * step # [mAs]
  return C


# Get nominal capacity from power drawn during discharge phases
def get_nominal_capacity(t, U_Batt, T_ON, T_OFF, nr_of_intervals, R):
  C = 0.0
  
  # full discharge phases
  for i in range(int(nr_of_intervals)):
    U_cutoff = i * (T_ON+T_OFF)
    td = U_cutoff + T_ON
    tr = td + T_OFF
     
    x, y = get_interval(t, U_Batt, U_cutoff, td)
    C_interval = get_used_capacity_in_interval(x, y, R)
    C += C_interval
  
  # remaining discharge until t_cutoff
  U_cutoff = nr_of_intervals * (T_ON + T_OFF)
  x, y = get_interval(t, U_Batt, U_cutoff, inf)
  C_remaining = get_used_capacity_in_interval(x, y, R)  
  C += C_remaining
    
  return C
   
   
# Function used to fit the U_Batt relaxation curve.
# Expects time (t) in seconds.
def relaxation_curve(t, a, b, c, d, e):
  # return a * (np.exp(b * t)) -c * (np.exp(-d * t))
  # return a * (1 - np.exp(-b * t)) + c * (1 - np.exp(-d * t))
  return  a - b * (np.exp(-c * t)) - d * (np.exp(-e * t))


# Exponential polynomials used to fit the parameter params  
def expfunc(SOC, p):
  p = np.array(p)
  p = np.pad(p, (0,10 - p.shape[0]), 'constant', constant_values=(0,0))
  return p[0]*np.exp(-p[1]*SOC) + p[2] + p[3]*SOC + p[4]*np.power(SOC,2) + p[5]*np.power(SOC,3) + p[6]*np.power(SOC,4) + p[7]*np.power(SOC,5) + p[8]*np.power(SOC,6) + p[9]*np.power(SOC,7)  

def expfunc3(SOC, p0, p1, p2):
  return expfunc(SOC, [p0, p1, p2])

def expfunc4(SOC, p0, p1, p2, p3):
  return expfunc(SOC, [p0, p1, p2, p3])
  
def expfunc5(SOC, p0, p1, p2, p3, p4):
  return expfunc(SOC, [p0, p1, p2, p3, p4])

def expfunc6(SOC, p0, p1, p2, p3, p4, p5):
  return expfunc(SOC, [p0, p1, p2, p3, p4, p5])

def expfunc7(SOC, p0, p1, p2, p3, p4, p5, p6):
  return expfunc(SOC, [p0, p1, p2, p3, p4, p5, p6])

def expfunc8(SOC, p0, p1, p2, p3, p4, p5, p6, p7):
  return expfunc(SOC, [p0, p1, p2, p3, p4, p5, p6, p7])

def expfunc9(SOC, p0, p1, p2, p3, p4, p5, p6, p7, p8):
  return expfunc(SOC, [p0, p1, p2, p3, p4, p5, p6, p7, p8])

def expfunc10(SOC, p0, p1, p2, p3, p4, p5, p6, p7, p8, p9):
  return expfunc(SOC, [p0, p1, p2, p3, p4, p5, p6, p7, p8, p9])

def getExpfunc(order):
  if order == 3: return expfunc3
  if order == 4: return expfunc4
  if order == 5: return expfunc5
  if order == 6: return expfunc6
  if order == 7: return expfunc7
  if order == 8: return expfunc8
  if order == 9: return expfunc9
  if order == 10: return expfunc10
  return None
  
  
# Extract circuit parameters (U_Eq, R_S, R_TS, etc.) from measurement data.
# Expects time in seconds.
def extract_parameters(filename, t_offset, C_nominal, U_cutoff,I_dis, R, T_ON, T_OFF, iota, plot = True):
  print("Extracting {}\n".format(filename))
    
  t, U_Batt = read_measurement_array(filename)
  U_start = get_starting_voltage(t, U_Batt, t_offset)
  U_start_0 = U_start
  print("U_start = {} V".format(U_start))
  # Start voltage = mean voltage in offset time

  t, U_Batt = get_interval(t, U_Batt, t_offset) # cut idle time in beginning
   
  t_cutoff = get_cutoff_time(t, U_Batt, U_cutoff)
  print("t_cutoff = {} min".format(t_cutoff / 60.0))
   
  interval_len = (T_ON + T_OFF)
  nr_intervals = round(t[-1] / interval_len)
  print("discharge intervals = {}".format(nr_intervals))
  # calculate # of intervals by total time divide total operation step time (one discharge step time + one rest step time)
   
  if C_nominal is None:
    C_nominal = get_nominal_capacity(t, U_Batt, T_ON, T_OFF, nr_intervals, R) # [mAs]
  print("C_nominal = {} mAh".format(C_nominal / 3600.0))

  U_Eq_list = list()
  R_S_list  = list()
  R_TS_list = list()
  C_TS_list = list()
  R_TL_list = list()
  C_TL_list = list()
  SOC_list = list()
  td_list = list()
  tr_list = list()
  U_Batt_td_list = list()
  U_Batt_tsd_list = list()
  U_Batt_tdiota_list = list()
 
  C_Batt = C_nominal
  
  x0 = np.array([ 3, 0.01 ,  0.02,  0.01,  0.003]) #initinal value to reduce compution cost
  
  for i in range(int(nr_intervals)):
    print("\nInterval %i:" % i)
    
    U_cutoff = i * (T_ON+T_OFF)
    td = U_cutoff + T_ON
    tr = td + T_OFF
    
    td_list.append(td)
    tr_list.append(tr)

    # calculate voltage at start discharge
    _, y = get_interval(t, U_Batt, U_cutoff, U_cutoff +10)
    U_Batt_tsd = np.mean(y)
    U_Batt_tsd_list.append(U_Batt_tsd)
    print("U_Batt(tsd) = {} V".format(U_Batt_tsd))

    # calculate voltage at finishe discharge
    _, y = get_interval(t, U_Batt, td - 2, td)
    U_Batt_td = np.mean(y) # use average of a few ms for higher precision
    U_Batt_td_list.append(U_Batt_td)
    print("U_Batt(td) = {} V".format(U_Batt_td))


    # I_Batt_td = U_Batt_td / R
    R = U_Batt_td / I_dis
    print("I_Batt(td) = {} A".format(I_dis))
    print("R = {} ohm".format(R))

    # x, y = get_interval(t, U_Batt, U_cutoff, td)
    # C_interval = get_used_capacity_in_interval(x, y, R)
    C_interval = (td-U_cutoff)*I_dis*1000
    print("C_interval = {} mAh".format(C_interval / 3600.0)) 
     
    C_Batt -= C_interval
    print("new C_Batt = {} mAh".format(C_Batt / 3600.0))
     
    SOC = C_Batt / C_nominal
    SOC_list.append(SOC)
    print("new SOC = {} %".format(SOC) )
     

    
    _, y = get_interval(t, U_Batt, td + iota, td + 10)
    U_Batt_tdiota = np.mean(y) # use average of a few ms for higher precision
    U_Batt_tdiota_list.append(U_Batt_tdiota)
    print("U_Batt(td+i) = {} V".format(U_Batt_tdiota))
     

    R_S_1 = (U_start - U_Batt_tsd) / I_dis
    R_S_2 = (U_Batt_tdiota - U_Batt_td) / I_dis
    R_S = np.mean([R_S_1,R_S_2])
    R_S_list.append(R_S)
    print("R_S = {} Ohm".format(R_S))

    U_start = get_starting_voltage(t, U_Batt, tr)
    print("U_start = {} V".format(U_start))


    print("Exponential curve fitting...")
    x, y = get_interval(t, U_Batt, td + 10, tr)
    save_measurement_array("plots/interval/interval-{}-points.csv".format(i), x, y- U_Batt_tdiota)

    p, _ = optimization.curve_fit(relaxation_curve, x, y, maxfev=100000, p0=x0)
    x0 = p
    
    U_Eq = p[0]
    U_Eq_list.append(U_Eq)
    print("U_Eq = {} V".format(U_Eq))
    
    R_TS = p[1] * I_dis
    R_TS_list.append(R_TS)
    print("R_TS = {} Ohm".format(R_TS))
    
    R_TL = p[3] * I_dis
    R_TL_list.append(R_TL)
    print("R_TL = {} Ohm".format(R_TL))
     
    C_TS = 1.0 / float(R_TS * p[2])
    C_TS_list.append(C_TS)    
    print("C_TS = {} F".format(C_TS))
    
    C_TL = 1.0 / float(R_TL * p[4])
    C_TL_list.append(C_TL)
    print("C_TL = {} F".format(C_TL))
    
    if plot:
      plt.xlabel('t - td [s]')
      plt.ylabel('U [V]')
      pylab.plot(x, y, 'b.')
      pylab.plot(x, relaxation_curve(x, p[0], p[1], p[2], p[3]) + U_Batt_tdiota, 'r')
      pylab.show()
  
  if True:
    plt.xlabel('t [s]')
    plt.ylabel('U [V]')
    plt.plot(t, U_Batt, 'y-', label='U_Batt-obs.')
    plt.plot(td_list, U_Batt_td_list, 'r-', label="U_Batt(td)")
    plt.plot(td_list, U_Batt_tdiota_list, 'g-', label="U_Batt(td+i)")
    plt.plot(np.concatenate((np.array([0]), np.array(tr_list)), axis=0),\
           np.concatenate((np.array([U_start_0]), np.array(U_Eq_list)), axis=0),\
           'b-', label="U_Eq")
    plt.legend()
    plt.savefig("plots/SOC-OCV.png")
    plt.show()
      
  return U_start_0, C_nominal / 3600.0, {
    "U_Eq": np.array(U_Eq_list),
    "R_S":  np.array(R_S_list),
    "R_TS": np.array(R_TS_list),
    "C_TS": np.array(C_TS_list),
    "R_TL": np.array(R_TL_list),
    "C_TL": np.array(C_TL_list),
    "SOC": np.array(SOC_list),
  }


def poly_string(name, p):
  s = '    {} ='.format(name)
  degree = len(p) - 1
  i = degree
  for x in p:
    sign = '+' if x >= 0 else '-'
    x = abs(x)
    if i > 0:
      s += ' {} {}*SOC{}'.format(sign, x, i)
    else:
      s += ' {} {}\n'.format(sign, x)
    i -= 1
  return s, degree
 
 
def exp_poly_string(name, p):
  assert len(p) > 2
  s = '    {} = {}*exp({}*SOC1)'.format(name, p[0], -p[1])
  degree = len(p) - 3
  i = 0
  for x in p[2:]:
    sign = '+' if x >= 0 else '-'
    x = abs(x)
    if i > 0:
      s += ' {} {}*SOC{}'.format(sign, x, i)
    else:
      s += ' {} {}'.format(sign, x)
    i += 1
  return s + '\n', degree  


def soc_string(degree):
  s = ''
  for i in range(degree-1):
    s += '    SOC{} = SOC{} * SOC1\n'.format(i+2, i+1)
  return s


# Fit model functions to extracted parameter data.
# The result is the string of a python function taking the SOC value and 
# returning the current parameter values.
def fit_model_functions(U_start, U_cutoff, params, poly, orders, x0, plot = True):
  xdata_hires = np.linspace(1, 0, num=1000)

  s = ""
  max_degree = 0
  
  ##############################################################################
  name = "U_Eq" 
  print("Fitting %s..." % name)
  
  xdata = np.concatenate((np.array([1.0]),     params["SOC"]), axis=0)
  ydata = np.concatenate((np.array([U_start]), params[name]), axis=0)
  
  if U_cutoff is not None:
    xdata = np.concatenate((xdata, np.array([0.0])), axis=0)
    ydata = np.concatenate((ydata, np.array([U_cutoff])), axis=0)
  
  if poly[name]:
    p = np.polyfit(xdata, ydata, orders[name])
    ploty = np.poly1d(p)(xdata_hires) 
    tmp, degree = poly_string(name, p)
  else:
    p, _ = optimization.curve_fit(getExpfunc(orders[name]), xdata, ydata, maxfev=100000, p0=x0[name])
    ploty = expfunc(xdata_hires, p)
    tmp, degree = exp_poly_string(name, p)
    
  s += tmp
  if degree > max_degree: max_degree = degree
  
  if plot: 
    pylab.plot(xdata, ydata, 'b.')
    pylab.plot(xdata_hires, ploty, 'r')
    pylab.title('SOC-OCV')
    pylab.show()
    pylab.clf()
    
    save_measurement_array("plots/{}-points.csv".format(name), xdata * 100, ydata)
    save_measurement_array("plots/{}-func.csv".format(name), xdata_hires * 100, ploty)

  xdata = params["SOC"]
  
  ##############################################################################
  name = "R_S" 
  print("Fitting %s..." % name)
  
  ydata = params[name]
  if poly[name]:
    p = np.polyfit(xdata, ydata, orders[name])
    ploty = np.poly1d(p)(xdata_hires) 
    tmp, degree = poly_string(name, p) 
  else:
    p, _ = optimization.curve_fit(getExpfunc(orders[name]), xdata, ydata, maxfev=100000, p0=x0[name])
    ploty = expfunc(xdata_hires, p)
    tmp, degree = exp_poly_string(name, p)
    
  s += tmp
  if degree > max_degree: max_degree = degree

  pylab.plot(xdata, ydata, 'b.')
  pylab.plot(xdata_hires, ploty, 'r')
  pylab.title('SOC-R_S')
  pylab.savefig("plots/R_S.png")
  if plot: pylab.show()

  pylab.clf()
  save_measurement_array("plots/{}-points.csv".format(name), xdata * 100, ydata)
  save_measurement_array("plots/{}-func.csv".format(name), xdata_hires * 100, ploty)

  ##############################################################################
  name = "R_TS" 
  print("Fitting %s..." % name)
  
  ydata = params[name]
  if poly[name]:
    p = np.polyfit(xdata, ydata, orders[name])
    ploty = np.poly1d(p)(xdata_hires) 
    tmp, degree = poly_string(name, p)
  else:
    p, _ = optimization.curve_fit(getExpfunc(orders[name]), xdata, ydata, maxfev=100000, p0=x0[name])
    ploty = expfunc(xdata_hires, p)
    tmp, degree = exp_poly_string(name, p)
  
  s += tmp
  if degree > max_degree: max_degree = degree
  
  if plot: 
    pylab.plot(xdata, ydata, 'b.')
    pylab.plot(xdata_hires, ploty, 'r')
    pylab.title('SOC-R_TS')
    pylab.savefig("plots/R_TS.png")
    pylab.show()

    pylab.clf()
    
    save_measurement_array("plots/{}-points.csv".format(name), xdata * 100, ydata)
    save_measurement_array("plots/{}-func.csv".format(name), xdata_hires * 100, ploty)

  ##############################################################################
  name = "C_TS" 
  print("Fitting %s..." % name)
  
  ydata = params[name]
  if poly[name]:
    p = np.polyfit(xdata, ydata, orders[name])
    ploty = np.poly1d(p)(xdata_hires) 
    tmp, degree = poly_string(name, p)
  else:
    p, _ = optimization.curve_fit(getExpfunc(orders[name]), xdata, ydata, maxfev=100000, p0=x0[name])
    ploty = expfunc(xdata_hires, p)
    tmp, degree = exp_poly_string(name, p)
  
  s += tmp
  if degree > max_degree: max_degree = degree
  
  if plot: 
    pylab.plot(xdata, ydata, 'b.')
    pylab.plot(xdata_hires, ploty, 'r')
    pylab.title('SOC-C_TS')
    pylab.savefig("plots/C_TS.png")
    pylab.show()

    pylab.clf()
    
    save_measurement_array("plots/{}-points.csv".format(name), xdata * 100, ydata)
    save_measurement_array("plots/{}-func.csv".format(name), xdata_hires * 100, ploty)

  ##############################################################################
  name = "R_TL" 
  print("Fitting %s..." % name)
  
  ydata = params[name]
  if poly[name]:
    p = np.polyfit(xdata, ydata, orders[name])
    ploty = np.poly1d(p)(xdata_hires) 
    tmp, degree = poly_string(name, p)
  else:
    p, _ = optimization.curve_fit(getExpfunc(orders[name]), xdata, ydata, maxfev=100000, p0=x0[name])
    ploty = expfunc(xdata_hires, p)
    tmp, degree = exp_poly_string(name, p)
  
  s += tmp
  if degree > max_degree: max_degree = degree
  
  if plot: 
    pylab.plot(xdata, ydata, 'b.')
    pylab.plot(xdata_hires, ploty, 'r')
    pylab.title('SOC-R_TL')
    pylab.savefig("plots/R_TL.png")
    pylab.show()
    pylab.clf()
    
    save_measurement_array("plots/{}-points.csv".format(name), xdata * 100, ydata)
    save_measurement_array("plots/{}-func.csv".format(name), xdata_hires * 100, ploty)

  ##############################################################################
  name = "C_TL" 
  print("Fitting %s..." % name)
  
  ydata = params[name]
  if poly[name]:
    p = np.polyfit(xdata, ydata, orders[name])
    ploty = np.poly1d(p)(xdata_hires) 
    tmp, degree = poly_string(name, p)
  else:
    p, _ = optimization.curve_fit(getExpfunc(orders[name]), xdata, ydata, maxfev=100000, p0=x0[name])
    ploty = expfunc(xdata_hires, p)
    tmp, degree = exp_poly_string(name, p)
 
  s += tmp
  if degree > max_degree: max_degree = degree
 
  if plot: 
    pylab.plot(xdata, ydata, 'b.')
    pylab.plot(xdata_hires, ploty, 'r')
    pylab.title('SOC-C_TL')
    pylab.savefig("plots/C_TL.png")
    pylab.show()

    pylab.clf()
    
    save_measurement_array("plots/{}-points.csv".format(name), xdata * 100, ydata)
    save_measurement_array("plots/{}-func.csv".format(name), xdata_hires * 100, ploty)
  
  s = soc_string(max_degree) + s
  s = "  def getCircuitParams(self, SOC1):\n" + s
  return s + "    return U_Eq, R_S, R_TS, C_TS, R_TL, C_TL"
  

def print_lipo_model():
  # General battery and measurement parameters:
  # -------------------------------------------

  filename = "./measurements/RW9/cycle-3.csv"
  
  U_cutoff = 3.2 # [V]
  R = 24.8 # [Ohm]
  I_dis = 1 #[A]
  T_ON = 600 # [s]
  T_OFF = 1200 # [s]
  t_offset = 1200 # [s]

  iota = 0.005 # [s]
  C_norminal = 2.0961*3600000 # [mAs]
  # Extract circuit parameters for every discharge interval:
  # --------------------------------------------------------  
  
  U_start, C_nominal, params = extract_parameters(filename, t_offset, C_norminal, U_cutoff, I_dis, R, T_ON, T_OFF, iota, False)

  # Slightly modify last two C_TS points, so that fitted curve doesn't drop 
  # below zero for SOC > 0
  params["C_TS"][-2:] = params["C_TS"][-2:] + 200 
  
  
  # Fit model functions and print model as ready-to-use Battery class:
  # -----------------------------------------------------------------
  
  poly = { # type of polynomial (true = regular, false = expfunc)
    "U_Eq": False,
    "R_S" : True,
    "R_TS": False,
    "C_TS": False,
    "R_TL": False,
    "C_TL": False
  }
  
  orders = { # order of polynomial
    "U_Eq": 6,
    "R_S" : 4,
    "R_TS": 5,
    "C_TS": 5,
    "R_TL": 5,
    "C_TL": 5
  }
  
  x0 = { # start parameters for function fitting if needed
    "U_Eq": None,
    "R_S" : None,#np.array([1.0, 10.0, 0.0]),
    "R_TS": None,
    "C_TS": None,
    "R_TL": None,
    "C_TL": None,
  }
  
  s = '\nclass LiPo(Battery):\n'
  s += '  def getC_nominal(self): return {}\n'.format(C_nominal)
  s += '  def getU_cutoff(self): return {}\n'.format(U_cutoff)
  s += fit_model_functions(U_start, U_cutoff, params, poly, orders, x0, True)
  s += '\n'
  print(s)

  
  
if __name__ == "__main__":
  print_lipo_model()
  #print_alkaline_model()
  
  

  
