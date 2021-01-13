# Copyright 2020 the .NET Foundation
# Licensed under the MIT License

FROM ubuntu:20.04 AS build

ARG astrometry_net_version=0.82

# First stanza strongly derived from the astrometry.net Dockerfile.

ENV DEBIAN_FRONTEND=noninteractive

RUN apt -y update \
    && apt install -y apt-utils \
    && apt install -y --no-install-recommends \
        build-essential \
        curl \
        gcc \
        git \
        file \
        libbz2-dev \
        libcairo2-dev \
        libcfitsio-bin \
        libcfitsio-dev \
        libgsl-dev \
        libjpeg-dev \
        libnetpbm10-dev \
        libpng-dev \
        make \
        netpbm \
        pkg-config \
        python3 \
        python3-dev \
        python3-matplotlib \
        python3-numpy \
        python3-pip \
        python3-pil \
        python3-scipy \
        python3-setuptools \
        python3-tk \
        python3-wheel \
        swig \
        wcslib-dev \
        wcslib-tools \
        wget \
        zlib1g-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

RUN for x in \
        fitsio \
        astropy \
        pyavm \
        sep \
        toasty \
    ; do pip3 install --no-cache-dir $x; done

RUN mkdir /src
WORKDIR /src

RUN wget https://github.com/dstndstn/astrometry.net/releases/download/${astrometry_net_version}/astrometry.net-${astrometry_net_version}.tar.gz \
    && tar xzf astrometry.net-${astrometry_net_version}.tar.gz \
    && rm -f astrometry.net-${astrometry_net_version}.tar.gz \
    && mv astrometry.net-* astrometry \
    && cd astrometry \
    && make \
    && make py \
    && make extra \
    && make install INSTALL_DIR=/usr/local \
    && make clean

RUN ln -s /usr/bin/python3 /usr/bin/python
ENV mv /usr/local/lib/python/astrometry /usr/local/lib/python3.8/site-packages/

# Now our Python package

COPY . /src/wwt-aligner
RUN cd /src/wwt-aligner && pip3 install --no-cache-dir .

# Transfer to a new runtime image

FROM ubuntu:20.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt -y update \
    && apt install -y apt-utils \
    && apt install -y --no-install-recommends \
        curl \
        file \
        libbz2-1.0 \
        libcairo2 \
        libcfitsio-bin \
        libgsl23 \
        libjpeg8 \
        libnetpbm10 \
        libpng16-16 \
        netpbm \
        python3 \
        python3-matplotlib \
        python3-numpy \
        python3-pip \
        python3-pil \
        python3-scipy \
        python3-setuptools \
        python3-tk \
        python3-wheel \
        wcslib-tools \
        wget \
        zlib1g \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

COPY --from=build /usr/local /usr/local
RUN ln -s /usr/bin/python3 /usr/bin/python
CMD ["wwt-aligner-agent"]
