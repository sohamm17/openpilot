import os
import subprocess
import glob
import hashlib
import shutil
import threading
import time
from common.basedir import BASEDIR
from selfdrive.swaglog import cloudlog

android_packages = ("ai.comma.plus.offroad",)

def get_installed_apks():
  dat = subprocess.check_output(["pm", "list", "packages", "-f"], encoding='utf8').strip().split("\n")
  ret = {}
  for x in dat:
    if x.startswith("package:"):
      v, k = x.split("package:")[1].split("=")
      ret[k] = v
  return ret

def install_apk(path):
  # can only install from world readable path
  install_path = "/sdcard/%s" % os.path.basename(path)
  shutil.copyfile(path, install_path)

  ret = subprocess.call(["pm", "install", "-r", install_path])
  os.remove(install_path)
  return ret == 0

def start_offroad():
  set_package_permissions()
  system("am start -n ai.comma.plus.offroad/.MainActivity")

def extract_current_permissions(dump):
  perms = dump.split("runtime permissions")[1]
  return perms


def set_package_permissions():
  out = subprocess.Popen(['dumpsys', 'package', 'ai.comma.plus.offroad'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
  _,stderr = out.communicate()
  print(extract_current_permissions(str(stderr)))
  print(extract_current_permissions(str(stderr)))
  print(extract_current_permissions(str(stderr)))
  print(extract_current_permissions(str(stderr)))
  time.sleep(5)
  pm_grant("ai.comma.plus.offroad", "android.permission.ACCESS_FINE_LOCATION")
  pm_grant("ai.comma.plus.offroad", "android.permission.READ_PHONE_STATE")
  pm_grant("ai.comma.plus.offroad", "android.permission.READ_EXTERNAL_STORAGE")
  appops_set("ai.comma.plus.offroad", "SU", "allow")
  appops_set("ai.comma.plus.offroad", "WIFI_SCAN", "allow")
def appops_set(package, op, mode):
  system(f"LD_LIBRARY_PATH= appops set {package} {op} {mode}")

def pm_grant(package, permission):
  system(f"pm grant {package} {permission}")

def system(cmd):
  try:
    cloudlog.info("running %s" % cmd)
    subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True)
  except subprocess.CalledProcessError as e:
    cloudlog.event("running failed",
      cmd=e.cmd,
      output=e.output[-1024:],
      returncode=e.returncode)

# *** external functions ***

def update_apks():
  # install apks
  installed = get_installed_apks()

  install_apks = glob.glob(os.path.join(BASEDIR, "apk/*.apk"))
  for apk in install_apks:
    app = os.path.basename(apk)[:-4]
    if app not in installed:
      installed[app] = None

  cloudlog.info("installed apks %s" % (str(installed), ))

  for app in installed.keys():
    apk_path = os.path.join(BASEDIR, "apk/"+app+".apk")
    if not os.path.exists(apk_path):
      continue

    h1 = hashlib.sha1(open(apk_path, 'rb').read()).hexdigest()
    h2 = None
    if installed[app] is not None:
      h2 = hashlib.sha1(open(installed[app], 'rb').read()).hexdigest()
      cloudlog.info("comparing version of %s  %s vs %s" % (app, h1, h2))

    if h2 is None or h1 != h2:
      cloudlog.info("installing %s" % app)

      success = install_apk(apk_path)
      if not success:
        cloudlog.info("needing to uninstall %s" % app)
        system("pm uninstall %s" % app)
        success = install_apk(apk_path)

      assert success

def pm_apply_packages(cmd):
  def f():
    for p in android_packages:
      system("pm %s %s" % (cmd, p))
  threading.Thread(target=f).start()

if __name__ == "__main__":
  update_apks()
