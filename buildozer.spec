[app]

# (str) Title of your application
title = Laser Trigger

# (str) Package name
package.name = lasertrigger

# (str) Package domain (needed for android packaging)
package.domain = org.lasertrigger

# (str) Source code where the main.py lives
source.dir = .

# (list) Source files to include (let's include py and json save data files)
source.include_exts = py,png,jpg,json,ttf

# (str) Application versioning
version = 1.0

# (list) Application requirements
# Python 3 and Pygame are required
requirements = python3,kivy

# (str) Supported orientations (portrait is perfect for our vertical game)
orientation = portrait

# (bool) Use fullscreen
fullscreen = 1

# (list) Permissions
android.permissions = INTERNET

# (int) Target Android API (API 33 is Android 13)
android.api = 33

# (int) Minimum Android API (API 21 is Android 5.0)
android.minapi = 21

# (str) Android NDK version to use
android.ndk = 25b

# (bool) Skip NDK verification
android.skip_ndk_downloader = False

# (bool) Accept SDK license agreements automatically
android.accept_sdk_license = True

# (str) Android entry point
android.entrypoint = main.py

[buildozer]

# (int) Log level (0 = error, 1 = info, 2 = debug)
log_level = 2

# (int) Display warning if buildozer is run as root
warn_on_root = 1
