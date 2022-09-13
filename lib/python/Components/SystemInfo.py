from os import R_OK, access, listdir, walk
from os.path import exists as fileAccess, isdir, isfile, join as pathjoin
from re import findall
from subprocess import PIPE, Popen
from boxbranding import getBoxType, getBrandOEM, getDisplayType, getHaveAVJACK, getHaveHDMIinFHD, getHaveHDMIinHD, getHaveRCA, getHaveSCART, getHaveSCARTYUV, getHaveYUV, getImageType, getMachineBrand, getMachineBuild, getMachineMtdRoot, getMachineName
from enigma import Misc_Options, eDVBCIInterfaces, eDVBResourceManager, eGetEnigmaDebugLvl

from Components.About import getChipSetString
from Components.RcModel import rc_model
from Tools.BoxConfig import BoxConfig
from Tools.Directories import SCOPE_SKIN, fileCheck, fileContains, fileReadLine, fileReadLines, resolveFilename, fileExists, fileHas, fileReadLine, pathExists
from Tools.HardwareInfo import HardwareInfo

MODULE_NAME = __name__.split(".")[-1]
ENIGMA_KERNEL_MODULE = "enigma.ko"
PROC_PATH = "/proc/enigma"

SystemInfo = {}


class BoxInformation:  # To maintain data integrity class variables should not be accessed from outside of this class!
	def __init__(self):
		self.immutableList = []
		self.boxInfo = {}
		self.enigmaInfoList = []
		self.enigmaConfList = []
		lines = fileReadLines(pathjoin(resolveFilename(SCOPE_LIBDIR), "enigma.info"), source=MODULE_NAME)
		if lines:
			modified = self.checkChecksum(lines)
			if modified:
				print("[SystemInfo] WARNING: Enigma information file checksum is incorrect!  File appears to have been modified.")
				self.boxInfo["checksumerror"] = True
			else:
				print("[SystemInfo] Enigma information file checksum is correct.")
				self.boxInfo["checksumerror"] = False
			for line in lines:
				if line.startswith("#") or line.strip() == "":
					continue
				if "=" in line:
					item, value = [x.strip() for x in line.split("=", 1)]
					if item:
						self.immutableList.append(item)
						self.enigmaInfoList.append(item)
						self.boxInfo[item] = self.processValue(value)
			self.enigmaInfoList = sorted(self.enigmaInfoList)
			print("[SystemInfo] Enigma information file data loaded into BoxInfo.")
		else:
			print("[SystemInfo] ERROR: Enigma information file is not available!  The system is unlikely to boot or operate correctly.")
		lines = fileReadLines(pathjoin(resolveFilename(SCOPE_LIBDIR), "enigma.conf"), source=MODULE_NAME)
		if lines:
			print("[SystemInfo] Enigma config override file available and data loaded into BoxInfo.")
			self.boxInfo["overrideactive"] = True
			for line in lines:
				if line.startswith("#") or line.strip() == "":
					continue
				if "=" in line:
					item, value = [x.strip() for x in line.split("=", 1)]
					if item:
						self.enigmaConfList.append(item)
						if item in self.boxInfo:
							print("[SystemInfo] Note: Enigma information value '%s' with value '%s' being overridden to '%s'." % (item, self.boxInfo[item], value))
						self.boxInfo[item] = self.processValue(value)
			self.enigmaConfList = sorted(self.enigmaConfList)
		else:
			self.boxInfo["overrideactive"] = False

	def checkChecksum(self, lines):
		value = "Undefined!"
		data = []
		for line in lines:
			if line.startswith("checksum"):
				item, value = [x.strip() for x in line.split("=", 1)]
			else:
				data.append(line)
		data.append("")
		result = md5(bytearray("\n".join(data), "UTF-8", errors="ignore")).hexdigest()  # NOSONAR
		return value != result

	def processValue(self, value):
		valueTest = value.upper() if value else ""
		if value is None:
			pass
		elif value.startswith("\"") or value.startswith("'") and value.endswith(value[0]):
			value = value[1:-1]
		elif value.startswith("(") and value.endswith(")"):
			data = []
			for item in [x.strip() for x in value[1:-1].split(",")]:
				data.append(self.processValue(item))
			value = tuple(data)
		elif value.startswith("[") and value.endswith("]"):
			data = []
			for item in [x.strip() for x in value[1:-1].split(",")]:
				data.append(self.processValue(item))
			value = list(data)
		elif valueTest == "NONE":
			value = None
		elif valueTest in ("FALSE", "NO", "OFF", "DISABLED"):
			value = False
		elif valueTest in ("TRUE", "YES", "ON", "ENABLED"):
			value = True
		elif value.isdigit() or (value[0:1] == "-" and value[1:].isdigit()):
			value = int(value)
		elif valueTest.startswith("0X"):
			try:
				value = int(value, 16)
			except ValueError:
				pass
		elif valueTest.startswith("0O"):
			try:
				value = int(value, 8)
			except ValueError:
				pass
		elif valueTest.startswith("0B"):
			try:
				value = int(value, 2)
			except ValueError:
				pass
		else:
			try:
				value = float(value)
			except ValueError:
				pass
		return value

	def getEnigmaInfoList(self):
		return self.enigmaInfoList

	def getEnigmaConfList(self):
		return self.enigmaConfList

	def getItemsList(self):
		return sorted(list(self.boxInfo.keys()))

	def getItem(self, item, default=None):
		if item in self.boxInfo:
			value = self.boxInfo[item]
		elif item in SystemInfo:
			value = SystemInfo[item]
		else:
			value = default
		return value

	def setItem(self, item, value, immutable=False):
		if item in self.immutableList:
			print("[BoxInfo] Error: Item '%s' is immutable and can not be %s!" % (item, "changed" if item in self.boxInfo else "added"))
			return False
		if immutable:
			self.immutableList.append(item)
		self.boxInfo[item] = value
		SystemInfo[item] = value
		return True

	def deleteItem(self, item):
		if item in self.immutableList:
			print("[BoxInfo] Error: Item '%s' is immutable and can not be deleted!" % item)
		elif item in self.boxInfo:
			del self.boxInfo[item]
			return True
		return False


