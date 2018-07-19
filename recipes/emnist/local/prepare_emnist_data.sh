#!/bin/bash

# Prepare the EMNIST dataset.

url=http://www.itl.nist.gov/iaui/vip/cs_links/EMNIST/gzip.zip
batch_size=1000
outdir=data

# Download the data
if [ ! -f "${outdir}/gzip.zip" ]; then
    mkdir -p ${outdir}
    wget $url -P "${outdir}" || exit 1
else
    echo "Data already downloaded. Skipping."
fi

# Extract and prepare the data.
if [ ! -f "${outdir}/.done" ]; then
    mkdir -p "${outdir}"/rawdata
    mkdir -p "${outdir}"/letters/train "${outdir}"/letters/test
    mkdir -p "${outdir}"/digits/train "${outdir}"/digits/test

    # Extract the letters data set.
    unzip -p ${outdir}/gzip.zip gzip/emnist-letters-train-images-idx3-ubyte.gz | \
        gunzip > "${outdir}/rawdata/emnist-letters-train-images.raw" || exit 1
    unzip -p ${outdir}/gzip.zip gzip/emnist-letters-train-labels-idx1-ubyte.gz | \
        gunzip > "${outdir}/rawdata/emnist-letters-train-labels.raw" || exit 1
    unzip -p ${outdir}/gzip.zip gzip/emnist-letters-test-images-idx3-ubyte.gz | \
        gunzip > "${outdir}/rawdata/emnist-letters-test-images.raw" || exit 1
    unzip -p ${outdir}/gzip.zip gzip/emnist-letters-test-labels-idx1-ubyte.gz | \
        gunzip > "${outdir}/rawdata/emnist-letters-test-labels.raw" || exit 1

    python local/raw2npz.py \
        --batch-size ${batch_size} \
        "${outdir}/rawdata/emnist-letters-train-images.raw" \
        "${outdir}/rawdata/emnist-letters-train-labels.raw" \
        "${outdir}/letters/train" || exit 1
    find "${outdir}/letters/train" \
        -name 'batch*npz' | sort -V > "${outdir}/letters/train/archives" || exit 1

    python local/raw2npz.py \
        --batch-size ${batch_size} \
        "${outdir}/rawdata/emnist-letters-train-images.raw" \
        "${outdir}/rawdata/emnist-letters-train-labels.raw" \
        "${outdir}/letters/test" || exit 1
    find "${outdir}/letters/test" \
        -name 'batch*npz' | sort -V > "${outdir}/letters/test/archives" || exit 1

    # Extract the digits data set.
    unzip -p ${outdir}/gzip.zip gzip/emnist-digits-train-images-idx3-ubyte.gz | \
        gunzip > "${outdir}/rawdata/emnist-digits-train-images.raw" || exit 1
    unzip -p ${outdir}/gzip.zip gzip/emnist-digits-train-labels-idx1-ubyte.gz | \
        gunzip > "${outdir}/rawdata/emnist-digits-train-labels.raw" || exit 1
    unzip -p ${outdir}/gzip.zip gzip/emnist-digits-test-images-idx3-ubyte.gz | \
        gunzip > "${outdir}/rawdata/emnist-digits-test-images.raw" || exit 1
    unzip -p ${outdir}/gzip.zip gzip/emnist-digits-test-labels-idx1-ubyte.gz | \
        gunzip > "${outdir}/rawdata/emnist-digits-test-labels.raw" || exit 1

    python local/raw2npz.py \
        --batch-size ${batch_size} \
        "${outdir}/rawdata/emnist-digits-train-images.raw" \
        "${outdir}/rawdata/emnist-digits-train-labels.raw" \
        "${outdir}/digits/train" || exit 1
    find "${outdir}/digits/train" \
        -name 'batch*npz' | sort -V > "${outdir}/digits/train/archives" || exit 1

    python local/raw2npz.py \
        --batch-size ${batch_size} \
        "${outdir}/rawdata/emnist-digits-test-images.raw" \
        "${outdir}/rawdata/emnist-digits-test-labels.raw" \
        "${outdir}/digits/test" || exit 1
    find "${outdir}/digits/test" \
        -name 'batch*npz' | sort -V > "${outdir}/digits/test/archives" || exit 1

    rm -fr "${outdir}/rawdata" || exit 1

    date > "${outdir}/.done"
else
    echo "Data already prepared. Skipping."
fi