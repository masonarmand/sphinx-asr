################################
# Build Image
################################
FROM debian:bookworm-slim AS builder

# Install Dependencies
RUN apt-get update && apt-get install -y \
        build-essential \
        cmake \
        perl \
        python3 \
        && rm -rf /var/lib/apt/lists/*

# Build pocketsphinx
COPY vendor/pocketsphinx /build/pocketsphinx
WORKDIR /build/pocketsphinx
RUN cmake -S . -B build \
        && cmake --build build \
        && cmake --build build --target install

# Build sphinxtrain
COPY vendor/sphinxtrain /build/sphinxtrain
WORKDIR /build/sphinxtrain
RUN cmake -S . -B build \
        && cmake --build build \
        && cp /build/pocketsphinx/build/pocketsphinx_batch /build/sphinxtrain/build/

################################
# Final Image
################################
FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y \
        perl \
        python3 \
        sox \
    && rm -rf /var/lib/apt/lists/*

# copy only the files we need
COPY --from=builder /usr/local/bin/pocketsphinx /usr/local/bin/
COPY --from=builder /usr/local/bin/pocketsphinx_batch /usr/local/bin/
COPY --from=builder /usr/local/bin/pocketsphinx_lm_convert /usr/local/bin/
COPY --from=builder /usr/local/share/pocketsphinx/ /usr/local/share/pocketsphinx/
COPY --from=builder /build/sphinxtrain/build/ /opt/sphinxtrain/bin/
COPY --from=builder /build/sphinxtrain/scripts/ /opt/sphinxtrain/scripts/
COPY --from=builder /build/sphinxtrain/etc/ /opt/sphinxtrain/etc/

RUN ldconfig

# copy project scripts
COPY parsers/ /app/parsers/
COPY scripts/ /app/scripts/

WORKDIR /app

CMD ["/bin/bash"]
