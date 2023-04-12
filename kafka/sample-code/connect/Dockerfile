FROM confluentinc/cp-kafka-connect:7.0.9 as cp
RUN confluent-hub install --no-prompt confluentinc/kafka-connect-s3:10.4.2
RUN confluent-hub install --no-prompt confluentinc/kafka-connect-avro-converter:7.3.3
FROM quay.io/strimzi/kafka:0.34.0-kafka-3.4.0
USER root:root
# Add S3 dependency
COPY --from=cp /usr/share/confluent-hub-components/confluentinc-kafka-connect-s3/ /opt/kafka/plugins/kafka-connect-s3/
# Add Avro dependency
COPY --from=cp /usr/share/confluent-hub-components/confluentinc-kafka-connect-avro-converter/ /opt/kafka/plugins/avro/
