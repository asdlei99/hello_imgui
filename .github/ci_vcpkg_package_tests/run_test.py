import subprocess
import platform
import os
import sys
import shutil

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.abspath(os.path.join(THIS_DIR, "..", ".."))

FAILING_TESTS_MESSAGES = []
SUCCESSES_RUN = []
SUCCESSES_BUILD = []


def run_test_with_rendering_backend(rendering_backend: str) -> bool:
    platform_backends = ["SDL", "GLFW"]

    print("Running test with rendering backend: " + rendering_backend)
    print("-------------------------------------------------")
    build_dir = f"build-{rendering_backend}"
    os.chdir(THIS_DIR)
    if os.path.exists(build_dir):
        shutil.rmtree(build_dir)
    os.mkdir(build_dir)
    os.chdir(build_dir)

    if "VCPKG_ROOT" in os.environ:
        vcpkg_root = os.environ["VCPKG_ROOT"]
    elif "VCPKG_INSTALLATION_ROOT" in os.environ:
        vcpkg_root = os.environ["VCPKG_INSTALLATION_ROOT"]
    else:
        vcpkg_root = f"{REPO_DIR}/vcpkg"
    vcpkg_program = os.path.join(vcpkg_root, "vcpkg")

    if platform.system() == "Linux":
        os.environ["DISPLAY"] = ":99.0"

    overlay_dir = f"{REPO_DIR}/hello_imgui_cmake/overlay_vcpkg/hello-imgui"
    cmake_toolchain_file = os.path.join(vcpkg_root, "scripts/buildsystems/vcpkg.cmake")

    vcpkg_remove_cmd = f'{vcpkg_program} remove hello-imgui --recurse'
    vcpkg_install_cmd = f'{vcpkg_program} install "hello-imgui[{rendering_backend}, glfw-binding, sdl2-binding]" --overlay-ports={overlay_dir} --recurse'
    cmake_cmd = f"cmake -DCMAKE_TOOLCHAIN_FILE={cmake_toolchain_file} .."
    build_cmd = f"cmake --build . --config Release"
    test_app_glfw_cmd = "./ci_vcpkg_package_tests_app glfw"
    test_app_sdl_cmd = "./ci_vcpkg_package_tests_app sdl"

    success = True
    cmds = {
        "vcpkg remove hello_imgui": vcpkg_remove_cmd,
        f"vcpkg install hello_imgui {rendering_backend}": vcpkg_install_cmd,
        f"run cmake {rendering_backend}": cmake_cmd,
        f"run build {rendering_backend}": build_cmd,
    }

    # Only run app with selected platform backends
    if rendering_backend != "vulkan-binding" and platform.system() != "Darwin":
        cmds[f"run test app (Glfw - {rendering_backend})"] = test_app_glfw_cmd,
        cmds[f"run test app (SDL - {rendering_backend})"] = test_app_sdl_cmd,

    for name, cmd in cmds.items():
        print(f"""
        ****************************************************************************************************
        Running {name} 
        Rendering backend: {rendering_backend}
        Command:
        {cmd}
        ****************************************************************************************************
        """)
        try:
            subprocess.run(cmd, shell=True, check=True)
            if name.startswith("run test app"):
                SUCCESSES_RUN.append(name)
            if name.startswith("run build"):
                SUCCESSES_BUILD.append(name)
        except subprocess.CalledProcessError as e:
            message = f"""
            ****************************************************************************************************
            Failed to run {name}
            Rendering backend: {rendering_backend}
            Command:
            {cmd}
            with error: 
            {e}
            ****************************************************************************************************
            """
            FAILING_TESTS_MESSAGES.append(message)
            print(message)
            success = False
    return success


def prepare_display():
    if platform.system() == "Linux":
        subprocess.run("Xvfb :99 -screen 0 1024x768x24 > /dev/null 2>&1 &", shell=True, check=True)


def run_tests():
    prepare_display()
    rendering_backends = ["opengl3-binding", "vulkan-binding"]
    if platform.system() == "Windows":
        rendering_backends.append("dx11-binding")
        rendering_backends.append("dx12-binding")
    elif platform.system() == "Darwin":
        rendering_backends.append("metal-binding")

    all_success = True
    for backend in rendering_backends:
        success = run_test_with_rendering_backend(backend)
        all_success = all_success and success

    all_successes_run_str = "\n        ".join(SUCCESSES_RUN)
    all_successes_build_str = "\n        ".join(SUCCESSES_BUILD)
    print(f"""
    ****************************************************************************************************
    All tests finished
    Successful Runs: 
        {all_successes_run_str}
    Successful Builds:
        {all_successes_build_str}
    ****************************************************************************************************
    """)
    if all_success:
        print("All tests passed")
        sys.exit(0)
    else:
        all_failures_str = "\n    ".join(FAILING_TESTS_MESSAGES)
        print(f"""
        !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        Some tests failed
        Failures:
        {all_failures_str}
        !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        """)
        sys.exit(1)


if __name__ == "__main__":
    run_tests()