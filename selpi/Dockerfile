ARG BUILD_FROM
FROM ${BUILD_FROM}
# selpi itself (protocol library, web UI, API, SP LINK proxy) comes from the selpi fork at a fixed tag
ARG SELPI_REF=v0.9.0
ADD https://github.com/TesseractTimmee/selpi/archive/refs/tags/${SELPI_REF}.tar.gz /tmp/selpi.tar.gz
RUN pip3 install --no-cache-dir python-dotenv==1.1.1 pyserial==3.5 \
 && mkdir -p /tmp/src /opt/selpi && tar -xzf /tmp/selpi.tar.gz -C /tmp/src --strip-components=1 \
 && cd /tmp/src && cp -r connection memory sppro web commands exception.py settings.py \
      muster.py __init__.py selpi.py LICENSE.md /opt/selpi/ \
 && rm -rf /tmp/src /tmp/selpi.tar.gz
COPY run.sh /run.sh
RUN chmod a+x /run.sh
WORKDIR /opt/selpi
CMD [ "/run.sh" ]
