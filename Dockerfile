FROM alpine:latest

ARG TESSDATA_CHECKSUM=990fffb9b7a9b52dc9a2d053a9ef6852ca2b72bd8dfb22988b0b990a700fd3c7

# Install dependencies
RUN apk -U upgrade && \
    apk add \
    ghostscript \
    graphicsmagick \
    libreoffice \
    openjdk8 \
    poppler-utils \
    poppler-data \
    python3 \
    py3-magic \
    tesseract-ocr

# Download the trained models from the latest GitHub release of Tesseract, and
# store them under /usr/share/tessdata. This is basically what distro packages
# do under the hood.
#
# Because the GitHub release contains more files than just the trained models,
# we use `find` to fetch only the '*.traineddata' files in the top directory.
#
# Before we untar the models, we also check if the checksum is the expected one.
RUN mkdir tessdata && cd tessdata \
    && TESSDATA_VERSION=$(wget -O- -nv https://api.github.com/repos/tesseract-ocr/tessdata/releases/latest \
        | sed -n 's/^.*"tag_name": "\([0-9.]\+\)".*$/\1/p') \
    && apk --purge del jq \
    && wget https://github.com/tesseract-ocr/tessdata/archive/$TESSDATA_VERSION/tessdata-$TESSDATA_VERSION.tar.gz \
    && echo "$TESSDATA_CHECKSUM  tessdata-$TESSDATA_VERSION.tar.gz" | sha256sum -c \
    && tar -xzvf tessdata-$TESSDATA_VERSION.tar.gz -C . \
    && find . -name '*.traineddata' -maxdepth 2 -exec cp {} /usr/share/tessdata \; \
    && cd .. && rm -r tessdata

COPY conversion/common.py /usr/local/bin/
COPY conversion/pixels_to_pdf.py /usr/local/bin/
COPY conversion/doc_to_pixels.py /usr/local/bin/

# Add the unprivileged user
RUN adduser -s /bin/sh -D dangerzone
USER dangerzone

# /tmp/input_file is where the first convert expects the input file to be, and
# /tmp where it will write the pixel files
#
# /dangerzone is where the second script expects files to be put by the first one
#
# /safezone is where the wrapper eventually moves the sanitized files.
VOLUME /dangerzone /tmp/input_file /safezone
