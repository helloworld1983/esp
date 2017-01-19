#!/usr/bin/python3

from tkinter import *
from tkinter import messagebox
import os.path

from NoCConfiguration import *

class Components():

  EMPTY = [
  "empty",
  ]
  PROCESSORS = [
  "cpu",
  ]
  MISC = [
  "IO",
  ]
  MEM = [
  "mem_dbg",
  "mem_lite",
  ]
  ACCELERATORS = [
  ]

  def __init__(self):
    with open("../common/tile_acc.vhd") as fp:
      for line in fp:
        if line.find("if device") != -1:
           line = line[line.find("SLD_")+4:]
           line = line[:line.find("generate")]
           line = line.strip()
           self.ACCELERATORS.append(line)

#board configuration
class SoC_Config():
  HAS_FPU = "0"
  HAS_JTAG = False
  HAS_ETH = False
  HAS_SG = False
  HAS_SGMII = True
  HAS_SVGA = False
  IP_ADDR = ""
  IPs = Components()

  def read_config(self, temporary):
    filename = ".esp_config"
    warning = False
    if temporary == True:
      filename = ".esp_config.bak"
      warning = True
      if os.path.isfile(filename) == False:
        filename = ".esp_config"
        warning = False
        if os.path.isfile(filename) == False:
          return -1
    if os.path.isfile(filename) == False:
      print("Configuration file is not available")
      return -1
    if warning:
      first = True
      if os.path.isfile(".esp_config") == True:
        orig = open(".esp_config", 'r')
        with open(".esp_config.bak") as bak:
          for line_bak in bak:
            line_orig = orig.readline()
            if line_bak != line_orig:
              if first:
                print("WARNING: temporary configuration. Modifications are not reported into 'socmap.vhd' yet")
                first = False
              print("SAVED: " + line_orig.replace("\n","") + " -- TEMP: " + line_bak.replace("\n",""))
    fp = open(filename, 'r')
    line = fp.readline()
    if line.find("CONFIG_HAS_SG = y") != -1:
      self.transfers.set(1)
      self.HAS_SG = True
    else:
      self.transfers.set(0)
    # Topology
    line = fp.readline()
    item = line.split()
    rows = int(item[2])
    line = fp.readline()
    item = line.split()
    cols = int(item[2])
    self.noc.create_topology(self.noc.top, rows, cols)
    # Monitors
    line = fp.readline()
    if line.find("CONFIG_MON_DDR = y") != -1:
        self.noc.monitor_ddr.set(1)
    line = fp.readline()
    if line.find("CONFIG_MON_INJ = y") != -1:
        self.noc.monitor_inj.set(1)
    line = fp.readline()
    if line.find("CONFIG_MON_ROUTERS = y") != -1:
        self.noc.monitor_routers.set(1)
    line = fp.readline()
    if line.find("CONFIG_MON_ACCELERATORS = y") != -1:
        self.noc.monitor_accelerators.set(1)
    line = fp.readline()
    if line.find("CONFIG_MON_DVFS = y") != -1:
        self.noc.monitor_dvfs.set(1)
    # Tiles configuration
    for y in range(0, self.noc.rows):
      for x in range(0, self.noc.cols):
        line = fp.readline().replace("\n","")
        tile = self.noc.topology[y][x]
        tokens = line.split(' ')
        if len(tokens) > 1:
          tile.ip_type.set(tokens[4])
          tile.clk_region.set(int(tokens[5]))
          tile.has_pll.set(int(tokens[6]))
          tile.has_clkbuf.set(int(tokens[7]))
    # DVFS (skip whether it has it or not; we know that already)
    line = fp.readline()
    line = fp.readline()
    item = line.split();
    vf_points = int(item[2])
    self.noc.vf_points = vf_points
    # Power annotation
    for y in range(0, self.noc.rows):
      for x in range(0, self.noc.cols):
        line = fp.readline().replace("\n","")
        tile = self.noc.topology[y][x]
        if len(line) == 0:
          return
        tokens = line.split(' ')
        tile.create_characterization(self, self.noc.vf_points)
        if tile.ip_type.get() == tokens[2]:
          for vf in range(self.noc.vf_points):
            tile.energy_values.vf_points[vf].voltage = float(tokens[3 + vf * 3])
            tile.energy_values.vf_points[vf].frequency = float(tokens[3 + vf * 3 + 1])
            tile.energy_values.vf_points[vf].energy = float(tokens[3 + vf * 3 + 2])
    return 0

  def write_config(self):
    print("Writing backup configuration: \".esp_config.bak\"")
    fp = open('.esp_config.bak', 'w')
    has_dvfs = False;
    if self.transfers.get() == 1:
      fp.write("CONFIG_HAS_SG = y\n")
    else:
      fp.write("#CONFIG_HAS_SG is not set\n")
    fp.write("CONFIG_NOC_ROWS = " + str(self.noc.rows) + "\n")
    fp.write("CONFIG_NOC_COLS = " + str(self.noc.cols) + "\n")
    if self.noc.monitor_ddr.get() == 1:
      fp.write("CONFIG_MON_DDR = y\n")
    else:
      fp.write("#CONFIG_MON_DDR is not set\n")
    if self.noc.monitor_inj.get() == 1:
      fp.write("CONFIG_MON_INJ = y\n")
    else:
      fp.write("#CONFIG_MON_INJ is not set\n")
    if self.noc.monitor_routers.get() == 1:
      fp.write("CONFIG_MON_ROUTERS = y\n")
    else:
      fp.write("#CONFIG_MON_ROUTERS is not set\n")
    if self.noc.monitor_accelerators.get() == 1:
      fp.write("CONFIG_MON_ACCELERATORS = y\n")
    else:
      fp.write("#CONFIG_MON_ACCELERATORS is not set\n")
    if self.noc.monitor_dvfs.get() == 1:
      fp.write("CONFIG_MON_DVFS = y\n")
    else:
      fp.write("#CONFIG_MON_DVFS is not set\n")
    i = 0
    for y in range(0, self.noc.rows):
      for x in range(0, self.noc.cols):
        tile = self.noc.topology[y][x]
        selection = tile.ip_type.get()
        fp.write("TILE_" + str(y) + "_" + str(x) + " = ")
		# Tile number
        fp.write(str(i) + " ")
		# Tile type
        if self.IPs.PROCESSORS.count(selection):
          fp.write("cpu")
        elif self.IPs.MISC.count(selection):
          fp.write("misc")
        elif self.IPs.MEM.count(selection):
          if selection == "mem_dbg":
            fp.write("mem_dbg")
          else:
            fp.write("mem_lite")
        elif self.IPs.ACCELERATORS.count(selection):
          fp.write("acc")
        else:
          fp.write("empty")
		# Selected accelerator or tile type repeated
        fp.write(" " + selection)
		# Clock region info
        try:
          clk_region = tile.clk_region.get()
          fp.write(" " + str(clk_region))
          if clk_region != 0:
            has_dvfs = True;
        except:
          fp.write(" " + str(0))
        fp.write(" " + str(tile.has_pll.get()))
        fp.write(" " + str(tile.has_clkbuf.get()))
        fp.write("\n")
        i += 1
    if has_dvfs:
      fp.write("CONFIG_HAS_DVFS = y\n")
    else:
      fp.write("#CONFIG_HAS_DVFS is not set\n")
    fp.write("CONFIG_VF_POINTS = " + str(self.noc.vf_points) + "\n")
    for y in range(self.noc.rows):
      for x in range(self.noc.cols):
        tile = self.noc.topology[y][x]
        selection = tile.ip_type.get()
        fp.write("POWER_" + str(y) + "_" + str(x) + " = ")
        fp.write(selection + " ")
        if self.IPs.ACCELERATORS.count(selection) == 0:
          for vf in range(self.noc.vf_points):
            fp.write(str(0) + " " + str(0) + " " + str(0) + " ")
          fp.write("\n")
        else:
          for vf in range(self.noc.vf_points):
            fp.write(str(tile.energy_values.vf_points[vf].voltage) + " " + str(tile.energy_values.vf_points[vf].frequency) + " " + str(tile.energy_values.vf_points[vf].energy) + " ")
          fp.write("\n")

  def check_cfg(self, line, token, end):
    line = line[line.find(token)+len(token):]
    line = line[:line.find(end)]
    line = line.strip()
    return line

  def set_IP(self):
    self.IP_ADDR = str(int('0x' + self.IPM[:2], 16)) + "." + str(int('0x' + self.IPM[2:], 16)) + "." + str(int('0x' + self.IPL[:2], 16)) + "." + str(int('0x' + self.IPL[2:], 16))

  def __init__(self):
    #define whether SGMII has to be used or not: it is not used for PROFPGA boards
    with open("Makefile") as fp:
      for line in fp:
        if line.find("BOARD") != -1 and line.find("profpga") != -1:
          self.HAS_SGMII = False
    IPM = ""
    IPL = ""
    #determine other parameters
    with open("grlib_config.vhd") as fp:
      for line in fp:
        #check if the CPU is configured to used the CPU
        if line.find("CFG_FPU : integer") != -1:
          self.HAS_FPU = self.check_cfg(line, "integer := ", " ")
        #check if the SoC uses JTAG
        if line.find("CFG_AHB_JTAG") != -1:
          self.HAS_JTAG = int(self.check_cfg(line, "integer := ", ";"))
        #check if the SoC uses ETH
        if line.find("CFG_GRETH ") != -1:
          self.HAS_ETH = int(self.check_cfg(line, "integer := ", ";"))
        #check if the SoC has ethernet
        if line.find("CFG_ETH_IPM") != -1:
          self.IPM = self.check_cfg(line, "16#", "#")
        if line.find("CFG_ETH_IPL") != -1:
          self.IPL = self.check_cfg(line, "16#", "#")
        #check if the SoC uses SVGA
        if line.find("CFG_SVGA_ENABLE ") != -1:
          self.HAS_SVGA = int(self.check_cfg(line, "integer := ", ";"))
    #post process configuration
    self.set_IP()
    #0 = Bigphysical area ; 1 = Scatter/Gather
    self.transfers = IntVar()