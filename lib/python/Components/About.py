from sys import modules, version_info
import socket
import fcntl
import struct

from boxbranding import getImageVersion, getMachineBuild, getBoxType


def getVersionString():
	return getImageVersion()


def getFlashDateString():
	try:
		with open("/etc/install", "r") as f:
			flashdate = f.read()
			return flashdate
	except:
		return _("unknown")


def getEnigmaVersionString():
	return getImageVersion()


def getGStreamerVersionString():
	try:
		from glob import glob
		gst = [x.split("Version: ") for x in open(glob("/var/lib/opkg/info/gstreamer[0-9].[0-9].control")[0], "r") if x.startswith("Version:")][0]
		return "%s" % gst[1].split("+")[0].replace("\n", "")
	except:
		return _("unknown")


def getKernelVersionString():
	try:
		with open("/proc/version", "r") as f:
			kernelversion = f.read().split(" ", 4)[2].split("-", 2)[0]
			return kernelversion
	except:
		return _("unknown")


def getIsBroadcom():
	try:
		with open("/proc/cpuinfo", "r") as file:
			lines = file.readlines()
			for x in lines:
				splitted = x.split(": ")
				if len(splitted) > 1:
					splitted[1] = splitted[1].replace("\n", "")
					if splitted[0].startswith("Hardware"):
						system = splitted[1].split(" ")[0]
					elif splitted[0].startswith("system type"):
						if splitted[1].split(" ")[0].startswith("BCM"):
							system = "Broadcom"
		if "Broadcom" in system:
			return True
		else:
			return False
	except:
		return False


def getChipSetString():
	if getMachineBuild() in ('dm7080','dm820'):
		return "7435"
	elif getMachineBuild() in ('dm520','dm525'):
		return "73625"
	elif getMachineBuild() in ('dm900','dm920','et13000','sf5008'):
		return "7252S"
	elif getMachineBuild() in ('hd51','vs1500','h7'):
		return "7251S"
	elif getMachineBuild() in ('alien5',):
		return "S905D"
	else:
		try:
			f = open('/proc/stb/info/chipset', 'r')
			chipset = f.read()
			f.close()
			return str(chipset.lower().replace('\n','').replace('bcm','').replace('brcm','').replace('sti',''))
		except IOError:
			return "unavailable"


