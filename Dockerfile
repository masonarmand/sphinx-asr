FROM debian:bookworm-slim

################################
# Install Dependencies
################################
RUN apt-get update && apt-get install -y \
        build-essential \
        cmake \
        perl \
        python3 \
        ffmpeg \
        && rm -rf /var/lib/apt/lists/*

################################
# Build pocketsphinx
################################
COPY vendor/pocketsphinx /build/pocketsphinx
WORKDIR /build/pocketsphinx
RUN cmake -S . -B build \
        && cmake --build build \
        && cmake --build build --target install

################################
# Build sphinxtrain
################################
COPY vendor/sphinxtrain /build/sphinxtrain
WORKDIR /build/sphinxtrain
RUN cmake -S . -B build \
        && cmake --build build

# sphinxtrain needs poceksphinx_batch
RUN cp /build/pocketsphinx/build/pocketsphinx_batch \
        /build/sphinxtrain/build/

# copy project scripts
COPY parsers/ /app/parsers/
COPY scripts/ /app/scripts/

WORKDIR /app

# mount points
VOLUME ["/app/corpus", "/app/features", "/app/experiments"]

CMD ["/bin/bash"]
