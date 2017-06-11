import sys, math
import numpy as np

class CSV:
  def load2(filename, step = None):
    print("loading {}".format(filename))
    A = list()
    B = list()
    next = 0
    with open(filename, "r") as rfile:
      for line in rfile:
        fields = line.split(',');  
        if len(fields) < 2: continue   
        a = float(fields[0])
        b = float(fields[1])
      
        if step is not None:
          if a >= next: next += step
          else: continue
        
        A.append(a)
        B.append(b)
    return np.array(A), np.array(B)


  def load3(filename, step = None):
    print("loading {}".format(filename))
    A = list()
    B = list()
    C = list()
    next = 0
    with open(filename, "r") as rfile:
      for line in rfile:
        fields = line.split(',');  
        if len(fields) < 3: continue   
        a = float(fields[0])
        b = float(fields[1])
        c = float(fields[2])
      
        if step is not None:
          if a >= next: next += step
          else: continue
        
        A.append(a)
        B.append(b)
        C.append(c)
    return np.array(A), np.array(B), np.array(C)


  def saveX(filename, data):    
    print("saving {}".format(filename)) 
    with open(filename, "w") as wfile: 
      for i in range(len(data[0])):
        line = ', '.join("{}".format(d[i]) for d in data)  
        wfile.write("{}\n".format(line))
