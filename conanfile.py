import os
from conans import ConanFile, CMake, AutoToolsBuildEnvironment, tools
from conans.util import files


class LibrdkafkaConan(ConanFile):
    name = "libpulsar"
    sha256 = "3a365368f0d7beba091ba3a6d0f703dcc77545c8b454e5e33b72c1a29905232e"

    src_version = "2.2.1"
    version = src_version
    license = "BSD 2-Clause"
    url = "https://github.com/aahmed/conan-pulsar"
    description = "The Apache Pulsar C/C++ library"
    settings = "os", "compiler", "build_type", "arch"
    build_requires = "cmake_installer/3.13.3@conan/stable"
    options = {"shared": [True, False]}
    default_options = "shared=False"
    exports = "files/*"
    requires = "jsoncpp/1.8.4@theirix/stable"
    requires = "OpenSSL/1.0.2q@conan/stable"
    requires = "protobuf/3.5.1@zimmerk/stable"

    folder_name = "{}-{}".format(name, src_version)
    archive_name = "{}.tar.gz".format(folder_name)

    # For Windows use short paths (ignored for other OS's)
    short_paths=True

    def source(self):
        tools.download(
            "https://www.apache.org/dyn/closer.cgi?path=pulsar/pulsar-{}apache-pulsar-{}-src.tar.gz".format(
                self.src_version
            ),
            self.archive_name
        )
        tools.check_sha256(
            self.archive_name,
            self.sha256
        )
        tools.unzip(self.archive_name)
        os.unlink(self.archive_name)

    def build(self):
        if tools.os_info.is_windows:
            files.mkdir("./{}/build".format(self.folder_name))
            with tools.chdir("./{}/build".format(self.folder_name)):
                cmake = CMake(self)

                cmake.definitions["BUILD_TESTS"] = "OFF"
                cmake.definitions["LINK_STATIC"] = "ON"
                cmake.definitions["PYTHON_INCLUDE_DIR"] = "/usr/local/Frameworks/Python.framework/Versions/2.7/include/python2.7/"

                if self.settings.build_type == "Debug":
                    cmake.definitions["WITHOUT_OPTIMIZATION"] = "ON"
                if self.options.shared:
                    cmake.definitions["BUILD_SHARED_LIBS"] = "ON"

                # Enables overridding of default window build settings
                cmake.definitions["WITHOUT_WIN32_CONFIG"] = "ON"

                cmake.configure(source_dir="..", build_dir=".")
                cmake.build(build_dir=".")
        else:
            configure_args = [
                "--prefix=",
                "--disable-lz4",
                "--disable-ssl",
                "--disable-sasl"
            ]

            if self.options.shared:
                ldflags = os.environ.get("LDFLAGS", "")
                if tools.os_info.is_linux:
                    os.environ["LDFLAGS"] = ldflags
                elif tools.os_info.is_macos:
                    os.environ["LDFLAGS"] = ldflags + " -headerpad_max_install_names"
            else:
                configure_args.append("--enable-static")

            if self.settings.build_type == "Debug":
                configure_args.append("--disable-optimization")

            destdir = os.path.join(os.getcwd(), "install")
            with tools.chdir(self.folder_name):
                if tools.os_info.is_macos and self.options.shared:
                    path = os.path.join(os.getcwd(), "mklove", "modules", "configure.lib")
                    tools.replace_in_file(
                        path,
                         '-dynamiclib -Wl,-install_name,$(DESTDIR)$(libdir)/$(LIBFILENAME)',
                         '-dynamiclib -Wl,-install_name,@rpath/$(LIBFILENAME)',
                    )

                env_build = AutoToolsBuildEnvironment(self)
                env_build.configure(args=configure_args)
                env_build.make()
                env_build.make(args=["install", "DESTDIR="+destdir])

        with tools.chdir(self.folder_name):
            os.rename("LICENSE", "LICENSE.libpulsar")

    def package(self):
        if tools.os_info.is_windows:
            self.copy("libpulsar.h", dst="include/libpulsar",
                      src="{}/src".format(self.folder_name))
            self.copy("*.dll", dst="bin", keep_path=False)
            self.copy("*.lib", dst="lib", keep_path=False)
            self.copy("LICENSE.*", src=self.folder_name)
        else:
            install_folder = os.path.join(self.build_folder, "install")
            self.copy("*.h", src=install_folder)
            if self.options.shared:
                if tools.os_info.is_linux:
                    self.copy("*.so*", src=install_folder)
                elif tools.os_info.is_macos:
                    self.copy("*.dylib*", src=install_folder)
            else:
                self.copy("*.a", src=install_folder)
            self.copy("LICENSE.*", src=self.folder_name)

    def package_info(self):
        self.cpp_info.libs = ["libpulsar"]
