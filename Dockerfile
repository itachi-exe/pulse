FROM rust:1.75-slim as builder

WORKDIR /app
COPY Cargo.toml Cargo.lock* ./
COPY src ./src

RUN apt-get update && apt-get install -y pkg-config libssl-dev && rm -rf /var/lib/apt/lists/*
RUN cargo build --release

FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y libssl3 ca-certificates && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /app/target/release/pulse ./pulse

ENV RUST_LOG=pulse=info
ENV REDIS_URL=redis://redis:6379
ENV BIND_ADDR=0.0.0.0:7070

EXPOSE 7070
CMD ["./pulse"]
