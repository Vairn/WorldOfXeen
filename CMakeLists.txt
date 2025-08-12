cmake_minimum_required(VERSION 3.14.0)

# Toolchain configuration for Amiga cross-compilation

# Define AMIGA platform
set(AMIGA TRUE)

# Set project name and version
project(WorldOfXeen 
    VERSION 1.0.0
    DESCRIPTION "World of Xeen for Amiga"
    LANGUAGES C CXX ASM
)

# Set C standard
set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

# Set C++ standard
set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Build type configuration
if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release CACHE STRING "Choose the type of build" FORCE)
    set_property(CACHE CMAKE_BUILD_TYPE PROPERTY STRINGS "Debug" "Release" "MinSizeRel" "RelWithDebInfo")
endif()

# CPM Package Manager setup
set(CPM_DOWNLOAD_VERSION 0.40.2)
if(CPM_SOURCE_CACHE)
    set(CPM_DOWNLOAD_LOCATION "${CPM_SOURCE_CACHE}/cpm/CPM_${CPM_DOWNLOAD_VERSION}.cmake")
elseif(DEFINED ENV{CPM_SOURCE_CACHE})
    set(CPM_DOWNLOAD_LOCATION "$ENV{CPM_SOURCE_CACHE}/cpm/CPM_${CPM_DOWNLOAD_VERSION}.cmake")
else()
    set(CPM_DOWNLOAD_LOCATION "${CMAKE_BINARY_DIR}/cmake/CPM_${CPM_DOWNLOAD_VERSION}.cmake")
endif()

if(NOT (EXISTS ${CPM_DOWNLOAD_LOCATION}))
    message(STATUS "Downloading CPM.cmake to ${CPM_DOWNLOAD_LOCATION}")
    file(DOWNLOAD
        https://github.com/cpm-cmake/CPM.cmake/releases/download/v${CPM_DOWNLOAD_VERSION}/CPM.cmake
        ${CPM_DOWNLOAD_LOCATION}
    )
endif()

include(${CPM_DOWNLOAD_LOCATION})


# Fetch ACE Engine (AGA Branch)
message(STATUS "Fetching ACE Engine (AGA Branch)...")
CPMAddPackage(
    NAME ACE
    GIT_REPOSITORY https://github.com/Vairn/ACE.git
    GIT_TAG AGA
    OPTIONS
        "ACE_BUILD_EXAMPLES OFF"
        "ACE_BUILD_TESTS OFF"
        "ACE_BUILD_DOCS OFF"
        "ACE_USE_AGA_FEATURES ON"
)

# ACE Configuration
set(ACE_USE_AGA_FEATURES OFF)
set(ACE_USE_ECS_FEATURES OFF)
set(ACE_DEBUG_UAE OFF)


