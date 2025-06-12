FROM --platform=linux/amd64 ubuntu:20.04

# Avoid warnings by switching to noninteractive
ENV DEBIAN_FRONTEND=noninteractive

# Configure apt and install packages
RUN apt-get update \
    && apt-get -y install --no-install-recommends \
        git \
        curl \
        wget \
        build-essential \
        python3 \
        python3-pip \
        python3-dev \
        python3-venv \
        vim \
        less \
        gdal-bin \
        openjdk-8-jre \
    && apt-get clean -y \
    && rm -rf /var/lib/apt/lists/*

# Switch back to dialog for any ad-hoc use of apt-get
ENV DEBIAN_FRONTEND=dialog

# Set up Python environment
RUN python3 -m pip install --upgrade pip \
    && python3 -m pip install \
        ipython \
        pytest \
        black \
        flake8 

WORKDIR /workspace

RUN pip3 install requests numpy matplotlib netCDF4

COPY . .

# # install seadas v9.1.0
RUN curl -o install/seadas_9.1.0_linux64_installer.sh https://oceandata.sci.gsfc.nasa.gov/directdataaccess/SeaDAS/installer/9.1.0/seadas_9.1.0_linux64_installer.sh
RUN bash install/new_install_seadas.sh

# install ocssw
RUN chmod +x ./install/install_ocssw

RUN mkdir /root/SeaDAS/ocssw
RUN ./install/install_ocssw --install_dir=/root/SeaDAS/ocssw --tag T2024.16 --seadas --avhrr --czcs --goci --hawkeye --hico --meris --modisa --modist --mos --ocm1 --ocm2 --octs --olcis3a --olil8 --olil9 --osmi --seawifs --sgli --viirsn --viirsj1 --olcis3b

RUN echo "export PATH=$PATH:/root/SeaDAS/bin" >> ~/.bashrc
RUN echo "export OCSSWROOT=/root/SeaDAS/ocssw" >> ~/.bashrc
RUN echo "source /root/SeaDAS/ocssw/OCSSW_bash.env" >> ~/.bashrc

# install old seadas (requires java 8)
RUN curl -o install/seadas_7.5.3_linux64_installer.sh https://oceandata.sci.gsfc.nasa.gov/directdataaccess/SeaDAS/installer/7.5.3/seadas_7.5.3_linux64_installer.sh
RUN bash install/seadas_7.5.3_linux64_installer.sh -q 