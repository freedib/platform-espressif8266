# Copyright 2014-present PlatformIO <contact@platformio.org>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
ESP8266 RTOS SDK

ESP8266 SDK based on FreeRTOS, a truly free professional grade RTOS for
microcontrollers

https://github.com/espressif/ESP8266_RTOS_SDK
"""

from os.path import isdir, join

from SCons.Script import Builder, DefaultEnvironment

env = DefaultEnvironment()
platform = env.PioPlatform()

FRAMEWORK_DIR = platform.get_package_dir("framework-esp8266-rtos-sdk")
assert isdir(FRAMEWORK_DIR)

env.Append(
    ASFLAGS=["-x", "assembler-with-cpp"],

    CFLAGS=[
        "-std=gnu99",
        "-Wpointer-arith",
        "-Wno-implicit-function-declaration",
        "-Wl,-EL",
        "-fno-inline-functions",
        "-nostdlib"
    ],

    CCFLAGS=[
        "-Os",  # optimize for size
        "-mlongcalls",
        "-mtext-section-literals",
        "-falign-functions=4",
        "-U__STRICT_ANSI__",
        "-ffunction-sections",
        "-fdata-sections"
    ],

    CXXFLAGS=[
        "-fno-rtti",
        "-fno-exceptions",
        "-std=c++11",
        "-Wno-literal-suffix"
    ],

    LINKFLAGS=[
        "-Os",
        "-nostdlib",
        "-Wl,--no-check-sections",
        "-Wl,-static",
        "-Wl,--gc-sections",
        "-u", "call_user_start",
        "-u", "_printf_float",
        "-u", "_scanf_float"
    ],

    CPPDEFINES=[
        ("F_CPU", "$BOARD_F_CPU"),
        "__ets__",
        "ICACHE_FLASH"
    ],

    CPPPATH=[
        join(FRAMEWORK_DIR, "include"),
        join(FRAMEWORK_DIR, "extra_include"),
        join(FRAMEWORK_DIR, "driver_lib", "include"),
        join(FRAMEWORK_DIR, "include", "espressif"),
        join(FRAMEWORK_DIR, "include", "lwip"),
        join(FRAMEWORK_DIR, "include", "lwip", "ipv4"),
        join(FRAMEWORK_DIR, "include", "lwip", "ipv6"),
        join(FRAMEWORK_DIR, "include", "nopoll"),
        join(FRAMEWORK_DIR, "include", "spiffs"),
        join(FRAMEWORK_DIR, "include", "ssl"),
        join(FRAMEWORK_DIR, "include", "json"),
        join(FRAMEWORK_DIR, "include", "openssl"),
    ],

    LIBPATH=[
        join(FRAMEWORK_DIR, "lib"),
        join(FRAMEWORK_DIR, "ld")
    ],

    LIBS=[
        "cirom", "crypto", "driver", "espconn", "espnow", "freertos", "gcc",
        "json", "hal", "lwip", "main", "mesh", "mirom", "net80211", "nopoll",
        "phy", "pp", "pwm", "smartconfig", "spiffs", "ssl", "wpa", "wps"
    ],

    BUILDERS=dict(
        ElfToBin=Builder(
            action=env.VerboseAction(" ".join([
                '"%s"' % join(platform.get_package_dir("tool-esptool"), "esptool"),
                "-eo", "$SOURCE",
                "-bo", "${TARGET}",
                "-bm", "$BOARD_FLASH_MODE",
                "-bf", "${__get_board_f_flash(__env__)}",
                "-bz", "${__get_flash_size(__env__)}",
                "-bs", ".text",
                "-bs", ".data",
                "-bs", ".rodata",
                "-bc", "-ec",
                "-eo", "$SOURCE",
                "-es", ".irom0.text", "${TARGET}.irom0text.bin",
                "-ec", "-v"
            ]), "Building $TARGET"),
            suffix=".bin"
        )
    )
)

# copy CCFLAGS to ASFLAGS (-x assembler-with-cpp mode)
env.Append(ASFLAGS=env.get("CCFLAGS", [])[:])


###################################################################################

# evaluate SPI_FLASH_SIZE_MAP flag for NONOS_SDK 3.x and set CCFLAG

c1 = True               # if c1, for OTA use 1024+1024, else 512+512

board_flash_size = int(env.BoardConfig().get("upload.maximum_size", 524288))

if board_flash_size == 16777216:                 # 0x1000000  16M 1024+1024
    flash_size_map = 9
elif board_flash_size == 8388608:                # 0x800000    8M 1024+1024
    flash_size_map = 8
elif board_flash_size == 4194304 and c1:         # 0x400000    4M 1024+1024
    flash_size_map = 6 
elif board_flash_size == 2097152 and c1:         # 0x200000    2M 1024+1024
    flash_size_map = 5    
elif board_flash_size == 4194304 and not c1:     # 0x400000    4M 512+512
    flash_size_map = 4
elif board_flash_size == 2097152 and not c1:     # 0x200000    2M 512+512
    flash_size_map = 3
elif board_flash_size == 1048576:                # 0x100000    1M 512+512
    flash_size_map = 2
else:                                            #  0x80000    512K no OTA
    flash_size_map = 1

# for OTA, only size maps 5, 6, 8 and 9 are supported to avoid link twice for user1 and user2

env.Append(CCFLAGS=["-DSPI_FLASH_SIZE_MAP="+str(flash_size_map)])     # NONOS-SDK 3.x user_main.c need it
env.Append(FLASH_SIZE_MAP=flash_size_map)                             # will be used to extract sections
env.Append(FLASH_SIZE=board_flash_size)                               # will be used to extract sections

# create binaries list to upload

# check the init_data_default file to use
esp_init_data_default_file = "esp_init_data_default_v08.bin"       # new in NONOS 3.04
if not isfile(join(FRAMEWORK_DIR, "bin", esp_init_data_default_file)):
    esp_init_data_default_file = "esp_init_data_default.bin"
env.Append(ESP_INIT_DATA_DEFAULT_FILE=esp_init_data_default_file)  # for custom downloader

data_bin  = join(FRAMEWORK_DIR, "bin", esp_init_data_default_file)
blank_bin = join(FRAMEWORK_DIR, "bin", "blank.bin")
    
rf_cal_addr    = board_flash_size-0x5000     # 3fb000 for 4M board blank_bin
phy_data_addr  = board_flash_size-0x4000     # 3fc000 for 4M board data_bin
sys_param_addr = board_flash_size-0x2000     # 3fe000 for 4M board blank_bin

# user1.4096.new.6.bin or user1.16384.new.9.bin
user_bin = "user1."+str(int(board_flash_size/1024))+".new."+str(flash_size_map)+".bin"

if "ota" in BUILD_TARGETS:      # if OTA, flash user1 but generate user1 and user2
    boot_bin  = join(FRAMEWORK_DIR, "bin", "boot_v1.7.bin")
    user_bin  = join("$BUILD_DIR", user_bin)
    user_addr = 0x1000
else:                           # non ota
    boot_bin  = join("$BUILD_DIR", "eagle.flash.bin")       # firmware.bin # eagle.flash.bin
    user_bin  = join("$BUILD_DIR", "eagle.irom0text.bin")   # firmware.bin.irom0text.bin # eagle.irom0text.bin
    if (env['PIOFRAMEWORK'][0] == "esp8266-rtos-sdk"):
        user_addr = 0x20000
    else:
        user_addr = 0x10000

FLASH_IMAGES=[
    (hex(0),              boot_bin),
    (hex(user_addr),      user_bin),
    (hex(phy_data_addr),  data_bin),
    (hex(sys_param_addr), blank_bin),
    (hex(rf_cal_addr),    blank_bin)
]

# standard non OTA. Original version
FLASH_EXTRA_IMAGES=[
    (hex(user_addr),      join("$BUILD_DIR",  "${PROGNAME}.bin.irom0text.bin")),
    (hex(phy_data_addr),  data_bin),
    (hex(sys_param_addr), rf_cal_addr)
]


# allow user to specify a LDSCRIPT_PATH in pre: SCRIPT
if not env.BoardConfig().get("build.ldscript", ""):
    if not env.get('LDSCRIPT_PATH', None):
        if "ota" in BUILD_TARGETS:          # flash map size >= 5 only!!!
            LDSCRIPT_PATH=join(FRAMEWORK_DIR, "ld", "eagle.app.v6.new.2048.ld")
        else:
            LDSCRIPT_PATH=join(FRAMEWORK_DIR, "ld", "eagle.app.v6.ld")
        env.Replace(LDSCRIPT_PATH=LDSCRIPT_PATH)
       
###################################################################################
        

#
# Target: Build Driver Library
#

libs = []

libs.append(env.BuildLibrary(
    join(FRAMEWORK_DIR, "lib", "driver"),
    join(FRAMEWORK_DIR, "driver_lib")
))

env.Prepend(LIBS=libs)
