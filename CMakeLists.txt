cmake_minimum_required(VERSION 3.10)
project(vie)

# Find necessary packages
find_package(gRPC REQUIRED)
find_package(Protobuf REQUIRED)
find_package(Python3 COMPONENTS Interpreter REQUIRED)

# Include directories
include_directories(${CMAKE_CURRENT_BINARY_DIR})

# Enable testing
enable_testing()

# Protobuf and gRPC generation for Python persistence service
add_custom_command(
    OUTPUT ${CMAKE_SOURCE_DIR}/python_services/persistence/persistence_pb2.py
           ${CMAKE_SOURCE_DIR}/python_services/persistence/persistence_pb2_grpc.py
    COMMAND Python3::Interpreter -m grpc_tools.protoc
            -I ${CMAKE_SOURCE_DIR}/python_services/protos
            --python_out=${CMAKE_SOURCE_DIR}/python_services
            --grpc_python_out=${CMAKE_SOURCE_DIR}/python_services 
            persistence/persistence.proto
    DEPENDS ${CMAKE_SOURCE_DIR}/python_services/protos/persistence/persistence.proto
    COMMENT "Generating gRPC and Protobuf code for Python Persistence Service"
)

# Protobuf and gRPC generation for Python terrain generation service
add_custom_command(
    OUTPUT ${CMAKE_SOURCE_DIR}/python_services/terrain_generation/terrain_generation_pb2.py
           ${CMAKE_SOURCE_DIR}/python_services/terrain_generation/terrain_generation_pb2_grpc.py
    COMMAND Python3::Interpreter -m grpc_tools.protoc
            -I ${CMAKE_SOURCE_DIR}/python_services/protos
            --python_out=${CMAKE_SOURCE_DIR}/python_services
            --grpc_python_out=${CMAKE_SOURCE_DIR}/python_services
            terrain_generation/terrain_generation.proto
    DEPENDS ${CMAKE_SOURCE_DIR}/python_services/protos/terrain_generation/terrain_generation.proto
    COMMENT "Generating gRPC and Protobuf code for Python Terrain Generation Service"
)

# Add custom target to generate protobufs
add_custom_target(generate_protos ALL
                  DEPENDS ${CMAKE_SOURCE_DIR}/python_services/persistence/persistence_pb2.py
                          ${CMAKE_SOURCE_DIR}/python_services/persistence/persistence_pb2_grpc.py
                          ${CMAKE_SOURCE_DIR}/python_services/terrain_generation/terrain_generation_pb2.py
                          ${CMAKE_SOURCE_DIR}/python_services/terrain_generation/terrain_generation_pb2_grpc.py)

# Add custom target to recreate the .context file
add_custom_target(context
                  COMMAND ${CMAKE_COMMAND} -E env python ${CMAKE_SOURCE_DIR}/script/generate_context.py
                  WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
                  COMMENT "Recreating .context files")

# Add custom target to generate and optionally display Doxygen documentation
find_package(Doxygen REQUIRED)
if(DOXYGEN_FOUND)
    set(DOXYGEN_IN ${CMAKE_SOURCE_DIR}/Doxyfile)
    set(DOXYGEN_OUT ${CMAKE_BINARY_DIR}/Doxyfile)
    configure_file(${DOXYGEN_IN} ${DOXYGEN_OUT} @ONLY)
    add_custom_target(docs
                      COMMAND ${DOXYGEN_EXECUTABLE} ${DOXYGEN_OUT}
                      WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
                      COMMENT "Generating API documentation with Doxygen"
                      VERBATIM)

    add_custom_target(show_docs
                      COMMAND ${DOXYGEN_EXECUTABLE} ${DOXYGEN_OUT}
                      COMMAND ${CMAKE_COMMAND} -E env bash ${CMAKE_SOURCE_DIR}/script/show_docs.sh
                      WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
                      COMMENT "Generating and displaying API documentation with Doxygen"
                      VERBATIM)
endif()

# Add custom target to run Python unit tests
add_custom_target(run_tests
                  COMMAND ${CMAKE_COMMAND} -E env PYTHONPATH=${CMAKE_SOURCE_DIR}/python_services pytest --cov=vie/python_services --cov-report=html --cov-report=xml -v ${CMAKE_SOURCE_DIR}/python_services/
                  WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}/python_services/
                  COMMENT "Running Python unit tests with coverage")
