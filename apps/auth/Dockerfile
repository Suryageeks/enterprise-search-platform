FROM eclipse-temurin:21-jre

WORKDIR /app

COPY target/*.jar application.jar

EXPOSE 8082

ENTRYPOINT ["java", "-jar", "/app/application.jar"]