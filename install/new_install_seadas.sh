# note that this assumes the install script has been downloaded (handled by the Dockerfile)
# also only installs the 9.1.0 version, the 7.5.3 version is installed directly in the Dockerfile

echo "Installing SeaDAS 9.1.0"

yes $'1\n1\n\n\n1\nn' | bash ./install/seadas_9.1.0_linux64_installer.sh