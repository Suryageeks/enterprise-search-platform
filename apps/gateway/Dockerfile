FROM traefik:v3.3

COPY --chown=65532:65532 traefik/traefik.yml /etc/traefik/traefik.yml
COPY --chown=65532:65532 traefik/dynamic.yml /etc/traefik/dynamic.yml

USER 65532:65532

EXPOSE 9080 9081

CMD ["--configFile=/etc/traefik/traefik.yml"]