def getCPUSpeedMHzInt():
	cpu_speed = 0
	try:
		with open("/proc/cpuinfo", "r") as file:
			lines = file.readlines()
			for x in lines:
				splitted = x.split(": ")
				if len(splitted) > 1:
					splitted[1] = splitted[1].replace("\n", "")
					if splitted[0].startswith("cpu MHz"):
						cpu_speed = float(splitted[1].split(" ")[0])
						break
	except IOError:
		print("[About] getCPUSpeedMHzInt, /proc/cpuinfo not available")

	if cpu_speed == 0:
		if getMachineBuild() in ("h7", "hd51", "sf4008"):
			try:
				import binascii
				with open("/sys/firmware/devicetree/base/cpus/cpu@0/clock-frequency", "rb") as f:
					clockfrequency = f.read()
					cpu_speed = round(int(binascii.hexlify(clockfrequency), 16) // 1000000, 1)
			except IOError:
				cpu_speed = 1700
		else:
			try: # Solo4K sf8008
				with open("/sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_max_freq", "r") as file:
					cpu_speed = float(file.read()) // 1000
			except IOError:
				print("[About] getCPUSpeedMHzInt, /sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_max_freq not available")
	return int(cpu_speed)


def getCPUSpeedString():
	if getMachineBuild() in ('u41','u42','u43'):
		return "1,0 GHz"
	elif getMachineBuild() in ('dags72604','vusolo4k','vuultimo4k', 'vuzero4k', 'gb72604','vuduo4kse'):
		return "1,5 GHz"
	elif getMachineBuild() in ('formuler1tc','formuler1', 'triplex', 'tiviaraplus'):
		return "1,3 GHz"
	elif getMachineBuild() in ('gbmv200','u51','u52','u53','u532','u533','u54','u55','u56','u57','u5','u5pvr','h9','i55se','h9se','h9combo','h9combose','h10','cc1','sf8008','sf8008m','hd60','hd61','i55plus','ustym4kpro','beyonwizv2','viper4k','v8plus','multibox','plus'):
		return "1,6 GHz"
	elif getMachineBuild() in ('vuuno4kse','vuuno4k','dm900','dm920', 'gb7252', 'dags7252','xc7439','8100s'):
		return "1,7 GHz"
	elif getMachineBuild() in ('alien5','hzero','h8'):
		return "2,0 GHz"
	elif getMachineBuild() in ('vuduo4k',):
		return "2,1 GHz"
	elif getMachineBuild() in ('hd51','hd52','sf4008','vs1500','et1x000','h7','et13000','sf5008','osmio4k','osmio4kplus','osmini4k'):
		try:
			import binascii
			f = open('/sys/firmware/devicetree/base/cpus/cpu@0/clock-frequency', 'rb')
			clockfrequency = f.read()
			f.close()
			CPUSpeed_Int = round(int(binascii.hexlify(clockfrequency), 16)/1000000,1)
			if CPUSpeed_Int >= 1000:
				return _("%s GHz") % str(round(CPUSpeed_Int/1000,1))
			else:
				return _("%s MHz") % str(round(CPUSpeed_Int,1))
		except:
			return "1,7 GHz"
	else:
		try:
			file = open('/proc/cpuinfo', 'r')
			lines = file.readlines()
			for x in lines:
				splitted = x.split(': ')
				if len(splitted) > 1:
					splitted[1] = splitted[1].replace('\n','')
					if splitted[0].startswith("cpu MHz"):
						mhz = float(splitted[1].split(' ')[0])
						if mhz and mhz >= 1000:
							mhz = _("%s GHz") % str(round(mhz/1000,1))
						else:
							mhz = _("%s MHz") % str(round(mhz,1))
			file.close()
			return mhz
		except IOError:
			return "unavailable"


def getCPUArch():
	if getBoxType() in ("osmio4k", ):
		return "ARM V7"
	if "ARM" in getCPUString():
		return getCPUString()
	return _("Mipsel")


def getCPUString():
	if getMachineBuild() in ('vuduo4k','vuduo4kse','osmio4k','osmio4kplus','osmini4k','dags72604','vuuno4kse','vuuno4k', 'vuultimo4k','vusolo4k', 'vuzero4k', 'hd51', 'hd52', 'sf4008', 'dm900','dm920', 'gb7252', 'gb72604', 'dags7252', 'vs1500', 'et1x000', 'xc7439','h7','8100s','et13000','sf5008'):
		return "Broadcom"
	elif getMachineBuild() in ('gbmv200','u41','u42','u43','u51','u52','u53','u532','u533','u54','u55','u56','u57','u5','u5pvr','h9','i55se','h9se','h9combo','h9combose','h10','cc1','sf8008','sf8008m','hd60','hd61','i55plus','ustym4kpro','beyonwizv2','viper4k','v8plus','multibox','plus','hzero','h8'):
		return "Hisilicon"
	elif getMachineBuild() in ('alien5',):
		return "AMlogic"
	else:
		try:
			system="unknown"
			file = open('/proc/cpuinfo', 'r')
			lines = file.readlines()
			for x in lines:
				splitted = x.split(': ')
				if len(splitted) > 1:
					splitted[1] = splitted[1].replace('\n','')
					if splitted[0].startswith("system type"):
						system = splitted[1].split(' ')[0]
					elif splitted[0].startswith("Processor"):
						system = splitted[1].split(' ')[0]
			file.close()
			return system
		except IOError:
			return "unavailable"


def getCpuCoresInt():
	cores = 0
	try:
		with open("/proc/cpuinfo", "r") as file:
			lines = file.readlines()
			for x in lines:
				splitted = x.split(": ")
				if len(splitted) > 1:
					splitted[1] = splitted[1].replace("\n", "")
					if splitted[0].startswith("processor"):
						cores = int(splitted[1]) + 1
	except IOError:
		pass
	return cores


def getCpuCoresString():
	cores = getCpuCoresInt()
	return {
			0: _("unavailable"),
			1: _("Single core"),
			2: _("Dual core"),
			4: _("Quad core"),
			8: _("Octo core")
			}.get(cores, _("%d cores") % cores)


def _ifinfo(sock, addr, ifname):
	iface = struct.pack('256s', bytes(ifname[:15], 'utf-8'))
	info = fcntl.ioctl(sock.fileno(), addr, iface)
	if addr == 0x8927:
		return ''.join(['%02x:' % ord(chr(char)) for char in info[18:24]])[:-1].upper()
	else:
		return socket.inet_ntoa(info[20:24])


def getIfConfig(ifname):
	ifreq = {"ifname": ifname}
	infos = {}
	sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	# offsets defined in /usr/include/linux/sockios.h on linux 2.6
	infos["addr"] = 0x8915 # SIOCGIFADDR
	infos["brdaddr"] = 0x8919 # SIOCGIFBRDADDR
	infos["hwaddr"] = 0x8927 # SIOCSIFHWADDR
	infos["netmask"] = 0x891b # SIOCGIFNETMASK
	try:
		for k, v in infos.items():
			ifreq[k] = _ifinfo(sock, v, ifname)
	except:
		pass
	sock.close()
	print("[About] ifreq: ", ifreq)
	return ifreq


def getIfTransferredData(ifname):
	with open("/proc/net/dev", "r") as f:
		for line in f:
			if ifname in line:
				data = line.split("%s:" % ifname)[1].split()
				rx_bytes, tx_bytes = (data[0], data[8])
				return rx_bytes, tx_bytes


def getPythonVersionString():
	return "%s.%s.%s" % (version_info.major, version_info.minor, version_info.micro)


def getEnigmaUptime():
	from time import time
	import os
	location = "/etc/enigma2/profile"
	try:
		seconds = int(time() - os.path.getmtime(location))
		return formatUptime(seconds)
	except:
		return ''


def getBoxUptime():
	try:
		f = open("/proc/uptime", "rb")
		seconds = int(f.readline().split('.')[0])
		f.close()
		return formatUptime(seconds)
	except:
		return ''


def formatUptime(seconds):
	out = ''
	if seconds > 86400:
		days = int(seconds / 86400)
		out += ("1 day" if days == 1 else "%d days" % days) + ", "
	if seconds > 3600:
		hours = int((seconds % 86400) / 3600)
		out += ("1 hour" if hours == 1 else "%d hours" % hours) + ", "
	if seconds > 60:
		minutes = int((seconds % 3600) / 60)
		out += ("1 minute" if minutes == 1 else "%d minutes" % minutes) + " "
	else:
		out += ("1 second" if seconds == 1 else "%d seconds" % seconds) + " "
	return out


def getEnigmaUptime():
	from time import time
	import os
	location = "/etc/enigma2/profile"
	try:
		seconds = int(time() - os.path.getmtime(location))
		return formatUptime(seconds)
	except:
		return ''

def getBoxUptime():
	try:
		f = open("/proc/uptime", "rb")
		seconds = int(f.readline().split('.')[0])
		f.close()
		return formatUptime(seconds)
	except:
		return ''
		
def formatUptime(seconds):
	out = ''
	if seconds > 86400:
		days = int(seconds / 86400)
		out += (_("1 day") if days == 1 else _("%d days") % days) + ", "
	if seconds > 3600:
		hours = int((seconds % 86400) / 3600)
		out += (_("1 hour") if hours == 1 else _("%d hours") % hours) + ", "
	if seconds > 60:
		minutes = int((seconds % 3600) / 60)
		out += (_("1 minute") if minutes == 1 else _("%d minutes") % minutes) + " "
	else:
		out += (_("1 second") if seconds == 1 else _("%d seconds") % seconds) + " "
	return out

# For modules that do "from About import about"
about = modules[__name__]
