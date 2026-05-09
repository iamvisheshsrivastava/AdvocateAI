ARG FLUTTER_VERSION=3.41.8

FROM ghcr.io/cirruslabs/flutter:${FLUTTER_VERSION} AS build

WORKDIR /app

COPY test_app/pubspec.yaml test_app/pubspec.lock ./
RUN flutter pub get

COPY test_app ./

ARG API_BASE_URL=
RUN flutter build web --release --dart-define=API_BASE_URL=${API_BASE_URL}

FROM nginx:1.27-alpine

COPY test_app/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/build/web /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -qO- http://127.0.0.1/ >/dev/null || exit 1