BoxInfo = BoxInformation()

ARCHITECTURE = BoxInfo.getItem("architecture")
BRAND = BoxInfo.getItem("brand")
MODEL = BoxInfo.getItem("model")
SOC_FAMILY = BoxInfo.getItem("socfamily")
DISPLAYTYPE = BoxInfo.getItem("displaytype")
MTDROOTFS = BoxInfo.getItem("mtdrootfs")
DISPLAYMODEL = BoxInfo.getItem("displaymodel")


# Parse the boot commandline.
# cmdline = fileReadLine("/proc/cmdline", source=MODULE_NAME)
# cmdline = {k: v.strip('"') for k, v in findall(r'(\S+)=(".*?"|\S+)', cmdline)}

def getNumVideoDecoders():
	numVideoDecoders = 0
	while fileExists("/dev/dvb/adapter0/video%d" % numVideoDecoders, "f"):
		numVideoDecoders += 1
	return numVideoDecoders


def countFrontpanelLEDs():
	numLeds = fileExists("/proc/stb/fp/led_set_pattern") and 1 or 0
	while fileExists("/proc/stb/fp/led%d_pattern" % numLeds):
		numLeds += 1
	return numLeds


def haveInitCam():
	for cam in listdir("/etc/init.d"):
		if cam.startswith("softcam.") and not cam.endswith("None"):
			return True
		elif cam.startswith("cardserver.") and not cam.endswith("None"):
			return True
	return False


def getRCFile(ext):
	filename = resolveFilename(SCOPE_SKINS, pathjoin("rc", "%s.%s" % (BoxInfo.getItem("rcname"), ext)))
	if not isfile(filename):
		filename = resolveFilename(SCOPE_SKINS, pathjoin("rc", "dmm1.%s" % ext))
	return filename


def getModuleLayout():
	modulePath = BoxInfo.getItem("enigmamodule")
	if modulePath:
		process = Popen(("/sbin/modprobe", "--dump-modversions", modulePath), stdout=PIPE, stderr=PIPE, universal_newlines=True)
		stdout, stderr = process.communicate()
		if process.returncode == 0:
			for detail in stdout.split("\n"):
				if "module_layout" in detail:
					return detail.split("\t")[0]
	return None


def Check_Softcam():
	found = False
	if fileExists("/etc/enigma2/noemu"):
		found = False
	else:
		for cam in listdir("/etc/init.d"):
			if cam.startswith('softcam.') and not cam.endswith('None'):
				found = True
				break
			elif cam.startswith('cardserver.') and not cam.endswith('None'):
				found = True
				break
	return found


