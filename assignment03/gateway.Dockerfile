# Stage 1: Build
FROM rust:1.85-slim as builder
WORKDIR /app
COPY . .
RUN cargo build --release

# Stage 2: Run
FROM debian:bookworm-slim
WORKDIR /app
COPY --from=builder /app/target/release/assignment03 .
# Ensure libssl is available for reqwest
RUN apt-get update && apt-get install -y libssl3 ca-certificates && rm -rf /var/lib/apt/lists/*
CMD ["./assignment03"]