file(GLOB_RECURSE SOURCES src/*.c src/states/*.c include/*.h)
# ELF2HUNK support for Amiga executable conversion
if(ELF2HUNK)
    set(XEEN_EXECUTABLE WorldOfXeen.elf)
    set(XEEN_OUTPUT_EXECUTABLE WorldOfXeen.exe)
    add_executable(${XEEN_EXECUTABLE} ${SOURCES})
    
    target_link_libraries(${XEEN_EXECUTABLE} -Wl,-Map=WorldOfXeen.map)
    
    add_custom_command(
        TARGET ${XEEN_EXECUTABLE} POST_BUILD
        COMMAND ${ELF2HUNK} ${XEEN_EXECUTABLE} ${XEEN_OUTPUT_EXECUTABLE}
    )
    add_custom_command(
        TARGET ${XEEN_EXECUTABLE} POST_BUILD
        COMMAND ${OBJDUMP} --disassemble -S ${XEEN_EXECUTABLE} > WorldOfXeen.s
    )
else()
    SET(XEEN_EXECUTABLE WorldOfXeen)
    SET(XEEN_OUTPUT_EXECUTABLE WorldOfXeen)
    
    add_executable(${XEEN_EXECUTABLE} ${SOURCES})
endif()

# Add ACE Engine as subdirectory
#add_subdirectory(deps/ace ace)

# Version generation based on current date
string(TIMESTAMP YEAR "%y")
string(TIMESTAMP DAY "%d")
string(TIMESTAMP MONTH "%m")
MATH(EXPR VER_MAJOR "0 + ${YEAR}")
MATH(EXPR VER_MINOR "0 + ${MONTH}")
MATH(EXPR VER_FIX "0 + ${DAY}")
set(VERSION "${VER_MAJOR}.${VER_MINOR}.${VER_FIX}")

# Compile definitions and includes
target_compile_definitions(${XEEN_EXECUTABLE} PRIVATE WorldOfXeen_VERSION="${VERSION}")
include_directories(include/ Tools/gifd_tools/)

# Link libraries
target_link_libraries(${XEEN_EXECUTABLE} ace)

# Compiler options
target_compile_options(${XEEN_EXECUTABLE} PUBLIC -fomit-frame-pointer)

# Debug configuration
if(GAME_DEBUG)
    target_compile_definitions(${XEEN_EXECUTABLE} PRIVATE GAME_DEBUG)
    target_compile_definitions(ace PUBLIC ACE_DEBUG_ALL ACE_DEBUG_UAE)
endif()

# Directory setup
set(RES_DIR ${CMAKE_CURRENT_LIST_DIR}/assets)
set(DATA_DIR ${CMAKE_CURRENT_BINARY_DIR}/data)
set(GEN_DIR ${CMAKE_CURRENT_BINARY_DIR}/generated)

# Custom target for processing assets
add_custom_target(process_assets
    COMMAND ${CMAKE_COMMAND} -E echo "Setting up asset conversion tools..."
    COMMAND python3 -m pip install -r ${CMAKE_CURRENT_SOURCE_DIR}/Tools/requirements.txt
    COMMAND ${CMAKE_COMMAND} -E echo "Testing asset conversion tools..."
    COMMAND python3 ${CMAKE_CURRENT_SOURCE_DIR}/Tools/test_tools.py
    WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
    COMMENT "Setting up and testing asset conversion tools"
)

# Custom target for converting game assets (requires user-provided data)
add_custom_target(convert_assets
    COMMAND ${CMAKE_COMMAND} -E echo "Asset conversion requires user-provided World of Xeen data."
    COMMAND ${CMAKE_COMMAND} -E echo "Usage: python3 Tools/xeen_convert_batch.py --input <path_to_game_data> --output <output_dir>"
    WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
    COMMENT "Asset conversion instructions"
)

# Generating ZIP
set(WorldOfXeen_ZIP_NAME "${CMAKE_PROJECT_NAME} ${VER_MAJOR}_${VER_MINOR}_${VER_FIX}")
add_custom_target(generateZip COMMAND
    ${CMAKE_COMMAND} -E tar "cf" "${WorldOfXeen_ZIP_NAME}.zip" --format=zip
    "${CMAKE_CURRENT_BINARY_DIR}/${XEEN_OUTPUT_EXECUTABLE}" "${DATA_DIR}"
    COMMENT "Generating ${WorldOfXeen_ZIP_NAME}.zip"
)

# Generating ADF
set(ADF_DIR "${CMAKE_CURRENT_BINARY_DIR}/adf")
add_custom_target(generateAdf
    COMMAND ${CMAKE_COMMAND} -E make_directory "${ADF_DIR}/s"
    COMMAND ${CMAKE_COMMAND} -E copy "${CMAKE_CURRENT_BINARY_DIR}/${XEEN_OUTPUT_EXECUTABLE}" "${ADF_DIR}"
    COMMAND ${CMAKE_COMMAND} -E copy_directory "${DATA_DIR}" "${ADF_DIR}/data"
    COMMAND ${CMAKE_COMMAND} -E echo "${XEEN_OUTPUT_EXECUTABLE}" > "${ADF_DIR}/s/startup-sequence"
    COMMAND exe2adf -l ${CMAKE_PROJECT_NAME} -a "${CMAKE_PROJECT_NAME}.adf" -d ${ADF_DIR}
    COMMAND ${CMAKE_COMMAND} -E rm -rf "${ADF_DIR}"
    COMMENT "Generating ADF file"
)

# Print configuration summary
message(STATUS "")
message(STATUS "Configuration Summary:")
message(STATUS "  Project: ${CMAKE_PROJECT_NAME} v${VERSION}")
message(STATUS "  Build Type: ${CMAKE_BUILD_TYPE}")
message(STATUS "  Target: Amiga (m68k)")
message(STATUS "  ACE Engine: Local subdirectory")
message(STATUS "  ACE AGA Features: ${ACE_USE_AGA_FEATURES}")
message(STATUS "") 