def Check_SysSoftcam():
	syscam = ""
	if isfile('/etc/init.d/softcam'):
		if (islink('/etc/init.d/softcam') and not readlink('/etc/init.d/softcam').lower().endswith('none')):
			try:
				syscam = readlink('/etc/init.d/softcam').rsplit('.', 1)[1]
				if syscam.lower().startswith('oscam'):
					syscam = "oscam"
				if syscam.lower().startswith('ncam'):
					syscam = "ncam"
				if syscam.lower().startswith('cccam'):
					syscam = "cccam"
			except:
				pass
	return syscam


def Refresh_SysSoftCam():
	BoxInfo.setItem("ShowOscamInfo", Check_SysSoftcam() in ("oscam", "ncam"), True)
	BoxInfo.setItem("ShowCCCamInfo", Check_SysSoftcam() in ("cccam",), True)


BoxInfo.setItem("DebugLevel", eGetEnigmaDebugLvl())
BoxInfo.setItem("InDebugMode", eGetEnigmaDebugLvl() >= 4)
BoxInfo.setItem("ModuleLayout", getModuleLayout(), immutable=True)

BoxInfo.setItem("12V_Output", Misc_Options.getInstance().detected_12V_output())  #FIXME : Do we need this?
BoxInfo.setItem("3DMode", fileCheck("/proc/stb/fb/3dmode") or fileCheck("/proc/stb/fb/primary/3d"))
BoxInfo.setItem("3DZNorm", fileCheck("/proc/stb/fb/znorm") or fileCheck("/proc/stb/fb/primary/zoffset"))
BoxInfo.setItem("7segment", DISPLAYTYPE in ("7segment",))
BoxInfo.setItem("AmlogicFamily", SOC_FAMILY.startswith(("aml", "meson")) or exists("/proc/device-tree/amlogic-dt-id") or exists("/usr/bin/amlhalt") or exists("/sys/module/amports"))
BoxInfo.setItem("ArchIsARM64", ARCHITECTURE == "aarch64" or "64" in ARCHITECTURE)
BoxInfo.setItem("ArchIsARM", ARCHITECTURE.startswith(("arm", "cortex")))
BoxInfo.setItem("Blindscan", isPluginInstalled("Blindscan"))
BoxInfo.setItem("BoxName", GetBoxName())
canImageBackup = not MODEL.startswith('az') and not BRAND.startswith('cube') and not BRAND.startswith('wetek') and not MODEL.startswith('alien')
BoxInfo.setItem("canImageBackup", canImageBackup)
BoxInfo.setItem("CanMeasureFrontendInputPower", eDVBResourceManager.getInstance().canMeasureFrontendInputPower())
BoxInfo.setItem("canMultiBoot", MultiBoot.getBootSlots())
BoxInfo.setItem("CanNotDoSimultaneousTranscodeAndPIP", MODEL in ("vusolo4k", "gbquad4k", "gbue4k"))
BoxInfo.setItem("canRecovery", MODEL in ("hd51", "vs1500", "h7", "8100s") and ("disk.img", "mmcblk0p1") or MODEL in ("xc7439", "osmio4k", "osmio4kplus", "osmini4k") and ("emmc.img", "mmcblk1p1") or MODEL in ("gbmv200", "cc1", "sf8008", "sf8008m", "sf8008opt", "sx988", "ip8", "ustym4kpro", "ustym4kottpremium", "beyonwizv2", "viper4k", "og2ott4k") and ("usb_update.bin", "none"))
BoxInfo.setItem("CanUse3DModeChoices", fileExists("/proc/stb/fb/3dmode_choices") and True or False)
BoxInfo.setItem("CIHelper", fileExists("/usr/bin/cihelper"))
BoxInfo.setItem("DeepstandbySupport", MODEL != 'dm800')
BoxInfo.setItem("DefaultDisplayBrightness", MODEL in ("dm900", "dm920") and 8 or 5)
BoxInfo.setItem("FBLCDDisplay", fileCheck("/proc/stb/fb/sd_detach"))
BoxInfo.setItem("Fan", fileCheck("/proc/stb/fp/fan"))
BoxInfo.setItem("FanPWM", BoxInfo.getItem("Fan") and fileCheck("/proc/stb/fp/fan_pwm"))
BoxInfo.setItem("ForceLNBPowerChanged", fileCheck("/proc/stb/frontend/fbc/force_lnbon"))
BoxInfo.setItem("ForceToneBurstChanged", fileCheck("/proc/stb/frontend/fbc/force_toneburst"))
BoxInfo.setItem("FrontpanelDisplay", fileExists("/dev/dbox/oled0") or fileExists("/dev/dbox/lcd0"))
BoxInfo.setItem("GBWOL", fileExists("/usr/bin/gigablue_wol"))
BoxInfo.setItem("grautec", fileExists("/tmp/usbtft"))
BoxInfo.setItem("GraphicLCD", MODEL in ("vuultimo", "xpeedlx3", "et10000", "mutant2400", "quadbox2400", "sezammarvel", "atemionemesis", "mbultra", "beyonwizt4", "osmio4kplus"))
BoxInfo.setItem("HasExternalPIP", MODEL not in ("et9x00", "et6x00", "et5x00") and fileCheck("/proc/stb/vmpeg/1/external"))
BoxInfo.setItem("HasFullHDSkinSupport", MODEL not in ("et4000", "et5000", "sh1", "hd500c", "hd1100", "xp1000", "lc"))
BoxInfo.setItem("HasHiSi", pathExists("/proc/hisi"))
BoxInfo.setItem("hasPIPVisibleProc", fileCheck("/proc/stb/vmpeg/1/visible"))
BoxInfo.setItem("HasMMC", fileHas("/proc/cmdline", "root=/dev/mmcblk") or MultiBoot.canMultiBoot() and fileHas("/proc/cmdline", "root=/dev/sda"))
BoxInfo.setItem("HasSDmmc", MultiBoot.canMultiBoot() and "sd" in MultiBoot.getBootSlots()["2"] and "mmcblk" in MTDROOTFS)
BoxInfo.setItem("HasSDswap", MODEL in ("h9", "i55plus") and pathExists("/dev/mmcblk0p1"))
BoxInfo.setItem("HaveCISSL", fileCheck("/etc/ssl/certs/customer.pem") and fileCheck("/etc/ssl/certs/device.pem"))
BoxInfo.setItem("HAVEEDIDDECODE", fileCheck("/proc/stb/hdmi/raw_edid") and fileCheck("/usr/bin/edid-decode"))
BoxInfo.setItem("HaveID", fileCheck("/etc/.id"))
BoxInfo.setItem("HAVEINITCAM", haveInitCam())
BoxInfo.setItem("HaveTouchSensor", MODEL in ("dm520", "dm525", "dm900", "dm920"))
BoxInfo.setItem("HDMICEC", fileExists("/dev/hdmi_cec") or fileExists("/dev/misc/hdmi_cec0"))
BoxInfo.setItem("HDMIin", MODEL in ("inihdp", "hd2400", "et10000", "dm7080", "dm820", "dm900", "dm920", "vuultimo4k", "et13000", "sf5008", "vuuno4kse", "vuduo4k", "vuduo4kse") or BoxInfo.getItem("machinebuild") in ("spycat4k", "spycat4kcombo", "gbquad4k"))
BoxInfo.setItem("HiSilicon", SOC_FAMILY.startswith("hisi") or exists("/proc/hisi") or exists("/usr/bin/hihalt") or exists("/usr/lib/hisilicon"))
BoxInfo.setItem("LcdDisplay", fileExists("/dev/dbox/lcd0"))
BoxInfo.setItem("LcdLiveTV", fileCheck("/proc/stb/fb/sd_detach") or fileCheck("/proc/stb/lcd/live_enable"))
BoxInfo.setItem("LcdLiveTVPiP", fileCheck("/proc/stb/lcd/live_decoder"))
BoxInfo.setItem("LCDMiniTV", fileExists("/proc/stb/lcd/mode"))
BoxInfo.setItem("LCDMiniTVPiP", BoxInfo.getItem("LCDMiniTV") and MODEL not in ("gb800ueplus", "gbquad4k", "gbue4k"))
BoxInfo.setItem("LCDSKINSetup", fileExists("/usr/share/enigma2/display"))
BoxInfo.setItem("LEDButtons", MODEL == "vuultimo")
BoxInfo.setItem("LedPowerColor", fileExists("/proc/stb/fp/ledpowercolor"))
BoxInfo.setItem("LedStandbyColor", fileExists("/proc/stb/fp/ledstandbycolor"))
BoxInfo.setItem("LedSuspendColor", fileExists("/proc/stb/fp/ledsuspendledcolor"))
BoxInfo.setItem("MiddleFlash", BoxInfo.getItem("middleflash") and not BoxInfo.getItem("smallflash"))
BoxInfo.setItem("MiniTV", fileCheck("/proc/stb/fb/sd_detach") or fileCheck("/proc/stb/lcd/live_enable"))
BoxInfo.setItem("need_dsw", MODEL not in ("osminiplus", "osmega"))
BoxInfo.setItem("NumFrontpanelLEDs", countFrontpanelLEDs())
BoxInfo.setItem("NumVideoDecoders", getNumVideoDecoders())
BoxInfo.setItem("OledDisplay", fileExists("/dev/dbox/oled0") or MODEL in ("osminiplus",))
BoxInfo.setItem("PIPAvailable", BoxInfo.getItem("NumVideoDecoders", 1) > 1)
BoxInfo.setItem("Power4x7On", fileExists("/proc/stb/fp/power4x7on"))
BoxInfo.setItem("Power4x7Standby", fileExists("/proc/stb/fp/power4x7standby"))
BoxInfo.setItem("Power4x7Suspend", fileExists("/proc/stb/fp/power4x7suspend"))
BoxInfo.setItem("PowerLed", fileExists("/proc/stb/power/powerled"))
BoxInfo.setItem("PowerLed2", fileExists("/proc/stb/power/powerled2"))
BoxInfo.setItem("RecoveryMode", fileCheck("/proc/stb/fp/boot_mode"))
BoxInfo.setItem("Satfinder", isPluginInstalled("Satfinder"))
BoxInfo.setItem("SmallFlash", BoxInfo.getItem("smallflash"))
BoxInfo.setItem("SoftCam", Check_Softcam())
BoxInfo.setItem("StandbyPowerLed", fileExists("/proc/stb/power/standbyled"))
BoxInfo.setItem("STi", SOC_FAMILY.startswith("sti"))
BoxInfo.setItem("SuspendPowerLed", fileExists("/proc/stb/power/suspendled"))
BoxInfo.setItem("USETunersetup", BoxInfo.getItem("ForceLNBPowerChanged") or BoxInfo.getItem("ForceToneBurstChanged"))
BoxInfo.setItem("VFD_scroll_repeats", fileCheck("/proc/stb/lcd/scroll_repeats"))
BoxInfo.setItem("VFD_scroll_delay", fileCheck("/proc/stb/lcd/scroll_delay"))
BoxInfo.setItem("VFD_initial_scroll_delay", fileCheck("/proc/stb/lcd/initial_scroll_delay"))
BoxInfo.setItem("VFD_final_scroll_delay", fileCheck("/proc/stb/lcd/final_scroll_delay"))
BoxInfo.setItem("VideoDestinationConfigurable", fileExists("/proc/stb/vmpeg/0/dst_left"))
BoxInfo.setItem("WakeOnLAN", fileCheck("/proc/stb/power/wol") or fileCheck("/proc/stb/fp/wol"))
BoxInfo.setItem("XcoreVFD", MODEL in ("xc7346", "xc7439"))
BoxInfo.setItem("ZapMode", fileCheck("/proc/stb/video/zapmode") or fileCheck("/proc/stb/video/zapping_mode"))

# dont't sort
BoxInfo.setItem("ConfigDisplay", BoxInfo.getItem("FrontpanelDisplay") and DISPLAYTYPE not in ("7segment",))
BoxInfo.setItem("dFlash", canImageBackup and exists("/usr/lib/enigma2/python/Plugins/Extensions/dFlash"))
BoxInfo.setItem("dBackup", canImageBackup and not BoxInfo.getItem("dFlash") and exists("/usr/lib/enigma2/python/Plugins/Extensions/dBackup"))
BoxInfo.setItem("ImageBackup", canImageBackup and not BoxInfo.getItem("dFlash") and not BoxInfo.getItem("dBackup"))

SystemInfo["SeekStatePlay"] = False
SystemInfo["StatePlayPause"] = False
SystemInfo["StandbyState"] = False
SystemInfo["FastChannelChange"] = False

Refresh_SysSoftCam()
